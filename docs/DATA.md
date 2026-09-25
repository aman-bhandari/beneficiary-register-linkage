# What the data is

No real citizen record is used anywhere. The people and their records are generated. Everything the generated
world is measured against is real and cited below.

## Real, and where it comes from

| What | Source | Read |
|---|---|---|
| Pensioners per scheme for all 13 districts | ssp.uk.gov.in, district table, financial year 2026-27, instalment 5 | 25 Sep 2026 |
| Pensioners per scheme for every gram panchayat and town in Almora (1,497 units, 11 blocks) and Udham Singh Nagar (403 units) | ssp.uk.gov.in, district → area → tehsil → block → panchayat drill-down. Aggregate counts only; no individual page was opened | 25 Sep 2026 |
| Eligibility rules for old-age, widow and disability pensions | ssp.uk.gov.in/FAQ.aspx, quoted word for word in `rules/schemes.yaml` | 25 Sep 2026 |
| Pension amount (₹1,500 a month) and the ₹48,000 annual income line | ssp.uk.gov.in/Pension_Amount_Details.aspx (Government Order dated 1 February 2020) | 25 Sep 2026 |
| District size, sex ratio, Scheduled Caste and Scheduled Tribe shares | Census 2011: Almora 622,506 (SC 22.68%); Udham Singh Nagar 1,648,902 (SC 14.45%, ST 7.46%) | Census 2011 District Census Handbooks, as quoted on Wikipedia |
| Udham Singh Nagar's language mix | Census 2011: Hindi 62%, Punjabi 10%, Bengali 7.9%, Urdu 6.4%, Kumaoni 5.2%, Tharu 2.9% | same |
| Names | Common Kumaoni, plains Hindu, Scheduled Caste, Sikh, Muslim, Bengali and Tharu given names and surnames, each in Devanagari with the Roman spellings records actually use | `pipeline/names.py` |

The scraper is `scraper/ssp_counts.js`; its output is committed under `data/ref/` with the fetch time.

## Generated, and how

`pipeline/generate.py` builds each district one tehsil at a time from a fixed seed (2026), so every run produces
the same people.

**People and households.** Each panchayat gets a population in proportion to its pension counts, scaled to the
district's Census size (urban share: Almora 10%, Udham Singh Nagar 35.6%). Households are drawn from four shapes:
an old person alone (mostly widows), an elderly couple whose children have left, a nuclear family, and three
generations. Hill households are older and smaller; plains households younger and larger. Deaths in the last six
years are part of the population, so the death register has real people to describe. Families do not reuse a
first name. Towns are addressed by ward.

**Eligibility, as in truth.** Old-age: 60 or over, from a BPL household or with family income up to ₹4,000 a
month, and no Treasury or defence pension. Widow: widowed, 18 to 60, same income test. Disability: certified 40%
or more, same income test.

**Enrolment, calibrated to the portal.** For every panchayat and scheme, eligible people are enrolled until the
count matches the portal. Who gets left out is not random: people living alone and people without Aadhaar are
left out more often. Where the portal pays more people than meet every criterion, the remainder are filled from
people who nearly qualify (usually on income), and marked as such in the truth. The portal's widow roll is far
larger than the number of poor widows aged 18 to 60, so poor widows over 60 fill the rest of it, as they
evidently do in practice.

| | Almora | Udham Singh Nagar |
|---|---|---|
| Households | about 164,000 | about 360,000 |
| Living people | 626,000 | 1.65 million |
| Portal pensioners (old-age + widow + disability) | 77,943 | 162,000 (approx.) |
| Enrolled in the synthetic world | 99% of the portal figure | see `summary.json` |

**Ten registers, each in its own department's layout.**

| Register | Department | Script | Birth | Aadhaar seeded |
|---|---|---|---|---|
| Pension roll (eSPAN) | Social Welfare | Hindi | birth date | 88% |
| Parivar register | Panchayati Raj | Hindi | birth date | 40% |
| Ration cards | Food & Civil Supplies | English | age when the card was last updated | 93% |
| MGNREGA job cards | Rural Development | English | age at registration | 85% |
| PM-KISAN | Agriculture | English | birth date for half | 99% |
| Death register | Health (Civil Registration) | Hindi or English | age at death | 35% |
| UDID disability certificates | Social Justice | English | birth date | 85% |
| Treasury pension roll | Finance | English | exact birth date | 97% |
| Ex-servicemen register | Sainik Kalyan | English | birth date | 90% |
| PMAY-G housing | Rural Development | English | none | 90% |

**Realistic damage.** Every register writes each person down its own way:
- Names: Hindi or English script, a different accepted spelling (Kamla/Kamala, Mohd/Md), typos, a middle name or
  the Devi/Kaur suffix present or absent, a missing surname, initials, a maiden name.
- Dates: 45% of older people's birth dates are the 1 January estimate. Ages are often rounded to a multiple of
  five, and ages on a card go stale from the year it was issued.
- Relation names: the father's or the husband's name, depending on the form.
- Places: panchayat names re-typed with doubled vowels or a dropped 'h'.
- Identifiers: Aadhaar missing, and 0.6% of Aadhaar numbers with two digits transposed.
- Coverage: family phones shared across a household; deaths not struck off the Parivar register (55%) or the
  ration card (50%).

## Planted problems, with sizes (assumptions)

| Planted | Share of the pension roll | What it models |
|---|---|---|
| Paid after death | 1.2% | a pensioner who died in the last three years still on the roll |
| Enrolled twice in one scheme | 0.4% | a second record typed differently, paid into another account |
| Two pensions at once | 0.3% | a widow drawing both the widow and the old-age pension |
| Income above the limit | 0.8% | a retired state employee (Treasury pension) on the old-age roll |
| Age inflated | 0.5% | true age 52 to 58, roll says 60 or more |
| Ghost | 0.2% | a pension record for a person who exists nowhere else |
| Account ring | about 1 per 20,000 pensions | 6 to 12 unrelated pensions redirected into one account |

These sizes are assumptions chosen to be plausible, not estimates of Uttarakhand's actual leakage. The system's
accuracy in finding them is what is measured, not how much leakage there is.

## What this data cannot show

- **Income.** No register holds it. A priority ration card proves low income; its absence proves nothing. Defence
  pensions are visible only through the ex-servicemen register, private income not at all.
- **People on no register at all.** They cannot be found by linking records. They are counted in the evaluation
  as missed, and only a door-to-door survey reaches them.
- **The real pattern of errors.** Real registers will fail in ways this generator does not model. The first step
  of any pilot is to run the linkage on a real district extract and measure it against a hand-checked sample.
