# Step 6: Train/development detector baselines

The two CPU baselines use the same 12 frozen, source-derived features and 9,214 primary training records. Hyperparameter selection and operating thresholds use only 2,303 development records (1,080 phishing; 1,223 benign). The script checks the Step 4 matrix hash, ignores method-validation and final rows, standardizes logistic inputs using train-only fitted statistics, and applies the Step 5 candidate grids and 1% empirical benign false-positive target. Its ten candidate AP scores and model hashes are in `data/manifests/compphish_v4_baselines.json`. Selected model files are local under ignored `data/processed/models/` and are not published in this PR; load only locally produced, trusted joblib files.

| Detector | Selected configuration | Development AP | ROC-AUC | Threshold | Benign FPR | Phishing recall | Precision | 50% recall gate |
|---|---|---:|---:|---:|---:|---:|---:|---|
| L2 logistic regression | C=10 | 0.9223 | 0.9200 | 0.89708 | 0.981% (12/1223) | 38.43% (415/1080) | 97.19% | **Failed** |
| Shallow gradient boosting | depth=3, 200 trees | 0.9582 | 0.9606 | 0.89266 | 0.981% (12/1223) | 61.11% (660/1080) | 98.21% | Passed |

Each empirical FPR has a 95% Wilson interval of about 0.562%–1.707%. The point target is met; the interval does not establish a population FPR below 1%. AP is average precision, the chosen selection metric. These are within-dataset development estimates, subject to source confounding and provisional grouping. They are neither final-test performance nor evidence of phishing-page evasion.

The joint detector feasibility gate fails because logistic regression recall is below the protocol's predeclared 50% floor. Do not silently relax the target or replace the model after seeing this result. Before cue/attack experiments, review a versioned protocol amendment or a prespecified narrower study; retain this result in the eventual paper. The handling requirements gate and all later cue/grammar/budget/precision gates also remain open.

Reproduce with Python 3.14.5 and `requirements-step6-models.txt` in an isolated environment:

```sh
python3 scripts/train_baseline_detectors.py
```

The exact dataset-derived matrix must already exist locally under `data/processed/`. The script reports an error if its hash does not match the Step 4 manifest. It writes the development summary to the tracked manifest and model files to the ignored local directory. It does not inspect final values, fit on development, or run attacks.
