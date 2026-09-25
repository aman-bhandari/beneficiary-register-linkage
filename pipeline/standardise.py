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
    "sainik": ("Sainik Kalyan", dict(name="name", sex="gender", dob="dob", aadhaar="aadhaar", account="account",
                                     panchayat="village", block="block")),
    "pmay": ("Rural Development (Housing)", dict(name="beneficiary_name", rel_name="father_husband_name",
                                                 sex="gender", aadhaar="aadhaar", account="account",
                                                 panchayat="village", block="block")),
}
SEX = {"M": "M", "F": "F", "पुरुष": "M", "महिला": "F", "पु": "M", "म": "F", "MALE": "M", "FEMALE": "F"}


def token(v) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)) or v == "":
        return None
    return hmac.new(KEY, str(v).encode(), hashlib.sha256).hexdigest()[:20]


def birth_columns(df: pd.DataFrame, cmap: dict) -> pd.DataFrame:
    """birth_date (exact only), birth_year, birth_exact, age_only. A 1 January birth date is an estimate."""
    n = len(df)
    out = pd.DataFrame({"birth_date": [None] * n, "birth_year": [None] * n, "birth_exact": [False] * n,
                        "age_only": [False] * n}, index=df.index)
    if "dob" in cmap:
        d = pd.to_datetime(df[cmap["dob"]], format="%d-%m-%Y", errors="coerce")
        has = d.notna()
        exact = has & ~((d.dt.day == 1) & (d.dt.month == 1))
        out.loc[has, "birth_year"] = d[has].dt.year
        out.loc[exact, "birth_date"] = d[exact].dt.date
        out.loc[exact, "birth_exact"] = True
    if "age" in cmap:
        need = out.birth_year.isna() & df[cmap["age"]].notna()
        on = df.loc[need, cmap["age_as_on"]]
        yr = (pd.to_datetime(on, format="%d-%m-%Y", errors="coerce").dt.year
              if pd.api.types.is_string_dtype(on) else pd.to_numeric(on))
        out.loc[need, "birth_year"] = (yr - df.loc[need, cmap["age"]]).astype("float")
        out.loc[need, "age_only"] = True
    return out


def standardise(reg: str, df: pd.DataFrame) -> pd.DataFrame:
    """Column-wise: each distinct name is parsed once, however many records carry it."""
    dept, cmap = REGISTERS[reg]
    col = lambda k: df[cmap[k]] if k in cmap else pd.Series([None] * len(df), index=df.index)
    names = col("name").where(col("name").map(lambda v: isinstance(v, str)), "")
    rels = col("rel_name").where(col("rel_name").map(lambda v: isinstance(v, str)), "")
    parsed = {v: split_name(v) for v in pd.unique(pd.concat([names, rels]))}
    pn = names.map(parsed)
    pr = rels.map(parsed)
    part = lambda s, k: s.map(lambda d: d[k] or None)
    b = birth_columns(df, cmap)
    tok = lambda k: col(k).map(token) if k in cmap else pd.Series([None] * len(df), index=df.index)
    places = {v: place_key(v) or None for v in pd.unique(col("panchayat"))} if "panchayat" in cmap else {}
    out = pd.DataFrame({
        "record_id": df["record_id"], "register": reg, "department": dept, "name": col("name"),
        "first": part(pn, "first"), "middle": part(pn, "middle"), "last": part(pn, "last"),
        "name_fold": part(pn, "fold"), "skel_first": part(pn, "skel_first"), "skel_last": part(pn, "skel_last"),
        "rel_first": part(pr, "first"), "rel_skel": part(pr, "skel_first"),
        "sex": col("sex").map(lambda v: SEX.get(str(v).upper(), SEX.get(v))),
        "birth_date": b.birth_date, "birth_year": b.birth_year, "birth_exact": b.birth_exact, "age_only": b.age_only,
        "aadhaar_token": tok("aadhaar"), "account_token": tok("account"), "mobile_token": tok("mobile"),
        "panchayat_key": col("panchayat").map(places) if "panchayat" in cmap else None,
        "block": col("block") if "block" in cmap else None,
        "doc_key": (reg + ":" + df[cmap["doc"]].astype(str)) if "doc" in cmap else None,
        "script": names.map(lambda v: "dev" if any("\u0900" <= ch <= "\u097f" for ch in v) else "rom"),
    })
    return out


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
