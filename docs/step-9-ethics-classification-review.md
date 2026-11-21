# Ethics classification review for the CompPhish FYP

This is a project-specific assessment for the student's declaration, not a University ethics decision. The student reports studying at IIT Sri Lanka on a University of Westminster affiliated FYP and expects Class 1. The supplied *CSE UG Project Ethics Guidance v1.0* is dated 19 October 2026 (local PDF SHA-256 `60279d6cd16ae23beaf9d2039cac9ed6c2350e16bfb52f1ac72cd68c89f4dbb7`). It says every undergraduate student submits an ethics declaration on Blackboard with the proposal; low/no-risk Class 1 requires supervisor sign-off. A submitted declaration is not the same as an accepted one. Changes affecting the declaration must be discussed and resubmitted. The guide directs supervisors to apply the Class 1 screening questions and their own risk assessment, and to use the University's current classification guidance where needed.

## Factual project description for the declaration

The PoC trains two classifiers on the public CompPhish v4 URL/archived-HTML dataset. It extracts features from inert archived files and runs local, bounded changes to feature vectors to compare detector verdicts under different factual cue disclosures. It has no recruited participants, interviews, live URL visits, live phishing-site edits, credential collection, or deployment. It stores the publisher's raw archive and row-level derived files locally; raw and processed rows are ignored by Git. GitHub PRs contain code, aggregate metrics, and manifests. The archived HTML is unsanitized and has not been audited to establish that it contains no directly or indirectly identifiable personal data. Model-directed phishing-evasion research may also trigger the University's security-sensitive screening question even when it is offline and defensive in intent.

## Class 1 screen: evidence and unresolved answers

| Screen | Current evidence | Classification status |
|---|---|---|
| Human/animal participants | None in the current PoC | Appears compatible with Class 1 |
| Personal safety, tissue, fieldwork | None in the current PoC | Appears compatible with Class 1 |
| Identifiable/traceable personal data | Public archived HTML/URLs have not been audited for this | Unknown; cannot answer No yet |
| Security-sensitive research | Study concerns cybersecurity and model-guided phishing-detector evasion | Must be decided by supervisor under current Westminster policy |
| Low/no risk of harm, safeguards | Offline work and no published raw artifacts reduce risk, but cybersecurity and dissemination still matter | Supervisor assessment required |
| Accepted ethics declaration | No acceptance or sign-off evidence supplied | Pending |

The [Westminster classification table](https://www.westminster.ac.uk/sites/default/public-files/general-documents/Criteria-and-Classification-for-review-table.pdf) lists no security-sensitive research and no identifiable personal data among Class 1 criteria, with student supervisor sign-off. The [security-sensitive research policy](https://www.westminster.ac.uk/sites/default/public-files/general-documents/Security-Sensitive-Research-and-KE-Activity-Policy.pdf) expressly includes cybersecurity and directs designated security-sensitive work to Class 4 review and a restricted University store. Whether this specific bounded undergraduate PoC is so designated is an institutional judgment, not something the dataset license or this repo can decide. The [research ethics policy](https://www.westminster.ac.uk/sites/default/public-files/general-documents/Research-and-knowledge-exchange-ethics-policy_0.pdf) applies ethics across the research lifecycle, including data use and dissemination.

## Decision needed before further evaluation

Submit or update the declaration with the accurate project description above and the current storage/publication plan. Ask the IIT/Westminster supervisor to record (1) the security-sensitive screening decision, (2) the personal-data screening decision for archived URL/HTML, (3) whether Class 1 is accepted or a different review route is required, and (4) the permitted storage and dissemination arrangements. If security-sensitive status is assigned, follow the University's designated review and secure-storage process; do not infer that local personal-computer storage or GitHub metadata publication is permitted. Record the decision and any conditions in a versioned project note before method-validation or final evaluation. Do not upload the raw archive, derived row-level matrix, or local query log for review unless the supervisor specifies an approved channel.
