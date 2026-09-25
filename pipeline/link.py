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
import numpy as np
import pandas as pd
import splink.comparison_level_library as cll
import splink.comparison_library as cl
from splink import DuckDBAPI, Linker, SettingsCreator, block_on

ROOT = Path(__file__).resolve().parent.parent


def name_comparison(col: str, skel: str, label: str) -> cl.CustomComparison:
    extra = []
    if col == "first":
        # compound given names are written joined or spaced: 'Ramlal' / 'Ram Lal' (Ram + middle Lal)
        joined = ('("first_l" || replace(coalesce("middle_l", \'\'), \' \', \'\')) = "first_r" or '
                  '("first_r" || replace(coalesce("middle_r", \'\'), \' \', \'\')) = "first_l"')
        extra = [cll.CustomLevel(joined, label_for_charts="same compound name, joined or spaced")]
    return cl.CustomComparison(
        output_column_name=label,
        comparison_levels=[
            cll.NullLevel(col),
            cll.ExactMatchLevel(col, term_frequency_adjustments=(col in ("first", "last"))),
            *extra,
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
                # one register listing a person in two different households is rare; namesakes are not
                cll.ElseLevel().configure(label_for_charts="same register, another household",
                                          m_probability=0.03, u_probability=1.0, fix_m_probability=True, fix_u_probability=True),  # -5 bits
            ]),
        ],
        retain_intermediate_calculation_columns=False,
        retain_matching_columns=True,
    )


COLS = ["unique_id", "record_id", "register", "first", "middle", "last", "skel_first", "skel_last", "rel_first",
        "rel_skel", "sex", "birth_date", "birth_year", "birth_exact", "panchayat_key", "block",
        "aadhaar_token", "account_token", "doc_key"]


def connect(tmp: Path) -> duckdb.DuckDBPyConnection:
    tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET memory_limit='5GB'")
    con.execute(f"SET temp_directory='{tmp}'")
    con.execute("SET max_temp_directory_size='40GB'")      # a runaway join fails instead of filling the disk
    con.execute("SET preserve_insertion_order=false")
    return con


def run(con, threshold: float, log=print):
    """Train and score inside DuckDB; records never pass through pandas."""
    db = DuckDBAPI(connection=con)
    linker = Linker("recs", settings(), db)
    t = time.time()
    linker.training.estimate_probability_two_random_records_match([block_on("aadhaar_token")], recall=0.8)
    linker.training.estimate_u_using_random_sampling(max_pairs=4e6, seed=2026)   # deterministic builds
    linker.training.estimate_parameters_using_expectation_maximisation(block_on("aadhaar_token"))
    linker.training.estimate_parameters_using_expectation_maximisation(block_on("skel_first", "skel_last", "panchayat_key"))
    log(f"trained in {time.time() - t:.0f}s")
    t = time.time()
    pred = linker.inference.predict(threshold_match_probability=0.2)
    log(f"scored in {time.time() - t:.0f}s")
    return linker, pred


def household_consensus(con, pred_table: str, log=print) -> pd.DataFrame:
    """Second pass. Ration cards, family-register households and job cards list whole families. When two such
    documents already share at least two matched members, they describe one household, and a person with the same
    first name, same sex and a birth year within six years on both is the same person, even with the surname or
    relation name missing on one side. Returns the extra edges, each labelled with its reason."""
    con.execute("create or replace table r as select unique_id, doc_key, first, skel_first, sex, birth_year, aadhaar_token from recs where doc_key is not null")
    # households are recognised from any two members matched with at least moderate confidence: two different
    # people each resembling a member of the same other household is what namesakes almost never produce
    con.execute(f"create or replace table ew as select unique_id_l, unique_id_r from {pred_table} where match_probability >= 0.5")
    con.execute("""create or replace table ld as
        select least(a.doc_key, b.doc_key) d1, greatest(a.doc_key, b.doc_key) d2, count(distinct a.unique_id) shared
        from ew e join r a on a.unique_id = e.unique_id_l join r b on b.unique_id = e.unique_id_r
        where a.doc_key <> b.doc_key and split_part(a.doc_key, ':', 1) <> split_part(b.doc_key, ':', 1)
        group by 1, 2 having count(distinct a.unique_id) >= 2""")
    con.execute("create or replace table la as select ld.d2, ld.shared, a.* from ld join r a on a.doc_key = ld.d1")
    # step by step: joined in one statement, the optimiser pairs all records by first name before narrowing to
    # linked households (billions of rows)
    extra = con.execute("""
        select la.unique_id unique_id_l, b.unique_id unique_id_r, la.shared
        from la join r b on b.doc_key = la.d2
        where la.sex = b.sex
          and (la.skel_first = b.skel_first or jaro_winkler_similarity(la.first, b.first) >= 0.85)
          and (la.birth_year is null or b.birth_year is null or abs(la.birth_year - b.birth_year) <= 6)
          and not (la.aadhaar_token is not null and b.aadhaar_token is not null and la.aadhaar_token <> b.aadhaar_token)
    """).df()
    # one person per member: if a member resembles two people on the other document, take neither
    extra = extra[~extra.duplicated("unique_id_l", keep=False) & ~extra.duplicated("unique_id_r", keep=False)]
    log(f"household consensus: {len(extra):,} member pairs on linked household documents")
    return extra


def components(n: int, edges: pd.DataFrame) -> np.ndarray:
    """Connected components by union-find over record ids 0..n-1; returns the root (smallest id) per record."""
    parent = np.arange(n, dtype=np.int64)

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root
    for a, b in zip(edges.unique_id_l.to_numpy(), edges.unique_id_r.to_numpy()):
        ra, rb = find(int(a)), find(int(b))
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    return np.array([find(i) for i in range(n)], dtype=np.int64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--district", default="Almora")
    ap.add_argument("--threshold", type=float, default=0.9)
    ap.add_argument("--strong-weight", type=float, default=4.0,
                    help="first-pass edges without an agreeing identifier need at least this match weight")
    a = ap.parse_args()
    GEN = ROOT / "data" / "gen" / a.district.lower().replace(" ", "_")
    t0 = time.time()
    con = connect(ROOT / "data" / "tmp")
    con.execute(f"create table recs as select {', '.join(COLS)} from read_parquet('{GEN / 'standard.parquet'}')")
    n = con.execute("select count(*) from recs").fetchone()[0]
    linker, pred = run(con, a.threshold)
    con.execute(f"copy (select * from {pred.physical_name}) to '{GEN / 'pairs.parquet'}' (format parquet)")
    # hard constraints: two records carrying different Aadhaar numbers, or birth years more than ten years apart,
    # are never joined, however similar the names; this is what stops chains of namesakes merging
    con.execute(f"""create table e as select p.unique_id_l, p.unique_id_r from {pred.physical_name} p
        join recs l on l.unique_id = p.unique_id_l join recs r on r.unique_id = p.unique_id_r
        where p.match_probability >= {a.threshold}
          -- a first-pass join needs an agreeing identifier, relation name or exact birth date, or overwhelming
          -- name-and-place evidence; the household pass recovers the rest far more safely than namesakes allow
          and (p.match_weight >= {a.strong_weight} or p.gamma_aadhaar_token = 1 or p.gamma_account_token = 1
               or p.gamma_relation_name >= 3 or p.gamma_birth = 4)
          and not (l.aadhaar_token is not null and r.aadhaar_token is not null and l.aadhaar_token <> r.aadhaar_token)
          and not coalesce(abs(l.birth_year - r.birth_year) > 10, false)""")
    strong = con.execute("select * from e").df()
    extra = household_consensus(con, pred.physical_name)
    extra.to_parquet(GEN / "consensus_pairs.parquet")
    code = {"almora": "ALM", "udham_singh_nagar": "USN"}.get(GEN.name, GEN.name[:3].upper())
    rid = con.execute("select unique_id, record_id from recs order by unique_id").df()
    assert (rid.unique_id.to_numpy() == np.arange(n)).all(), "unique_id must be 0..n-1"

    def save(edges, name):
        root = components(n, edges)
        pd.DataFrame({"unique_id": rid.unique_id, "record_id": rid.record_id,
                      "cluster_id": [f"{code}-{v}" for v in root]}).to_parquet(GEN / name)
        return len(np.unique(root))
    save(strong, "clusters_pass1.parquet")          # kept to measure what the household pass adds
    persons = save(pd.concat([strong, extra[["unique_id_l", "unique_id_r"]]]), "clusters.parquet")
    (GEN / "link_model.json").write_text(json.dumps(linker.misc.save_model_to_json(), indent=1))
    scored = con.execute(f"select count(*) from {pred.physical_name}").fetchone()[0]
    print(f"{n:,} records, {scored:,} scored pairs, {len(extra):,} household pairs, {persons:,} persons, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
