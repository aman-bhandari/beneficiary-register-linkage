"""Findings accuracy against the planted truth.

Integrity cases are scored per pension record: a planted anomaly is found when a case of the matching type
names that record. Exclusion cases are scored per person: a case is right when the person it names is truly
eligible for that scheme and receives no pension; recall is measured against everyone truly left out, and again
against those the registers could have revealed (the rest are invisible to any record-based method and need a
field survey).

    python eval/findings_eval.py [--district Almora]
"""
import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PLANT_FOR = {"paid_after_death": "died_still_paid", "duplicate_enrolment": "duplicate_same_scheme",
             "two_pensions": "two_pensions", "income_above_limit": "treasury_income",
             "age_disagreement": "age_inflated", "shared_account": "account_ring", "uncorroborated": "ghost"}


def majority_pid(g: Path) -> pd.Series:
    """person_key -> the true person most of its records belong to."""
    c = pd.read_parquet(g / "clusters.parquet", columns=["record_id", "cluster_id"])
    t = pd.read_parquet(g / "truth_records.parquet", columns=["record_id", "pid"])
    m = c.merge(t, on="record_id").groupby(["cluster_id", "pid"]).size().rename("n").reset_index()
    return m.sort_values("n", ascending=False).drop_duplicates("cluster_id").set_index("cluster_id").pid


def evaluate(district: str) -> dict:
    g = ROOT / "data" / "gen" / district.lower().replace(" ", "_")
    cases = pd.read_parquet(g / "cases.parquet")
    truth = pd.read_parquet(g / "truth_records.parquet")
    persons = pd.read_parquet(g / "persons.parquet").set_index("pid")
    out = {"district": district, "integrity": [], "exclusion": []}

    for ctype, plant in PLANT_FOR.items():
        planted = set(truth.loc[truth.plant == plant, "record_id"])
        flagged = set(cases.loc[cases.type == ctype, "record_id"].dropna())
        hit = planted & flagged
        # a flagged record that was not planted may still be a real problem the generator created by chance
        # (e.g. an 'eligible' pensioner who died and whose record stayed): count those separately
        pid_of = truth.set_index("record_id").pid
        spurious = flagged - planted
        also_true = 0
        if ctype == "paid_after_death":
            also_true = sum(1 for r in spurious if not persons.loc[pid_of[r], "alive"])
        out["integrity"].append(dict(type=ctype, planted=len(planted), flagged=len(flagged), found=len(hit),
                                     recall=round(len(hit) / len(planted), 4) if planted else None,
                                     precision=round((len(hit) + also_true) / len(flagged), 4) if flagged else None))

    pid = majority_pid(g)
    exc = cases[cases.kind == "exclusion"].copy()
    exc["pid"] = exc.person_key.map(pid)
    alive = persons[persons.alive & ~persons.ghost]
    receives = alive.schemes.fillna("") != ""
    for scheme in ("old_age", "widow", "disability"):
        el = alive.eligible.fillna("").str.contains(scheme)
        truly_out = set(alive.index[el & ~receives])
        flagged = exc[exc.scheme == scheme]
        right = flagged.pid.isin(truly_out)
        # 'truly left out' but eligible for a different scheme than the one flagged still has a real case
        any_scheme_out = set(alive.index[(alive.eligible.fillna("") != "") & ~receives])
        right_any = flagged.pid.isin(any_scheme_out)
        out["exclusion"].append(dict(
            scheme=scheme, truly_left_out=len(truly_out), flagged=len(flagged), correct=int(right.sum()),
            precision=round(right.mean(), 4) if len(flagged) else None,
            precision_any_scheme=round(right_any.mean(), 4) if len(flagged) else None,
            recall=round(len(set(flagged.pid) & truly_out) / len(truly_out), 4) if truly_out else None,
            high_priority_precision=round(right[flagged.priority == "high"].mean(), 4) if (flagged.priority == "high").any() else None))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--district", action="append")
    a = ap.parse_args()
    ds = a.district or [p.name.replace("_", " ").title() for p in sorted((ROOT / "data" / "gen").iterdir())
                        if (p / "cases.parquet").exists()]
    print(json.dumps([evaluate(d) for d in ds], indent=1))
