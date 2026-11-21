# Step 9: Resolve pilot scope and project paired precision

This is a development-informed protocol amendment, not a final result. The frozen Step 8 search and models are unchanged. No final or method-validation feature values, predictions, cue outcomes, or attack outcomes were inspected in this step.

## Decision 1: State the attack endpoint precisely

The candidate grammar independently changes up to five model-input coordinates to training-derived percentile values. The selected point changes one coordinate within five total binary queries. URL and HTML features have dependencies, so a modified vector may not map to any valid URL or page. Protocol v3 explicitly limits the study to **bounded abstract feature-vector prediction flips**. The paper must not call these usable phishing-site edits, website evasion, rendered-page changes, or deployable attacks. We keep the full Step 8 grammar and log; no hidden feasibility claim is added. A page-space check would require a separate documented method and cannot retrofit these results.

## Decision 2: Narrow the knowledge claim

K0 and K2 were operationally identical in Step 8 because the fixed search did not consume semantic definitions. Protocol v3 therefore uses **K0 only** for its two confirmatory contrasts (one per detector). K2 may be stated descriptively as equivalent under this implementation, but RQ3/H3 knowledge-interaction inference is not tested. The model families can still be compared descriptively. This amendment changes the claim and multiplicity family, not the attack procedure; rerunning Step 8 would reproduce the same outcomes.

The primary estimand remains paired M-family minus S on the preassigned same-family eligible subset. The selected budget is frozen at one changed coordinate and five total queries, chosen on development by pooled arm success. The original 1% detector result and subsequent 2% operating-point amendment remain visible.

## Decision 3: Project precision from development groups

The script `scripts/project_step9_precision.py` uses the Step 8 local selected-point log after verifying its SHA-256. It resamples connected groups 10,000 times, retaining all paired rows within a selected group. The intervals below use 97.5% coverage for the two confirmatory model contrasts (Bonferroni familywise 5%). They are **development pilot intervals and same-size projections**, not final confidence intervals.

| Detector | Matched rows | Groups | M-only / S-only discordant pairs | Development paired difference | Adjusted pilot interval | Projected half-width |
|---|---:|---:|---:|---:|---:|---:|
| Logistic regression | 347 | 268 | 178 / 6 | +49.6 points | +42.7 to +56.6 points | 7.0 points |
| Shallow boosted trees | 290 | 236 | 24 / 2 | +7.6 points | +3.8 to +11.7 points | 4.2 points |

The versioned precision gate requires at least 200 eligible groups per model and a projected adjusted half-width no greater than 8 percentage points. Both pass **conditionally on final eligible-group composition resembling development**. The margin for a practically small paired difference is fixed at ±5 points. The projected logistic half-width is larger than that margin, so a near-zero logistic final result may remain inconclusive rather than support equivalence. No final effect size, coverage, or group composition can be assumed from this projection. The full reproducible statistics are in `data/manifests/compphish_v4_step9_precision.json`.

## Institutional handling gate

The repository contains the CompPhish v4 CC BY 4.0 release and notes that raw/derived records are kept locally and ignored by Git. It does **not** identify the university's governing FYP ethics or cybersecurity data-handling policy, an exemption, or supervisor/institution approval. This gate cannot be marked complete from dataset licensing alone. Before method-validation or final evaluation, obtain the applicable institutional requirements and record the decision, permitted storage/processing, and publication limits. The already completed offline pilot is documented as research activity; this report does not retroactively claim institutional clearance.

## Next allowed work

Protocol v3 and the Step 8 pilot are ready for review. The remaining pre-final tasks are: verify institutional handling, run a frozen implementation check on the method-validation split without tuning to its outcomes, and commit a final-freeze manifest with hashes and analysis settings. The final split remains sealed until those tasks pass. If the method check exposes a defect, version an amendment and rerun the development pilot before any final access.

Reproduce the projection using the Step 6 modeling environment and the local Step 8 row log:

```sh
python3 scripts/project_step9_precision.py
```
