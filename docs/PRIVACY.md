# Privacy design

Linking welfare data across departments creates the very risk the linkage is meant to govern: one place that
knows everything about everyone. This is how the design limits that, and what each control does in the prototype.

| Risk | Control | Where it is enforced | Verified by |
|---|---|---|---|
| One department reads another's beneficiary list | Identifiers are replaced by keyed tokens (HMAC-SHA256) at standardisation; matching runs on tokens and folded name keys. A blinded mode encodes names as Bloom filters, so the matcher never sees them | `pipeline/standardise.py`, `pipeline/blind.py` | tokens only in the warehouse |
| An officer sees rows outside their posting | The officer's district and block are folded into every SQL query. Rows outside the posting are never selected, and the API reports how many it refused | `api/governance.py: scope_sql` | `tests/test_api.py` role matrix |
| Names seen without need | Names, birth dates and document numbers are masked until an officer opens one case and states a reason (15+ characters). The reveal covers that case, for that posting only | `api/main.py: unmask` | test: masked, then unmasked with a reason |
| Aadhaar or bank numbers exposed | Always masked to the last four digits, even after unmasking | `mask_fields` | test |
| Planners single out a person from counts | Aggregate cells under 10 are withheld for statewide and other-department roles | `suppress` | test: no overlap cell under 10 |
| Access leaves no trace | Every list, open, unmask, decision, refusal and upload is appended to a log. Each entry carries the hash of the one before it, and the database refuses edits and deletions | `Audit` (SQLite with triggers) | test: an edit is refused; a forced edit is detected at the exact entry |
| A machine decides a citizen's entitlement | Nothing changes a benefit. Cases are recommendations; the only actions are an officer's review decision and a note | `review` endpoint | test: review leaves records and pensions unchanged |
| A wrong match excludes someone | Linkage accuracy is measured per vulnerable group, not only on average. Two records with different Aadhaar numbers are never joined. A case is not raised while a nearby unlinked record could belong to the same person | `pipeline/link.py`, `pipeline/findings.py` | `docs/RESULTS.md` |

## Digital Personal Data Protection Act 2023 and Rules 2025

As we read it, a department processing beneficiary data to deliver a subsidy or benefit relies on the Act's
legitimate use for the State (section 7(b)): data the person earlier consented to give for a benefit, or data
already held in a State register. That use comes with standards set in the Rules. How the design meets them:

| Standard | In this design |
|---|---|
| Lawful processing for a stated purpose | One purpose per role, stated on screen: verifying eligibility and payments. No other use is built |
| Data minimisation | The warehouse keeps only the fields a case needs. Identifiers are tokenised; income is never collected |
| Accuracy | Every case shows the source record from each department side by side, so an officer can see a wrong match |
| Storage limitation | Reviewed cases can be purged on a schedule. Not built in the prototype: a retention period is the department's decision |
| Security safeguards | Role-scoped queries, masking, keyed tokens, append-only hash-chained log |
| Accountability | The access log answers who saw which person, when, and why |
| A contact for the data principal | Out of scope for the prototype; the department's grievance officer in a deployment |

## What the prototype does not do

- Logins are demo headers (`X-Role`). A deployment would sit behind the state's single sign-on (Jan Parichay) with
  the posting taken from the HRMS.
- Keys are environment variables with demo defaults. A deployment would hold them in a key-management service and
  rotate them.
- Bloom-filter encodings resist casual reading but have published frequency attacks. The key stays with the
  linkage unit, and encodings are never published.
