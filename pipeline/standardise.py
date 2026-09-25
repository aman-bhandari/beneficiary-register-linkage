"""Department registers -> one common record layout.

Each department keeps its own columns, script and conventions. This maps each to:
    record_id, register, name, rel_name, sex, birth_date, birth_year, birth_exact, age_only,
    aadhaar_token, account_token, mobile_token, panchayat_key, block, district
plus the folded name keys from normalise.split_name.

Identifiers are replaced by keyed tokens (HMAC-SHA256 under a key held by the linkage unit) at this step. No raw
Aadhaar, account or mobile number goes past it.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import date
from pathlib import Path

import pandas as pd

from normalise import parse_date, place_key, split_name

ROOT = Path(__file__).resolve().parent.parent


def gen_dir(district: str) -> Path:
    return ROOT / "data" / "gen" / district.lower().replace(" ", "_")
KEY = os.environ.get("LINKAGE_KEY", "demo-linkage-key-rotate-me").encode()

# register -> (department, column map). Column map: common field -> source column
REGISTERS = {
    "pension": ("Social Welfare", dict(name="applicant_name", rel_name="father_husband_name", sex="gender",
                                       dob="dob", aadhaar="aadhaar", account="bank_account", mobile="mobile",
                                       panchayat="gram_panchayat", block="block")),
    "parivar": ("Panchayati Raj", dict(name="member_name", rel_name="father_husband_name", sex="gender",
                                       dob="dob", aadhaar="aadhaar", panchayat="gram_panchayat", block="block",
                                       doc="family_id")),
    "ration": ("Food & Civil Supplies", dict(name="member_name", sex="gender", age="member_age", age_as_on="age_as_on",
                                             aadhaar="aadhaar", mobile="mobile", panchayat="village", block="block",
                                             doc="card_no")),
    "mgnrega": ("Rural Development", dict(name="worker_name", rel_name="father_husband_name", sex="gender",
                                          age="age", age_as_on="registered", aadhaar="aadhaar", account="account",
                                          panchayat="village", block="block", doc="job_card_no")),
    "kisan": ("Agriculture", dict(name="farmer_name", rel_name="father_husband_name", sex="gender", dob="dob",
                                  aadhaar="aadhaar", account="account", panchayat="village", block="block")),
    "death": ("Health (Civil Registration)", dict(name="deceased_name", rel_name="father_husband_name", sex="gender",
                                                  age="age_at_death", age_as_on="date_of_death", aadhaar="aadhaar",
                                                  panchayat="village", block="block")),
    "udid": ("Social Justice (UDID)", dict(name="name", rel_name="father_guardian_name", sex="gender", dob="dob",
                                           aadhaar="aadhaar", mobile="mobile", panchayat="village", block="block")),
    "treasury": ("Finance (Treasury)", dict(name="pensioner_name", sex="gender", dob="dob", aadhaar="aadhaar",
                                            account="account")),
    "pmay": ("Rural Development (Housing)", dict(name="beneficiary_name", rel_name="father_husband_name",
                                                 sex="gender", aadhaar="aadhaar", account="account",
                                                 panchayat="village", block="block")),
}
SEX = {"M": "M", "F": "F", "पुरुष": "M", "महिला": "F", "पु": "M", "म": "F", "MALE": "M", "FEMALE": "F"}


def token(v) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)) or v == "":
        return None
    return hmac.new(KEY, str(v).encode(), hashlib.sha256).hexdigest()[:20]


def birth_fields(row, cmap):
    """-> (birth_date, birth_year, birth_exact, age_only). A 1 January birth date is treated as an estimate."""
    if "dob" in cmap:
        d = parse_date(row.get(cmap["dob"]))
        if d:
            exact = not (d.day == 1 and d.month == 1)
            return (d if exact else None), d.year, exact, False
    if "age" in cmap and pd.notna(row.get(cmap["age"])):
        on = row.get(cmap["age_as_on"])
        yr = parse_date(on).year if isinstance(on, str) and parse_date(on) else int(on)
        return None, int(yr - int(row[cmap["age"]])), False, True
    return None, None, False, False


def standardise(reg: str, df: pd.DataFrame) -> pd.DataFrame:
    dept, cmap = REGISTERS[reg]
    out = []
    for row in df.to_dict("records"):
        nm = row.get(cmap["name"])
        n = split_name(nm if isinstance(nm, str) else "")
        rv = row.get(cmap["rel_name"]) if "rel_name" in cmap else ""
        rn = split_name(rv if isinstance(rv, str) else "")
        bd, by, bx, ao = birth_fields(row, cmap)
        out.append(dict(
            record_id=row["record_id"], register=reg, department=dept,
            name=row.get(cmap["name"]), first=n["first"] or None, middle=n["middle"] or None,
            last=n["last"] or None, name_fold=n["fold"] or None, skel_first=n["skel_first"] or None,
            skel_last=n["skel_last"] or None, rel_first=rn["first"] or None, rel_skel=rn["skel_first"] or None,
            sex=SEX.get(str(row.get(cmap["sex"])).upper(), SEX.get(row.get(cmap["sex"]))),
            birth_date=bd, birth_year=by, birth_exact=bx, age_only=ao,
            aadhaar_token=token(row.get(cmap.get("aadhaar", ""))),
            account_token=token(row.get(cmap["account"])) if "account" in cmap else None,
            mobile_token=token(row.get(cmap["mobile"])) if "mobile" in cmap else None,
            panchayat_key=place_key(row.get(cmap["panchayat"])) or None if "panchayat" in cmap else None,
            block=(row.get(cmap["block"]) or None) if "block" in cmap else None,
            doc_key=(f"{reg}:{row[cmap['doc']]}" if "doc" in cmap and row.get(cmap["doc"]) else None),
            script="dev" if any("\u0900" <= ch <= "\u097f" for ch in str(row.get(cmap["name"]) or "")) else "rom",
        ))
    return pd.DataFrame(out)


def load_all(district: str) -> pd.DataFrame:
    g = gen_dir(district)
    frames = [standardise(reg, pd.read_parquet(g / f"{reg}.parquet")) for reg in REGISTERS
              if (g / f"{reg}.parquet").exists()]
    df = pd.concat(frames, ignore_index=True)
    df["unique_id"] = df.index.astype("int64")
    df["birth_date"] = pd.to_datetime(df["birth_date"])
    df["birth_year"] = df["birth_year"].astype("Int64")
    return df


if __name__ == "__main__":
    import argparse
    import time
    ap = argparse.ArgumentParser()
    ap.add_argument("--district", default="Almora")
    a = ap.parse_args()
    t = time.time()
    d = load_all(a.district)
    d.to_parquet(gen_dir(a.district) / "standard.parquet")
    print(d.groupby("register").size().to_dict(), f"{len(d):,} records in {time.time() - t:.0f}s")
