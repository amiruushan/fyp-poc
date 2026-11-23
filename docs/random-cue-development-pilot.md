# Random-cue evaluation: revised development feasibility

**Status:** Revised development pilot complete; reserved test groups remain sealed. This report supersedes the initial, smaller development allocation for feasibility planning. It does not replace or combine with the original Step 11 evaluation.

## Allocation revision

The first proposed allocation restricted both new training and development to original-train groups. Its 68 and 70 eligible groups failed the planned 200-group precision gate. A larger development share within that restricted pool could not plausibly reach 200 while preserving a useful training set.

The revised design keeps the same **1,232 reserved test groups** unchanged. Those groups were selected only from the original training partition, where no attack outcomes had been run. All remaining connected groups are divided into fresh training and development sets. This allows groups used in prior work to support new model fitting or development tuning, while every prior final/development outcome remains outside this new test cohort. The test group identifiers have not been scored by the revised pilot.

| New partition | Groups | Rows | Phishing | Legitimate | Mixed-label groups |
|---|---:|---:|---:|---:|---:|
| Train | 4,910 | 8,108 | 3,802 | 4,306 | 28 |
| Development | 4,176 | 5,405 | 2,535 | 2,870 | 1 |
| Test (sealed) | 1,232 | 1,842 | 864 | 978 | 0 |

The fixed test group membership and revised group-only allocation are recorded in `data/manifests/compphish_v4_random_cue_splits.csv`; counts and hashes are in `data/manifests/compphish_v4_random_cue_split_stats.json`. The revised allocator uses seed 8675311 and keeps all test IDs from the prior allocation. New models were fitted without those test groups.

## Pilot method

Fresh logistic regression and shallow gradient boosting models were fitted on the new training groups. Hyperparameters and a threshold targeting 2% empirical development benign FPR were selected on the new development groups. The three cue selectors were:

- **F:** first factual feature in the preassigned family.
- **M:** distinct eligible same-family feature with greatest positive local score reduction under train-only median/mode replacement.
- **R:** seeded uniform draw from factual, mutable same-family cues other than M. Starts without a distinct random alternative are excluded from the M/R matched set and counted in coverage.

The search remained an abstract feature-vector prediction-flip procedure with the same candidate ordering and 5/10/20/40 total-query caps. The initial verdict counts as query one. The test set was not loaded by the pilot.

## Development-only results

| Detector | Detected phishing starts | Matched rows | Matched groups | Coverage | F at 5 | R at 5 | M at 5 | M−R at 5, 97.5% group-bootstrap interval |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Logistic regression | 1,644 | 566 | 332 | 34.4% | 34.10% | 39.40% | 69.08% | +29.68 points [+23.70, +34.77] |
| Gradient boosting | 1,993 | 678 | 366 | 34.0% | 43.36% | 42.63% | 50.00% | +7.37 points [+4.27, +11.40] |

Intervals use 10,000 connected-group bootstrap replicates and 97.5% coverage for the two model-specific M-minus-R planning contrasts. These are development intervals, not final confirmatory results. At 5 queries, M-minus-F was +34.98 points for logistic regression (97.5% interval +28.08 to +42.62) and +6.64 points for boosting (+3.70 to +10.54).

| Detector | M−R at 10 queries | M−R at 20 queries | M−R at 40 queries |
|---|---:|---:|---:|
| Logistic regression | +6.54 points | 0 points | 0 points |
| Gradient boosting | +0.88 points | 0 points | 0 points |

The planned gate requires at least 200 eligible connected groups per detector and adjusted interval half-width no larger than eight points. The revised pilot has **332 and 366 matched groups**. The observed adjusted half-widths are approximately **5.98 points** (logistic) and **4.02 points** (boosting), so the development-only precision gate passes.

## Interpretation and remaining gates

This passes a *planning* gate; it does not establish the confirmatory effect. The new result is still on CompPhish v4, and the development selection, feature work, and data source are shared with the earlier project. Describe it as a new group-held-out evaluation on the same dataset, not an independent replication or evidence of cross-dataset generalization. The endpoint remains abstract vector flips; no valid page edits were demonstrated.

Before opening the reserved test groups:

1. Verify that the supervisor's Class 1 declaration covers this new comparison and processing scope.
2. Freeze the revised protocol, exact test memberships, model/cue/search code, random seeds, development-selected thresholds, analysis and multiplicity, and all artifact hashes.
3. Independently confirm the test groups have no overlap with any prior evaluated group and that new train models exclude every test group.
4. Evaluate the new test set once. Report matched coverage, random/model cue collisions (zero by design here because R excludes M), all three selector rates on common eligible starts, paired M−R and M−F contrasts, adjusted intervals, and all query-budget results.

Do not tune or select a new rule after observing test outcomes. The earlier Step 11 final result remains a separate study and must not be pooled with the new cohort.
