"""Linkage accuracy against the planted truth.

Pairwise precision and recall: every pair of records put in one cluster is a predicted match; every pair of
records describing one person is a true match. Reported overall, per register pair, and per hard-case group,
because an average hides who the matcher fails, and a missed or wrong merge is where exclusion begins.

    python eval/linkage_eval.py --district Almora [--clusters clusters.parquet]
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def pairs_within(d: pd.DataFrame, key: str) -> pd.DataFrame:
    """All record pairs sharing `key` (only for groups up to 60 records, larger ones are summarised by count)."""
    d = d[d.groupby(key)[key].transform("size").between(2, 60)]
    m = d.merge(d, on=key, suffixes=("_l", "_r"))
    m[key + "_l"] = m[key + "_r"] = m[key]
    return m[m.record_id_l < m.record_id_r]


def evaluate(recs: pd.DataFrame) -> dict:
    """recs: record_id, cluster_id, pid (+ attributes). Counts via group sizes, so it is exact at any scale."""
    c2 = lambda s: int((s * (s - 1) // 2).sum())
    tp = c2(recs.groupby(["cluster_id", "pid"]).size())
    pred = c2(recs.groupby("cluster_id").size())
    true = c2(recs.groupby("pid").size())
    return dict(records=len(recs), persons_true=int(recs.pid.nunique()), persons_found=int(recs.cluster_id.nunique()),
                true_pairs=true, predicted_pairs=pred, correct_pairs=tp,
                precision=round(tp / pred, 4) if pred else None, recall=round(tp / true, 4) if true else None)


def by_group(recs: pd.DataFrame, persons: pd.DataFrame) -> list[dict]:
    """Recall and precision for pairs where the person belongs to a group that is easy to fail."""
    tp_pairs = pairs_within(recs, "pid")
    tp_pairs["found"] = tp_pairs.cluster_id_l == tp_pairs.cluster_id_r
    pp = pairs_within(recs, "cluster_id")
    pp["correct"] = pp.pid_l == pp.pid_r
    p = persons.set_index("pid")
    age = (pd.Timestamp("2026-09-25") - pd.to_datetime(p.birth)).dt.days / 365.25
    groups = {
        "everyone": pd.Series(True, index=p.index),
        "aged 60 and over": age >= 60,
        "married women": (p.sex == "F") & p.married,
        "widows": (p.sex == "F") & p.widowed,
        "no Aadhaar": ~p.has_aadhaar,
        "Scheduled Caste": p.category == "sc",
        "Scheduled Tribe": p.category == "st",
        "Muslim names": p.community == "muslim",
        "Sikh names": p.community == "sikh",
        "Bengali names": p.community == "bengali",
    }
    out = []
    for g, mask in groups.items():
        ids = set(mask[mask].index)
        if not ids:
            continue
        t = tp_pairs[tp_pairs.pid_l.isin(ids)]
        q = pp[pp.pid_l.isin(ids) | pp.pid_r.isin(ids)]
        out.append(dict(group=g, true_pairs=len(t), recall=round(t.found.mean(), 4) if len(t) else None,
                        predicted_pairs=len(q), precision=round(q.correct.mean(), 4) if len(q) else None))
    # script: pairs where one record is in Devanagari and the other in Roman
    xs = tp_pairs[tp_pairs.script_l != tp_pairs.script_r]
    out.append(dict(group="Hindi-script vs English-script records", true_pairs=len(xs),
                    recall=round(xs.found.mean(), 4) if len(xs) else None, predicted_pairs=None, precision=None))
    return out


def by_register(recs: pd.DataFrame) -> list[dict]:
    t = pairs_within(recs, "pid")
    t["found"] = t.cluster_id_l == t.cluster_id_r
    t["pair"] = np.where(t.register_l <= t.register_r, t.register_l + "-" + t.register_r, t.register_r + "-" + t.register_l)
    g = t.groupby("pair").found.agg(["size", "mean"]).reset_index().sort_values("size", ascending=False)
    return [dict(registers=r["pair"], true_pairs=int(r["size"]), recall=round(r["mean"], 4)) for r in g.to_dict("records")]


def load(district: str, clusters_file: str = "clusters.parquet") -> tuple[pd.DataFrame, pd.DataFrame]:
    g = ROOT / "data" / "gen" / district.lower().replace(" ", "_")
    c = pd.read_parquet(g / clusters_file)
    t = pd.read_parquet(g / "truth_records.parquet")
    s = pd.read_parquet(g / "standard.parquet", columns=["record_id", "script"])
    recs = c[["record_id", "cluster_id"]].merge(t[["record_id", "pid", "register"]], on="record_id").merge(s, on="record_id")
    return recs, pd.read_parquet(g / "persons.parquet")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--district", default="Almora")
    ap.add_argument("--clusters", default="clusters.parquet")
    ap.add_argument("--detail", action="store_true")
    a = ap.parse_args()
    recs, persons = load(a.district, a.clusters)
    out = dict(overall=evaluate(recs))
    if a.detail:
        out["groups"] = by_group(recs, persons)
        out["register_pairs"] = by_register(recs)
    print(json.dumps(out, indent=2))
