# Status: P-003 complete

The definition of done was set in `~/workshop/documents/p003-plan.md` before any code. Against it:

| # | Acceptance criterion | State | Evidence |
|---|---|---|---|
| AC1 | ≥6 registers in their own schemas and scripts, mapped to one; a new CSV can be uploaded and mapped | **Met**: 10 registers | `pipeline/standardise.py`; Add a file page; `test_department_file_links_to_known_people` |
| AC2 | Linkage precision ≥95%, recall ≥90% overall, reported per hard-case group | **Met**: 96.9% / 92.1% across both districts | `docs/RESULTS.md`. Udham Singh Nagar alone: 96.0% / 89.7% |
| AC3 | Duplicates and integrity signals, each type's recall measured | **Met**: 6 types | `docs/RESULTS.md`, Method page |
| AC4 | Exclusion list for three pensions with criterion trace and cited source; recall measured | **Met** | Case file; `rules/schemes.yaml`; recall stated with its reasons |
| AC5 | Scheme overlap matrix by district and block; conflicting overlaps flagged | **Met** | Planning page; "Two pensions at once" cases |
| AC6 | ≥4 roles enforced in the query, masking, unmask with reason, verifying hash chain, suppressed small cells | **Met**: 6 roles | `tests/test_api.py`, `tests/test_governance.py` |
| AC7 | Review queue: confirm / not a problem / field visit; nothing changes a benefit | **Met** | `test_review_is_recorded_and_changes_no_benefit`; the decision stamp |
| AC8 | Block coverage vs estimated eligible; ₹ leakage at real rates | **Met** | Planning page |
| AC9 | Blinded (Bloom-filter) linkage runs; accuracy cost measured | **Met**: end to end on both districts; costs 0.3 points of recall in Almora, 4.2 in Udham Singh Nagar | `pipeline/blind_link.py`; `docs/RESULTS.md` |
| AC10 | README, results, demo script, registration draft; rebuild from seed; UI check passes | **Met**: a rebuild from nothing (16 min) reproduced every figure exactly | this folder; `scripts_rebuild.sh`; `ui/check/ui_check.cjs` |

## What is left for Aman

1. **Record the three-minute demo video.** The script is `docs/DEMO.md`.
2. **Decide on registration.** The draft is in `docs/REGISTRATION-DRAFT.md`. It is one entry per person, so P-001
   and P-003 cannot both go in under your name.
3. **Optional: host a read-only demo** for the prototype URL. The rival entry "Adhikar" has one, so this is worth
   considering.

## Running it

```bash
cd ~/workshop/ukis-p003
./run.sh serve                     # http://127.0.0.1:8003
./run.sh build                     # full rebuild from seed, about 16 minutes
./run.sh test                      # 23 tests
~/.claude/browser/run.sh ui/check/ui_check.cjs
```
