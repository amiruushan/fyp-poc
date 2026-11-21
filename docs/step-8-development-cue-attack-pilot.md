# Step 8: Factual cues and bounded development pilot

This offline development pilot follows protocol v2 and the frozen Step 6 models. It uses the 2% benign FPR operating thresholds and only primary development rows. It does not visit archived URLs, render pages, edit HTML, use method-validation or final rows, or train models. The user-facing cue is a factual feature value plus a fixed template; the code records feature identities and values in the local matrix rather than constructing persuasive warning text.

## 1. Factual cue audit

An independent recomputation parsed archived URL/HTML for **all 2,303 development records** using the Step 3 pinned offline dependencies. Every one of the **27,636 feature checks** matched the Step 4 source-derived matrix within `1e-9` (zero failures). HTML hashes were checked against the matrix. This validates the factual source values used to select cues on the development partition. It does not assess human comprehension, model explanation quality, or a live website.

Families were frozen in the Step 3 registry. S takes the first factual feature in the hash-preassigned family without model relevance. M-family takes the most locally relevant distinct eligible feature in that family; relevance is a positive reduction in the frozen phishing score when the coordinate is replaced by its train-only median/mode. M-global takes the top eligible feature across all families. No fitted score, threshold, or attribution is disclosed to the simulated attacker. `html_content` contains only one registry feature and therefore cannot enter the distinct same-family contrast.

## 2. Feature-change grammar

Numeric candidates are the training 5th and 95th percentiles, rounded inward for integer counts; binary candidates toggle. Each candidate starts from the original vector, changes at most five coordinates, and stays within these train-derived bounds. The search enumerates one-coordinate candidates before combinations, with a cue coordinate ranked first in S/M and registry order in V. It receives binary predictions only, counts the initial verdict plus each submitted candidate, and stops at the first flip. The budget grid is 1–5 changed coordinates and 5/10/20/40 total binary queries. All arms share candidates, model, start, tie-breaking, and query caps; only coordinate priority differs.

This grammar is an **abstract feature-space relaxation**. It does not enforce all dependencies among URL-derived and HTML-derived features and does not establish that any candidate corresponds to a real page or URL. No rejected candidates arose under these simple numeric bounds. K0 and K2 get the same coordinate interface, and this fixed search does not use semantic definitions; their behavior is therefore identical. This pilot cannot test RQ3's knowledge interaction. A later versioned protocol must either implement genuinely distinct knowledge procedures or narrow that claim.

## 3. Paired pilot results

The pooled-success rule selected **one changed coordinate and five total queries** in both detectors. It selected this point using pooled V/S/M-family success among values between 10% and 90%, without using the arm differences. The matched subset was fixed by source cue availability and model relevance before attack outcomes.

| Detector | Initially detected phishing starts | Distinct same-family pairs (groups) | V bypass | S bypass | M-family bypass | Paired M-family − S |
|---|---:|---:|---:|---:|---:|---:|
| Logistic regression | 592 | 347 (268) | 42.4% | 24.2% | 73.8% | +49.6 percentage points |
| Shallow boosted trees | 762 | 290 (236) | 72.8% | 66.6% | 74.1% | +7.6 percentage points |

Those three arm rates use only the **same matched pairs** for each detector. Exploratory 95% connected-group bootstrap intervals for the paired differences are +43.7 to +55.3 points (logistic) and +4.3 to +11.1 points (boosting), with 2,000 development replicates. These are pilot intervals after development choices, not final confirmatory intervals.

Across **all** initially detected phishing starts, V/S/M-global-with-V-fallback bypass rates are respectively 45.4%/25.7%/91.2% for logistic and 69.8%/63.0%/72.0% for boosting. The all-start rates and matched rates have different denominators and must not be pooled or compared as though they estimate the same policy. S cue availability is 100% under the source feature registry; distinct matched M-family availability is 347/592 (58.6%) for logistic and 290/762 (38.1%) for boosting. The full budget grid, family exclusions, query means, and model hashes are in `data/manifests/compphish_v4_step8_pilot.json`. A row-level selected-point log with serials but no URLs or HTML is local and Git-ignored at `data/processed/step8_pilot_selected_log.csv`.

## 4. Decision and next gate

The development curve has nonsaturated pooled headroom and hundreds of eligible connected groups. It supports continuing to a **precision/feasibility review**, not to final evaluation. The large logistic contrast is specific to this coordinate-priority search and its abstract percentile edits; it is not an operational phishing evasion result. The low boosted matched coverage and K0/K2 equivalence limit the planned factorial hypothesis. Before any final run, resolve institutional data-handling requirements, define an honest knowledge-condition amendment or narrow RQ3, evaluate dependency/feasibility limits, project clustered precision and an equivalence margin, then freeze analysis and model/protocol hashes.

Reproduce in an environment containing the Step 3 pinned parser libraries and Step 6 modeling libraries. For the Step 3 environment created earlier:

```sh
"$HOME/.venvs/fyp-poc-step3/bin/python" -m pip install -r requirements-step6-models.txt
"$HOME/.venvs/fyp-poc-step3/bin/python" scripts/run_step8_development_pilot.py
```

The script rejects matrix or model hash mismatches, checks every development feature against source, and prints only aggregate pilot results. Dataset-derived row logs remain ignored by Git.
