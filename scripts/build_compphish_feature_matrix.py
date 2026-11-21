#!/usr/bin/env python3
"""Build the shared CompPhish v4 feature matrix from mapping and archived HTML."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, urlparse

import bs4
import openpyxl
import tldextract
from bs4 import BeautifulSoup


EXPECTED = {"beautifulsoup4": "4.13.4", "openpyxl": "3.1.5", "tldextract": "5.2.0"}
BASE_COLUMNS = ["serial_number", "canonical_serial", "group_id", "split", "label", "included_primary", "mixed_label_exact_html", "url", "html_sha256"]


def check_versions() -> dict[str, str]:
    actual = {"beautifulsoup4": bs4.__version__, "openpyxl": openpyxl.__version__, "tldextract": tldextract.__version__}
    if actual != EXPECTED:
        raise RuntimeError(f"Pinned dependency mismatch: expected {EXPECTED}, got {actual}")
    return actual


def norm_serial(value: object) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def norm_label(value: object) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def read_mapping(path: Path) -> dict[str, tuple[str, str]]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook[workbook.sheetnames[0]]
    rows = sheet.iter_rows(values_only=True)
    header = [str(value).strip() if value is not None else "" for value in next(rows)]
    if header[:3] != ["serial_number", "url", "label"]:
        raise ValueError(f"Unexpected mapping header: {header[:3]}")
    records: dict[str, tuple[str, str]] = {}
    for row in rows:
        serial, url, label = norm_serial(row[0]), str(row[1] or "").strip(), norm_label(row[2])
        if serial in records:
            raise ValueError(f"Duplicate mapping serial: {serial}")
        if label not in {"0", "1"}:
            raise ValueError(f"Unexpected label {label!r} at serial {serial}")
        records[serial] = (url, label)
    workbook.close()
    return records


def read_splits(path: Path, mapping: dict[str, tuple[str, str]]) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            serial = row["serial_number"]
            if serial in rows:
                raise ValueError(f"Duplicate split serial: {serial}")
            if row["split"] not in {"train", "development", "method_validation", "final"}:
                raise ValueError(f"Unexpected split {row['split']!r} at serial {serial}")
            if row["label"] != mapping[serial][1]:
                raise ValueError(f"Split label does not match mapping for serial {serial}")
            if row["included_primary"] not in {"0", "1"}:
                raise ValueError(f"Invalid included_primary value for serial {serial}")
            rows[serial] = row
    if set(rows) != set(mapping):
        raise ValueError(f"Mapping/split serial mismatch: mapping={len(mapping)} split={len(rows)}")
    return rows


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def parse_html_recovering_numeric_references(html: str, serial: str) -> tuple[BeautifulSoup, int]:
    try:
        return BeautifulSoup(html, "html.parser"), 0
    except ValueError as original_error:
        # CPython's HTMLParser can consume following letters into a malformed
        # semicolon-less numeric reference (for example &#39Africa) and then
        # crash while converting it to an integer. Insert the missing delimiter
        # after the valid numeric prefix, preserving the standard intended parse.
        repaired, decimal_count = re.subn(r"&#([0-9]+)(?=[A-Za-z])", r"&#\1;", html)
        repaired, hex_count = re.subn(r"&#([xX][0-9A-Fa-f]+)(?=[G-Zg-z])", r"&#\1;", repaired)
        repair_count = decimal_count + hex_count
        if not repair_count:
            raise RuntimeError(f"HTML parser failed for serial {serial}; no recognized malformed numeric reference to repair") from original_error
        try:
            return BeautifulSoup(repaired, "html.parser"), repair_count
        except Exception as retry_error:
            raise RuntimeError(f"HTML parser recovery failed for serial {serial}") from retry_error


def compute_features(url: str, html: str, extractor, serial: str) -> tuple[dict[str, int | float], int]:
    parsed = urlparse(url)
    extracted = extractor(url)
    hostname = ".".join(part for part in (extracted.subdomain, extracted.domain, extracted.suffix) if part)
    soup, repaired_refs = parse_html_recovering_numeric_references(html, serial)
    title = soup.title.string.strip().lower() if soup.title and soup.title.string else ""
    return {
        "url_length": len(url),
        "no_of_slashes_inpath": parsed.path.count("/"),
        "num_query_params": len(parse_qs(parsed.query)),
        "numeric_proportion": sum(character.isdigit() for character in url) / len(url) if url else 0.0,
        "hostname_digit_ratio": len(re.sub("[^0-9]", "", hostname)) / len(hostname) if hostname else 0.0,
        "url_entropy": shannon_entropy(url),
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
    }, repaired_refs


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--split-csv", type=Path, required=True)
    parser.add_argument("--registry-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, default=Path("data/processed/compphish_v4_feature_matrix.csv"))
    parser.add_argument("--output-json", type=Path, default=Path("data/manifests/compphish_v4_feature_matrix.json"))
    args = parser.parse_args()

    versions = check_versions()
    registry = json.loads(args.registry_json.read_text(encoding="utf-8"))
    features = registry["features"]
    feature_names = [item["name"] for item in features]
    if len(feature_names) != len(set(feature_names)):
        raise ValueError("Feature registry contains duplicate names")
    for item in features:
        if item["type"] not in {"integer", "float", "boolean"}:
            raise ValueError(f"Unsupported type {item['type']!r} for {item['name']}")

    mapping = read_mapping(args.data_dir / "Mapping_File.xlsx")
    split_rows = read_splits(args.split_csv, mapping)
    extractor = tldextract.TLDExtract(cache_dir=None, suffix_list_urls=(), fallback_to_snapshot=True, include_psl_private_domains=False)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    temporary_csv = args.output_csv.with_name(args.output_csv.name + ".tmp")
    found: set[str] = set()
    html_recoveries: list[dict[str, object]] = []
    row_count = 0
    try:
        with zipfile.ZipFile(args.data_dir / "All_HTML.zip") as archive, temporary_csv.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=BASE_COLUMNS + feature_names, lineterminator="\n")
            writer.writeheader()
            for info in archive.infolist():
                if info.is_dir() or not info.filename.lower().endswith(".txt"):
                    continue
                serial = PurePosixPath(info.filename).stem
                if serial not in mapping:
                    raise ValueError(f"HTML archive contains unknown serial {serial}")
                if serial in found:
                    raise ValueError(f"Duplicate HTML archive serial: {serial}")
                url, label = mapping[serial]
                split_row = split_rows[serial]
                if split_row["label"] != label:
                    raise ValueError(f"Mapping/split mismatch for serial {serial}")
                content = archive.read(info)
                html = content.decode("utf-8")
                values, repaired_refs = compute_features(url, html, extractor, serial)
                if repaired_refs:
                    html_recoveries.append({"serial_number": serial, "malformed_numeric_references_delimited": repaired_refs})
                if set(values) != set(feature_names):
                    raise ValueError(f"Computed columns do not match registry for serial {serial}")
                for item in features:
                    value = values[item["name"]]
                    if isinstance(value, float) and not math.isfinite(value):
                        raise ValueError(f"Non-finite feature {item['name']} at serial {serial}")
                    if item["type"] in {"integer", "boolean"} and (not isinstance(value, int) or isinstance(value, bool)):
                        raise ValueError(f"Expected integer-like feature {item['name']} at serial {serial}")
                    if item["type"] == "boolean" and value not in {0, 1}:
                        raise ValueError(f"Expected 0/1 flag {item['name']} at serial {serial}")
                digest = hashlib.sha256(content).hexdigest()
                writer.writerow({
                    "serial_number": serial,
                    "canonical_serial": split_row["canonical_serial"],
                    "group_id": split_row["group_id"],
                    "split": split_row["split"],
                    "label": label,
                    "included_primary": split_row["included_primary"],
                    "mixed_label_exact_html": split_row["mixed_label_exact_html"],
                    "url": url,
                    "html_sha256": digest,
                    **values,
                })
                found.add(serial)
                row_count += 1
                if row_count % 1000 == 0:
                    print(f"Processed {row_count} HTML records", file=sys.stderr)
        if found != set(mapping):
            raise ValueError(f"HTML/mapping serial mismatch: missing={len(set(mapping) - found)} extra={len(found - set(mapping))}")

        # Exact triplet duplicates must reproduce identical features and share one canonical row.
        canonical_features: dict[str, tuple[str, ...]] = {}
        with temporary_csv.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                values = tuple(row[name] for name in feature_names)
                if row["included_primary"] == "1":
                    if row["serial_number"] != row["canonical_serial"]:
                        raise ValueError(f"Primary row is not its canonical record: {row['serial_number']}")
                    canonical_features[row["canonical_serial"]] = values
                elif row["canonical_serial"] not in canonical_features:
                    # CSV follows archive order rather than serial order; deferred checks happen below.
                    continue
                elif canonical_features[row["canonical_serial"]] != values:
                    raise ValueError(f"Collapsed duplicate differs in recomputed feature values: {row['serial_number']}")
        # Re-read after the canonical pass so a duplicate appearing earlier in archive order is checked too.
        with temporary_csv.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                if row["included_primary"] != "1" and canonical_features.get(row["canonical_serial"]) != tuple(row[name] for name in feature_names):
                    raise ValueError(f"Collapsed duplicate differs in recomputed feature values: {row['serial_number']}")
        if len(canonical_features) != sum(row["included_primary"] == "1" for row in split_rows.values()):
            raise ValueError("Primary included row count does not match unique canonical records")
        os.replace(temporary_csv, args.output_csv)
    except Exception:
        temporary_csv.unlink(missing_ok=True)
        raise

    output_hash = sha256_file(args.output_csv)
    manifest = {
        "dataset": registry["dataset"],
        "doi": registry["doi"],
        "registry_version": registry["registry_version"],
        "feature_columns": feature_names,
        "base_columns": BASE_COLUMNS,
        "record_count": row_count,
        "primary_analysis_record_count": sum(row["included_primary"] == "1" for row in split_rows.values()),
        "exact_duplicate_records_retained_but_excluded_from_primary": row_count - sum(row["included_primary"] == "1" for row in split_rows.values()),
        "recomputed_from_sources": ["all 12 registry features; archived HTML parsed inertly with html.parser"],
        "html_parser_recovery": {
            "policy": "On HTMLParser integer-conversion failure only, insert a missing semicolon after a valid decimal/hex numeric-reference prefix and retry parsing.",
            "affected_documents": len(html_recoveries),
            "details": html_recoveries,
        },
        "released_values_not_used_for_any_feature": True,
        "final_split": "features are materialized by the frozen registry rule, but no final-split values are summarized, compared, tuned on, or evaluated in this step",
        "dependencies": versions,
        "tldextract_configuration": {"version": "5.2.0", "private_suffixes": False, "suffix_list_urls": [], "fallback_to_pinned_package_snapshot": True},
        "input_sha256": {
            "All_HTML.zip": sha256_file(args.data_dir / "All_HTML.zip"),
            "Mapping_File.xlsx": sha256_file(args.data_dir / "Mapping_File.xlsx"),
            "split_csv": sha256_file(args.split_csv),
            "registry_json": sha256_file(args.registry_json),
        },
        "output_csv": str(args.output_csv),
        "output_sha256": output_hash,
        "scope_note": "Full source-derived matrix only; no model fitting, feature selection, or final-set analysis.",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"record_count": row_count, "primary_analysis_record_count": manifest["primary_analysis_record_count"],
                      "feature_count": len(feature_names), "output_csv": str(args.output_csv), "output_sha256": output_hash}, indent=2))


if __name__ == "__main__":
    main()
