# Registration draft — P-003 (not submitted)

The team decides whether and when to register. The rules allow one entry per person, so this and the P-001 draft
cannot both be submitted under the same name.

**Problem:** P-003 AI-Driven Integrated Beneficiary Data Governance

**Solution title:** Ekatra: who is left out, and which payments are wrong, across ten department registers

**Description** (for the form):

Ekatra links the beneficiary registers that Uttarakhand's departments keep separately and raises cases for welfare
officers. It covers the Social Welfare pension roll, the Parivar register, ration cards, MGNREGA job cards,
PM-KISAN, the death register, UDID disability certificates, the Treasury pension roll, the ex-servicemen register
and PMAY housing. It finds two things no department can see alone. First, people who meet every published
criterion for old-age, widow or disability pension and receive none, including widows found through their
husband's death registration. Second, payments that look wrong: pensions paid after a registered death,
duplicate enrolments, pensioners with a Treasury income above the limit, and several pensions paid into one
account.

It runs on two whole districts at 1:1 scale: Almora (hill) and Udham Singh Nagar (plains). That is 2.3 million
people and 4.7 million register records, built on real geography. The pension counts for every gram panchayat
match the Social Welfare portal as of 25 September 2026. The rules are quoted word for word from the department's
portal. The people are synthetic; no real citizen data is used.

Names are matched across Hindi and English script and across community naming conventions: Kumaoni, Sikh,
Muslim, Bengali and Tharu. A household pass uses whole-family documents to link people whose surname is missing.
Measured against planted truth, 96.9% of joined record pairs are correct and 92.1% of true pairs are found (98.6% / 96.4% in Almora, 96.0% / 89.7% in Udham Singh Nagar). Accuracy is reported separately for widows, people without Aadhaar, and Scheduled
Caste, Scheduled Tribe, Muslim and Sikh names, because a wrong match is where exclusion begins.

Every case shows each criterion, the register it came from, the rule's text, and why the records were judged to
be one person. Access is scoped in the database query to the officer's district or block. Names stay masked until
an officer states a reason. Every access goes to a hash-chained log. No benefit is changed automatically. Runs
offline on a laptop, with no language model.

**Prototype URL:** none yet (runs locally; a video and the source can be shared).
