"""Findings from linked registers: who appears eligible and is left out, which payments look wrong, and where
schemes overlap. Every finding is a case for an officer, never an action on a citizen.

Reads, per district: the department registers, standard.parquet and clusters.parquet (record -> person_key).
Never reads the planted truth. Writes: people.parquet (one row per linked person), cases.parquet, overlap.parquet.

    python pipeline/findings.py [--district Almora]      (default: every generated district)
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from normalise import fold_word, to_roman

ROOT = Path(__file__).resolve().parent.parent
RULES = yaml.safe_load((ROOT / "rules" / "schemes.yaml").read_text())
TODAY = date(2026, 9, 25)
MONTHLY = RULES["monthly_amount"]
INCOME_LIMIT = RULES["income_limit_month"]
SCHEME_KEY = {"वृद्धावस्था पेंशन": "old_age", "विधवा पेंशन": "widow", "दिव्यांग पेंशन": "disability"}
RATION_RANK = {"AAY": 3, "PHH": 2, "SFY": 1, "NPHH": 0}
GRACE_DAYS = 90                         # a death is reported and the roll updated within a quarter


def gen_dir(district: str) -> Path:
    return ROOT / "data" / "gen" / district.lower().replace(" ", "_")


def crit(scheme: str, cid: str, met, evidence: str) -> dict:
    """One line of a criterion trace, with the published text it is tested against."""
    c = next(x for x in RULES["schemes"][scheme]["criteria"] if x["id"] == cid)
    src = RULES["sources"][c["source"]]
    return dict(criterion=c["en"], met=met, evidence=evidence, quote=c["quote"], source=src["url"])


def fold_first(name) -> str | None:
    if not isinstance(name, str):
        return None
    words = [fold_word(w) for w in to_roman(name).split()]
    return words[0] if words else None


# ---------------------------------------------------------------------------------------------------------------
# people: one row per linked person, built only from what the registers say
# ---------------------------------------------------------------------------------------------------------------
def build_people(g: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    std = pd.read_parquet(g / "standard.parquet", columns=[
        "record_id", "register", "name", "sex", "birth_date", "birth_year", "birth_exact", "age_only",
        "block", "panchayat_key", "aadhaar_token", "account_token", "doc_key", "script", "first", "skel_first", "rel_skel"])
    cl = pd.read_parquet(g / "clusters.parquet", columns=["record_id", "cluster_id"])
    rec = std.merge(cl, on="record_id")
    raw = {r: pd.read_parquet(g / f"{r}.parquet") for r in
           ("pension", "death", "ration", "parivar", "udid", "treasury", "kisan", "mgnrega", "pmay", "sainik")}
    units = pd.read_parquet(g / "units.parquet")
    district = units.district.iloc[0]

    # birth: exact dates first, then the median year of everything else
    exact = rec[rec.birth_exact].drop_duplicates("cluster_id").set_index("cluster_id").birth_date
    years = rec[rec.birth_year.notna()].groupby("cluster_id").birth_year.agg(
        year="median", sources="size", spread=lambda s: float(s.max() - s.min()))
    by = years.join(exact.rename("birth_date"), how="left")
    by["birth_year_best"] = np.where(by.birth_date.notna(), pd.to_datetime(by.birth_date).dt.year, by.year.round())

    first = lambda s: s.dropna().iloc[0] if s.notna().any() else None
    # vectorised: most common value per person by counting (person, value) pairs, not a Python mode per group
    def most_common(col):
        c = rec.dropna(subset=[col]).groupby(["cluster_id", col]).size().rename("n").reset_index()
        return c.sort_values(["cluster_id", "n"], ascending=[True, False]).drop_duplicates("cluster_id").set_index("cluster_id")[col]
    base = rec.groupby("cluster_id").agg(records=("record_id", "size"), aadhaar_n=("aadhaar_token", "count"))
    base["has_aadhaar"] = base.pop("aadhaar_n") > 0
    base["registers"] = rec.drop_duplicates(["cluster_id", "register"]).sort_values("register").groupby("cluster_id").register.agg(",".join)
    base["sex"] = most_common("sex")
    base["block"] = most_common("block")
    order = {"pension": 0, "parivar": 1, "death": 2}
    dev = rec[rec.script == "dev"].assign(o=lambda d: d.register.map(order).fillna(9)).sort_values(["cluster_id", "o"])
    base["name_hi"] = dev.drop_duplicates("cluster_id").set_index("cluster_id").name
    rom = rec[rec.script == "rom"]
    base["name_en"] = rom.drop_duplicates("cluster_id").set_index("cluster_id").name.str.title()

    def attach(reg, cols):
        d = raw[reg][["record_id"] + cols].merge(cl, on="record_id")
        return d
    # the panchayat as written by the departments that use the portal's own spelling
    pan = pd.concat([attach("pension", ["gram_panchayat"]).rename(columns={"gram_panchayat": "p"}),
                     attach("parivar", ["gram_panchayat"]).rename(columns={"gram_panchayat": "p"}),
                     attach("ration", ["village"]).rename(columns={"village": "p"}).assign(p=lambda d: d.p.str.upper())])
    base["panchayat"] = pan.dropna(subset=["p"]).groupby(["cluster_id", "p"]).size().rename("n").reset_index().sort_values(
        ["cluster_id", "n"], ascending=[True, False]).drop_duplicates("cluster_id").set_index("cluster_id").p

    death = attach("death", ["date_of_death", "registration_no"]).drop_duplicates("cluster_id").set_index("cluster_id").rename(
        columns={"registration_no": "death_reg"})[["date_of_death", "death_reg"]]
    death["date_of_death"] = pd.to_datetime(death.date_of_death, format="%d-%m-%Y").dt.date
    ration = attach("ration", ["card_type", "card_no"])
    ration["rank"] = ration.card_type.map(RATION_RANK)
    rbest = ration.sort_values("rank", ascending=False).groupby("cluster_id").agg(
        ration_type=("card_type", "first"), ration_card=("card_no", "first"))
    udid = attach("udid", ["percentage", "disability_type"]).sort_values("percentage", ascending=False).drop_duplicates(
        "cluster_id").set_index("cluster_id").rename(columns={"percentage": "disability_pct"})[["disability_pct", "disability_type"]]
    tre = attach("treasury", ["monthly_pension", "ppo_no"]).sort_values("monthly_pension", ascending=False).drop_duplicates(
        "cluster_id").set_index("cluster_id").rename(columns={"monthly_pension": "treasury_pension"})[["treasury_pension", "ppo_no"]]
    sai = attach("sainik", ["monthly_pension", "service_no"]).drop_duplicates("cluster_id").set_index("cluster_id").rename(
        columns={"monthly_pension": "defence_pension", "service_no": "service_no"})[["defence_pension", "service_no"]]
    kis = attach("kisan", ["land_ha"]).groupby("cluster_id").agg(land_ha=("land_ha", "max"))
    mg = attach("mgnrega", ["active"]).groupby("cluster_id").agg(mgnrega_active=("active", "max"))
    pm = attach("pmay", ["sanction_year"]).groupby("cluster_id").agg(pmay_year=("sanction_year", "max"))
    pen = attach("pension", ["scheme", "status"])
    pen["scheme_key"] = pen.scheme.map(SCHEME_KEY)
    pens = pen.sort_values("scheme_key").groupby("cluster_id").agg(pensions=("scheme_key", ",".join),
                                                                   pension_records=("record_id", "size"))

    people = base.join([by[["birth_year_best", "birth_date", "sources", "spread"]], death, rbest, udid, tre, sai, kis,
                        mg, pm, pens])
    people["alive"] = people.date_of_death.isna()
    people["age"] = TODAY.year - people.birth_year_best
    people["district"] = district
    people.index.name = "person_key"
    people = people.reset_index()
    people["widow_evidence"] = None
    wid = widowhood(raw, cl, people)
    people = people.merge(wid, on="person_key", how="left", suffixes=("_x", ""))
    people = people.drop(columns=[c for c in people.columns if c.endswith("_x")])
    return people, rec


def widowhood(raw: dict, cl: pd.DataFrame, people: pd.DataFrame) -> pd.DataFrame:
    """A woman is evidenced as widowed when the man named as her husband in the family register, in the same
    household, has a death registration or is marked मृत (deceased) there."""
    pv = raw["parivar"][["record_id", "family_id", "member_name", "relation", "gender", "father_husband_name", "remark"]].merge(cl, on="record_id")
    dead = set(people.loc[~people.alive, "person_key"])
    reg = people.set_index("person_key")
    pv["first"] = pv.member_name.map(fold_first)
    pv["husband_first"] = pv.father_husband_name.map(fold_first)
    men = pv[(pv.gender == "पु")][["family_id", "first", "cluster_id", "remark", "member_name"]]
    women = pv[(pv.gender == "म") & pv.relation.isin(["पत्नी", "माता", "मुखिया"])]
    m = women.merge(men, left_on=["family_id", "husband_first"], right_on=["family_id", "first"], suffixes=("", "_h"))
    m["husband_dead"] = m.cluster_id_h.isin(dead) | (m.remark_h == "मृत")
    m = m[m.husband_dead & (m.cluster_id != m.cluster_id_h)]

    def note(r):
        if r.cluster_id_h in dead:
            p = reg.loc[r.cluster_id_h]
            return f"Husband {r.member_name_h}: death registered {p.death_reg} on {p.date_of_death:%d %b %Y}"
        return f"Husband {r.member_name_h}: marked मृत (deceased) in Parivar register {r.family_id}"
    m["widow_evidence"] = m.apply(note, axis=1)
    return m.groupby("cluster_id").widow_evidence.first().rename_axis("person_key").reset_index()


# ---------------------------------------------------------------------------------------------------------------
# cases
# ---------------------------------------------------------------------------------------------------------------
def poverty(p) -> tuple[str | None, str]:
    """-> (strength, evidence). strong: NFSA priority card; possible: State Food Scheme card; None: no evidence."""
    if isinstance(p.treasury_pension, (int, float)) and p.treasury_pension == p.treasury_pension and p.treasury_pension > INCOME_LIMIT:
        return None, f"Treasury pension Rs {int(p.treasury_pension):,} a month (PPO {p.ppo_no}) is above the Rs {INCOME_LIMIT:,} limit"
    if p.defence_pension == p.defence_pension and p.defence_pension and p.defence_pension > INCOME_LIMIT:
        return None, f"Defence pension Rs {int(p.defence_pension):,} a month (Sainik Kalyan register) is above the Rs {INCOME_LIMIT:,} limit"
    if p.ration_type in ("AAY", "PHH"):
        return "strong", f"{p.ration_type} ration card {p.ration_card} (National Food Security Act priority household)"
    if p.ration_type == "SFY":
        return "possible", f"State Food Scheme card {p.ration_card}: low income likely, to be verified"
    return None, "No ration card showing low income" if p.ration_type != p.ration_type or p.ration_type is None else f"{p.ration_type} card: not a priority household"


def age_text(p) -> str:
    if pd.notna(p.birth_date):
        return f"Born {pd.Timestamp(p.birth_date):%d %b %Y} ({int(p.sources)} record{'s' if p.sources > 1 else ''})"
    return f"Birth year about {int(p.birth_year_best)} from {int(p.sources)} record{'s' if p.sources > 1 else ''}" + (
        f", which differ by up to {int(p.spread)} years" if p.spread and p.spread > 0 else "")


def near_misses(rec: pd.DataFrame, clusters: set, target: pd.DataFrame, years: int = 5) -> set:
    """People in `clusters` for whom `target` holds a record the linkage did not join to them but which could be
    theirs: same panchayat (or town ward) and sex, and either the same first-name skeleton with a birth year within
    `years`, or a close spelling (Jaro-Winkler 0.88+) within two years. Measured: searching the whole block instead
    suppressed nine cases in ten, most of them real. Such a person may already be enrolled, or already dead, under a
    record we failed to link, so no case is raised on them until that is checked. Runs in DuckDB: in the plains
    the candidate pairs run to tens of millions."""
    import duckdb
    cols = ["cluster_id", "panchayat_key", "sex", "first", "skel_first", "birth_year"]
    mine = rec[rec.cluster_id.isin(clusters)].dropna(subset=["panchayat_key", "skel_first"])[cols].drop_duplicates()
    t = target.dropna(subset=["panchayat_key", "skel_first"])[cols]
    con = duckdb.connect()
    con.execute("SET memory_limit='3GB'")
    con.register("mine", mine)
    con.register("t", t)
    got = con.execute(f"""
        select distinct m.cluster_id from mine m join t
          on m.panchayat_key = t.panchayat_key and m.sex = t.sex and substr(m.skel_first, 1, 1) = substr(t.skel_first, 1, 1)
        where m.cluster_id <> t.cluster_id
          and ((m.skel_first = t.skel_first and coalesce(abs(m.birth_year - t.birth_year), 0) <= {years})
               or (coalesce(abs(m.birth_year - t.birth_year), 0) <= 2 and jaro_winkler_similarity(m.first, t.first) >= 0.88))
    """).df()
    con.close()
    return set(got.cluster_id)


def exclusion_cases(people: pd.DataFrame, rec: pd.DataFrame) -> list[dict]:
    out = []
    cand = people[people.alive & people.pensions.isna() & people.age.notna()]
    # only people who would otherwise get a case need the near-miss search: strong poverty evidence and an age,
    # widowhood or disability that qualifies
    strong = cand.ration_type.isin(["AAY", "PHH"]) & ~(cand.treasury_pension.fillna(0) > INCOME_LIMIT) & ~(
        cand.defence_pension.fillna(0) > INCOME_LIMIT)
    could = (cand.age >= 60) | ((cand.sex == "F") & cand.widow_evidence.notna() & (cand.age >= 18)) | (cand.disability_pct.fillna(0) >= 40)
    cand = cand[strong & could]
    # a pension record in the same panchayat that could be theirs: probably enrolled, linkage missed it
    maybe_enrolled = near_misses(rec, set(cand.person_key), rec[rec.register == "pension"])
    # a death record nearby that could be theirs: probably dead, linkage missed it
    maybe_dead = near_misses(rec, set(cand.person_key), rec[rec.register == "death"])
    for p in cand.itertuples():
        if p.person_key in maybe_enrolled or p.person_key in maybe_dead:
            continue
        pov, pov_ev = poverty(p)
        if pov != "strong":
            continue                  # a State Food Scheme card alone does not prove income under Rs 4,000: survey list, not a case
        age = int(p.age)
        found = None
        exact_birth = pd.notna(p.birth_date)
        old_enough = age >= 61 or (exact_birth and age >= 60)     # an estimated 60 is as likely 59
        if old_enough and pov:
            found = ("old_age", [crit("old_age", "age60", True, age_text(p)), crit("old_age", "poor", True, pov_ev)])
        elif p.sex == "F" and isinstance(p.widow_evidence, str) and 18 <= age < 60 and pov:
            found = ("widow", [crit("widow", "widow", True, p.widow_evidence), crit("widow", "age18_60", True, age_text(p)),
                               crit("widow", "poor", True, pov_ev),
                               crit("widow", "no_adult_son", None, "Not checked automatically: confirm sons' ages and status at the visit")])
        elif p.disability_pct == p.disability_pct and p.disability_pct is not None and p.disability_pct >= 40 and pov:
            found = ("disability", [crit("disability", "disability40", True, f"UDID certificate: {int(p.disability_pct)}% ({p.disability_type})"),
                                    crit("disability", "poor", True, pov_ev)])
        if not found:
            continue
        scheme, trace = found
        # reliability of the age claim decides priority as much as poverty does
        # an estimated age of exactly 60 is as likely 58 as 62: high priority needs a birth date, or 61 and over
        # from two agreeing registers
        sure_age = exact_birth or (p.sources >= 2 and (p.spread or 0) <= 3)
        if pov == "strong":
            priority = "high" if (sure_age or scheme != "old_age") else "medium"
        else:
            priority = "low"                       # State Food Scheme card: income has to be verified first
        out.append(dict(kind="exclusion", type=f"eligible_not_enrolled", scheme=scheme, person_key=p.person_key,
                        priority=priority, amount_rs=MONTHLY * 12,
                        title=f"Appears eligible for {RULES['schemes'][scheme]['name_en'].lower()}, receives no pension",
                        trace=trace, evidence=[]))
    return out


def integrity_cases(people: pd.DataFrame, rec: pd.DataFrame, g: Path) -> list[dict]:
    """Each check is a vectorised filter over the pension roll; Python only touches the flagged rows."""
    pen = pd.read_parquet(g / "pension.parquet").merge(pd.read_parquet(g / "clusters.parquet", columns=["record_id", "cluster_id"]), on="record_id")
    pen["scheme_key"] = pen.scheme.map(SCHEME_KEY)
    pen["account_token"] = pen.record_id.map(rec.set_index("record_id").account_token)
    P = people.set_index("person_key")
    pen = pen.join(P[["date_of_death", "death_reg", "treasury_pension", "ppo_no", "records"]], on="cluster_id")
    out = []
    ev = lambda r: dict(register="pension", record_id=r.record_id, detail=f"{r.pension_id} · {r.scheme} · sanctioned {r.sanction_year}")

    def case(r, type_, scheme, priority, amount, title, trace, evidence=None, **kw):
        out.append(dict(kind="integrity", type=type_, scheme=scheme, person_key=r.cluster_id, priority=priority,
                        amount_rs=amount, record_id=r.record_id, title=title, trace=trace, evidence=evidence or [ev(r)], **kw))

    # paid after a registered death (beyond a quarter's grace for the roll to catch up)
    dod = pd.to_datetime(pen.date_of_death)
    days = (pd.Timestamp(TODAY) - dod).dt.days
    dead = pen[days > GRACE_DAYS]
    # check the death record against the pension record directly, not only through the cluster
    std = rec.set_index("record_id")
    drec = rec[rec.register == "death"].drop_duplicates("cluster_id").set_index("cluster_id")
    for r, d in zip(dead.itertuples(), days[days > GRACE_DAYS]):
        months = int(d // 30)
        a, b = std.loc[r.record_id], drec.loc[r.cluster_id] if r.cluster_id in drec.index else None
        agree = b is not None and a.skel_first == b.skel_first and (
            pd.isna(a.birth_year) or pd.isna(b.birth_year) or abs(a.birth_year - b.birth_year) <= 5)
        case(r, "paid_after_death", r.scheme_key, "high" if agree else "medium", months * MONTHLY, f"Pension active {months} months after a registered death",
             [dict(criterion="Pensioner is alive", met=False, evidence=f"Death registered {r.death_reg} on {pd.Timestamp(r.date_of_death):%d %b %Y}",
                   quote=None, source="Civil Registration System (death register)")])
    live = pen[~(days > GRACE_DAYS)]

    # the same person twice in one scheme
    n_same = live.groupby(["cluster_id", "scheme_key"]).record_id.transform("size")
    rank = live.groupby(["cluster_id", "scheme_key"]).cumcount()
    dups = live[(n_same > 1) & (rank > 0)]
    std = rec.set_index("record_id")
    rel = std.rel_skel if "rel_skel" in std.columns else None

    def same_person(x, y):
        """Two roll entries are one person only if first names agree and neither birth year nor the father's or
        husband's name contradicts it; otherwise the linkage has joined two namesakes."""
        a, b = std.loc[x], std.loc[y]
        if a.skel_first != b.skel_first:
            return False
        if pd.notna(a.birth_year) and pd.notna(b.birth_year) and abs(a.birth_year - b.birth_year) > 3:
            return False
        rx, ry = rel.get(x) if rel is not None else None, rel.get(y) if rel is not None else None
        if pd.notna(rx) and pd.notna(ry):
            return rx == ry
        return pd.notna(a.birth_year) and a.birth_year == b.birth_year
    first_rec = live[n_same > 1].groupby(["cluster_id", "scheme_key"]).record_id.first()
    dups = dups[[same_person(first_rec[(r.cluster_id, r.scheme_key)], r.record_id) for r in dups.itertuples()]]
    ids = live[n_same > 1].groupby(["cluster_id", "scheme_key"]).pension_id.agg(", ".join)
    for r in dups.itertuples():
        grp = live[(live.cluster_id == r.cluster_id) & (live.scheme_key == r.scheme_key)]
        case(r, "duplicate_enrolment", r.scheme_key, "high", 12 * MONTHLY, f"Enrolled {len(grp)} times in the same scheme",
             [dict(criterion="One enrolment per person per scheme", met=False,
                   evidence=f"{len(grp)} active records: {ids[(r.cluster_id, r.scheme_key)]}", quote=None, source=None)],
             [ev(x) for x in grp.itertuples()])

    # two different social-security pensions at once
    n_sch = live.groupby("cluster_id").scheme_key.transform("nunique")
    two = live[n_sch > 1]
    for pk, grp in two.groupby("cluster_id"):
        r = next(grp.itertuples())
        if not same_person(grp.record_id.iloc[0], grp.record_id.iloc[-1]):
            continue
        out.append(dict(kind="integrity", type="two_pensions", scheme=",".join(sorted(grp.scheme_key.unique())), person_key=pk,
                        priority="medium", amount_rs=12 * MONTHLY, record_id=grp.record_id.iloc[-1],
                        title="Receives two social-security pensions",
                        trace=[dict(criterion="Rule on holding two pensions", met=None,
                                    evidence=", ".join(grp.scheme) + ": the portal does not state whether this is allowed; confirm the rule",
                                    quote=None, source=None)],
                        evidence=[ev(x) for x in grp.itertuples()]))

    # income above the limit, from the Treasury roll
    rich = live[live.treasury_pension.fillna(0) > INCOME_LIMIT]
    for r in rich.itertuples():
        case(r, "income_above_limit", r.scheme_key, "high", 12 * MONTHLY, f"Draws a state pension of Rs {int(r.treasury_pension):,} a month",
             [crit(r.scheme_key, "poor", False, f"Treasury pension Rs {int(r.treasury_pension):,} a month (PPO {r.ppo_no})")])

    # age: the roll says 60 or more, every other register (at least two, agreeing) says 57 or less
    oth = rec[(rec.register != "pension") & rec.birth_year.notna() & rec.cluster_id.isin(set(live.cluster_id))]
    agg = oth.groupby("cluster_id").birth_year.agg(n="size", lo="min", hi="max", med="median")
    listing = oth.groupby("cluster_id").apply(lambda d: "; ".join(f"{a}: about {int(b)}" for a, b in zip(d.register, d.birth_year)), include_groups=False)
    oa = live[live.scheme_key == "old_age"].join(agg, on="cluster_id")
    claimed = pd.to_datetime(oa.dob, format="%d-%m-%Y", errors="coerce").dt.year
    flag = (oa.n >= 2) & ((oa.hi - oa.lo) <= 4) & ((TODAY.year - claimed) >= 60) & ((TODAY.year - oa.med) <= 57)
    for r, cy in zip(oa[flag].itertuples(), claimed[flag]):
        case(r, "age_disagreement", "old_age", "medium", 12 * MONTHLY,
             f"Pension roll gives age {TODAY.year - int(cy)}; {int(r.n)} other registers give about {int(TODAY.year - r.med)}",
             [crit("old_age", "age60", False, f"Roll: born {r.dob}. " + listing.get(r.cluster_id, ""))])

    # a pension record nothing else corroborates. Measured: most are linkage misses, not ghosts (right 5-31% of
    # the time), so they are not raised as cases; the count is reported with that caveat instead.
    n_pen = pen.groupby("cluster_id").record_id.transform("size")
    RAISE_UNCORROBORATED = False
    lone = live[live.records == n_pen[live.index]]
    maybe_known = near_misses(rec, set(lone.cluster_id), rec[rec.register != "pension"], years=6)
    lone = lone[~lone.cluster_id.isin(maybe_known)]
    (g / "uncorroborated.json").write_text(json.dumps({"pension_records": int(len(lone))}))
    for r in (lone.itertuples() if RAISE_UNCORROBORATED else []):
        case(r, "uncorroborated", r.scheme_key, "low", 12 * MONTHLY, "No other department's register knows this pensioner",
             [dict(criterion="Identity corroborated by at least one other register", met=False,
                   evidence="Not found in family, ration, job card, farmer, disability or death registers", quote=None, source=None)])

    # several unrelated people's pensions paid into one account
    shared = pen.dropna(subset=["account_token"])
    shared = shared[shared.groupby("account_token").cluster_id.transform("nunique") >= 3]
    for token, grp in shared.groupby("account_token"):
        k = grp.cluster_id.nunique()
        for r in grp.itertuples():
            case(r, "shared_account", r.scheme_key, "high", 12 * MONTHLY, f"Pension paid into an account shared by {k} unrelated pensioners",
                 [dict(criterion="Pension paid into the pensioner's own account", met=False,
                       evidence=f"Account ending ...{str(r.bank_account)[-4:]} receives {len(grp)} pensions", quote=None, source=None)],
                 [ev(x) for x in grp.itertuples()], group=token[:10])
    return out


def overlap(people: pd.DataFrame) -> pd.DataFrame:
    """Persons in each pair of programmes, by block. Counts only; small cells are suppressed at display time."""
    flags = pd.DataFrame({
        "person_key": people.person_key, "district": people.district, "block": people.block,
        "old_age": people.pensions.fillna("").str.contains("old_age"),
        "widow": people.pensions.fillna("").str.contains("widow"),
        "disability": people.pensions.fillna("").str.contains("disability"),
        "ration_priority": people.ration_type.isin(["AAY", "PHH"]),
        "mgnrega_active": people.mgnrega_active.fillna(False).astype(bool),
        "pm_kisan": people.land_ha.notna(),
        "pmay_house": people.pmay_year.notna(),
        "udid": people.disability_pct.notna(),
        "treasury": people.treasury_pension.notna(),
    })[people.alive.values]
    progs = [c for c in flags.columns if c not in ("person_key", "district", "block")]
    rows = []
    for (d, b), g in flags.groupby(["district", "block"]):
        for i, a in enumerate(progs):
            for c in progs[i:]:
                rows.append(dict(district=d, block=b, a=a, b=c, persons=int((g[a] & g[c]).sum())))
    return pd.DataFrame(rows)


def run(district: str):
    g = gen_dir(district)
    t = time.time()
    people, rec = build_people(g)
    cases = exclusion_cases(people, rec) + integrity_cases(people, rec, g)
    cdf = pd.DataFrame(cases)
    P = people.set_index("person_key")
    cdf["district"] = district
    cdf["block"] = cdf.person_key.map(P.block)
    cdf["panchayat"] = cdf.person_key.map(P.panchayat)
    code = {"Almora": "ALM", "Udham Singh Nagar": "USN"}.get(district, district[:3].upper())
    cdf["case_id"] = [f"{code}-{i + 1:06d}" for i in range(len(cdf))]
    for c in ("trace", "evidence"):
        cdf[c] = cdf[c].map(lambda v: json.dumps(v, ensure_ascii=False, default=str))
    people["survey_list"] = (people.alive & people.pensions.isna() & (people.age >= 60) & (people.ration_type == "SFY")
                             & people.treasury_pension.isna() & people.defence_pension.isna())
    people.to_parquet(g / "people.parquet")
    cdf.to_parquet(g / "cases.parquet")
    overlap(people).to_parquet(g / "overlap.parquet")
    print(f"{district}: {len(people):,} people, {len(cdf):,} cases in {time.time() - t:.0f}s")
    print(cdf.groupby(["kind", "type"]).size().to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--district", action="append")
    a = ap.parse_args()
    for d in a.district or [p.name.replace("_", " ").title() for p in sorted((ROOT / "data" / "gen").iterdir())
                            if (p / "clusters.parquet").exists()]:
        run(d)
