"""Probabilistic record linkage across all department registers (Splink 4 on DuckDB).

Every register row is a record; linkage decides which records describe the same person. The model is
Fellegi-Sunter: each field comparison contributes a match weight learnt from the data itself (EM), so every
accepted pair can be explained field by field ("Aadhaar token agrees +12.1, birth year within 2 -1.3, ...").

    python pipeline/link.py [--threshold 0.9]
Output: data/gen/pairs.parquet (scored pairs), clusters.parquet (record -> person_key), link_model.json
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import duckdb
import pandas as pd
import splink.comparison_level_library as cll
import splink.comparison_library as cl
from splink import DuckDBAPI, Linker, SettingsCreator, block_on

ROOT = Path(__file__).resolve().parent.parent


def name_comparison(col: str, skel: str, label: str) -> cl.CustomComparison:
    return cl.CustomComparison(
        output_column_name=label,
        comparison_levels=[
            cll.NullLevel(col),
            cll.ExactMatchLevel(col, term_frequency_adjustments=(col == "first")),
            cll.CustomLevel(f'"{skel}_l" = "{skel}_r"', label_for_charts="same consonant skeleton"),
            cll.JaroWinklerLevel(col, 0.88),
            cll.CustomLevel(f'(length("{col}_l") = 1 or length("{col}_r") = 1) and substr("{col}_l", 1, 1) = substr("{col}_r", 1, 1)',
                            label_for_charts="initial agrees"),
            cll.ElseLevel(),
        ])


BIRTH = cl.CustomComparison(
    output_column_name="birth",
    comparison_levels=[
        cll.CustomLevel('"birth_year_l" is null or "birth_year_r" is null', label_for_charts="unknown").configure(is_null_level=True),
        cll.CustomLevel('"birth_exact_l" and "birth_exact_r" and "birth_date_l" = "birth_date_r"', label_for_charts="same birth date"),
        cll.CustomLevel('"birth_year_l" = "birth_year_r"', label_for_charts="same birth year"),
        cll.CustomLevel('abs("birth_year_l" - "birth_year_r") <= 2', label_for_charts="within 2 years"),
        cll.CustomLevel('abs("birth_year_l" - "birth_year_r") <= 6', label_for_charts="within 6 years"),
        cll.ElseLevel(),
    ])

PLACE = cl.CustomComparison(
    output_column_name="place",
    comparison_levels=[
        cll.CustomLevel('"block_l" is null or "block_r" is null', label_for_charts="unknown").configure(is_null_level=True),
        cll.CustomLevel('"panchayat_key_l" = "panchayat_key_r"', label_for_charts="same panchayat"),
        cll.CustomLevel('"block_l" = "block_r"', label_for_charts="same block"),
        cll.ElseLevel(),
    ])


def settings() -> SettingsCreator:
    return SettingsCreator(
        link_type="dedupe_only",
        unique_id_column_name="unique_id",
        blocking_rules_to_generate_predictions=[
            block_on("aadhaar_token"),
            block_on("account_token"),
            block_on("skel_first", "skel_last", "panchayat_key"),
            block_on("skel_first", "skel_last", "birth_year"),
            block_on("skel_first", "rel_skel", "block"),          # surname missing, or changed at marriage
            block_on("skel_last", "rel_skel", "panchayat_key"),   # first name mistyped
            block_on("skel_first", "panchayat_key", "birth_year"),
            # surname and relation missing, birth year estimated: same first name, same panchayat, within 3 years
            'l.skel_first = r.skel_first and l.panchayat_key = r.panchayat_key and abs(l.birth_year - r.birth_year) <= 3',
            'l.skel_last = r.skel_last and l.panchayat_key = r.panchayat_key and l.sex = r.sex and abs(l.birth_year - r.birth_year) <= 2',
        ],
        comparisons=[
            name_comparison("first", "skel_first", "first_name"),
            name_comparison("last", "skel_last", "surname"),
            name_comparison("rel_first", "rel_skel", "relation_name"),
            cl.ExactMatch("middle").configure(term_frequency_adjustments=False),
            BIRTH,
            cl.ExactMatch("sex"),
            PLACE,
            cl.ExactMatch("aadhaar_token"),
            cl.ExactMatch("account_token"),
            # two lines on one ration card / family-register household / job card are two different people
            cl.CustomComparison(output_column_name="same_document", comparison_levels=[
                cll.CustomLevel('"doc_key_l" is null or "doc_key_r" is null or "register_l" <> "register_r"',
                               label_for_charts="different registers").configure(is_null_level=True),
                # fixed, not learnt: left to EM, siblings on one card (same surname, father, village) teach the
                # model that sharing a card means a match, which is exactly backwards
                cll.CustomLevel('"doc_key_l" = "doc_key_r"', label_for_charts="listed on the same document").configure(
                    m_probability=0.01 / 2**12, u_probability=0.01, fix_m_probability=True, fix_u_probability=True),  # -12 bits
                cll.ElseLevel(),
            ]),
        ],
        retain_intermediate_calculation_columns=False,
        retain_matching_columns=True,
    )


def run(df: pd.DataFrame, threshold: float, log=print):
    con = duckdb.connect()
    con.execute("SET memory_limit='6GB'")
    db = DuckDBAPI(connection=con)
    cols = ["unique_id", "record_id", "register", "first", "middle", "last", "skel_first", "skel_last", "rel_first",
            "rel_skel", "sex", "birth_date", "birth_year", "birth_exact", "panchayat_key", "block",
            "aadhaar_token", "account_token", "doc_key"]
    linker = Linker(df[cols], settings(), db)
    t = time.time()
    linker.training.estimate_probability_two_random_records_match(
        [block_on("aadhaar_token")], recall=0.8)
    linker.training.estimate_u_using_random_sampling(max_pairs=4e6)
    linker.training.estimate_parameters_using_expectation_maximisation(block_on("aadhaar_token"))
    linker.training.estimate_parameters_using_expectation_maximisation(block_on("skel_first", "skel_last", "panchayat_key"))
    log(f"trained in {time.time() - t:.0f}s")
    t = time.time()
    pred = linker.inference.predict(threshold_match_probability=0.2)
    log(f"predicted in {time.time() - t:.0f}s")
    t = time.time()
    clusters = linker.clustering.cluster_pairwise_predictions_at_threshold(pred, threshold_match_probability=threshold)
    log(f"clustered in {time.time() - t:.0f}s")
    return linker, pred.as_pandas_dataframe(), clusters.as_pandas_dataframe()


def household_consensus(df: pd.DataFrame, edges: pd.DataFrame, log=print) -> pd.DataFrame:
    """Second pass. Ration cards, family-register households and job cards list whole families. When two such
    documents already share at least two matched members, they describe one household, and a person with the same
    first name, same sex and a birth year within six years on both is the same person, even with the surname or
    relation name missing on one side. Returns the extra edges, each labelled with its reason."""
    con = duckdb.connect()
    con.execute("SET memory_limit='4GB'")
    con.register("rdf", df[["unique_id", "doc_key", "skel_first", "sex", "birth_year"]].dropna(subset=["doc_key"]))
    con.register("edf", edges[["unique_id_l", "unique_id_r"]])
    con.execute("create table r as select * from rdf")
    con.execute("create table e as select * from edf")
    # step by step: joined in one statement, the optimiser pairs all records by first name before narrowing to
    # linked households (billions of rows)
    con.execute("""create table ld as
        select least(a.doc_key, b.doc_key) d1, greatest(a.doc_key, b.doc_key) d2, count(*) shared
        from e join r a on a.unique_id = e.unique_id_l join r b on b.unique_id = e.unique_id_r
        where a.doc_key <> b.doc_key and split_part(a.doc_key, ':', 1) <> split_part(b.doc_key, ':', 1)
        group by 1, 2 having count(*) >= 2""")
    con.execute("create table la as select ld.d2, ld.shared, a.* from ld join r a on a.doc_key = ld.d1")
    extra = con.execute("""
        select la.unique_id unique_id_l, b.unique_id unique_id_r, la.shared
        from la join r b on b.doc_key = la.d2
        where la.skel_first = b.skel_first and la.sex = b.sex
          and (la.birth_year is null or b.birth_year is null or abs(la.birth_year - b.birth_year) <= 6)
    """).df()
    log(f"household consensus: {len(extra):,} member pairs on linked household documents")
    return extra


def components(ids: pd.Series, edges: pd.DataFrame) -> pd.Series:
    """Connected components by union-find; returns cluster id (smallest member id) per unique_id."""
    parent = {int(i): int(i) for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in zip(edges.unique_id_l.to_numpy(), edges.unique_id_r.to_numpy()):
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    return pd.Series({i: find(i) for i in parent})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--district", default="Almora")
    ap.add_argument("--threshold", type=float, default=0.9)
    a = ap.parse_args()
    GEN = ROOT / "data" / "gen" / a.district.lower().replace(" ", "_")
    df = pd.read_parquet(GEN / "standard.parquet")
    t0 = time.time()
    linker, pairs, _ = run(df, a.threshold)
    pairs.to_parquet(GEN / "pairs.parquet")
    strong = pairs[pairs.match_probability >= a.threshold][["unique_id_l", "unique_id_r"]]
    extra = household_consensus(df, strong)
    extra.to_parquet(GEN / "consensus_pairs.parquet")
    code = {"almora": "ALM", "udham_singh_nagar": "USN"}.get(GEN.name, GEN.name[:3].upper())

    def save(edges, name):
        comp = components(df.unique_id, edges)
        c = pd.DataFrame({"unique_id": comp.index.astype("int64"), "cluster_id": [f"{code}-{v}" for v in comp.values]})
        c.merge(df[["unique_id", "record_id"]], on="unique_id").to_parquet(GEN / name)
        return c
    save(strong, "clusters_pass1.parquet")          # kept to measure what the household pass adds
    clusters = save(pd.concat([strong, extra[["unique_id_l", "unique_id_r"]]]), "clusters.parquet")
    (GEN / "link_model.json").write_text(json.dumps(linker.misc.save_model_to_json(), indent=1))
    print(f"{len(df)} records, {len(pairs)} scored pairs, {clusters.cluster_id.nunique()} persons, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
