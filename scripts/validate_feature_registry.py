#!/usr/bin/env python3
"""Independently recompute frozen features on a deterministic development sample."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, urlparse

import bs4
import openpyxl
import tldextract
from bs4 import BeautifulSoup


EXPECTED = {"beautifulsoup4": "4.13.4", "openpyxl": "3.1.5", "tldextract": "5.2.0"}
SEED = 20261122
SAMPLE_PER_LABEL = 100


def version_checks() -> None:
    actual = {"beautifulsoup4": bs4.__version__, "openpyxl": openpyxl.__version__, "tldextract": tldextract.__version__}
    if actual != EXPECTED:
        raise RuntimeError(f"Pinned dependency mismatch: expected {EXPECTED}, got {actual}")


def norm_serial(value: object) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def norm_label(value: object) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    return -sum((n / len(value)) * math.log2(n / len(value)) for n in counts.values())


def independent_values(url: str, html: str, extractor) -> dict[str, float | int]:
    parsed = urlparse(url)
    extracted = extractor(url)
    hostname = ".".join(part for part in (extracted.subdomain, extracted.domain, extracted.suffix) if part)
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip().lower() if soup.title and soup.title.string else ""
    return {
        "url_length": len(url),
        "no_of_slashes_inpath": parsed.path.count("/"),
        "num_query_params": len(parse_qs(parsed.query)),
        "numeric_proportion": sum(char.isdigit() for char in url) / len(url) if url else 0.0,
        "hostname_digit_ratio": len(re.sub("[^0-9]", "", hostname)) / len(hostname) if hostname else 0.0,
        "url_entropy": entropy(url),
        "has_embedded_url": int(url.count("http://") + url.count("https://") > 1),
        "uses_https": int(parsed.scheme == "https"),
        "no_of_forms": len(soup.find_all("form")),
        "no_of_images": len(soup.find_all("img")),
        "has_missing_title": int(title in {"index", "home", "page", ""}),
        "has_inline_event_handlers": int(any(
            tag.get(attribute)
            for tag in soup.find_all(["a", "button"])
            for attribute in ("onclick", "onmouseover")
        )),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--split-csv", type=Path, required=True)
    parser.add_argument("--registry-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    version_checks()

    registry = json.loads(args.registry_json.read_text())
    feature_names = [feature["released_column"] for feature in registry["features"]]
    by_name = {feature["name"]: feature for feature in registry["features"]}

    candidates: dict[str, dict[str, list[dict[str, str]]]] = {"0": {}, "1": {}}
    with args.split_csv.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["split"] not in {"train", "development", "method_validation", "final"}:
                raise ValueError(f"Unknown split {row['split']}")
            if row["split"] == "development" and row["included_primary"] == "1":
                candidates[row["label"]].setdefault(row["group_id"], []).append(row)

    rng = random.Random(SEED)
    sample: list[dict[str, str]] = []
    selected_groups: dict[str, list[str]] = {"0": [], "1": []}
    available = {label: list(candidates[label]) for label in ("0", "1")}
    rng.shuffle(available["0"])
    rng.shuffle(available["1"])
    used_groups: set[str] = set()
    for label in ("0", "1"):
        for group_id in available[label]:
            if group_id in used_groups:
                continue
            selected_groups[label].append(group_id)
            sample.append(min(candidates[label][group_id], key=lambda row: (int(row["serial_number"]), row["serial_number"])))
            used_groups.add(group_id)
            if len(selected_groups[label]) == SAMPLE_PER_LABEL:
                break
    if len(sample) != SAMPLE_PER_LABEL * 2:
        raise ValueError(f"Expected {SAMPLE_PER_LABEL * 2} sample rows; found {len(sample)}")

    mapping_wb = openpyxl.load_workbook(args.data_dir / "Mapping_File.xlsx", read_only=True, data_only=True)
    mapping_ws = mapping_wb[mapping_wb.sheetnames[0]]
    mapping_iter = mapping_ws.iter_rows(values_only=True)
    mapping_header = [str(value).strip() if value is not None else "" for value in next(mapping_iter)]
    if mapping_header[:3] != ["serial_number", "url", "label"]:
        raise ValueError(f"Unexpected mapping header: {mapping_header[:3]}")
    wanted = {row["serial_number"] for row in sample}
    url_by_serial: dict[str, str] = {}
    for row in mapping_iter:
        serial = norm_serial(row[0])
        if serial in wanted:
            url_by_serial[serial] = str(row[1] or "").strip()
    mapping_wb.close()
    if set(url_by_serial) != wanted:
        raise ValueError("Unable to find all sampled URLs in the mapping workbook")

    feature_wb = openpyxl.load_workbook(args.data_dir / "All_Features_threshold90.xlsx", read_only=True, data_only=True)
    feature_ws = feature_wb[feature_wb.sheetnames[0]]
    feature_iter = feature_ws.iter_rows(values_only=True)
    feature_header = [str(value).strip() if value is not None else "" for value in next(feature_iter)]
    if feature_header[:3] != ["serial_number", "url", "label"]:
        raise ValueError(f"Unexpected feature header: {feature_header[:3]}")
    index_by_name = {name: index for index, name in enumerate(feature_header)}
    missing_columns = sorted(set(feature_names) - set(index_by_name))
    if missing_columns:
        raise ValueError(f"Released table lacks registry columns: {missing_columns}")
    released: dict[str, dict[str, object]] = {}
    for row in feature_iter:
        serial = norm_serial(row[0])
        if serial in wanted:
            released[serial] = {name: row[index_by_name[name]] for name in feature_names}
    feature_wb.close()
    if set(released) != wanted:
        raise ValueError("Unable to find all sampled feature rows in released workbook")

    extractor = tldextract.TLDExtract(cache_dir=None, suffix_list_urls=(), fallback_to_snapshot=True, include_psl_private_domains=False)
    serial_by_archive_name = {PurePosixPath(f"{row['serial_number']}.txt").name: row["serial_number"] for row in sample}
    actual: dict[str, dict[str, float | int]] = {}
    html_hashes: dict[str, str] = {}
    with zipfile.ZipFile(args.data_dir / "All_HTML.zip") as archive:
        found: set[str] = set()
        for info in archive.infolist():
            serial = serial_by_archive_name.get(PurePosixPath(info.filename).name)
            if serial is None:
                continue
            content = archive.read(info)
            html = content.decode("utf-8")
            actual[serial] = independent_values(url_by_serial[serial], html, extractor)
            html_hashes[serial] = hashlib.sha256(content).hexdigest()
            found.add(serial)
        if found != wanted:
            raise ValueError(f"Sample HTML missing from archive: {sorted(wanted - found)[:10]}")

    comparisons: dict[str, dict[str, object]] = {}
    mismatches_total = 0
    for name, feature in by_name.items():
        released_column = feature["released_column"]
        numeric_errors: list[float] = []
        mismatches: list[dict[str, object]] = []
        for row in sample:
            serial = row["serial_number"]
            expected, observed = released[serial][released_column], actual[serial][name]
            try:
                delta = abs(float(expected) - float(observed))
                match = delta <= 1e-9
                numeric_errors.append(delta)
            except (TypeError, ValueError):
                match, delta = expected == observed, None
            if not match:
                mismatches.append({"serial_number": serial, "label": row["label"], "released": expected, "recomputed": observed, "absolute_error": delta})
        mismatches_total += len(mismatches)
        comparisons[name] = {
            "feature_id": feature["feature_id"],
            "sample_count": len(sample),
            "matches": len(sample) - len(mismatches),
            "mismatch_count": len(mismatches),
            "maximum_absolute_error": max(numeric_errors, default=0.0),
            "mismatch_examples": mismatches[:10],
        }

    result = {
        "dataset": registry["dataset"],
        "registry_version": registry["registry_version"],
        "validation_scope": "development split only; no final split rows read",
        "sampling": {"seed": SEED, "rows_per_label": SAMPLE_PER_LABEL, "one_row_per_connected_group": True,
                     "label_0_groups": selected_groups["0"], "label_1_groups": selected_groups["1"],
                     "sample_serials": sorted(wanted), "sample_html_sha256": html_hashes},
        "dependencies": {"beautifulsoup4": bs4.__version__, "openpyxl": openpyxl.__version__, "tldextract": tldextract.__version__},
        "recomputation": "direct independent implementations; archived HTML parsed inertly with html.parser; bundled extractor not imported or executed",
        "comparison_tolerance": 1e-9,
        "total_feature_mismatches": mismatches_total,
        "features": comparisons,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"sample_rows": len(sample), "total_feature_mismatches": mismatches_total,
                      "per_feature_mismatches": {name: item["mismatch_count"] for name, item in comparisons.items()}}, indent=2))


if __name__ == "__main__":
    main()
