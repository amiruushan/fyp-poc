#!/usr/bin/env python3
"""Offline integrity, linkage, duplicate, and grouping audit for CompPhish v4."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html.parser
import importlib.metadata
import json
import math
import pickletools
import re
import statistics
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit

import openpyxl
import tldextract


def norm_serial(value: object) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def norm_label(value: object) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def norm_feature_id(value: object) -> str:
    raw = str(value or "").strip()
    digits = raw[1:].translate(str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")) if raw.startswith("F") else ""
    return f"F{int(digits)}" if digits.isdigit() else ""


def canonical_url(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parts = urlsplit(raw if "://" in raw else "//" + raw)
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        return ""
    port = parts.port
    netloc = host
    if port and not ((parts.scheme.lower() == "http" and port == 80) or (parts.scheme.lower() == "https" and port == 443)):
        netloc += f":{port}"
    scheme = parts.scheme.lower()
    path = parts.path or "/"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def get_rows(path: Path) -> tuple[list[str], list[dict[str, object]]]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    iterator = ws.iter_rows(values_only=True)
    header = [str(v).strip() if v is not None else "" for v in next(iterator)]
    while header and not header[-1]:
        header.pop()
    rows = [dict(zip(header, values)) for values in iterator]
    wb.close()
    return header, rows


class TemplateParser(html.parser.HTMLParser):
    """Fingerprint normalized DOM structure, stable attributes, and visible text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.events: list[str] = []
        self.skip_content: list[str] = []

    @staticmethod
    def attrs_key(attrs: list[tuple[str, str | None]]) -> str:
        stable = {"class", "id", "role", "type", "name", "rel", "method", "aria-label", "itemprop"}
        normalized = []
        for name, value in attrs:
            name = name.lower()
            value = " ".join((value or "").split()).casefold()
            if name in stable and value:
                value = re.sub(r"\d+", "#", value)
                if name == "class":
                    value = " ".join(sorted(value.split()))
                normalized.append(f"{name}={value}")
            else:
                normalized.append(name)
        return ",".join(sorted(normalized))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style"}:
            self.skip_content.append(tag.lower())
        self.events.append(f"S:{tag.lower()}[{self.attrs_key(attrs)}]")

    def handle_endtag(self, tag: str) -> None:
        self.events.append(f"E:{tag.lower()}")
        if self.skip_content and self.skip_content[-1] == tag.lower():
            self.skip_content.pop()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.events.append(f"S:{tag.lower()}[{self.attrs_key(attrs)}]")
        self.events.append(f"E:{tag.lower()}")

    def handle_decl(self, decl: str) -> None:
        self.events.append(f"D:{decl.lower()}")

    def handle_data(self, data: str) -> None:
        if self.skip_content:
            return
        text = " ".join(data.split()).casefold()
        if text:
            self.events.append(f"T:{text}")


class UnionFind:
    def __init__(self, items: list[str]) -> None:
        self.parent = {x: x for x in items}
        self.size = {x: 1 for x in items}

    def find(self, item: str) -> str:
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != item:
            next_item = self.parent[item]
            self.parent[item] = root
            item = next_item
        return root

    def union(self, first: str, second: str) -> None:
        a, b = self.find(first), self.find(second)
        if a == b:
            return
        if self.size[a] < self.size[b]:
            a, b = b, a
        self.parent[b] = a
        self.size[a] += self.size[b]


def hashed_key(prefix: str, value: str) -> str:
    return prefix + hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()


def pct(values: list[int], p: float) -> int:
    if not values:
        return 0
    values = sorted(values)
    return values[min(len(values) - 1, max(0, math.ceil(len(values) * p) - 1))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--release-manifest", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--group-csv", type=Path, required=True)
    args = parser.parse_args()

    tool_versions = {
        "openpyxl": importlib.metadata.version("openpyxl"),
        "tldextract": importlib.metadata.version("tldextract"),
    }
    if tool_versions != {"openpyxl": "3.1.5", "tldextract": "5.2.0"}:
        raise SystemExit(f"Use pinned audit dependencies (openpyxl 3.1.5, tldextract 5.2.0); found {tool_versions}")

    release = json.loads(args.release_manifest.read_text())
    expected = {f["filename"]: f for f in release["files"]}
    required = {
        "All_Features_threshold90.xlsx", "All_HTML.zip", "Data_Dictionary.xlsx",
        "feature extractor.zip", "Mapping_File.xlsx", "Readme.docx", "requirements.txt",
    }
    file_checks: dict[str, dict[str, object]] = {}
    for filename in sorted(required):
        path = args.data_dir / filename
        if not path.exists():
            raise SystemExit(f"Required v4 file is missing: {filename}")
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                size += len(chunk)
                digest.update(chunk)
        expected_info = expected[filename]
        file_checks[filename] = {
            "actual_size": size,
            "expected_size": expected_info["size"],
            "size_match": size == expected_info["size"],
            "actual_sha256": digest.hexdigest(),
            "expected_sha256": expected_info["sha256"],
            "sha256_match": digest.hexdigest() == expected_info["sha256"],
        }

    mapping_header, mappings = get_rows(args.data_dir / "Mapping_File.xlsx")
    feature_header, features = get_rows(args.data_dir / "All_Features_threshold90.xlsx")
    dictionary_header, dictionary_rows = get_rows(args.data_dir / "Data_Dictionary.xlsx")
    if mapping_header[:3] != ["serial_number", "url", "label"]:
        raise SystemExit(f"Unexpected mapping columns: {mapping_header[:3]}")
    if feature_header[:3] != ["serial_number", "url", "label"]:
        raise SystemExit(f"Unexpected feature identifiers: {feature_header[:3]}")
    dictionary_feature_rows = [
        row for row in dictionary_rows
        if norm_feature_id(row.get("Feature ID"))
    ]
    dictionary_ids = {norm_feature_id(row.get("Feature ID")) for row in dictionary_feature_rows}
    expected_dictionary_ids = {f"F{i}" for i in range(1, 71)}
    dictionary_fields = [
        "Feature Name", "Data Type", "Category", "Description",
        "Computational Rule/Threshold/Criteria",
    ]
    dictionary_names = {
        str(row.get("Feature Name") or "").strip().casefold(): str(row.get("Feature Name") or "").strip()
        for row in dictionary_feature_rows
    }
    feature_name_set = {str(name).strip().casefold() for name in feature_header[3:]}
    dictionary_name_set = set(dictionary_names)
    case_only_name_differences = [
        {"feature_table": str(name).strip(), "data_dictionary": dictionary_names[str(name).strip().casefold()]}
        for name in feature_header[3:]
        if str(name).strip().casefold() in dictionary_names
        and str(name).strip() != dictionary_names[str(name).strip().casefold()]
    ]

    with zipfile.ZipFile(args.data_dir / "feature extractor.zip") as source_bundle:
        source_names = source_bundle.namelist()
        python_sources = {
            name: source_bundle.read(name).decode("utf-8", "replace")
            for name in source_names if name.lower().endswith(".py")
        }
        pickle_members = [name for name in source_names if name.lower().endswith((".pki", ".pkl", ".pickle"))]
        pickle_audit = []
        for name in pickle_members:
            operations = [op.name for op, _, _ in pickletools.genops(source_bundle.read(name))]
            executable_ops = {"GLOBAL", "STACK_GLOBAL", "EXT1", "EXT2", "EXT4", "REDUCE", "BUILD", "NEWOBJ", "NEWOBJ_EX"}
            pickle_audit.append({
                "member": PurePosixPath(name).name,
                "opcode_count": len(operations),
                "protocol": next((arg for op, arg, _ in pickletools.genops(source_bundle.read(name)) if op.name == "PROTO"), None),
                "global_or_constructor_opcodes": sum(op in executable_ops for op in operations),
            })

    map_by_id: dict[str, dict[str, object]] = {}
    duplicate_map_ids: list[str] = []
    map_url_counts: Counter[str] = Counter()
    map_canonical_counts: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    canonical_url_labels: dict[str, set[str]] = defaultdict(set)
    domains: dict[str, str] = {}
    registrable_domain_keys: set[str] = set()
    id_url_errors = 0
    id_label_errors = 0
    malformed_urls = 0
    missing_host_rows = 0
    unregistrable_host_rows = 0
    extract = tldextract.TLDExtract(suffix_list_urls=(), include_psl_private_domains=True, cache_dir=None)
    domain_row_ids: dict[str, list[str]] = defaultdict(list)
    for row in mappings:
        rid = norm_serial(row.get("serial_number"))
        if rid in map_by_id:
            duplicate_map_ids.append(rid)
        map_by_id[rid] = row
        url = str(row.get("url") or "").strip()
        label = norm_label(row.get("label"))
        labels[label] += 1
        map_url_counts[url] += 1
        canon = canonical_url(url)
        if canon:
            map_canonical_counts[canon] += 1
            canonical_url_labels[canon].add(label)
            parsed = urlsplit(canon)
            host = parsed.hostname or ""
            if not host:
                missing_host_rows += 1
                malformed_urls += 1
                domain_key = "UNPARSEABLE:" + rid
                domains[rid] = domain_key
                domain_row_ids[domain_key].append(rid)
                continue
            suffix = extract(host)
            reg = f"{suffix.domain}.{suffix.suffix}" if suffix.domain and suffix.suffix else ""
            if reg:
                domain_key = reg.lower()
                registrable_domain_keys.add(domain_key)
            else:
                unregistrable_host_rows += 1
                domain_key = "HOST:" + host.lower()
        else:
            malformed_urls += 1
            missing_host_rows += 1
            domain_key = "UNPARSEABLE:" + rid
        domains[rid] = domain_key
        domain_row_ids[domain_key].append(rid)

    feature_by_id: dict[str, dict[str, object]] = {}
    duplicate_feature_ids: list[str] = []
    feature_missing: Counter[str] = Counter()
    for row in features:
        rid = norm_serial(row.get("serial_number"))
        if rid in feature_by_id:
            duplicate_feature_ids.append(rid)
        feature_by_id[rid] = row
        for name in feature_header[3:]:
            if row.get(name) is None or str(row.get(name)).strip() == "":
                feature_missing[name] += 1
    missing_feature_rows = sorted(set(map_by_id) - set(feature_by_id))
    extra_feature_rows = sorted(set(feature_by_id) - set(map_by_id))
    for rid in set(map_by_id) & set(feature_by_id):
        if str(map_by_id[rid].get("url") or "").strip() != str(feature_by_id[rid].get("url") or "").strip():
            id_url_errors += 1
        if norm_label(map_by_id[rid].get("label")) != norm_label(feature_by_id[rid].get("label")):
            id_label_errors += 1

    archive_path = args.data_dir / "All_HTML.zip"
    with zipfile.ZipFile(archive_path) as archive:
        infos = [x for x in archive.infolist() if not x.is_dir()]
        names = [x.filename for x in infos]
        unsafe_paths = [n for n in names if PurePosixPath(n).is_absolute() or ".." in PurePosixPath(n).parts]
        html_infos = [x for x in infos if x.filename.lower().endswith(".txt")]
        html_by_stem: dict[str, list[zipfile.ZipInfo]] = defaultdict(list)
        exact_hashes: Counter[str] = Counter()
        exact_hash_by_id: dict[str, str] = {}
        templates: dict[str, str] = {}
        size_by_template: Counter[str] = Counter()
        for info in html_infos:
            stem = PurePosixPath(info.filename).stem
            html_by_stem[stem].append(info)
            # Reading each member checks the member CRC and never writes it to disk.
            payload = archive.read(info)
            content_hash = hashlib.sha256(payload).hexdigest()
            exact_hashes[content_hash] += 1
            exact_hash_by_id[stem] = content_hash
            shape = TemplateParser()
            shape.feed(payload.decode("utf-8", "replace"))
            template = hashlib.sha256("\n".join(shape.events).encode("utf-8")).hexdigest()
            templates[stem] = template
            size_by_template[template] += 1
        mapped_ids = set(map_by_id)
        archive_ids = set(html_by_stem)
        missing_html = sorted(mapped_ids - archive_ids)
        extra_html = sorted(archive_ids - mapped_ids)
        duplicate_html_stems = sorted(k for k, v in html_by_stem.items() if len(v) > 1)
        duplicate_archive_files = len(html_infos) - len(exact_hashes)
        exact_hash_label_sets: dict[str, set[str]] = defaultdict(set)
        exact_hash_row_counts: Counter[str] = Counter()
        for rid, content_hash in exact_hash_by_id.items():
            exact_hash_label_sets[content_hash].add(norm_label(map_by_id[rid].get("label")))
            exact_hash_row_counts[content_hash] += 1
        mixed_label_exact_hashes = {h for h, ls in exact_hash_label_sets.items() if len(ls) > 1}
        mixed_label_exact_rows = sum(exact_hash_row_counts[h] for h in mixed_label_exact_hashes)

    # Merge rows sharing either an offline public-suffix registrable domain or
    # the normalized HTML-template fingerprint.
    uf = UnionFind(sorted(map_by_id))
    domain_representative: dict[str, str] = {}
    template_representative: dict[str, str] = {}
    row_templates: dict[str, str] = {}
    for rid in sorted(map_by_id):
        d = domains[rid]
        if d in domain_representative:
            uf.union(rid, domain_representative[d])
        else:
            domain_representative[d] = rid
        template = templates.get(rid)
        if template:
            row_templates[rid] = template
            if template in template_representative:
                uf.union(rid, template_representative[template])
            else:
                template_representative[template] = rid

    groups: dict[str, list[str]] = defaultdict(list)
    for rid in sorted(map_by_id):
        groups[uf.find(rid)].append(rid)
    stable_group = {rid: "g-" + hashlib.sha256("\n".join(sorted(members)).encode()).hexdigest()[:16]
                    for members in groups.values() for rid in members}
    labels_by_group: dict[str, set[str]] = defaultdict(set)
    for rid, row in map_by_id.items():
        labels_by_group[stable_group[rid]].add(norm_label(row.get("label")))
    mixed_class_groups = sum(1 for v in labels_by_group.values() if len(v) > 1)

    args.group_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.group_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["serial_number", "group_id", "domain_group_id", "template_group_id", "label"])
        for rid in sorted(map_by_id, key=lambda x: (int(x) if x.isdigit() else 10**30, x)):
            writer.writerow([
                rid, stable_group[rid], hashed_key("d-", domains[rid]),
                hashed_key("t-", row_templates[rid]) if rid in row_templates else "", norm_label(map_by_id[rid].get("label")),
            ])

    group_sizes = [len(v) for v in groups.values()]
    result = {
        "dataset": release["dataset"],
        "version": release["version"],
        "doi": release["doi"],
        "license": release["license"],
        "audit_tool_versions": tool_versions,
        "files": file_checks,
        "mapping": {
            "header": mapping_header,
            "rows": len(mappings),
            "unique_serials": len(map_by_id),
            "duplicate_serial_count": len(duplicate_map_ids),
            "labels": dict(labels),
            "exact_duplicate_url_rows": sum(n - 1 for n in map_url_counts.values() if n > 1),
            "normalized_duplicate_url_rows": sum(n - 1 for n in map_canonical_counts.values() if n > 1),
            "normalized_url_groups_with_mixed_labels": sum(
                1 for labels_for_url in canonical_url_labels.values() if len(labels_for_url) > 1
            ),
            "malformed_urls": malformed_urls,
            "rows_with_missing_host": missing_host_rows,
            "rows_with_host_without_registrable_suffix": unregistrable_host_rows,
            "distinct_registrable_domains": len(registrable_domain_keys),
            "distinct_host_fallback_groups": len({d for d in domain_row_ids if d.startswith("HOST:")}),
            "distinct_domain_groups_for_splitting": len(domain_row_ids),
            "domain_groups_with_multiple_rows": sum(1 for v in domain_row_ids.values() if len(v) > 1),
            "domain_groups_with_mixed_labels": sum(1 for v in domain_row_ids.values() if len({norm_label(map_by_id[r].get('label')) for r in v}) > 1),
        },
        "features": {
            "header_columns": len(feature_header),
            "feature_columns_excluding_serial_url_label": len(feature_header) - 3,
            "rows": len(features),
            "unique_serials": len(feature_by_id),
            "duplicate_serial_count": len(duplicate_feature_ids),
            "missing_rows_vs_mapping": len(missing_feature_rows),
            "extra_rows_vs_mapping": len(extra_feature_rows),
            "url_mismatch_rows": id_url_errors,
            "label_mismatch_rows": id_label_errors,
            "missing_cells_by_feature": dict(feature_missing),
        },
        "data_dictionary": {
            "header": dictionary_header,
            "document_rows": len(dictionary_rows),
            "feature_rows": len(dictionary_feature_rows),
            "unique_feature_ids": len(dictionary_ids),
            "missing_feature_ids": sorted(expected_dictionary_ids - dictionary_ids,
                                           key=lambda x: int(x[1:])),
            "extra_feature_ids": sorted(dictionary_ids - expected_dictionary_ids),
            "feature_table_feature_count": len(feature_header) - 3,
            "missing_names_case_insensitive": sorted(feature_name_set - dictionary_name_set),
            "extra_names_case_insensitive": sorted(dictionary_name_set - feature_name_set),
            "case_only_name_differences": case_only_name_differences,
            "empty_cells_by_field": {
                field: sum(row.get(field) is None or not str(row.get(field)).strip()
                           for row in dictionary_feature_rows)
                for field in dictionary_fields
            },
            "feature_ids_with_empty_computational_rule": [
                norm_feature_id(row.get("Feature ID")) for row in dictionary_feature_rows
                if row.get("Computational Rule/Threshold/Criteria") is None
                or not str(row.get("Computational Rule/Threshold/Criteria")).strip()
            ],
            "non_feature_note_rows": sum(
                1 for row in dictionary_rows
                if str(row.get("Feature ID") or "").strip()
                and not norm_feature_id(row.get("Feature ID"))
            ),
        },
        "feature_extractor_bundle": {
            "member_count": len(source_names),
            "python_source_count": len(python_sources),
            "source_has_pickle_load": any("pickle.load" in source for source in python_sources.values()),
            "pickle_payloads_statically_disassembled": pickle_audit,
            "executed": False,
        },
        "html_archive": {
            "member_count": len(infos),
            "text_html_member_count": len(html_infos),
            "unique_serial_stems": len(html_by_stem),
            "missing_mapping_serials": len(missing_html),
            "extra_archive_serials": len(extra_html),
            "duplicate_stems": len(duplicate_html_stems),
            "exact_duplicate_content_rows": duplicate_archive_files,
            "distinct_exact_sha256_contents": len(exact_hashes),
            "exact_content_groups_with_mixed_labels": len(mixed_label_exact_hashes),
            "rows_in_mixed_label_exact_content_groups": mixed_label_exact_rows,
            "unsafe_member_paths": len(unsafe_paths),
        },
        "grouping": {
            "registrable_domain_extractor": "tldextract 5.2.0; bundled PSL; private suffixes included; no network fetch",
            "html_template_rule": "HTMLParser DOM structure plus sorted class/id/role/type/name/rel/method/aria-label/itemprop values (digit runs normalized); visible text lowercased with whitespace collapsed; other attribute values omitted; comments omitted",
            "group_count_connected_domain_or_template": len(groups),
            "mixed_label_connected_groups": mixed_class_groups,
            "group_size_min": min(group_sizes) if group_sizes else 0,
            "group_size_median": statistics.median(group_sizes) if group_sizes else 0,
            "group_size_p95_nearest_rank": pct(group_sizes, .95),
            "group_size_p99_nearest_rank": pct(group_sizes, .99),
            "group_size_max": max(group_sizes, default=0),
            "groups_over_100_rows": sum(n > 100 for n in group_sizes),
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "mapping": result["mapping"],
        "features": {k: v for k, v in result["features"].items() if k != "missing_cells_by_feature"},
        "html_archive": result["html_archive"],
        "grouping": result["grouping"],
        "all_download_checksums_match": all(x["sha256_match"] and x["size_match"] for x in file_checks.values()),
    }, indent=2))


if __name__ == "__main__":
    main()
