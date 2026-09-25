# Results

Every figure is measured against the planted truth of the synthetic population (`eval/report.py` →
`eval/results.json`). Build: seed 2026, 25 September 2026.

## The two districts

| | Almora (hill) | Udham Singh Nagar (plains) |
|---|---|---|
| Households | 163,842 | 371,425 |
| Living people | 626,046 | 1,650,197 |
| Deceased in the last six years (for the death register) | 45,353 | 90,629 |
| Register records, ten departments | 1,481,204 | 3,231,909 |
| Pensioners on the portal (old-age, widow, disability) | 77,943 | 163,179 |
| Enrolled in the synthetic world | 77,116 (98.9%) | 163,094 (99.9%) |
| of which near-eligible fill (usually income) | 4,931 | 1,944 |
| Generation time | 19 s | 49 s |
| Linkage time (train, score, household pass) | about 20 s | about 45 s |

## Record linkage

Correct = share of joined pairs that are truly one person (precision). Found = share of true pairs that were
joined (recall).

| Group | Almora correct | Almora found | USN correct | USN found |
|---|---|---|---|---|
| **Everyone** | **98.6%** | **96.4%** | **96.0%** | **89.7%** |
| Aged 60 and over | 98.9% | 95.4% | 97.0% | 89.2% |
| Married women | 98.6% | 97.0% | 96.1% | 91.1% |
| Widows | 98.3% | 97.2% | 95.2% | 92.7% |
| No Aadhaar | 95.6% | 84.9% | 86.9% | 70.7% |
| Scheduled Caste | 97.9% | 95.5% | 98.0% | 87.3% |
| Scheduled Tribe (Tharu, Buksa) | — | — | 95.3% | 85.7% |
| Muslim names | — | — | 93.3% | 92.5% |
| Sikh names | — | — | 96.3% | 90.4% |
| Bengali names | — | — | 92.0% | 96.4% |
| Hindi-script vs English-script pairs (found) | — | 96.4% | — | 89.3% |

Across both districts together (3.55 million true pairs): **96.9% correct, 92.1% found**. The plan's bar was 95%
and 90%.

**Who the matcher fails most:** people without Aadhaar, especially in the plains (71% found). They depend
entirely on names, dates and places, and plains panchayats are large, with many namesakes. This is where
exclusion from a linkage system starts. It is why a case is never raised on a person while a nearby unlinked
record could be theirs.

### What each part contributes

| Configuration | Almora correct / found | USN correct / found |
|---|---|---|
| First pass only (probabilistic model) | 98.6% / 91.0% | 96.2% / 79.6% |
| + household consensus | 98.6% / 96.4% | 96.0% / 89.7% |

The household pass recognises that a ration card and a Parivar household describe one family once two members
match. It then joins same-named members of similar age even when the surname is missing. It adds 5 to 10 points of
recall at no cost in precision.

### Tuning, measured

| First-pass evidence bar W | USN correct / found | Almora correct / found |
|---|---|---|
| none (probability 0.9 only) | 93.6% / 88.3% | 98.0% / 97.2% |
| 5 | 97.2% / 86.0% | 99.2% / 95.0% |
| 6 | 98.2% / 82.0% | 99.5% / 92.5% |
| 12 | 99.4% / 76.8% | 99.9% / 78.9% |
| **4, with the wider household pass (chosen)** | **96.0% / 89.7%** | **98.6% / 96.4%** |

W is the minimum match weight a first-pass join needs when no identifier, relation name or exact birth date agrees.

## Findings

### Payments to check

| Finding | Almora planted | found | right when raised | USN planted | found | right when raised |
|---|---|---|---|---|---|---|
| Paid after a registered death | 925 | 78.6% | 92.3% | 1,957 | 68.0% | 83.5% |
| Enrolled twice in one scheme | 308 | 68.5% | 89.0% | 652 | 62.0% | 78.8% |
| Two pensions at once | 231 | 93.5% | 96.0% | 490 | 94.7% | 87.1% |
| Income above the limit (Treasury) | 616 | 97.4% | 88.4% | 1,305 | 94.3% | 90.6% |
| Age disagrees across registers | 385 | 47.3% | 100.0% | 815 | 25.1% | 100.0% |
| Account shared by unrelated pensioners | 72 | 97.2% | 100.0% | 96 | 100.0% | 100.0% |

"Right when raised" counts a flagged pension as right when the person is truly dead, even if that record was not
one the generator planted.

### People left out

| Scheme | Almora truly left out | raised | right | high priority right | USN truly left out | raised | right | high priority right |
|---|---|---|---|---|---|---|---|---|
| Old-age | 14,509 | 4,915 | 88.2% | 90.1% | 24,403 | 10,651 | 65.9% | 80.5% |
| Widow | 1,462 | 142 | 95.8% | 95.8% | 2,485 | 174 | 87.4% | 87.4% |
| Disability | 3,376 | 768 | 99.2% | 99.2% | 10,878 | 2,634 | 98.3% | 98.3% |

Cases are raised only on strong evidence: a priority ration card for income, and an exact birth date or two
agreeing registers for age. That keeps the register trustworthy but finds 23% to 30% of the truly left out. The
rest are split three ways:
- **Survey list:** a State Food Scheme card only, so income is likely low but not proven. Counted per block on the
  Planning page.
- **No evidence:** no ration card at all.
- **Invisible:** widows whose husband's death predates the registers.

Widow recall is the weakest (6% to 9%). A widow is found only when her husband's death is on record in the same
household, and most older widows lost their husbands before digital registration began.

Remaining wrong old-age cases in the plains are mostly people just under 60, deaths that were never registered,
and pension records the linkage missed. The near-miss guard catches a share of the last two.

### Removed after measurement

| Tried | Result | Decision |
|---|---|---|
| "Not known to any other register" (ghost pensioners) as a case | Right 5% (plains) to 31% (hills): most are linkage misses, not ghosts | Not raised. The Method page reports the count: 218 (Almora) and 2,139 (USN) uncorroborated records against 154 and 326 planted ghosts |
| Cases on a State Food Scheme card | 28,000 low-priority cases in Almora alone, about 20% right | Survey list instead |
| Near-miss search across the whole block | Suppressed nine real cases in ten | Narrowed to the panchayat |
| Letting the model learn the "same document" weight | It learnt that siblings on one card are a match (precision fell to 87%) | Weight fixed at −12 bits |
| An ex-servicemen register | 420 of 1,036 wrong high-priority cases in Almora were ex-servicemen whose defence pension nothing showed | Added the Sainik Kalyan register; those cases disappeared |

## Tests

- `./run.sh test`: 23 tests pass. They cover:
  - name folding across scripts and communities;
  - masking, and the audit log's tamper detection (an edit is refused; a forced edit is found at its exact entry);
  - the role matrix against the built warehouse: row scope for district and block, refusals, small-cell
    suppression, unmask with a reason, review changing no benefit, every access logged;
  - a department CSV mapped and matched.
- `ui/check/ui_check.cjs`: every page, for all six roles, at 390 px and 1366 px. It checks for a heading, no
  sideways scroll, no console error, and tabs matching the role. It then opens a case end to end: masked, revealed
  with a reason, stamped with a decision. Finally, a block officer is refused another block's case by URL.
