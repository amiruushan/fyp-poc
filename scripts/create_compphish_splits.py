#!/usr/bin/env python3
"""Create reproducible group-exclusive splits without reading model features."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

import openpyxl


SPLITS = ("train", "development", "method_validation", "final")
FRACTIONS = {"train": 0.60, "development": 0.15, "method_validation": 0.10, "final": 0.15}
STRATA = ("0", "1", "x")


def norm_serial(value: object) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def norm_label(value: object) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def class_key(label: str) -> str:
    if label == "1":
        return "phishing"
    if label == "0":
        return "legitimate"
    raise ValueError(f"Unexpected label {label!r}")


def read_mapping(path: Path) -> dict[str, tuple[str, str]]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = ws.iter_rows(values_only=True)
    header = [str(v).strip() if v is not None else "" for v in next(rows)]
    required = ["serial_number", "url", "label"]
    if header[:3] != required:
        raise ValueError(f"Unexpected mapping header: {header[:3]}")
    records = {}
    for row in rows:
        serial = norm_serial(row[0])
        if serial in records:
            raise ValueError(f"Duplicate serial in mapping: {serial}")
        records[serial] = (str(row[1] or "").strip(), norm_label(row[2]))
    wb.close()
    return records


def target_cost(current: dict[str, Counter[str]], targets: dict[str, Counter[str]], totals: Counter[str]) -> float:
    cost = 0.0
    for split in SPLITS:
        for label in STRATA:
            total = totals[label]
            if total == 0:
                continue
            error = (current[split][label] - targets[split][label]) / total
            cost += error * error
    return cost


def allocate_groups(group_rows: dict[str, Counter[str]], seed: int, trials: int) -> tuple[dict[str, str], float, int]:
    totals = Counter()
    for counts in group_rows.values():
        totals.update(counts)
    targets = {
        split: Counter({label: totals[label] * FRACTIONS[split] for label in STRATA})
        for split in SPLITS
    }

    best_assignment: dict[str, str] | None = None
    best_cost = float("inf")
    best_trial = -1
    group_ids = list(group_rows)
    for trial in range(trials):
        rng = random.Random(seed + trial)
        tie_order = {group_id: rng.random() for group_id in group_ids}
        ordered = sorted(group_ids, key=lambda g: (-(group_rows[g]["0"] + group_rows[g]["1"]), tie_order[g], g))
        current = {split: Counter() for split in SPLITS}
        assignment: dict[str, str] = {}
        for group_id in ordered:
            counts = group_rows[group_id]
            deltas = {}
            for split in SPLITS:
                delta = 0.0
                for label in STRATA:
                    if totals[label] == 0:
                        continue
                    total = totals[label]
                    before = (current[split][label] - targets[split][label]) / total
                    after = (current[split][label] + counts[label] - targets[split][label]) / total
                    delta += after * after - before * before
                deltas[split] = delta
            best_delta = min(deltas.values())
            choices = [s for s, delta in deltas.items() if abs(delta - best_delta) < 1e-15]
            selected = rng.choice(choices)
            assignment[group_id] = selected
            current[selected].update(counts)
        score = target_cost(current, targets, totals)
        if score < best_cost:
            best_assignment, best_cost, best_trial = assignment, score, trial

    if best_assignment is None:
        raise RuntimeError("Group allocation failed")

    # Deterministic single-group local moves improve the best greedy allocation.
    assignment = best_assignment.copy()
    current = {split: Counter() for split in SPLITS}
    for group_id, split in assignment.items():
        current[split].update(group_rows[group_id])
    ordered_ids = sorted(group_rows, key=lambda g: (-(group_rows[g]["0"] + group_rows[g]["1"]), g))
    for _ in range(3):
        changed = False
        for group_id in ordered_ids:
            origin = assignment[group_id]
            counts = group_rows[group_id]
            origin_cost = target_cost(current, targets, totals)
            selected, selected_cost = origin, origin_cost
            current[origin].subtract(counts)
            for destination in SPLITS:
                if destination == origin:
                    continue
                current[destination].update(counts)
                score = target_cost(current, targets, totals)
                current[destination].subtract(counts)
                if score + 1e-15 < selected_cost:
                    selected, selected_cost = destination, score
            if selected != origin:
                current[selected].update(counts)
                assignment[group_id] = selected
                changed = True
            else:
                current[origin].update(counts)
        if not changed:
            break
    return assignment, target_cost(current, targets, totals), best_trial


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--group-csv", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261121)
    parser.add_argument("--trials", type=int, default=64)
    args = parser.parse_args()

    mapping = read_mapping(args.data_dir / "Mapping_File.xlsx")
    groups: dict[str, dict[str, str]] = {}
    group_members: dict[str, list[str]] = defaultdict(list)
    with args.group_csv.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            serial, group_id, label = row["serial_number"], row["group_id"], row["label"]
            if serial in groups:
                raise ValueError(f"Duplicate serial in group manifest: {serial}")
            if serial not in mapping or mapping[serial][1] != label:
                raise ValueError(f"Mapping/group mismatch for serial {serial}")
            groups[serial] = {"group_id": group_id, "label": label}
            group_members[group_id].append(serial)
    if set(mapping) != set(groups):
        raise ValueError("Mapping and group manifest serial sets differ")

    # Collapse only exact duplicate URL + exact HTML + same-label records.
    # Similar pages and the same HTML served at distinct URLs remain separate.
    tuple_members: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    exact_html_labels: dict[str, set[str]] = defaultdict(set)
    digest_by_serial: dict[str, str] = {}
    with zipfile.ZipFile(args.data_dir / "All_HTML.zip") as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".txt"):
                continue
            serial = PurePosixPath(info.filename).stem
            if serial not in mapping:
                raise ValueError(f"HTML archive contains unknown serial {serial}")
            url, label = mapping[serial]
            digest = hashlib.sha256(archive.read(info)).hexdigest()
            tuple_members[(url, digest, label)].append(serial)
            exact_html_labels[digest].add(label)
            digest_by_serial[serial] = digest

    canonical_by_serial: dict[str, str] = {}
    duplicate_counts_by_label: Counter[str] = Counter()
    for (url, digest, label), members in tuple_members.items():
        canonical = min(members, key=lambda x: (int(x) if x.isdigit() else 10**30, x))
        for serial in members:
            canonical_by_serial[serial] = canonical
        duplicate_counts_by_label[label] += len(members) - 1
        member_groups = {groups[serial]["group_id"] for serial in members}
        if len(member_groups) != 1:
            raise ValueError("Exact duplicate record crosses connected groups")

    included_canonical = {canonical_by_serial[s] for s in mapping}
    unit_group: dict[str, str] = {}
    unit_label: dict[str, str] = {}
    for serial in mapping:
        canonical = canonical_by_serial[serial]
        group_id = groups[serial]["group_id"]
        if canonical in unit_group and unit_group[canonical] != group_id:
            raise ValueError("Canonical record appears in different groups")
        unit_group[canonical] = group_id
        unit_label[canonical] = groups[serial]["label"]

    group_counts: dict[str, Counter[str]] = defaultdict(Counter)
    group_has_mixed_html: set[str] = set()
    mixed_exact_html_canonical = set()
    for canonical in sorted(included_canonical):
        group_counts[unit_group[canonical]][unit_label[canonical]] += 1
        digest = digest_by_serial[canonical]
        if len(exact_html_labels[digest]) > 1:
            group_has_mixed_html.add(unit_group[canonical])
            mixed_exact_html_canonical.add(canonical)
    for group_id in group_has_mixed_html:
        group_counts[group_id]["x"] = 1
    assignment, score, chosen_trial = allocate_groups(group_counts, args.seed, args.trials)

    # Every original row receives the same split as its connected group. The
    # primary-analysis flag excludes only repeated identical URL/HTML/label rows.
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, Counter[str]] = {s: Counter() for s in SPLITS}
    groups_by_split: dict[str, set[str]] = {s: set() for s in SPLITS}
    exact_html_mixed_rows = Counter()
    with args.output_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["serial_number", "canonical_serial", "group_id", "split", "label", "included_primary", "mixed_label_exact_html"])
        for serial in sorted(mapping, key=lambda x: (int(x) if x.isdigit() else 10**30, x)):
            canonical = canonical_by_serial[serial]
            group_id = groups[serial]["group_id"]
            split = assignment[group_id]
            label = groups[serial]["label"]
            included = serial == canonical
            mixed = len(exact_html_labels[digest_by_serial[serial]]) > 1
            writer.writerow([serial, canonical, group_id, split, label, int(included), int(mixed)])
            groups_by_split[split].add(group_id)
            if included:
                counts[split][label] += 1
            if mixed and included:
                exact_html_mixed_rows[split] += 1

    if set().union(*(groups_by_split[s] for s in SPLITS)) != set(group_counts):
        raise ValueError("Not every group was assigned to exactly one split")
    if any(groups_by_split[a] & groups_by_split[b] for i, a in enumerate(SPLITS) for b in SPLITS[i + 1:]):
        raise ValueError("A connected group appears in more than one split")
    if any(counts[s]["0"] == 0 or counts[s]["1"] == 0 for s in SPLITS):
        raise ValueError("At least one split is missing a class")

    total_units = sum(counts[s].total() for s in SPLITS)
    all_groups_by_split = {s: len(groups_by_split[s]) for s in SPLITS}
    stats = {
        "dataset": "CompPhish v4",
        "doi": "10.17632/fmbs4kp9wz.4",
        "assignment": {
            "seed": args.seed,
            "greedy_restarts": args.trials,
            "selected_restart_index": chosen_trial,
            "objective": "sum of squared deviations for label counts and mixed-label exact-HTML group counts, normalized by their dataset totals",
            "group_exclusivity": "connected domain/template group IDs are assigned atomically",
            "primary_duplicate_policy": "collapse exact URL + exact HTML SHA-256 + same-label rows; retain distinct URL/page pairs even when HTML is identical",
            "final_set": "assigned from labels and group metadata only; no feature values, model scores, or attack outcomes were inspected",
        },
        "original_rows": len(mapping),
        "primary_analysis_rows": total_units,
        "exact_duplicate_rows_excluded_from_primary": len(mapping) - total_units,
        "excluded_duplicate_rows_by_label": {class_key(k): v for k, v in duplicate_counts_by_label.items()},
        "mixed_label_exact_html_rows_retained_primary": len(mixed_exact_html_canonical),
        "mixed_label_exact_html_groups": len(group_has_mixed_html),
        "connected_groups": len(group_counts),
        "maximum_group_size_primary_rows": max(sum(c.values()) for c in group_counts.values()),
        "splits": {},
    }
    for split in SPLITS:
        n = counts[split].total()
        stats["splits"][split] = {
            "target_fraction": FRACTIONS[split],
            "primary_rows": n,
            "actual_fraction": n / total_units,
            "phishing": counts[split]["1"],
            "legitimate": counts[split]["0"],
            "group_count": all_groups_by_split[split],
            "mixed_label_exact_html_rows_retained_primary": exact_html_mixed_rows[split],
            "mixed_label_exact_html_groups": sum(1 for g in groups_by_split[split] if g in group_has_mixed_html),
        }
    args.output_json.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
