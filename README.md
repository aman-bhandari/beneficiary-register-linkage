# Ekatra (एकत्र): integrated beneficiary data governance

UKIS 2026, problem P-003 (Social Welfare Department, Uttarakhand).

Links the beneficiary registers of ten departments for two districts and produces cases for a welfare officer:
people who meet every published pension criterion and receive none, and payments that look wrong (paid after a
registered death, duplicate enrolment, income above the limit, and others). Officers record decisions; no benefit
changes automatically. Districts: Almora (hill) and Udham Singh Nagar (plains) at 1:1 scale. Geography, portal
counts, rules and census shares are real; people and records are synthetic.

## What is in this repository

| Path | Contents |
|---|---|
| `pipeline/generate.py` | Synthetic people, households and ten registers per district, each in its own layout and script, with planted problems |
| `pipeline/standardise.py` | One layout; script-neutral name keys; keyed Aadhaar, account and mobile tokens |
| `pipeline/link.py` | Record linkage with Splink (Fellegi-Sunter, EM-trained) on DuckDB, then a household-consensus pass |
| `pipeline/blind_link.py` | The same linkage on Bloom-filter encodings; the matcher never sees a name |
| `pipeline/findings.py` | Cases with a criterion trace citing `rules/schemes.yaml` |
| `pipeline/warehouse.py` | `data/warehouse.duckdb`, the only data the application reads |
| `rules/schemes.yaml` | Eligibility rules for three pensions, quoted with sources |
| `api/` | FastAPI; `governance.py`: six roles, query scoping, masking, hash-chained access log |
| `ui/` | React + Vite interface, Hindi and English; `ui/check/ui_check.cjs` page check |
| `eval/report.py` | Linkage and finding accuracy against the planted truth |
| `scraper/ssp_counts.js` | Pension counts per panchayat from ssp.uk.gov.in |
| `data/ref/` | Portal counts (read 25 Sep 2026), committed |
| `tests/` | 23 tests: normalisation, governance, API role matrix |
| `docs/` | STATUS, PLAN, RESULTS, DATA, PRIVACY, DEMO, REGISTRATION-DRAFT |

## Status (25 September 2026)

| Item | State |
|---|---|
| Acceptance criteria (10, `docs/PLAN.md`) | All met; table in `docs/STATUS.md` |
| Scale | 2 districts, 2.3 million people, 4.7 million records, 10 registers |
| Findings | 6 integrity types and "left out" cases; scheme overlap matrix; coverage and ₹ leakage by block |
| Governance | 6 roles; masking with recorded reason; hash-chained log; review queue |
| Rebuild | From seed in 16 min; reproduces every figure |
| Tests, page check | 23 pass; page check passes for 6 roles at 2 widths |
| Demo video, hosted demo, registration | Not done |

## Results (against the planted truth)

| | Almora (hill) | Udham Singh Nagar (plains) |
|---|---|---|
| Linkage precision / recall | 98.6% / 96.4% | 96.0% / 89.7% |
| Hindi-script vs English-script pairs found | 96.4% | 89.3% |
| Paid after a registered death: recall / precision | 78.6% / 92.3% | 68.0% / 83.5% |
| Income above the limit: recall / precision | 97.4% / 88.4% | 94.3% / 90.6% |
| Several unrelated pensions on one account: recall / precision | 97.2% / 100% | 100% / 100% |
| "Left out" old-age cases precision (high priority) | 88.2% (90.1%) | 65.9% (80.5%) |
| "Left out" disability cases precision | 99.2% | 98.3% |

Blinded linkage: recall 0.3 points lower in Almora, 4.2 in Udham Singh Nagar; precision unchanged. Weakest groups:
plains people without Aadhaar (71% of pairs found) and widows (a case needs the husband's registered death).
Full results: `docs/RESULTS.md`.

## Run

Tested on Ubuntu (WSL2), 16 GB RAM. No GPU, no language model, no cloud service.

| Requirement | Note |
|---|---|
| Python 3.12+ | tested 3.14 |
| Node 20+ | tested 24; builds the interface |
| RAM | 16 GB recommended for the build |
| Disk | about 3 GB under `data/` after a build |
| Internet | pip and npm only; portal counts are committed |

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
./run.sh ui
./run.sh build            # both districts, about 16 min, deterministic
./run.sh serve            # http://127.0.0.1:8003
./run.sh test             # needs the build
```

Roles: pick one in the interface, or send `X-Role: <key>` to the API (`/api/roles` lists them).

| Command | Note |
|---|---|
| `./run.sh build Almora` | one district, about 3 min; one scope test then fails by design |
| `./run.sh ui-check` | Playwright page check; needs `npm install && npx playwright install chromium` |
| `./run.sh scrape` | refresh portal counts, about 40 min per district |

Generated, not committed: `data/gen/`, `data/warehouse.duckdb`, `data/audit.db`.

## Method

- Cross-script matching: names are transliterated, folded (aspiration, long vowels, v/w/b, final schwa) and reduced
  to a consonant skeleton (भगवती देवी बिष्ट and BHAGAWATI BIST both give `bgbt`), then scored field by field with
  learned weights.
- Households: two family documents that share two matched members are one household; same-named members of similar
  age on both are one person. Adds 5 to 10 recall points at over 99% precision.
- Records with different Aadhaar numbers are never joined. A person is not raised as "left out" while an unlinked
  nearby pension or death record could be theirs. A State Food Scheme card alone does not prove income under
  ₹4,000; those people go to a survey list, not to cases.

## Governance

Six roles enforced in the query: a block officer sees their own block; a state planner sees figures only, with cells
under 10 withheld; another department sees its own overlaps. Names stay masked until a reason is recorded. Aadhaar
and bank numbers are never shown in full. Every access is appended to a hash-chained log. DPDP 2023 mapping:
`docs/PRIVACY.md`.

## Third-party components

Splink 4 (MIT) · DuckDB (MIT) · pandas, NumPy (BSD) · indic-transliteration (MIT) · FastAPI, Uvicorn, Pydantic ·
PyYAML · React · Vite · Tailwind CSS · Mukta and Tiro Devanagari Hindi fonts (SIL OFL) · Playwright (Apache-2.0).
Portal figures are the Social Welfare Department's public counts.

## Limits

- People are synthetic; a pilot needs a real district extract with a hand-checked sample.
- No register shows income; cases ask for it to be confirmed at the visit.
- People on no register are not found by linking.
- Most older widows are not found: a case needs the husband's registered death.
- Plains people without Aadhaar: 71% of pairs found.
- Logins are demo headers, not single sign-on.
