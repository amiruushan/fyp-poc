# Step 4: Full source-derived feature matrix

## Result

`scripts/build_compphish_feature_matrix.py` builds all 12 frozen registry features directly from the mapping workbook and archived HTML, without using any values from the publisher's feature workbook. It preserves every source row and attaches its split, group, canonical-duplicate, label, and exact HTML SHA-256 metadata. The `included_primary` flag marks the 15,355 primary-analysis rows; the 3 duplicate records remain in the file for provenance but must be excluded from primary model fitting.

The full local output was generated successfully: 15,358 records, 12 feature columns. It is written under `data/processed/`, which is ignored by Git because it contains dataset-derived records. The tracked manifest `data/manifests/compphish_v4_feature_matrix.json` records the output hash, source archive hash, pinned dependencies, feature schema, and row counts; it does not include individual feature values.

## Parser recovery

The full archive contains one HTML document (serial `202420251302`) whose malformed semicolon-less numeric character references caused Python 3.14's `html.parser` to raise an integer-conversion error. The builder retries only on that parser error, inserting a missing semicolon after a valid decimal/hex numeric prefix, then parses with the same pinned BeautifulSoup `html.parser` backend. Eleven malformed references were delimited in that single document. The original bytes and HTML hash remain unchanged. Any other parser error fails the build rather than silently skipping the row. This recovery is recorded in the matrix manifest.

## Final-set handling

Feature values for every row are mechanically materialized from the frozen registry so both detector families can use the same matrix. This step does not compute final-set distributions, compare final values with labels, tune features or thresholds, or fit/evaluate models. Keep final-set rows sealed until the experimental protocol and analysis plan are frozen. The matrix is local and ignored by Git; only its manifest is committed.

## Reproduction

Use the isolated environment with the pinned versions in `requirements-step3-validation.txt`:

```sh
"$HOME/.venvs/fyp-poc-step3/bin/python" scripts/build_compphish_feature_matrix.py \
  --data-dir data/raw/compphish_v4 \
  --split-csv data/manifests/compphish_v4_splits.csv \
  --registry-json data/manifests/compphish_v4_feature_registry.json
```

The output defaults to `data/processed/compphish_v4_feature_matrix.csv`. Override `--output-csv` and `--output-json` only if you need a different local destination. Before any model training or attack simulation, check institutional rules for use and distribution of the dataset. Preserve the source-confounding, absent-timestamp, provisional-grouping, and conflicting-label caveats from Step 2/3 in any results or paper claims.
