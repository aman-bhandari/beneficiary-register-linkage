"""Who may see what, enforced where the data is read, and a tamper-evident record of every access.

Roles decide rows (district, block) and columns (identity fields) inside the SQL itself: a row outside an
officer's posting is never selected, so the API can say how many it refused. Identity fields are masked unless
an officer with the right unmasks one case and gives a reason. Every read of individual data, every unmask,
every review decision and every upload is appended to a hash-chained log; changing or deleting any past entry
breaks the chain, and /api/audit/verify says where.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DB = ROOT / "data" / "audit.db"


@dataclass(frozen=True)
class Role:
    key: str
    title: str
    title_hi: str
    office: str
    districts: tuple | None = None           # None: statewide
    blocks: tuple | None = None               # None: whole district
    cases: bool = False                       # may list and open individual cases
    unmask: bool = False                      # may reveal names on a case, with a reason
    review: bool = False                      # may record a decision on a case
    audit: bool = False                       # may read the audit log
    aggregates: bool = True
    min_cell: int = 0                         # aggregate cells smaller than this are suppressed
    programmes: tuple | None = None           # restricts overlap views to these programmes
    note: str = ""


ROLES = {r.key: r for r in [
    Role("planner", "State planning officer", "राज्य नियोजन अधिकारी", "Directorate of Social Welfare",
         min_cell=10, note="Statewide figures only. No individual record, no name, and no figure small enough to identify one."),
    Role("dswo_almora", "District Social Welfare Officer, Almora", "जिला समाज कल्याण अधिकारी, अल्मोड़ा",
         "Social Welfare, Almora", districts=("Almora",), cases=True, unmask=True, review=True,
         note="Every case in Almora district. Names stay masked until a case is opened with a stated reason."),
    Role("aswo_hawalbag", "Assistant Social Welfare Officer, Hawalbagh block", "सहायक समाज कल्याण अधिकारी, हवालबाग",
         "Social Welfare, Hawalbagh", districts=("Almora",), blocks=("HAWALBAG",), cases=True, unmask=True, review=True,
         note="Cases in Hawalbagh block only: the field officer who verifies them."),
    Role("dswo_usn", "District Social Welfare Officer, Udham Singh Nagar", "जिला समाज कल्याण अधिकारी, ऊधम सिंह नगर",
         "Social Welfare, Udham Singh Nagar", districts=("Udham Singh Nagar",), cases=True, unmask=True, review=True,
         note="Every case in Udham Singh Nagar district."),
    Role("dso_almora", "District Supply Officer, Almora", "जिला पूर्ति अधिकारी, अल्मोड़ा", "Food & Civil Supplies, Almora",
         districts=("Almora",), min_cell=10, programmes=("ration_priority", "old_age", "widow", "disability", "mgnrega_active"),
         note="Another department: overlap figures for its own programme in its own district. No Social Welfare case, no name."),
    Role("auditor", "Data governance officer", "डेटा गवर्नेंस अधिकारी", "Information Technology Development Agency",
         audit=True, min_cell=10, note="Reads the audit log and verifies it has not been altered. No citizen data."),
]}


def scope_sql(role: Role, alias: str = "") -> tuple[str, list]:
    """The row filter for a role, to be ANDed into every query over people, cases or records."""
    a = f"{alias}." if alias else ""
    clauses, params = [], []
    if role.districts:
        clauses.append(f"{a}district in ({','.join('?' * len(role.districts))})")
        params += list(role.districts)
    if role.blocks:
        clauses.append(f"{a}block in ({','.join('?' * len(role.blocks))})")
        params += list(role.blocks)
    return (" and ".join(clauses) or "true"), params


# ---------------------------------------------------------------------------------------------------------------
# masking
# ---------------------------------------------------------------------------------------------------------------
_DIGITS = re.compile(r"\d")


def mask_name(name: str | None) -> str | None:
    """'Kamla Devi Bisht' -> 'K•••• D••• B••••'. Enough to tell cases apart, not enough to identify."""
    if not name:
        return name
    return " ".join(w[0] + "•" * max(2, len(w) - 1) for w in str(name).split())


def mask_number(v, keep: int = 4) -> str | None:
    if v in (None, "None", "nan") or v != v:
        return None
    s = str(v)
    digits = [c for c in s if c.isdigit()]
    if len(digits) <= keep:
        return "•" * len(s)
    kept = "".join(digits[-keep:])
    return "•" * (len(digits) - keep) + kept


ID_FIELDS = {"aadhaar": 4, "bank_account": 4, "account": 4, "mobile": 2}
NAME_FIELDS = {"applicant_name", "father_husband_name", "member_name", "head_of_family", "worker_name", "farmer_name",
               "deceased_name", "name", "father_guardian_name", "pensioner_name", "beneficiary_name"}
DOC_FIELDS = {"card_no", "family_id", "job_card_no", "registration_no", "udid_no", "ppo_no", "beneficiary_id", "pension_id",
              "service_no"}


def mask_fields(fields: dict, unmasked: bool) -> dict:
    """Aadhaar, accounts and mobiles are always masked; names and document numbers only until unmasked."""
    out = {}
    for k, v in fields.items():
        if v in ("None", "nan", "NaN", "<NA>") or (isinstance(v, float) and v != v):
            v = None
        if k in ID_FIELDS:
            out[k] = mask_number(v, ID_FIELDS[k])
        elif k in NAME_FIELDS and not unmasked:
            out[k] = mask_name(v)
        elif k in DOC_FIELDS and not unmasked:
            out[k] = mask_number(v, 3) if v and _DIGITS.search(str(v)) else v
        elif k == "dob" and not unmasked and v:
            out[k] = "••-••-" + str(v)[-4:]
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------------------------------------------------
# hash-chained audit log
# ---------------------------------------------------------------------------------------------------------------
class Audit:
    def __init__(self, path: Path = AUDIT_DB):
        self.path = path
        self.lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._con() as c:
            c.executescript("""
                create table if not exists events (
                    seq integer primary key, ts text not null, role text not null, action text not null,
                    object text, detail text, prev_hash text not null, hash text not null);
                create table if not exists reviews (
                    case_id text not null, decision text not null, note text, role text not null, ts text not null,
                    seq integer not null);
                create table if not exists unmasked (case_id text not null, role text not null, ts text not null,
                    reason text not null, seq integer not null);
                -- append-only: the database itself refuses edits and deletions
                create trigger if not exists events_no_update before update on events
                    begin select raise(abort, 'audit log is append-only'); end;
                create trigger if not exists events_no_delete before delete on events
                    begin select raise(abort, 'audit log is append-only'); end;
            """)

    def _con(self):
        return sqlite3.connect(self.path, timeout=10)

    @staticmethod
    def digest(prev: str, ts: str, role: str, action: str, obj, detail) -> str:
        body = json.dumps([prev, ts, role, action, obj, detail], ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(body.encode()).hexdigest()

    def log(self, role: str, action: str, obj: str | None = None, detail: dict | None = None) -> int:
        d = json.dumps(detail or {}, ensure_ascii=False, sort_keys=True)
        with self.lock, self._con() as c:
            row = c.execute("select hash from events order by seq desc limit 1").fetchone()
            prev = row[0] if row else "0" * 64
            ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
            h = self.digest(prev, ts, role, action, obj, d)
            cur = c.execute("insert into events (ts, role, action, object, detail, prev_hash, hash) values (?,?,?,?,?,?,?)",
                            (ts, role, action, obj, d, prev, h))
            return cur.lastrowid

    def events(self, limit=200, offset=0, action=None) -> list[dict]:
        q = "select seq, ts, role, action, object, detail, prev_hash, hash from events"
        p: list = []
        if action:
            q += " where action = ?"
            p.append(action)
        q += " order by seq desc limit ? offset ?"
        with self._con() as c:
            rows = c.execute(q, p + [limit, offset]).fetchall()
        return [dict(seq=r[0], ts=r[1], role=r[2], action=r[3], object=r[4], detail=json.loads(r[5] or "{}"),
                     prev_hash=r[6], hash=r[7]) for r in rows]

    def count(self) -> int:
        with self._con() as c:
            return c.execute("select count(*) from events").fetchone()[0]

    def verify(self) -> dict:
        """Recompute every hash from the first entry. Any edit, insertion or deletion shows up as a break."""
        prev = "0" * 64
        n = 0
        with self._con() as c:
            for seq, ts, role, action, obj, detail, prev_hash, h in c.execute(
                    "select seq, ts, role, action, object, detail, prev_hash, hash from events order by seq"):
                if prev_hash != prev or self.digest(prev, ts, role, action, obj, detail) != h:
                    return dict(ok=False, entries_checked=n, broken_at=seq,
                                reason="entry altered" if prev_hash == prev else "chain broken before this entry")
                prev, n = h, n + 1
        return dict(ok=True, entries_checked=n, head=prev)

    def review(self, case_id: str, decision: str, note: str, role: str) -> int:
        seq = self.log(role, "review", case_id, {"decision": decision, "note": note})
        with self._con() as c:
            c.execute("insert into reviews values (?,?,?,?,?,?)",
                      (case_id, decision, note, role, time.strftime("%Y-%m-%dT%H:%M:%S"), seq))
        return seq

    def reviews(self, case_ids: list[str] | None = None) -> dict[str, dict]:
        with self._con() as c:
            rows = c.execute("select case_id, decision, note, role, ts from reviews order by seq").fetchall()
        out = {}
        for cid, dec, note, role, ts in rows:
            if case_ids is None or cid in case_ids:
                out[cid] = dict(decision=dec, note=note, role=role, ts=ts)
        return out

    def unmask(self, case_id: str, role: str, reason: str) -> int:
        seq = self.log(role, "unmask", case_id, {"reason": reason})
        with self._con() as c:
            c.execute("insert into unmasked values (?,?,?,?,?)", (case_id, role, time.strftime("%Y-%m-%dT%H:%M:%S"), reason, seq))
        return seq

    def is_unmasked(self, case_id: str, role: str) -> bool:
        with self._con() as c:
            return c.execute("select 1 from unmasked where case_id = ? and role = ?", (case_id, role)).fetchone() is not None
