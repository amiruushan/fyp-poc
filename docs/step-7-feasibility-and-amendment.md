# Step 7: Development feasibility audit and protocol v2

The Step 6 models are frozen. On the development set, logistic regression missed the protocol v1 50% recall floor at the 1% benign FPR target. This step audited the same saved models on a fixed, small target grid (1%, 2%, 3%, 5%) and examined whether misses concentrated in a few connected groups. It did not use method-validation or final rows.

| Target benign FPR | Logistic recall | Boosted-tree recall | Achieved benign FPR |
|---:|---:|---:|---:|
| 1% | 38.43% (415/1080) | 61.11% (660/1080) | 0.981% (12/1223) |
| 2% | 54.81% (592/1080) | 70.56% (762/1080) | 1.962% (24/1223) |
| 3% | 62.22% (672/1080) | 74.44% (804/1080) | 2.944% (36/1223) |
| 5% | 72.78% (786/1080) | 80.00% (864/1080) | 4.988% (61/1223) |

At 2%, logistic misses occur across 350 connected groups (488 phishing misses), with the largest group contributing 12 misses and the ten largest groups 13.5% of misses. At 1%, its 665 misses occur across 465 groups, with the largest group contributing 13. The failure is therefore not explained by one dominant group. For boosted trees at 2%, 318 misses occur across 237 groups; the largest group contributes 9. These are descriptive diagnostics, not a causal source-shortcut audit. The full numeric curve, threshold values, and group summaries are in `data/manifests/compphish_v4_feasibility_audit.json`.

## Versioned decision

Protocol v2 changes the shared benign FPR target from 1% to **2%**, the smallest audited target at which both frozen detector families clear the unchanged 50% development recall floor. It freezes the logistic threshold at 0.7911127720700377 and boosted-tree threshold at 0.792962872694845, tied to the Step 6 model hashes. No model is refitted and no feature registry or split changes. `configs/experiment_protocol_v1.json` and the original Step 6 1% results remain intact.

This amendment is **development-informed** and must be identified as such in the paper. The 1% results stay in the baseline report and as a sensitivity operating point. At 2%, 24/1223 benign rows are false positives; the 95% Wilson interval is approximately 1.322%–2.903%. The empirical target is not a population guarantee. Passing the development recall gate permits planning the next pilot; it does not authorize final evaluation. Dataset handling requirements, cue fidelity, grammar, query-budget selection, and precision projection remain outstanding.

Reproduce with the Step 6 pinned environment and locally produced, hash-verified model files:

```sh
python3 scripts/audit_detector_feasibility.py
```

The script reads only development primary rows from the local Step 4 matrix. It verifies model/matrix hashes and reproduces the original 1% operating-point counts before writing the audit. The published dataset's class-confounded provenance and provisional grouping continue to limit generalization claims.
