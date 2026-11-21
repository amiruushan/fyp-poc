# Step 10: Method-validation check and final freeze

The student reported that the supervisor accepted a Class 1 declaration covering this PoC and local dataset processing. The declaration itself was not supplied or independently inspected. A local, Git-ignored `data/processed/ethics_status_reported.json` records that user-reported status for the runner; it is not a University approval artifact. The method-validation run was then carried out once on the reserved 10% split. No final rows were parsed for model evaluation or attack outcomes.

## Frozen implementation check

`run_step10_method_validation.py` requires the local ethics-status record and verifies the Step 4 matrix, both Step 6 model files, protocol v3, the Step 8 script hash, and the train-derived feature grammar. It reuses the frozen Step 8 feature-space candidate generator and binary-query accounting, the one-coordinate/five-query budget, the 2% detector thresholds, same-family cue selection, and K0 only. An independent offline source recomputation checked **18,420/18,420 feature values** across all **1,535 method-validation records** with zero mismatches. A synthetic self-check also passed without opening dataset files. The runner enforces the five-query cap, requires the expected row counts, and writes a row-level log to ignored local storage.

| Detector | Initially detected phishing | Matched rows | Matched groups | V bypass | S bypass | M-family bypass | Paired M−S | 97.5% group bootstrap interval |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Logistic regression | 386/720 | 226 | 205 | 42.0% | 25.7% | 75.2% | +49.6 points | +40.8 to +58.1 points |
| Shallow boosted trees | 497/720 | 183 | 176 | 69.4% | 58.5% | 70.5% | +12.0 points | +6.1 to +18.2 points |

These are method-validation diagnostics under an abstract feature-vector attack, not final confirmatory results. The boosted matched group count is 176 because this partition is smaller than development; the Step 9 projection gate of 200 groups applied to the development estimate for a similarly sized final split, not as a minimum for this 10% check. The method run was not used to select another threshold, candidate grammar, cue rule, or query budget. The full aggregate result is in `data/manifests/compphish_v4_method_validation.json`.

## Final freeze

`data/manifests/compphish_v4_final_freeze.json` locks the Step 4 matrix, registry, split manifest, protocol v3, Step 8 attack script, Step 10 runner, two model files, and method result by SHA-256. It also records the two confirmatory detector contrasts, K0 condition, one-change/five-query budget, group bootstrap procedure, and ±5-point equivalence margin. `scripts/verify_compphish_final_freeze.py` verified all ten artifact hashes. The freeze records **no final evaluation**; it is a boundary for a later explicitly authorized step. The same abstract-feature and source-confounding limitations remain.

Reproduce the synthetic check without opening dataset files:

```sh
"$HOME/.venvs/fyp-poc-step3/bin/python" scripts/run_step10_method_validation.py --self-check
```

A real method-validation run additionally requires the accepted-declaration status recorded locally and the pinned parser/modeling dependencies. The local status record used here reflects the user's report and should be replaced or supplemented with the actual institutional acceptance reference in the research record. Do not commit the declaration or row-level query log. Verify the freeze without scoring any final records:

```sh
python3 scripts/verify_compphish_final_freeze.py
```
