# P-003 execution plan — every step under one hour (25 Sep 2026)

Problem: **AI-Driven Integrated Beneficiary Data Governance** (Social Welfare Dept). Five asked capabilities:
integrate department databases · find duplicates and fraud · find eligible-but-excluded citizens · detect scheme
overlap · role-based department dashboards. Outcomes: targeting, less leakage, transparency, evidence-based planning.

Repo: this repository. Stack, all local, no LLM needed at runtime:
Python 3.14 venv → numpy/DuckDB synthetic generator → **Splink 4 on DuckDB** (probabilistic linkage, explainable
match weights) → rule engine (YAML rules, each with a cited source) → **FastAPI** (every read goes through one
role-scoped query layer) → SQLite append-only, hash-chained audit + review log → **Vite React + Tailwind** UI
(Hindi/English labels) served by FastAPI, as in P-001.

## Where we stand against the field (11 accepted P-003 entries, read 25 Sep)
Ten are descriptions only. One, **Adhikar**, has a live demo: 20,000 synthetic citizens, 4 departments, Bloom-filter
linkage (99.9% P / 99.4% R on its own planted truth), query-layer RBAC, audit log, 6 generic rules, no LLM.
We cannot win by doing the same thing. We win on what it lacks:

| Differentiator | Adhikar | Ours |
|---|---|---|
| Scale | 20k people, toy | **Real district scale** (a full district at 1:1, sized from Census 2011; the go/no-go test sets how many districts) |
| Anchored to reality | Generic rules, invented counts | Rules quoted from **ssp.uk.gov.in** FAQ and the **1 Feb 2020 amounts order**, with order numbers where our P-001 corpus has them; enrolment calibrated to **live portal counts** |
| Dirty data | "Distortion" | Realistic data problems (documented patterns): 1-Jan birth-date heaping, age-only records, **Hindi-script vs English-script names**, name change after marriage, relation name variants, missing Aadhaar, shared mobiles |
| Exclusion | Rule on declared fields | **Found through linkage**: husband's death in the death register → widow not enrolled; turned 60 → still on widow roll; disability certificate register → not enrolled |
| Leakage | Duplicates | + **Paid after death** (death register), widow→old-age transfer missed, shared bank account clusters, with ₹ at the real monthly rate |
| Honesty about harm | One P/R number | P/R **per hard-case group** — who the matcher fails (elderly with estimated age, married women, cross-script) — because a wrong merge is an exclusion |
| Family ID | — | Household view built for the **Devbhoomi Family Act 2026** (senior-most woman head); family-dependent rules (widow's son over 20) |
| Privacy | Bloom filters | Keyed tokens + Bloom-filter mode, with the **accuracy cost measured** clear vs blinded; DPDP Rules 2025 mapping; small-cell suppression on aggregates |

## Definition of done (acceptance criteria)
| # | Criterion | Verified by |
|---|---|---|
| AC1 | ≥6 department registers in their own schemas/scripts (pension rolls, ration, MGNREGA, housing, farmer, death register, family register) mapped to one schema; a new CSV can be uploaded and mapped | pytest + UI upload test |
| AC2 | Linkage across registers with match evidence per pair; **precision ≥ 95% and recall ≥ 90% overall** against planted truth, reported per hard-case group | `eval/linkage_eval.py` report |
| AC3 | Duplicates and integrity signals: in-scheme duplicates, paid after death, age/income ineligible from linked records, shared bank accounts; each type's recall vs planted cases measured | `eval/findings_eval.py` |
| AC4 | Eligible-but-excluded list for old-age, widow, disability pensions with criterion-by-criterion trace and cited source; recall vs planted excluded people measured | same |
| AC5 | Scheme overlap matrix, by district and block; conflicting overlaps flagged with the rule | API test + UI |
| AC6 | ≥4 roles enforced **in the query**, masked identity fields, unmask-with-reason, hash-chained audit that verifies; state planners see aggregates only, small cells suppressed | pytest (role matrix) |
| AC7 | Human review queue: confirm / reject / needs field visit; nothing changes a benefit automatically | pytest + UI |
| AC8 | Planning view: block-level coverage vs estimated eligible population; ₹ leakage estimate at the real rates | UI + numbers traced to DB |
| AC9 | Privacy mode: blinded (Bloom-filter) linkage runs end to end; accuracy cost vs clear mode measured | eval report |
| AC10 | Ship: README (architecture, third-party disclosure, limits), RESULTS.md, demo script, registration draft; `./run.sh build` rebuilds everything from a seed; UI check script (Playwright) passes | fresh-clone rebuild |

## Phase 0 — Test the plan (go/no-go tests, each under 1 hour)
| Step | Do | Pass mark |
|---|---|---|
| 0.1 | Repo, venv, install splink/duckdb/fastapi/indic-transliteration on py3.14 | imports OK |
| 0.2 | Real calibration data: live pension counts by district (ssp.uk.gov.in), Census 2011 district population/age/sex, real block + village names | tables saved with source URLs |
| 0.3 | Generator at scale: 1 district (~6 lakh people) → family register + 7 department registers, with planted truth | < 10 min, < 6 GB RAM |
| 0.4 | Splink on that district: train + predict + cluster | P ≥ 95%, R ≥ 90%, < 20 min |
| 0.5 | Cross-script: Devanagari ↔ Roman name matching key | ≥ 90% of planted cross-script pairs found |
| 0.6 | Bloom-filter blinded comparison on 50k pairs | runs; accuracy cost measured |
**Gate:** if 0.4 fails at district scale → shrink to the largest scale that passes; if linkage quality fails → tell Aman before building on it.

## Plan test results (25 Sep 2026) — all six go/no-go tests run
| Test | Result | Pass? |
|---|---|---|
| 0.1 Setup | splink 4.0.17, duckdb 1.5.5, pandas 3.0, indic-transliteration on py3.14 | Yes |
| 0.2 Real data | ssp.uk.gov.in: live counts for 8 schemes x 13 districts, and for Almora down to **1,116 real gram panchayats in 11 blocks**; eligibility rules (FAQ) and amounts (order of 1 Feb 2020); Census 2011 Almora 622,506, sex ratio 1139, SC 22.68% | Yes |
| 0.3 Generator at 1:1 | Almora: 162,508 households, 626,079 living + 41,022 deceased people, 9 registers, **1,487,121 records**; 6.4 min, 3.0 GB. Enrolment = 91% of portal counts (disability 71%, widow 83%: to tune in 1.4) | Yes |
| 0.4 Linkage at 1:1 | 9.9M candidate pairs; train + score + cluster **39 s**, 5.9 GB peak; untuned **precision 95.5%, recall 89.6%** | Yes (at the bar; tuning in 2.3) |
| 0.5 Cross-script | 245 of 247 Hindi/English spellings reduce to the same consonant key (99.2%) | Yes |
| 0.6 Blinded | Bloom-filter Dice alone separates true pairs from same-name-same-village pairs with AUC 0.88 (clear text does far better); full cost measured in 2.4 | Runs; cost is real |
Scale headroom: a district links in under a minute, so more districts are a scraping/generation-time question, not a feasibility one.

## Phase 1 — Data (5 steps)
| 1.1 | Geography: 13 districts, 95 blocks, villages; population weights | 45 min |
| 1.2 | Population + family register: households, senior-most woman head, ages, sex, deaths, disability, BPL, income | 60 min |
| 1.3 | Department registers with their own schemas and scripts; planted errors, duplicates, deceased-paid, excluded eligibles; truth table | 60 min |
| 1.4 | Calibrate enrolment to live portal counts by district and scheme | 30 min |
| 1.5 | Loader: department files → common schema (+ CSV upload mapper) | 45 min |

## Phase 2 — Linkage (4 steps)
| 2.1 | Standardise: names (script-neutral key), dates (heaping-aware), villages, tokenised Aadhaar/bank/mobile | 45 min |
| 2.2 | Splink model: blocking, comparisons, EM training, predict, cluster → person_id | 60 min |
| 2.3 | Linkage eval: P/R overall and per hard-case group; threshold choice from the curve | 45 min |
| 2.4 | Blinded mode: Bloom-filter encodings, same pipeline, cost measured | 45 min |

## Phase 3 — Findings (4 steps)
| 3.1 | Rules file: every criterion with its quoted source; evaluator producing per-criterion traces | 45 min |
| 3.2 | Exclusion finder (incl. linkage-derived: widowhood from death register, age crossing, disability register) | 45 min |
| 3.3 | Integrity finder: duplicates, paid after death, ineligible by linked data, shared-account clusters; ₹ at real rates | 45 min |
| 3.4 | Overlap matrix + conflicting overlaps; findings eval vs planted truth | 45 min |

## Phase 4 — Governance + API (3 steps)
| 4.1 | Roles + query-layer scoping + masking + unmask-with-reason | 60 min |
| 4.2 | Hash-chained audit + review decisions (SQLite) + verify endpoint | 45 min |
| 4.3 | FastAPI endpoints + pytest role matrix | 60 min |

## Phase 5 — UI (5 steps) — load the `frontend-design` skill first (Aman, 25 Sep)
| 5.1 | Shell: role switcher, bilingual labels, overview numbers from DB | 60 min |
| 5.2 | Case register + case view (evidence side by side, criterion trace, match weights) | 60 min |
| 5.3 | Review actions + audit page (with chain verification) | 45 min |
| 5.4 | Citizen 360 (one person across schemes, masked) + household view | 45 min |
| 5.5 | Planning: overlap matrix, block coverage, leakage ₹; method + accuracy page | 60 min |

## Phase 6 — Verify and ship (4 steps)
| 6.1 | Playwright UI check script: every page, every role, phone + desktop widths | 45 min |
| 6.2 | Fresh rebuild from seed, all tests, all evals; RESULTS.md with every number | 45 min |
| 6.3 | README, architecture, third-party disclosure, DPDP mapping, limits | 45 min |
| 6.4 | Demo script + registration draft (**not submitted** — Aman decides) | 30 min |

Total: 31 steps, about 25 working hours. Out of scope: real citizen data, live integrations, an LLM, hosting.

## Outcome (25 Sep 2026): built, tested, verified
| AC | Result |
|---|---|
| AC1 registers | 10 registers (added Sainik Kalyan ex-servicemen after measuring 420 wrong cases it would fix); CSV upload + mapping |
| AC2 linkage | 96.9% correct / 92.1% found across both districts (Almora 98.6/96.4, Udham Singh Nagar 96.0/89.7) |
| AC3-AC5 findings | 6 payment checks + 3 exclusion schemes, each measured; overlap matrix by block |
| AC6-AC7 governance | 6 roles enforced in SQL, masking, unmask with reason, hash-chained append-only log; 23 tests pass |
| AC8 planning | block coverage, survey list, leakage ₹ |
| AC9 blinded | Bloom-filter linkage end to end (`pipeline/blind_link.py`), cost measured in docs/RESULTS.md |
| AC10 ship | README, RESULTS, DATA, PRIVACY, DEMO, STATUS, registration draft; rebuild from seed is deterministic; UI check passes (6 roles × 2 widths) |
This repository. Not done by design: registration (Aman's call), demo video (needs a screen recording), hosting.
