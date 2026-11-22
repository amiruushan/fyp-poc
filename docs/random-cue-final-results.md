# Random-cue comparison: one-time held-out results

**Status:** One frozen run completed. This is a new group-held-out evaluation on CompPhish v4 and must remain separate from the original Step 11 study. Its test groups were taken from the original training partition, which had not been used for attack-outcome evaluation. The protocol, split, source matrix, feature registry, pilot, trained model files, and evaluator were hash-checked before the test scores were calculated. The aggregate output is `data/manifests/compphish_v4_random_cue_final_results.json`.

## Design

The fixed holdout contains 1,232 connected groups and 1,842 rows (864 phishing and 978 legitimate). New logistic-regression and gradient-boosting models were fit on 8,108 training rows. Thresholds were set from development data to target a 2% empirical benign FPR. The primary population is initially detected phishing starts with a factual mutable cue M and a distinct factual same-family random cue R. All three arms (first-available F, seeded random R, and model-selected M) use the same one-coordinate search and query budget. The initial verdict counts as query one. The primary endpoint is the paired M-minus-R difference at five total queries. Intervals use 10,000 connected-group bootstrap draws and 97.5% confidence per detector for the two planned primary contrasts.

## Results

| Detector | Test FPR | Test recall | Detected phishing starts | Matched rows / groups | Coverage | F at 5 | R at 5 | M at 5 | Primary M−R, 97.5% interval |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Logistic regression | 2.66% (26/978) | 56.02% (484/864) | 484 | 198 / 75 | 40.9% | 20.71% | 24.24% | 66.16% | **+41.92 points** [+17.86, +55.56] |
| Gradient boosting | 2.66% (26/978) | 59.14% (511/864) | 511 | 218 / 72 | 42.7% | 32.57% | 32.57% | 39.45% | **+6.88 points** [+0.46, +15.92] |

The primary estimates favor M over R for both detectors, and both planned intervals exclude zero. However, the confirmatory matched sets contain only 75 and 72 groups, well below the development planning gate of 200 groups. Their interval half-widths are about 18.85 and 7.73 points; the logistic result fails the planned eight-point precision limit, and the group-count gate fails for both models. Treat these as positive but imprecise evidence, not a fully precise confirmation of the effect size. Do not change the frozen test or rerun it to increase the matched count.

M−F at five queries was +45.45 points for logistic regression and +6.88 points for boosting. This is secondary and descriptive. At 10 queries, the F/R/M rates were 50.00%/50.51%/82.32% for logistic regression and 94.04%/93.58%/94.50% for boosting. At 20 and 40 queries, all three arms had equal rates within each detector (98.99% logistic; 98.62% boosting). Thus the measured cue-selection advantage is concentrated in the tighter query budgets. The endpoint remains a flip in an abstract feature vector, not a valid URL or functioning phishing page.

The test FPR was 2.66% for both models, above the 2% empirical development target. This is a test-set generalization result, not a threshold adjustment opportunity; thresholds remain frozen. The experiment uses one dataset and does not establish cross-dataset generalization.

## Reproduction and integrity

The run is write-once: `scripts/run_random_cue_final_evaluation.py` refuses to overwrite the aggregate result. It validates frozen hashes, verifies that all test serials belonged to the original training partition, and checks saved model hashes. The freeze details and hashes are in `data/manifests/compphish_v4_random_cue_freeze.json`; the exact pre-run protocol is `configs/random_cue_evaluation_frozen_v2.json`. The first invocation stopped at a serial/group key mismatch in its pre-score isolation check; no scores were computed and no result file was written. That check was corrected, the evaluator hash re-frozen, and the successful run completed once.

To view the committed aggregate values in a terminal:

```sh
python3 - <<'PY'
import json
from pathlib import Path
r = json.loads(Path('data/manifests/compphish_v4_random_cue_final_results.json').read_text())
for name, m in r['models'].items():
    d = m['paired_differences_at_5']['M-R']
    print(name, 'matched rows/groups:', m['matched_rows'], m['matched_groups'])
    print('  F/R/M at 5:', *(f"{m['rates_by_query_budget']['5'][a]:.2%}" for a in ('F','R','M')))
    print(f"  M-R: {d['difference']:+.2%}, interval {d['interval_97_5'][0]:+.2%} to {d['interval_97_5'][1]:+.2%}")
PY
```
