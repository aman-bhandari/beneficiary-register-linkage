"""Assemble what the application may read into one DuckDB file: data/warehouse.duckdb.

It holds linked people, their register records, cases, overlaps, the linkage explanation for each person and the
calibration against the portal. It never holds the planted truth: accuracy figures are copied in as numbers
from the evaluation reports, so the application cannot peek at the answers.

    python pipeline/warehouse.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "data" / "gen"
OUT = ROOT / "data" / "warehouse.duckdb"

# the register fields an officer may see on a record (identifiers masked at the API)
SHOW = {
    "pension": ["pension_id", "scheme", "applicant_name", "father_husband_name", "gender", "dob", "category",
                "gram_panchayat", "block", "bank_account", "aadhaar", "mobile", "sanction_year", "status"],
    "parivar": ["family_id", "member_name", "relation", "gender", "dob", "father_husband_name", "gram_panchayat",
                "remark", "aadhaar"],
    "ration": ["card_no", "card_type", "head_of_family", "member_name", "member_age", "age_as_on", "gender",
               "relation_to_head", "aadhaar", "mobile", "village"],
    "mgnrega": ["job_card_no", "worker_name", "father_husband_name", "gender", "age", "registered", "caste",
                "account", "aadhaar", "village", "active"],
    "kisan": ["registration_no", "farmer_name", "father_husband_name", "gender", "dob", "aadhaar", "account",
              "land_ha", "village"],
    "death": ["registration_no", "deceased_name", "gender", "age_at_death", "date_of_death", "father_husband_name",
              "village", "aadhaar"],
    "udid": ["udid_no", "name", "father_guardian_name", "gender", "dob", "disability_type", "percentage", "aadhaar",
             "mobile", "village"],
    "treasury": ["ppo_no", "pensioner_name", "dob", "gender", "monthly_pension", "treasury", "account", "aadhaar"],
    "sainik": ["service_no", "name", "rank", "regiment", "dob", "gender", "monthly_pension", "aadhaar", "account", "village"],
    "pmay": ["beneficiary_id", "beneficiary_name", "father_husband_name", "gender", "sanction_year", "account",
             "aadhaar", "village"],
}
DEPT = {"pension": "Social Welfare", "parivar": "Panchayati Raj", "ration": "Food & Civil Supplies",
        "mgnrega": "Rural Development", "kisan": "Agriculture", "death": "Health (Civil Registration)",
        "udid": "Social Justice (UDID)", "treasury": "Finance (Treasury)", "pmay": "Rural Development (Housing)",
        "sainik": "Sainik Kalyan (ex-servicemen)"}


def main():
    t = time.time()
    if OUT.exists():
        OUT.unlink()
    con = duckdb.connect(str(OUT))
    con.execute("SET preserve_insertion_order=false")
    first = True
    for g in sorted(p for p in GEN.iterdir() if (p / "cases.parquet").exists()):
        mode = "create table" if first else "insert into"
        sel = lambda name: f"read_parquet('{g / name}')"
        units = pd.read_parquet(g / "units.parquet")
        district = units.district.iloc[0]
        con.execute(f"{mode} people {'as' if first else ''} select * from {sel('people.parquet')}")
        con.execute(f"{mode} cases {'as' if first else ''} select * from {sel('cases.parquet')}")
        con.execute(f"{mode} overlap {'as' if first else ''} select * from {sel('overlap.parquet')}")
        con.execute(f"{mode} units {'as' if first else ''} select district, tehsil, block, panchayat, area, old_age, widow, disability from {sel('units.parquet')}")
        # records: the common fields plus the department's own fields as JSON, for the evidence view
        parts = []
        for reg, cols in SHOW.items():
            if not (g / f"{reg}.parquet").exists():
                continue
            raw = pd.read_parquet(g / f"{reg}.parquet", columns=["record_id"] + cols)
            raw["fields"] = raw[cols].astype(str).where(raw[cols].notna(), None).to_dict("records")
            raw["fields"] = raw["fields"].map(lambda d: json.dumps(d, ensure_ascii=False))
            parts.append(raw[["record_id", "fields"]].assign(register=reg, department=DEPT[reg]))
        fields = pd.concat(parts, ignore_index=True)
        con.register("fields_df", fields)
        con.execute(f"""{mode} records {'as' if first else ''}
            select c.record_id, c.cluster_id person_key, f.register, f.department, s.name, s.script,
                   s.birth_year, s.sex, s.block, '{district}' district, f.fields,
                   s.aadhaar_token, s.skel_first, s.panchayat_key
            from {sel('clusters.parquet')} c
            join fields_df f using (record_id)
            join {sel('standard.parquet')} s using (record_id)""")
        con.unregister("fields_df")
        # linkage explanation: the scored pairs that hold each person together, and the household pass
        con.execute(f"""{mode} link_pairs {'as' if first else ''}
            select cl.record_id record_l, cr.record_id record_r, cl.cluster_id person_key, p.match_weight,
                   p.match_probability, p.gamma_first_name, p.gamma_surname, p.gamma_relation_name, p.gamma_middle,
                   p.gamma_birth, p.gamma_sex, p.gamma_place, p.gamma_aadhaar_token, p.gamma_account_token,
                   p.gamma_same_document, 'model' as via
            from {sel('pairs.parquet')} p
            join {sel('clusters.parquet')} cl on cl.unique_id = p.unique_id_l
            join {sel('clusters.parquet')} cr on cr.unique_id = p.unique_id_r
            where cl.cluster_id = cr.cluster_id and p.match_probability >= 0.5""")
        con.execute(f"""insert into link_pairs
            select cl.record_id, cr.record_id, cl.cluster_id, null, null, null, null, null, null, null, null, null,
                   null, null, null, 'household: ' || h.shared || ' other members already matched'
            from {sel('consensus_pairs.parquet')} h
            join {sel('clusters.parquet')} cl on cl.unique_id = h.unique_id_l
            join {sel('clusters.parquet')} cr on cr.unique_id = h.unique_id_r""")
        model = json.loads((g / "link_model.json").read_text())
        summ = json.loads((g / "summary.json").read_text())
        con.execute(f"{mode} meta {'as' if first else ''} select ? district, ? link_model, ? summary",
                    [district, json.dumps(model), json.dumps(summ, ensure_ascii=False)])
        first = False
        print(f"  {district}: loaded [{time.time() - t:.0f}s]")
    # accuracy figures, copied from the evaluation reports (the truth itself stays out)
    acc = ROOT / "eval" / "results.json"
    con.execute("create table accuracy as select ? report", [acc.read_text() if acc.exists() else "{}"])
    for tbl, cols in {"people": ["person_key", "district", "block"], "cases": ["case_id", "person_key", "district", "block"],
                      "records": ["person_key", "record_id"], "link_pairs": ["person_key"]}.items():
        for c in cols:
            con.execute(f"create index idx_{tbl}_{c} on {tbl}({c})")
    for tbl in ("people", "cases", "records", "link_pairs", "overlap", "units"):
        print(f"  {tbl}: {con.execute(f'select count(*) from {tbl}').fetchone()[0]:,}")
    con.close()
    print(f"warehouse: {OUT} ({OUT.stat().st_size / 1e6:.0f} MB) in {time.time() - t:.0f}s")


if __name__ == "__main__":
    main()
