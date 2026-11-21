# Step 3: Feature registry and leakage-resistant splits

## Purpose and boundary

This step fixes the shared detector inputs and a group-exclusive data partition before any model training or attack pilot. Both detector families must receive the same feature columns. Split creation reads mapping labels, the existing connected domain/template groups, and HTML hashes to apply the duplicate policy; it does not read feature values. The final partition is assigned but is not used for feature selection, recomputation tuning, or analysis.

The official dataset is CompPhish v4 (DOI [10.17632/fmbs4kp9wz.4](https://doi.org/10.17632/fmbs4kp9wz.4)). Raw publisher files remain local and ignored by Git. The bundled feature extractor was read as source only; it was not imported or executed.

## Frozen common feature registry

`data/manifests/compphish_v4_feature_registry.json` defines 12 common inputs: URL length, path slash count, query key count, numeric proportion, hostname digit ratio, URL entropy, embedded URL flag, HTTPS flag, form count, image count, missing-title flag, and inline event-handler flag. It records the official feature ID, table column, type, and precise rule for each feature. The rules follow the inspected source where definitions are clear. Features requiring source/brand lists, ambiguous link-count semantics, or fitted phishing-only corpus statistics are excluded.

An independent deterministic recomputation sampled 100 development records per label, one row per connected group (200 rows total; seed `20261122`). It parsed archived HTML as inert text with BeautifulSoup 4.13.4 and `html.parser`; URL features were recomputed independently. It compared only those sampled rows to the released workbook. Dependency versions are pinned in `requirements-step3-validation.txt`. The feature extractor itself and all final-split feature values were not executed or inspected.

Nine features matched the released table for all 200 sampled rows (float tolerance `1e-9`). Three HTML columns expose a material discrepancy in this sample:

| Feature | Matches | Disagreements | Observed issue |
|---|---:|---:|---|
| `no_of_forms` | 193/200 | 7 | Released values were 0 where archived HTML had forms |
| `no_of_Images` | 193/200 | 7 | Released values were 0 where archived HTML had images |
| `has_inline_event_handlers` | 197/200 | 3 | Released values were 0 where archived HTML had a matching handler |

The disagreements are a limitation of the published feature table, not a reason to drop measurable source features. The PoC pipeline must recompute these three columns from archived HTML for every record and must not use the corresponding released values. The recomputation manifest `data/manifests/compphish_v4_feature_recompute.json` preserves the sample serials, group IDs, archived HTML hashes, exact per-feature comparison counts, and mismatch examples. This resolves the otherwise silent loss of HTML signal while keeping both detector families on one frozen registry. The result is a source-level reproduction for this sample, not proof that every row in the dataset has been fully re-extracted.

## Duplicate policy and group partition

The primary analysis collapses only extra records with the same raw URL, exact HTML SHA-256, and label. It retains separate URL/page records even when their HTML bytes match. Exact HTML reused under conflicting labels remains in the dataset and is flagged; its connected group is never split across partitions. Thus the primary population is 15,355 records after excluding 3 exact triplet duplicates (all phishing), including all 241 rows in the 8 mixed-label exact-HTML groups.

Group allocation is deterministic (seed `20261121`; 64 greedy restarts) and targets 60/15/10/15 percent for train/development/method validation/final while balancing class counts and the placement of mixed-label exact-HTML groups. It assigns whole domain/template connected components atomically. The resulting partitions are:

| Split | Rows | Share | Phishing | Legitimate | Groups | Mixed-label exact-HTML rows |
|---|---:|---:|---:|---:|---:|---:|
| Train | 9,214 | 60.01% | 4,321 | 4,893 | 4,955 | 233 |
| Development | 2,303 | 15.00% | 1,080 | 1,223 | 1,952 | 3 |
| Method validation | 1,535 | 10.00% | 720 | 815 | 1,459 | 2 |
| Final | 2,303 | 15.00% | 1,080 | 1,223 | 1,952 | 3 |

The assignment and metrics are recorded in `data/manifests/compphish_v4_split_stats.json`; row membership is in `data/manifests/compphish_v4_splits.csv`. The validation sample was drawn only from development. The final split should remain sealed through model/attack design and be evaluated once under the pre-registered protocol.

## Reproduction commands

Install the pinned Step 3 validation requirements in an isolated Python environment, then run:

```sh
python scripts/create_compphish_splits.py \
  --data-dir data/raw/compphish_v4 \
  --group-csv data/manifests/compphish_v4_groups.csv \
  --output-csv data/manifests/compphish_v4_splits.csv \
  --output-json data/manifests/compphish_v4_split_stats.json

python scripts/validate_feature_registry.py \
  --data-dir data/raw/compphish_v4 \
  --split-csv data/manifests/compphish_v4_splits.csv \
  --registry-json data/manifests/compphish_v4_feature_registry.json \
  --output-json data/manifests/compphish_v4_feature_recompute.json
```

## Limits and next-step gates

The release has class-confounded source provenance, no row-level timestamps, seven exact duplicate URL rows, and 8 identical-HTML groups carrying conflicting labels. Domain/template grouping is provisional because official row-level source labels and timestamps are unavailable. These limitations constrain generalization claims and should be carried into the paper. Institutional rules for handling or distributing the downloaded dataset have not yet been checked; check them before model training, attack simulation, or any external release. Step 4 should first produce a full common-registry matrix with the three flagged HTML features regenerated for all records, then freeze the method-validation protocol before any final-set analysis.
