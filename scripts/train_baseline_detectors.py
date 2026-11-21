#!/usr/bin/env python3
"""Fit Step 5 baseline detectors using train/development rows only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import platform
import warnings
from pathlib import Path

import joblib
import numpy as np
import scipy
import sklearn
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


VERSIONS = {"python": "3.14.5", "scikit_learn": "1.8.0", "numpy": "2.4.4", "scipy": "1.17.1", "joblib": "1.5.3"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wilson(successes: int, total: int) -> list[float]:
    if not total:
        return [0.0, 1.0]
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z*z/total
    center = (p + z*z/(2*total)) / denominator
    radius = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / denominator
    return [center-radius, center+radius]


def operating_threshold(scores: np.ndarray, labels: np.ndarray, target: float) -> float:
    benign = scores[labels == 0]
    if not len(benign):
        raise ValueError("Development set contains no benign rows")
    # Candidate scores include exact boundaries; the next representable value
    # above the maximum admits the all-negative operating point.
    candidates = np.append(np.unique(scores), np.nextafter(np.max(scores), np.inf))
    for threshold in candidates:
        if np.count_nonzero(benign >= threshold) / len(benign) <= target:
            return float(threshold)
    raise AssertionError("All-negative threshold was not found")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, default=Path("data/processed/compphish_v4_feature_matrix.csv"))
    parser.add_argument("--matrix-manifest", type=Path, default=Path("data/manifests/compphish_v4_feature_matrix.json"))
    parser.add_argument("--registry", type=Path, default=Path("data/manifests/compphish_v4_feature_registry.json"))
    parser.add_argument("--protocol", type=Path, default=Path("configs/experiment_protocol_v1.json"))
    parser.add_argument("--model-dir", type=Path, default=Path("data/processed/models"))
    parser.add_argument("--output", type=Path, default=Path("data/manifests/compphish_v4_baselines.json"))
    args = parser.parse_args()

    versions = {"python": platform.python_version(), "scikit_learn": sklearn.__version__, "numpy": np.__version__, "scipy": scipy.__version__, "joblib": joblib.__version__}
    if versions != VERSIONS:
        raise RuntimeError(f"Pinned version mismatch: expected {VERSIONS}, got {versions}")
    manifest = json.loads(args.matrix_manifest.read_text())
    if sha256(args.matrix) != manifest["output_sha256"]:
        raise ValueError("Feature matrix hash differs from Step 4 manifest")
    registry = json.loads(args.registry.read_text())
    protocol = json.loads(args.protocol.read_text())
    if protocol["final_access_allowed"] is not False or protocol["selection_split"] != "development":
        raise ValueError("Protocol does not reserve the final split")
    features = [item["name"] for item in registry["features"]]
    if features != manifest["feature_columns"]:
        raise ValueError("Registry and matrix feature order differ")

    rows: dict[str, list[list[float]]] = {"train": [], "development": []}
    labels: dict[str, list[int]] = {"train": [], "development": []}
    serials: dict[str, list[str]] = {"train": [], "development": []}
    with args.matrix.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if not set(features).issubset(reader.fieldnames or []):
            raise ValueError("Matrix is missing registry features")
        for row in reader:
            split = row["split"]
            if split not in rows:
                continue  # Do not parse or inspect method-validation/final values.
            if row["included_primary"] != "1":
                continue
            rows[split].append([float(row[name]) for name in features])
            labels[split].append(int(row["label"]))
            serials[split].append(row["serial_number"])
    X_train, X_dev = np.asarray(rows["train"], dtype=np.float64), np.asarray(rows["development"], dtype=np.float64)
    y_train, y_dev = np.asarray(labels["train"]), np.asarray(labels["development"])
    if len(X_train) != 9214 or len(X_dev) != 2303 or not np.isfinite(X_train).all() or not np.isfinite(X_dev).all():
        raise ValueError("Unexpected train/development size or non-finite feature")
    if len(set(serials["train"])) != len(X_train) or len(set(serials["development"])) != len(X_dev):
        raise ValueError("Duplicate primary serial")

    results = {}
    selected_models = {}
    for family in ("logistic_regression", "gradient_boosting"):
        settings = protocol["models"][family]
        if family == "logistic_regression":
            grid = [{"C": C} for C in settings["C"]]
            build = lambda p: make_pipeline(StandardScaler(), LogisticRegression(C=p["C"], l1_ratio=0, solver="lbfgs", max_iter=settings["max_iter"], random_state=protocol["seed"]))
            tie_key = lambda p: (p["C"],)
        else:
            grid = [{"max_depth": d, "n_estimators": n} for d, n in itertools.product(settings["max_depth"], settings["n_estimators"])]
            build = lambda p: GradientBoostingClassifier(max_depth=p["max_depth"], n_estimators=p["n_estimators"], learning_rate=settings["learning_rate"], min_samples_leaf=settings["min_samples_leaf"], subsample=settings["subsample"], random_state=protocol["seed"])
            tie_key = lambda p: (p["max_depth"], p["n_estimators"])
        candidates = []
        for params in grid:
            model = build(params)
            with warnings.catch_warnings():
                warnings.simplefilter("error", ConvergenceWarning)
                model.fit(X_train, y_train)
            scores = model.predict_proba(X_dev)[:, 1]
            candidates.append({"params": params, "development_average_precision": float(average_precision_score(y_dev, scores)), "development_roc_auc": float(roc_auc_score(y_dev, scores))})
            print(f"{family} {params}: AP={candidates[-1]['development_average_precision']:.6f}", flush=True)
        best = sorted(candidates, key=lambda c: (-round(c["development_average_precision"], 12), tie_key(c["params"])))[0]
        selected = build(best["params"])
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            selected.fit(X_train, y_train)
        scores = selected.predict_proba(X_dev)[:, 1]
        threshold = operating_threshold(scores, y_dev, protocol["development_fpr_target"])
        predicted = scores >= threshold
        fp = int(np.count_nonzero(predicted & (y_dev == 0)))
        benign_n = int(np.count_nonzero(y_dev == 0))
        recall = float(recall_score(y_dev, predicted))
        selected_models[family] = selected
        results[family] = {"candidates": candidates, "selected_params": best["params"], "threshold": threshold,
            "development": {"rows": len(y_dev), "phishing": int(np.count_nonzero(y_dev == 1)), "benign": benign_n,
                "false_positives": fp, "false_positive_rate": fp/benign_n, "false_positive_rate_wilson_95": wilson(fp, benign_n),
                "recall": recall, "precision": float(precision_score(y_dev, predicted, zero_division=0)),
                "roc_auc": float(roc_auc_score(y_dev, scores)), "average_precision": float(average_precision_score(y_dev, scores)),
                "recall_gate_passed": recall >= protocol["minimum_development_recall_gate"]}}

    args.model_dir.mkdir(parents=True, exist_ok=True)
    model_files = {}
    for family, model in selected_models.items():
        path = args.model_dir / f"{family}.joblib"
        joblib.dump(model, path)
        model_files[family] = {"path": str(path), "sha256": sha256(path)}
    output = {"dataset": manifest["dataset"], "stage": "Step 6 train/development baseline", "seed": protocol["seed"],
        "matrix_sha256": manifest["output_sha256"], "registry_sha256": sha256(args.registry), "protocol_sha256": sha256(args.protocol),
        "versions": versions, "train_rows": len(y_train), "development_rows": len(y_dev),
        "feature_columns": features, "models": results, "local_model_files": model_files,
        "final_split_evaluated": False, "method_validation_evaluated": False,
        "gate_passed_both": all(v["development"]["recall_gate_passed"] for v in results.values())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"gate_passed_both": output["gate_passed_both"], "selected": {k: {"params": v["selected_params"], "threshold": v["threshold"], **v["development"]} for k,v in results.items()}}, indent=2))


if __name__ == "__main__":
    main()
