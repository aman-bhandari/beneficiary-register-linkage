# Three-minute demo script

Start: `./run.sh serve`, open http://127.0.0.1:8003. Record at 1366×768. Speak the lines in quotes; the steps in
brackets are what the screen shows.

| Time | Screen | Say |
|---|---|---|
| 0:00 | Overview, acting as District Social Welfare Officer, Almora | "Every department in Uttarakhand keeps its own list of beneficiaries. This links ten of them for a whole district, 1:1, so a welfare officer can see who is left out and which payments are wrong." |
| 0:15 | Point to the opening sentence (people left out) | "The first thing it shows is the people who appear to meet every published criterion and get nothing. Finding them is the harder search, and the one the department answers for." |
| 0:30 | [Cases → filter Left out, High] open the first case | "Each case is a file. On the left, why it was raised: every criterion, the register the fact came from, and the rule's own words from the department's portal." |
| 0:50 | Right side: records from each department | "On the right, the records themselves. The pension roll writes her name in Hindi, the ration card in English, the Parivar register differently again. The system matched them, and here is why: field by field, with the weight each field carried." |
| 1:15 | Names are masked; type a reason; Show names | "Names stay masked until I say why I need them. The reason goes into a log nobody can edit." |
| 1:30 | Record a decision: Field visit needed | "I decide; the system never does. The stamp goes on the file, and no benefit changes." |
| 1:40 | [Cases → Paid after a registered death] open one | "The other side: a pension still paid eighteen months after a death the Health Department registered. ₹27,000 so far." |
| 1:55 | Switch role to the Hawalbagh block officer; try the same case URL | "A block officer sees only her block. The case from another block is not hidden. The database never returns it." |
| 2:10 | Switch to State planning officer → Planning | "The state planner sees blocks, not people. Coverage, leakage and overlaps, with small counts withheld." |
| 2:25 | Access log → Verify the chain | "Every view is logged, chained by hash. Edit one entry and verification names it." |
| 2:35 | Method page, accuracy tables | "And it is measured, not claimed: how often a match is right, and how often each finding is right, broken down by the groups most at risk: widows, people without Aadhaar, Muslim and Sikh names." |
| 2:50 | Back to Overview | "Real geography, real portal counts, real rules. Synthetic people. Ready for a real district extract." |

## Before recording

- `rm data/audit.db` for a clean access log, then restart the service.
- Pick a case in advance: `curl -s -H 'X-Role: dswo_almora' 'localhost:8003/api/cases?kind=exclusion&priority=high&size=5'`.
- The browser zoom at 100%. System fonts are not needed: the interface bundles its own.
