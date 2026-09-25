# एकत्र · Ekatra — integrated beneficiary data governance

**UKIS 2026 · Problem P-003 · Social Welfare Department, Uttarakhand**

Ekatra links the beneficiary registers ten departments keep separately and shows a welfare officer two things
each department cannot see alone:

- **who is left out:** a person who meets every published criterion for a pension and receives none;
- **which payments look wrong:** paid after a registered death, enrolled twice, income above the limit, and more.

Every finding is a case for an officer, with the rule's own words, each department's record side by side, and the
reason the records were judged to be one person. Nothing changes a benefit automatically.

It runs on two whole districts at 1:1 scale, a hill district and a plains district, built from real geography
and real published counts. The people in it are synthetic.

## Built on what is real

| Real | Synthetic |
|---|---|
| All 1,116 gram panchayats of Almora and the panchayats and towns of Udham Singh Nagar, as listed on the Social Welfare Department's pension portal | Every person, household and record |
| Pensioners per panchayat and scheme on that portal (read 25 Sep 2026); the synthetic rolls match them | Planted problems (deaths still paid, duplicates, rings) whose sizes are stated assumptions |
| Eligibility rules and the ₹1,500 rate, quoted word for word with their source | |
| Census 2011 size, sex ratio, SC/ST shares and language mix of each district | |
| Naming conventions of Kumaoni, plains Hindu, Sikh, Muslim, Bengali and Tharu communities, in both scripts | |

See `docs/DATA.md` for every source and assumption.

## Measured, not claimed

Against the planted truth of 2.3 million synthetic people and 4.7 million records:

| | Almora (hill) | Udham Singh Nagar (plains) |
|---|---|---|
| Record pairs joined correctly / true pairs found | 98.6% / 96.4% | 96.0% / 89.7% |
| Hindi-script vs English-script pairs found | 96.4% | 89.3% |
| Pensions paid after a registered death: found / right when raised | 78.6% / 92.3% | 68.0% / 83.5% |
| Pensioners with a Treasury income above the limit: found / right | 97.4% / 88.4% | 94.3% / 90.6% |
| Accounts receiving several unrelated pensions: found / right | 97.2% / 100% | 100% / 100% |
| "Left out" cases right, old-age (high priority) | 88.2% (90.1%) | 65.9% (80.5%) |
| "Left out" cases right, disability | 99.2% | 98.3% |

With names blinded (Bloom-filter encodings; the matcher never sees a name), recall drops by 0.3 points in Almora
and 4.2 in Udham Singh Nagar; precision is unchanged.

Weakest spots, stated plainly: people without Aadhaar in the plains (71% of their record pairs found), and widows
(a case needs the husband's registered death, so most older widows cannot be found from records).

Full results, including what did not work, are in `docs/RESULTS.md`.

## How it works

```
ssp.uk.gov.in ─► scraper/ssp_counts.js ─► pension counts per panchayat (real)
                                              │
pipeline/generate.py ─► people, households, ten department registers, each in its own layout and script
pipeline/standardise.py ─► one layout; names folded to script-neutral keys; Aadhaar, account, mobile → keyed tokens
pipeline/link.py ─► Splink (Fellegi-Sunter, EM-trained) on DuckDB, then a household-consensus pass
pipeline/findings.py ─► cases: left out, paid wrongly; each with a criterion trace citing rules/schemes.yaml
pipeline/warehouse.py ─► data/warehouse.duckdb: what the application may read (no planted truth)
api/ ─► FastAPI; the officer's posting folded into every query; masking; hash-chained access log
ui/ ─► React interface in Hindi and English
eval/ ─► linkage and findings accuracy against the planted truth
```

**Matching across scripts.** भगवती देवी बिष्ट on the pension roll and BHAGAWATI BIST on a ration card are
transliterated, folded (aspiration, long vowels, v/w/b, final schwa) and reduced to a consonant skeleton (`bgbt`),
so the two can be compared at all. The model then scores each pair field by field and learns the weights.

**Households.** Ration cards, Parivar registers and job cards list whole families. When two such documents share
two matched members, they are one household, and a same-named member of similar age on both is the same person,
even with the surname missing. This pass adds 5 to 10 points of recall and is more than 99% precise.

**Refusing to guess.** Two records with different Aadhaar numbers are never joined. A person is not raised as
"left out" while a nearby pension or death record could be theirs and was not linked. A State Food Scheme card
alone does not prove income under ₹4,000, so those people form a survey list, not cases.

## Governance

Six roles, each enforced in the query. Examples: a block officer sees their own block only; a state planner sees
figures only, with cells under 10 withheld; another department sees its own programme's overlaps. Names stay masked
until an officer opens a case and states why. Aadhaar and bank numbers are never shown in full. Every access is
appended to a log chained by hash, which the database refuses to edit. See `docs/PRIVACY.md`, including the DPDP
2023 mapping.

## Running it

Everything runs on one laptop (tested on 16 GB RAM, WSL2). No cloud service and no language model.

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
(cd ui && npm install && npx vite build)
./run.sh build        # generate, link, find, evaluate, assemble: 16 minutes for both districts, deterministic
./run.sh serve        # http://127.0.0.1:8003
./run.sh test         # unit and API tests
~/.claude/browser/run.sh ui/check/ui_check.cjs    # every page, every role, phone and desktop
```

`./run.sh scrape` refreshes the portal counts (Chromium via Playwright; about 40 minutes per district). The
committed counts in `data/ref/` are enough to build.

## Third-party components

Splink 4 (MIT, UK Ministry of Justice) · DuckDB (MIT) · pandas, NumPy (BSD) · indic-transliteration (MIT) ·
FastAPI, Uvicorn, Pydantic (MIT/BSD) · PyYAML (MIT) · React (MIT) · Vite (MIT) · Tailwind CSS (MIT) · Mukta and
Tiro Devanagari Hindi fonts (SIL OFL, via Fontsource) · Playwright (Apache-2.0). Portal figures are the Social
Welfare Department's public counts. All code in `pipeline/`, `api/`, `ui/src/`, `eval/` and `scraper/` is original
to this entry.

## Limits

- The people are synthetic. Real registers will fail in ways the generator does not model; a pilot starts by
  measuring the linkage on a real district extract against a hand-checked sample.
- No register shows income. Cases say so, and ask for income to be confirmed at the visit.
- People on no register cannot be found by linking records; only a survey reaches them.
- Logins are demo headers; a deployment would use the state's single sign-on.
