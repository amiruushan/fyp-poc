#!/usr/bin/env python3
"""Development-only threshold and group-miss audit of frozen Step 6 models."""

import csv
import json
from collections import Counter
from pathlib import Path

import joblib
import numpy as np

from train_baseline_detectors import operating_threshold, sha256, wilson


TARGETS = (0.01, 0.02, 0.03, 0.05)
ROOT = Path(__file__).resolve().parents[1]


def main():
    base = json.loads((ROOT / "data/manifests/compphish_v4_baselines.json").read_text())
    registry = json.loads((ROOT / "data/manifests/compphish_v4_feature_registry.json").read_text())
    matrix_manifest = json.loads((ROOT / "data/manifests/compphish_v4_feature_matrix.json").read_text())
    matrix = ROOT / "data/processed/compphish_v4_feature_matrix.csv"
    if sha256(matrix) != base["matrix_sha256"] or sha256(matrix) != matrix_manifest["output_sha256"]:
        raise ValueError("Matrix hash mismatch")
    feature_names = [f["name"] for f in registry["features"]]
    rows = []
    with matrix.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["split"] == "development" and row["included_primary"] == "1":
                rows.append(row)
    if len(rows) != base["development_rows"]:
        raise ValueError("Unexpected development count")
    X = np.array([[float(row[name]) for name in feature_names] for row in rows])
    labels = np.array([int(row["label"]) for row in rows])
    groups = [row["group_id"] for row in rows]
    result = {"scope": "development primary rows only; frozen Step 6 models", "targets": list(TARGETS),
              "matrix_sha256": base["matrix_sha256"], "models": {}}
    for family in ("logistic_regression", "gradient_boosting"):
        model_info = base["local_model_files"][family]
        model_path = ROOT / model_info["path"]
        if sha256(model_path) != model_info["sha256"]:
            raise ValueError(f"Model hash mismatch: {family}")
        # Only locally produced, hash-verified model files are loaded.
        model = joblib.load(model_path)
        scores = model.predict_proba(X)[:, 1]
        curves = []
        for target in TARGETS:
            threshold = operating_threshold(scores, labels, target)
            predicted = scores >= threshold
            tp = int(np.count_nonzero(predicted & (labels == 1)))
            fp = int(np.count_nonzero(predicted & (labels == 0)))
            phishing_n, benign_n = int(np.count_nonzero(labels == 1)), int(np.count_nonzero(labels == 0))
            misses = Counter(groups[i] for i in range(len(rows)) if labels[i] == 1 and not predicted[i])
            missed_n = sum(misses.values())
            curves.append({"target_benign_fpr": target, "threshold": threshold,
                           "true_positives": tp, "false_positives": fp, "phishing": phishing_n, "benign": benign_n,
                           "recall": tp/phishing_n, "precision": tp/(tp+fp) if tp+fp else 0,
                           "achieved_benign_fpr": fp/benign_n, "benign_fpr_wilson_95": wilson(fp, benign_n),
                           "missed_phishing": missed_n, "groups_with_missed_phishing": len(misses),
                           "largest_single_group_misses": max(misses.values(), default=0),
                           "largest_ten_groups_share_of_misses": sum(sorted(misses.values(), reverse=True)[:10])/missed_n if missed_n else 0})
        first = curves[0]
        original = base["models"][family]["development"]
        if first["true_positives"] != round(original["recall"]*first["phishing"]) or first["false_positives"] != original["false_positives"]:
            raise ValueError(f"Original operating point did not reproduce for {family}")
        result["models"][family] = {"model_sha256": model_info["sha256"], "curve": curves}
    output = ROOT / "data/manifests/compphish_v4_feasibility_audit.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({name: [{"target": p["target_benign_fpr"], "recall": p["recall"], "fpr": p["achieved_benign_fpr"]} for p in item["curve"]] for name,item in result["models"].items()}, indent=2))


if __name__ == "__main__":
    main()
