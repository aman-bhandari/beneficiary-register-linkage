"""HTTP API for the governance platform. Every read goes through `Session`, which folds the officer's posting into
the SQL, masks identity fields, and writes the access to the audit log.

Demo identities: send header `X-Role: <role key>` (see /api/roles). In a deployment this is the login.

    uvicorn api.main:app --port 8003
"""
from __future__ import annotations

import csv
import io
import json
import re
import threading
from pathlib import Path

import duckdb
import yaml
from fastapi import FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .governance import ROLES, Audit, Role, mask_fields, mask_name, scope_sql

ROOT = Path(__file__).resolve().parent.parent
WAREHOUSE = ROOT / "data" / "warehouse.duckdb"
RULES = yaml.safe_load((ROOT / "rules" / "schemes.yaml").read_text())
UI = ROOT / "ui" / "dist"

app = FastAPI(title="Ekatra — integrated beneficiary data governance", version="1.0")
audit = Audit()
_local = threading.local()


def db() -> duckdb.DuckDBPyConnection:
    """One read-only connection per worker thread."""
    if getattr(_local, "con", None) is None:
        if not WAREHOUSE.exists():
            raise HTTPException(503, "warehouse not built: run ./run.sh build")
        _local.con = duckdb.connect(str(WAREHOUSE), read_only=True)
    return _local.con


def q(sql: str, params: list | None = None) -> list[dict]:
    cur = db().execute(sql, params or [])
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def one(sql: str, params: list | None = None):
    r = db().execute(sql, params or []).fetchone()
    return r[0] if r else None


def role_of(x_role: str | None) -> Role:
    r = ROLES.get(x_role or "")
    if not r:
        raise HTTPException(401, "unknown role: choose one from /api/roles")
    return r


def need(ok: bool, what: str):
    if not ok:
        raise HTTPException(403, f"not permitted for this role: {what}")


def suppress(n: int, role: Role):
    """Aggregate cells below the role's minimum are withheld (returned as None), so no count can single a person out."""
    return None if (role.min_cell and 0 < n < role.min_cell) else n


# ---------------------------------------------------------------------------------------------------------------
@app.get("/api/roles")
def roles():
    return [dict(key=r.key, title=r.title, title_hi=r.title_hi, office=r.office, districts=r.districts,
                 blocks=r.blocks, cases=r.cases, unmask=r.unmask, review=r.review, audit=r.audit, note=r.note)
            for r in ROLES.values()]


@app.get("/api/overview")
def overview(x_role: str | None = Header(None)):
    role = role_of(x_role)
    where, p = scope_sql(role)
    total_cases = one("select count(*) from cases")
    counts = q(f"""select kind, type, case when type = 'two_pensions' then null else scheme end scheme,
                          count(*) n, sum(amount_rs) amount,
                          sum(case when priority='high' then 1 else 0 end) high
                   from cases where {where} group by 1, 2, 3 order by 1, 4 desc""", p)
    people = q(f"""select count(*) people, sum(case when alive then 1 else 0 end) alive,
                          sum(case when pensions is not null and alive then 1 else 0 end) pensioners,
                          sum(records) records from people where {where}""", p)[0]
    in_scope = sum(c["n"] for c in counts)
    audit.log(role.key, "overview", None, {"cases_in_scope": in_scope})
    for c in counts:
        c["n"] = suppress(c["n"], role)
    meta = q("select district, summary from meta")
    return dict(role=role.key, scope=dict(districts=role.districts, blocks=role.blocks),
                cases_in_scope=in_scope if role.cases else None, cases_total=total_cases,
                cases_refused=total_cases - in_scope, counts=counts, people=people,
                districts=[dict(district=m["district"], **{k: v for k, v in json.loads(m["summary"]).items()
                                                        if k in ("households", "persons_alive", "records", "calibration")})
                           for m in meta if not role.districts or m["district"] in role.districts])


CASE_COLS = "case_id, kind, type, scheme, person_key, district, block, panchayat, priority, amount_rs, title"


@app.get("/api/cases")
def cases(x_role: str | None = Header(None), kind: str | None = None, type: str | None = None,
          scheme: str | None = None, block: str | None = None, priority: str | None = None,
          status: str | None = None, page: int = Query(1, ge=1), size: int = Query(50, le=200)):
    role = role_of(x_role)
    need(role.cases, "individual cases")
    where, p = scope_sql(role, "c")
    for col, v in (("kind", kind), ("type", type), ("scheme", scheme), ("block", block), ("priority", priority)):
        if v:
            where += f" and c.{col} = ?"
            p.append(v)
    reviews = audit.reviews()
    if status:
        decided = list(reviews)
        if status == "open":
            where += f" and c.case_id not in (select unnest(?::varchar[]))"
        else:
            decided = [k for k, v in reviews.items() if v["decision"] == status]
            where += f" and c.case_id in (select unnest(?::varchar[]))"
        p.append(decided)
    total = one(f"select count(*) from cases c where {where}", p)
    rows = q(f"""select {', '.join('c.' + x.strip() for x in CASE_COLS.split(','))}, pe.name_hi, pe.name_en, pe.age, pe.sex
                 from cases c left join people pe using (person_key)
                 where {where} order by case c.priority when 'high' then 0 when 'medium' then 1 else 2 end,
                          c.amount_rs desc, c.case_id limit ? offset ?""", p + [size, (page - 1) * size])
    all_filtered = one("select count(*) from cases") - one(f"select count(*) from cases c where {scope_sql(role, 'c')[0]}", scope_sql(role, "c")[1])
    for r in rows:
        unm = audit.is_unmasked(r["case_id"], role.key)
        if not unm:
            r["name_hi"], r["name_en"] = mask_name(r["name_hi"]), mask_name(r["name_en"])
        r["unmasked"] = unm
        r["review"] = reviews.get(r["case_id"])
    audit.log(role.key, "list_cases", None, {"filters": {k: v for k, v in dict(kind=kind, type=type, scheme=scheme, block=block,
                                                                                priority=priority, status=status).items() if v},
                                             "returned": len(rows), "matched": total})
    return dict(total=total, page=page, size=size, rows=rows, refused_by_scope=all_filtered)


def _case(case_id: str, role: Role) -> dict:
    where, p = scope_sql(role, "c")
    rows = q(f"select * from cases c where c.case_id = ? and {where}", [case_id] + p)
    if not rows:
        exists = one("select count(*) from cases where case_id = ?", [case_id])
        audit.log(role.key, "refused", case_id, {"reason": "outside posting" if exists else "no such case"})
        raise HTTPException(404 if not exists else 403, "outside your posting" if exists else "no such case")
    return rows[0]


def _person(person_key: str, role: Role, unmasked: bool) -> dict:
    pe = q("select * from people where person_key = ?", [person_key])[0]
    recs = q("""select record_id, register, department, name, script, birth_year, block, fields from records
                where person_key = ? order by register""", [person_key])
    for r in recs:
        r["fields"] = mask_fields(json.loads(r.pop("fields")), unmasked)
        if not unmasked:
            r["name"] = mask_name(r["name"])
    if not unmasked:
        for k in ("name_hi", "name_en"):
            pe[k] = mask_name(pe[k])
        for k in ("ration_card", "ppo_no", "death_reg"):
            if pe.get(k):
                pe[k] = "•••" + str(pe[k])[-3:]
        if pe.get("widow_evidence"):
            pe["widow_evidence"] = re.sub(r"Husband ([^:]+):", lambda m: f"Husband {mask_name(m.group(1))}:", pe["widow_evidence"])
    for k, v in list(pe.items()):
        if hasattr(v, "isoformat"):
            pe[k] = v.isoformat()
        elif isinstance(v, float) and v != v:
            pe[k] = None
    return dict(person=pe, records=recs, links=_links(person_key))


def _links(person_key: str) -> list[dict]:
    """Why these records were judged to be one person: each pair's match weight and the fields that agreed."""
    model = {m["district"]: json.loads(m["link_model"]) for m in q("select district, link_model from meta")}
    rows = q("select * from link_pairs where person_key = ? order by match_weight desc nulls last limit 40", [person_key])
    district = one("select district from people where person_key = ?", [person_key])
    comps = {c["output_column_name"]: c for c in model.get(district, {}).get("comparisons", [])}
    out = []
    for r in rows:
        parts = []
        for name, c in comps.items():
            gv = r.get(f"gamma_{name}")
            if gv is None or gv == -1:
                continue
            lvl = next((l for l in c["comparison_levels"] if l.get("comparison_vector_value") == gv), None)
            if lvl is None:
                # levels are listed in order: null first, then highest agreement down to 0
                non_null = [l for l in c["comparison_levels"] if not l.get("is_null_level")]
                lvl = non_null[len(non_null) - 1 - gv] if 0 <= gv < len(non_null) else None
            if not lvl:
                continue
            m, u = lvl.get("m_probability"), lvl.get("u_probability")
            import math
            w = round(math.log2(m / u), 1) if m and u else None
            parts.append(dict(field=name.replace("_", " "), level=lvl.get("label_for_charts"), weight=w))
        out.append(dict(record_l=r["record_l"], record_r=r["record_r"], via=r["via"],
                        match_weight=None if r["match_weight"] is None else round(r["match_weight"], 1),
                        match_probability=None if r["match_probability"] is None else round(r["match_probability"], 4),
                        fields=parts))
    return out


@app.get("/api/cases/{case_id}")
def case(case_id: str, x_role: str | None = Header(None)):
    role = role_of(x_role)
    need(role.cases, "individual cases")
    c = _case(case_id, role)
    unm = audit.is_unmasked(case_id, role.key)
    c["trace"] = json.loads(c["trace"])
    c["evidence"] = json.loads(c["evidence"])
    if not unm:
        # document numbers inside the explanation are masked like the records they come from
        hide = lambda t: re.sub(r"\d{6,}", lambda m: "•" * (len(m.group()) - 3) + m.group()[-3:], t) if isinstance(t, str) else t
        for tr in c["trace"]:
            tr["evidence"] = hide(tr.get("evidence"))
        for e in c["evidence"]:
            e["detail"] = hide(e.get("detail"))
    detail = _person(c["person_key"], role, unm)
    audit.log(role.key, "open_case", case_id, {"masked": not unm})
    reviews = audit.reviews([case_id])
    history = [e for e in audit.events(limit=2000) if e["object"] == case_id][:30]
    return dict(case=c, unmasked=unm, review=reviews.get(case_id), history=history, **detail)


class UnmaskBody(BaseModel):
    reason: str = Field(min_length=15, max_length=400)


@app.post("/api/cases/{case_id}/unmask")
def unmask(case_id: str, body: UnmaskBody, x_role: str | None = Header(None)):
    role = role_of(x_role)
    need(role.unmask, "revealing identity")
    _case(case_id, role)
    seq = audit.unmask(case_id, role.key, body.reason.strip())
    return dict(ok=True, audit_seq=seq)


class ReviewBody(BaseModel):
    decision: str = Field(pattern="^(confirmed|not_a_problem|field_visit)$")
    note: str = Field(default="", max_length=1000)


@app.post("/api/cases/{case_id}/review")
def review(case_id: str, body: ReviewBody, x_role: str | None = Header(None)):
    role = role_of(x_role)
    need(role.review, "recording a decision")
    _case(case_id, role)
    seq = audit.review(case_id, body.decision, body.note.strip(), role.key)
    return dict(ok=True, audit_seq=seq, note="Recorded for follow-up. No benefit is changed by this system.")


@app.get("/api/person/{person_key}")
def person(person_key: str, x_role: str | None = Header(None)):
    role = role_of(x_role)
    need(role.cases, "individual records")
    where, p = scope_sql(role)
    if not one(f"select count(*) from people where person_key = ? and {where}", [person_key] + p):
        audit.log(role.key, "refused", person_key, {"reason": "outside posting"})
        raise HTTPException(403, "outside your posting")
    audit.log(role.key, "open_person", person_key, {})
    return _person(person_key, role, False)


# ---------------------------------------------------------------------------------------------------------------
@app.get("/api/planning")
def planning(x_role: str | None = Header(None), district: str | None = None):
    role = role_of(x_role)
    need(role.aggregates, "aggregate figures")
    where, p = scope_sql(role)
    if district:
        where += " and district = ?"
        p.append(district)
    blocks = q(f"""
        select district, block,
               sum(case when alive then 1 else 0 end) people,
               sum(case when alive and age >= 60 then 1 else 0 end) aged_60,
               sum(case when alive and age >= 60 and ration_type in ('AAY','PHH') then 1 else 0 end) aged_60_priority_card,
               sum(case when alive and pensions like '%old_age%' then 1 else 0 end) old_age_pensioners,
               sum(case when alive and pensions like '%widow%' then 1 else 0 end) widow_pensioners,
               sum(case when alive and pensions like '%disability%' then 1 else 0 end) disability_pensioners,
               sum(case when survey_list then 1 else 0 end) survey_list
        from people where {where} group by 1, 2 order by 1, 2""", p)
    cw, cp = scope_sql(role)
    if district:
        cw += " and district = ?"
        cp.append(district)
    case_rows = q(f"""select district, block, kind, type, count(*) n, sum(amount_rs) amount from cases where {cw}
                      group by 1, 2, 3, 4""", cp)
    portal = q(f"""select district, block, sum(old_age) old_age, sum(widow) widow, sum(disability) disability
                   from units where {scope_sql(role)[0]} group by 1, 2""", scope_sql(role)[1])
    pmap = {(r["district"], r["block"]): r for r in portal}
    for b in blocks:
        k = (b["district"], b["block"])
        b["portal"] = pmap.get(k)
        cs = [c for c in case_rows if (c["district"], c["block"]) == k]
        b["left_out"] = sum(c["n"] for c in cs if c["kind"] == "exclusion")
        b["integrity"] = sum(c["n"] for c in cs if c["kind"] == "integrity")
        b["leakage_rs"] = sum(c["amount"] or 0 for c in cs if c["kind"] == "integrity" and c["type"] != "two_pensions")
        for key in list(b):
            if isinstance(b[key], int) and key not in ("leakage_rs",):
                b[key] = suppress(b[key], role)
    types = {}
    for c in case_rows:
        t = types.setdefault((c["kind"], c["type"]), dict(kind=c["kind"], type=c["type"], n=0, amount=0))
        t["n"] += c["n"]
        t["amount"] += c["amount"] or 0
    audit.log(role.key, "planning", district, {})
    return dict(blocks=blocks, totals=sorted(types.values(), key=lambda t: -t["n"]), monthly_rate=RULES["monthly_amount"])


PROGRAMMES = ["old_age", "widow", "disability", "ration_priority", "mgnrega_active", "pm_kisan", "pmay_house", "udid", "treasury"]


@app.get("/api/overlap")
def overlap(x_role: str | None = Header(None), district: str | None = None, block: str | None = None):
    role = role_of(x_role)
    need(role.aggregates, "aggregate figures")
    where, p = scope_sql(role)
    for col, v in (("district", district), ("block", block)):
        if v:
            where += f" and {col} = ?"
            p.append(v)
    rows = q(f"select a, b, sum(persons) persons from overlap where {where} group by 1, 2", p)
    progs = [x for x in PROGRAMMES if not role.programmes or x in role.programmes]
    cells = {}
    for r in rows:
        if r["a"] in progs and r["b"] in progs:
            cells[f"{r['a']}|{r['b']}"] = cells[f"{r['b']}|{r['a']}"] = suppress(int(r["persons"]), role)
    audit.log(role.key, "overlap", district or block, {})
    return dict(programmes=progs, cells=cells, min_cell=role.min_cell)


# ---------------------------------------------------------------------------------------------------------------
@app.get("/api/audit")
def audit_log(x_role: str | None = Header(None), limit: int = Query(100, le=500), offset: int = 0, action: str | None = None):
    role = role_of(x_role)
    need(role.audit or role.cases, "the audit log")
    events = audit.events(limit, offset, action)
    if not role.audit:                        # an officer sees only their own trail
        events = [e for e in events if e["role"] == role.key]
    return dict(events=events, total=audit.count())


@app.get("/api/audit/verify")
def audit_verify(x_role: str | None = Header(None)):
    role = role_of(x_role)
    need(role.audit or role.cases, "the audit log")
    res = audit.verify()
    audit.log(role.key, "verify_audit", None, res)
    return res


@app.get("/api/method")
def method(x_role: str | None = Header(None)):
    role_of(x_role)
    acc = json.loads(one("select report from accuracy") or "{}")
    calib = [json.loads(m["summary"]) for m in q("select district, summary from meta")]
    return dict(rules=RULES, accuracy=acc, calibration=calib)


# ---------------------------------------------------------------------------------------------------------------
# a department file arriving: map its columns, standardise, and see how much of it links to people already known
SYNONYMS = {
    "name": ["name", "beneficiary", "applicant", "member", "worker", "farmer", "pensioner", "naam", "नाम"],
    "rel_name": ["father", "husband", "guardian", "पिता", "पति"],
    "dob": ["dob", "birth", "जन्म"],
    "age": ["age", "आयु", "उम्र"],
    "sex": ["gender", "sex", "लिंग"],
    "aadhaar": ["aadhaar", "aadhar", "uid", "आधार"],
    "panchayat": ["panchayat", "village", "gram", "ward", "ग्राम"],
    "block": ["block", "ब्लॉक", "विकासखंड"],
    "account": ["account", "bank", "खाता"],
}


def guess_mapping(headers: list[str]) -> dict:
    """Map a department's column headers to the common fields by whole words ('Village' is not an age column)."""
    words = {h: re.findall(r"[a-z\u0900-\u097f]+", h.lower()) for h in headers}
    hit = lambda h, keys: any(w == k or w.startswith(k) for w in words[h] for k in keys)
    m = {}
    for field, keys in SYNONYMS.items():
        for h in headers:
            if h in m.values() or not hit(h, keys):
                continue
            if field == "name" and hit(h, SYNONYMS["rel_name"]):
                continue
            m[field] = h
            break
    return m


@app.post("/api/upload")
async def upload(file: UploadFile = File(...), department: str = Form(...), x_role: str | None = Header(None)):
    role = role_of(x_role)
    need(role.cases, "loading a department file")
    raw = (await file.read()).decode("utf-8-sig", errors="replace")
    rows = list(csv.DictReader(io.StringIO(raw)))[:2000]
    if not rows:
        raise HTTPException(400, "empty or unreadable CSV")
    headers = list(rows[0].keys())
    mapping = guess_mapping(headers)
    if "name" not in mapping:
        raise HTTPException(422, f"could not find a name column among {headers}")
    import sys
    sys.path.insert(0, str(ROOT / "pipeline"))
    from normalise import place_key, split_name
    from standardise import token
    matched, sample = 0, []
    where, p = scope_sql(role, "r")
    for i, row in enumerate(rows):
        n = split_name(row.get(mapping["name"]) or "")
        tok = token((row.get(mapping.get("aadhaar", "")) or "").replace(" ", "")) if "aadhaar" in mapping else None
        by = None
        if "dob" in mapping and re.search(r"\d{4}", row.get(mapping["dob"]) or ""):
            by = int(re.search(r"(\d{4})", row[mapping["dob"]]).group(1))
        elif "age" in mapping and (row.get(mapping["age"]) or "").strip().isdigit():
            by = 2026 - int(row[mapping["age"]])
        pk = place_key(row.get(mapping.get("panchayat", ""))) if "panchayat" in mapping else None
        hit = None
        if tok:
            hit = one(f"select r.person_key from records r where r.aadhaar_token = ? and {where} limit 1", [tok] + p)
        if not hit and n["skel_first"] and pk:
            hit = one(f"""select r.person_key from records r where r.skel_first = ? and r.panchayat_key = ?
                          and (? is null or abs(r.birth_year - ?) <= 2) and {where} limit 1""",
                      [n["skel_first"], pk, by, by] + p)
        matched += bool(hit)
        if i < 25:
            sample.append(dict(row=i + 1, name=mask_name(row.get(mapping["name"])), first=n["first"], surname=n["last"],
                               birth_year=by, place_key=pk, linked_to=hit))
    audit.log(role.key, "upload", department, {"file": file.filename, "rows": len(rows), "matched": matched,
                                               "mapping": mapping})
    return dict(department=department, file=file.filename, rows=len(rows), columns=headers, mapping=mapping,
                matched=matched, match_rate=round(matched / len(rows), 3), sample=sample,
                note="Preview only: rows are standardised and looked up, nothing is written to the registers.")


# ---------------------------------------------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return dict(ok=WAREHOUSE.exists(), people=one("select count(*) from people") if WAREHOUSE.exists() else 0,
                audit_entries=audit.count())


if UI.exists():
    app.mount("/assets", StaticFiles(directory=UI / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        f = UI / path
        return FileResponse(f if path and f.is_file() else UI / "index.html")
