"""A sample department file for the 'Check a department file' page: a Nanda Gaura (girl child) beneficiary list
as Women Empowerment and Child Development might export it, in its own column names. Most rows are girls already
in the Almora registers, written the way that department writes them; some are girls no register knows."""
import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
g = ROOT / "data" / "gen" / "almora"
r = random.Random(7)
pv = pd.read_parquet(g / "parivar.parquet")
girls = pv[(pv.relation.isin(["पुत्री", "पौत्री"])) & pv.dob.notna()].sample(240, random_state=7)
rows = [{"Beneficiary Name": x.member_name, "Father Name": x.father_husband_name, "DOB": x.dob,
         "Aadhaar No": x.aadhaar or "", "Village": x.gram_panchayat.title(), "Block": x.block.title()} for x in girls.itertuples()]
for i in range(60):
    rows.append({"Beneficiary Name": r.choice(["Aarohi", "Anvi", "Kritika", "Mansi", "Tanvi", "Diya", "Riya"]) + " " +
                 r.choice(["Bisht", "Negi", "Joshi", "Pant", "Arya", "Tamta"]), "Father Name": "",
                 "DOB": f"{r.randint(1, 28):02d}-{r.randint(1, 12):02d}-{r.randint(2009, 2025)}", "Aadhaar No": "",
                 "Village": r.choice(pv.gram_panchayat.unique()).title(), "Block": ""})
r.shuffle(rows)
out = ROOT / "data" / "samples"
out.mkdir(exist_ok=True)
pd.DataFrame(rows).to_csv(out / "nanda_gaura_sample.csv", index=False)
print(f"sample: {len(rows)} rows -> {out / 'nanda_gaura_sample.csv'}")
