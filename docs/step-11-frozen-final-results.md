# Step 11: Frozen final evaluation

The final split was opened once after `compphish_v4_final_freeze.json` verified all ten frozen artifact hashes. The evaluation used protocol v3, the two Step 6 models and their unchanged 2% development-selected thresholds, Step 8 cue/candidate rules, K0 only, and one changed coordinate within five total binary queries. No final outcome was used to choose a model, threshold, feature, cue, budget, or analysis rule. The script refuses to overwrite an existing final result manifest. Final source recomputation found **0 mismatches in 27,636 feature checks** across all 2,303 primary final rows.

## Detector context

| Detector | Final benign FPR | Phishing recall | Precision | ROC-AUC | Average precision |
|---|---:|---:|---:|---:|---:|
| Logistic regression | 2.13% (26/1223) | 54.54% (589/1080) | 95.77% | 0.9212 | 0.9226 |
| Shallow gradient boosting | 2.21% (27/1223) | 70.28% (759/1080) | 96.56% | 0.9608 | 0.9586 |

The final FPRs slightly exceed the **empirical development target** of 2%. That target was never a population guarantee. The 95% Wilson FPR intervals are approximately 1.45%–3.10% and 1.52%–3.19%, respectively. These detector metrics are within-dataset results under class-confounded acquisition sources and provisional domain/template grouping.

## Confirmatory matched-cue contrast

The primary population is initially detected phishing starts with an independently chosen factual S cue and a distinct eligible M-family cue in the same preassigned feature family. The frozen query/feature budget is one changed coordinate and five total binary queries. Rates below share the same matched rows within each detector.

| Detector | Matched rows (groups) | V bypass | S bypass | M-family bypass | Paired M−S | Bonferroni-adjusted 97.5% group-bootstrap interval |
|---|---:|---:|---:|---:|---:|---:|
| Logistic regression | 344 (268) | 43.60% | 23.84% | 77.03% | **+53.20 points** | +45.79 to +60.56 points |
| Shallow gradient boosting | 299 (237) | 66.89% | 60.20% | 73.91% | **+13.71 points** | +8.87 to +18.75 points |

Both adjusted intervals exclude zero under the frozen abstract feature-space protocol. The logistic matched pairs have 193 M-only and 10 S-only discordances; boosted trees have 43 and 2. This supports an incremental **coordinate-priority advantage** of the model-selected cue over the same-family independently chosen fact in these eligible subsets. It does not show a working phishing-page edit or an advantage in all phishing starts, all detectors, or other datasets.

Coverage matters: 344/589 (58.4%) initially detected logistic starts and 299/759 (39.4%) initially detected boosted starts entered this distinct same-family primary contrast. The all-start V/S/M-global-with-V-fallback bypass rates were 49.1%/27.5%/92.7% (logistic) and 68.4%/62.5%/74.6% (boosting); these use different denominators from the primary matched comparison. Mean selected-point query counts for each arm and the full 1–5-coordinate × 5/10/20/40-query sensitivity curve are in `data/manifests/compphish_v4_final_results.json`. Row-level logs stay local under Git-ignored `data/processed/`.

## Interpretation and reporting limits

The endpoint is a binary model prediction flip after an **abstract feature-vector change**. URL/HTML feature dependencies are not fully enforced, and no candidate was shown to correspond to a valid, visible, functioning, or deployable webpage. The K0/K2 knowledge interaction and conditional minimax selector were not tested. The 2% detector operating target was a versioned, development-informed amendment after the originally proposed 1% logistic recall gate failed; both operating-point results must be described in the paper. CompPhish v4 source provenance is confounded with class, row-level timestamps are unavailable, and external generalization is untested.

The frozen Step 8 search logged changed-coordinate count and binary-query cost but **did not record normalized perturbation magnitude**. The final result cannot support a magnitude distribution; this is a protocol reporting limitation to disclose, not a reason to rerun or retune the final split. The student's report of Class 1 supervisor acceptance and permitted local processing was used for Step 10; the declaration itself was not independently inspected here.

## Reproducibility boundary

The final aggregate JSON records the freeze-manifest hash and SHA-256 of the local selected-point row log. The run command was:

```sh
PYTHONPATH=/private/tmp/step3-libs:/private/tmp/compaudit-libs python3 scripts/run_step11_final_evaluation.py
```

Those temporary library paths are specific to the development machine; use the pinned Step 3 and Step 6 requirements in a fresh environment elsewhere. **Do not rerun the final evaluation to seek a different result.** The next work is statistical interpretation, robustness checks that do not retune the primary finding, reproduction packaging, and the IEEE Access draft.
