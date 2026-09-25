"""Blinded linkage: the same pipeline, with the linkage unit never seeing a name.

Each department would encode before sending: every name field becomes a Bloom-filter encoding (a CLK, 1,024 bits,
keyed HMAC bigram hashing: `blind.py`), and every blocking key (name skeletons, panchayat) a keyed hash. Aadhaar,
account and mobile are already keyed tokens. The matcher compares encodings by Dice coefficient inside DuckDB.
Birth year and sex travel in clear; they are coarse and are what makes the comparison possible at all.

Here the encoding is applied to the standardised table to emulate that, and the result is scored against the
same planted truth as the clear-name run, to measure what privacy costs in accuracy.

    python pipeline/blind_link.py --district Almora      -> data/gen/<district>/clusters_blind.parquet
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import time

import numpy as np
import pandas as pd
import splink.comparison_level_library as cll
import splink.comparison_library as cl
from splink import DuckDBAPI, Linker, SettingsCreator, block_on

import link
from blind import BITS, K, KEY, _bigrams

ROOT = link.ROOT
_clear_settings = link.settings            # the clear-name model, before it is swapped for the blinded one


def clk_bits(value, tag: str) -> str | None:
    """One field's Bloom-filter encoding as a '0101…' string DuckDB reads as BIT."""
    if not isinstance(value, str) or not value:
        return None
    bits = np.zeros(BITS, dtype=np.uint8)
    for g in _bigrams(value):
        f = f"{tag}:{g}".encode()
        h1 = int.from_bytes(hmac.new(KEY, b"1" + f, hashlib.sha256).digest()[:8], "big")
        h2 = int.from_bytes(hmac.new(KEY, b"2" + f, hashlib.sha256).digest()[:8], "big")
        for i in range(K):
            bits[(h1 + i * h2) % BITS] = 1
    return "".join("1" if b else "0" for b in bits)


def hkey(v) -> str | None:
    return hmac.new(KEY, str(v).encode(), hashlib.sha256).hexdigest()[:16] if isinstance(v, str) and v else None


def dice(col: str) -> str:
    return f'2.0 * bit_count("{col}_l" & "{col}_r") / nullif(bit_count("{col}_l") + bit_count("{col}_r"), 0)'


def name_comparison(col: str, skel: str, label: str) -> cl.CustomComparison:
    return cl.CustomComparison(output_column_name=label, comparison_levels=[
        cll.NullLevel(col),
        cll.ExactMatchLevel(col, term_frequency_adjustments=True),
        cll.CustomLevel(f"{dice(col)} >= 0.85", label_for_charts="encodings 85% alike"),
        cll.CustomLevel(f'"{skel}_l" = "{skel}_r"', label_for_charts="same hashed skeleton"),
        cll.CustomLevel(f"{dice(col)} >= 0.7", label_for_charts="encodings 70% alike"),
        cll.ElseLevel(),
    ])


def settings() -> SettingsCreator:
    base = _clear_settings()
    comps = [name_comparison("first", "skel_first", "first_name"), name_comparison("last", "skel_last", "surname"),
             name_comparison("rel_first", "rel_skel", "relation_name")]
    # keep every non-name comparison exactly as in the clear run
    rest = [c for c in base.comparisons if c.create_output_column_name() not in ("first_name", "surname", "relation_name")]
    return SettingsCreator(link_type="dedupe_only", unique_id_column_name="unique_id",
                           blocking_rules_to_generate_predictions=base.blocking_rules_to_generate_predictions,
                           comparisons=comps + rest, retain_intermediate_calculation_columns=False,
                           retain_matching_columns=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--district", default="Almora")
    ap.add_argument("--threshold", type=float, default=0.9)
    ap.add_argument("--strong-weight", type=float, default=4.0)
    a = ap.parse_args()
    GEN = ROOT / "data" / "gen" / a.district.lower().replace(" ", "_")
    t0 = time.time()
    df = pd.read_parquet(GEN / "standard.parquet", columns=link.COLS)
    # the encoding a department would do before sending: names -> CLKs, blocking keys -> keyed hashes.
    # Each distinct value is encoded once; the join happens in DuckDB so no per-record bit string sits in memory.
    con = link.connect(ROOT / "data" / "tmp")
    maps = {}
    for col, tag in (("first", "f"), ("last", "l"), ("rel_first", "r")):
        vals = df[col].dropna().unique()
        maps[col] = pd.DataFrame({"v": vals, "clk": [clk_bits(v, tag) for v in vals]})
        con.register(f"m_{col}", maps[col])
    for col in ("skel_first", "skel_last", "rel_skel", "panchayat_key", "middle"):
        m = {v: hkey(v) for v in df[col].dropna().unique()}
        df[col] = df[col].map(m)
    print(f"encoded {sum(len(m) for m in maps.values()):,} distinct names in {time.time() - t0:.0f}s")
    con.register("bdf", df)
    con.execute("""create table recs as
        select d.* exclude ("first", "last", rel_first), f.clk::BIT as "first", l.clk::BIT as "last", r.clk::BIT as rel_first
        from bdf d left join m_first f on d."first" = f.v left join m_last l on d."last" = l.v
        left join m_rel_first r on d.rel_first = r.v""")
    con.unregister("bdf")
    del df
    df = con.execute("select unique_id, record_id from recs order by unique_id").df()
    link.settings = settings                               # same training and scoring, blinded comparisons
    linker, pred = link.run(con, a.threshold)
    con.execute(f"""create table e as select p.unique_id_l, p.unique_id_r from {pred.physical_name} p
        join recs l on l.unique_id = p.unique_id_l join recs r on r.unique_id = p.unique_id_r
        where p.match_probability >= {a.threshold}
          and (p.match_weight >= {a.strong_weight} or p.gamma_aadhaar_token = 1 or p.gamma_account_token = 1
               or p.gamma_relation_name >= 3 or p.gamma_birth = 4)
          and not (l.aadhaar_token is not null and r.aadhaar_token is not null and l.aadhaar_token <> r.aadhaar_token)
          and not coalesce(abs(l.birth_year - r.birth_year) > 10, false)""")
    strong = con.execute("select * from e").df()
    # household pass on hashed skeletons (no spelling similarity: the matcher cannot read the names)
    con.execute("create or replace table r as select unique_id, doc_key, skel_first, sex, birth_year, aadhaar_token from recs where doc_key is not null")
    con.execute(f"create or replace table ew as select unique_id_l, unique_id_r from {pred.physical_name} where match_probability >= 0.5")
    con.execute("""create or replace table ld as
        select least(a.doc_key, b.doc_key) d1, greatest(a.doc_key, b.doc_key) d2, count(distinct a.unique_id) shared
        from ew e join r a on a.unique_id = e.unique_id_l join r b on b.unique_id = e.unique_id_r
        where a.doc_key <> b.doc_key and split_part(a.doc_key, ':', 1) <> split_part(b.doc_key, ':', 1)
        group by 1, 2 having count(distinct a.unique_id) >= 2""")
    con.execute("create or replace table la as select ld.d2, a.* from ld join r a on a.doc_key = ld.d1")
    extra = con.execute("""select la.unique_id unique_id_l, b.unique_id unique_id_r from la join r b on b.doc_key = la.d2
        where la.sex = b.sex and la.skel_first = b.skel_first
          and (la.birth_year is null or b.birth_year is null or abs(la.birth_year - b.birth_year) <= 6)
          and not (la.aadhaar_token is not null and b.aadhaar_token is not null and la.aadhaar_token <> b.aadhaar_token)""").df()
    extra = extra[~extra.duplicated("unique_id_l", keep=False) & ~extra.duplicated("unique_id_r", keep=False)]
    n = len(df)
    root = link.components(n, pd.concat([strong, extra]))
    pd.DataFrame({"unique_id": df.unique_id, "record_id": df.record_id,
                  "cluster_id": [f"B-{v}" for v in root]}).to_parquet(GEN / "clusters_blind.parquet")
    print(f"{n:,} records, blinded linkage, {len(np.unique(root)):,} persons, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
