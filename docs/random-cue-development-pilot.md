# Random-cue selector: development-only feasibility pilot

**Status:** Development pilot completed; the new test partition was not evaluated. This is not confirmatory evidence. The old Step 11 result remains unchanged.

## New group allocation

A deterministic, group-only allocator used the 4,955 connected groups (9,214 primary rows) that belonged to the original training partition. Development, method-validation, and original-final groups (5,363 groups) were excluded from this evaluation. Test group membership was generated before fitting the fresh models. New model fitting and cue-pilot code read only the new train and development partitions; the new test partition was not loaded by the pilot.

| New partition | Groups | Rows | Phishing | Legitimate | Mixed-label groups |
|---|---:|---:|---:|---:|---:|
| Train | 2,491 | 5,529 | 2,593 | 2,936 | 25 |
| Development | 1,232 | 1,843 | 864 | 979 | 1 |
| Test (sealed) | 1,232 | 1,842 | 864 | 978 | 0 |

The group-atomic membership is in `data/manifests/compphish_v4_random_cue_splits.csv`; aggregate counts and hashes are in `data/manifests/compphish_v4_random_cue_split_stats.json`. The seed is 8675309. The allocation is nearly class-balanced and excludes every previously attack-evaluated group. It is an allocation, not an evaluation of the test rows.

## Pilot implementation

Fresh logistic regression and shallow gradient boosting models were fit on the new train groups. Hyperparameters were selected by average precision on the new development groups. The threshold was selected on development for an empirical 2% benign FPR target. The pilot then selected same-family cues and ran the fixed abstract feature-vector search at query budgets 5, 10, 20, and 40. It did not open new test records.

Three selector rules were compared on development: F (first factual feature in the assigned family), M (highest positive local score-reduction feature in that family), and R (seeded uniform draw from factual mutable same-family cues, excluding M so the random comparator is a distinct cue). The same matched starts were used for all three arms. If no distinct random alternative existed, the start did not enter the M-versus-R matched denominator. This distinct-cue rule was adopted during the development feasibility work and is recorded in protocol v1; it must be held fixed before any test use.

## Development results

| Detector | Detected phishing | M/R/F matched rows | Matched groups | Coverage | F bypass | R bypass | M bypass | M−R at 5 queries (97.5% group-bootstrap interval) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Logistic regression | 445 | 136 | 68 | 30.6% | 34.56% | 41.18% | 77.94% | +36.76 points [21.31, 51.63] |
| Gradient boosting | 628 | 200 | 70 | 31.8% | 57.50% | 59.00% | 66.50% | +7.50 points [1.30, 15.31] |

The interval is 97.5% for the two detector-specific primary contrasts, using 10,000 connected-group bootstrap replicates. It is a development interval used only for planning. It is not a final estimate. The M cue was selected from positive local score-reduction candidates; the random cue was sampled from the remaining mutable factual cues. The reported contrasts are consequently conditional on each arm's development eligibility rules.

| Detector | M−R at 10 queries | M−R at 20 queries | M−R at 40 queries | M equals R cue rate |
|---|---:|---:|---:|---:|
| Logistic regression | +2.68 points | 0 points | 0 points | 0% by construction |
| Gradient boosting | +0.46 points | 0 points | 0 points | 0% by construction |

The design gate requires at least 200 eligible connected groups per detector and projected adjusted half-width no larger than eight points. This pilot supplies only 68 and 70 matched groups. Logistic precision is inadequate by that rule; boosting is also below the minimum group count despite the narrower development contrast. **The current test partition must remain sealed.**

## Decision and next action

This split does not support the predeclared precision gate for the new M-versus-random estimand. Do not interpret these development differences as confirmatory results or run the new test. The next step is a protocol amendment based on development-only evidence: increase the development share or choose a better precision strategy before test access, then re-estimate eligibility and precision. Because the source pool is fixed and the eligible rate is low, simply enlarging the development subset may still not produce 200 groups. If a defensible design cannot meet the gate without consuming too much training data, stop this new confirmatory comparison and seek a new dataset or clearly label the work as a lower-precision exploratory extension.

The experiment remains an abstract feature-vector attack on the same CompPhish v4 release. It cannot establish a functioning page edit or cross-dataset generalization. Check that the supervisor's existing Class 1 declaration covers this added comparison before processing proceeds.
