# Step 2: CompPhish v4 acquisition and data audit

**Status:** Acquisition and integrity audit complete; feature reconstruction and experimental use remain gated.
**Dataset:** CompPhish v4, DOI `10.17632/fmbs4kp9wz.4`.
**Source:** [Official Mendeley Data v4 record](https://data.mendeley.com/datasets/fmbs4kp9wz/4), which states CC BY 4.0.

## Acquisition and handling

The official v4 API listed eight files. Seven needed for this audit were downloaded into `data/raw/compphish_v4/`, which is ignored by Git. The dataset-creator scraper bundle was recorded in the release manifest but not downloaded or run. The feature table, HTML archive, data dictionary, feature-extractor bundle, mapping, README, and requirements file all match the publisher's exact byte sizes and SHA-256 hashes. The complete release inventory and publisher hashes are in `data/manifests/compphish_v4_release.json`.

The 726 MB archive was read in place. HTML was not opened in a browser, executed, or written out as extracted files; `zipfile` read members as inert bytes for checksums, CRC validation, and structural fingerprints. No archived URLs were visited and no live network lookup was used to derive domains. The bundled public-suffix snapshot in pinned `tldextract` 5.2.0 was used offline.

## Results

### Table and mapping integrity

- The mapping contains 15,358 records, with 15,358 unique serial numbers and only `serial_number`, `url`, and `label` columns.
- Label counts are 7,204 phishing (`1`) and 8,154 legitimate (`0`).
- The feature workbook contains 73 columns: those three identifiers and 70 feature columns. Its 15,358 serial numbers, URLs, and labels match the mapping exactly; there are no missing or extra rows, duplicate serials, or missing feature values.
- The dictionary has 70 feature entries plus a note row. IDs F6-F70 use Unicode subscript digits, but normalize to the expected F1-F70 sequence. Feature names match case-insensitively; one differs only by capitalization: `no_of_Images` in the table and `no_of_images` in the dictionary.
- The dictionary leaves the computational-rule field blank for 28 features: F2-F6, F10-F11, F15-F28, F39-F40, F44-F46, and F48-F49. The feature extractor source may clarify some rules; those definitions need review and independent checks before features are recomputed or selected.

### Archived HTML and duplicates

- The archive has 15,358 `.txt` members, one unique serial stem per record, with zero missing or extra serials relative to the mapping. All archive member paths are safe; all member CRCs validated while reading.
- There are 13,180 distinct exact HTML SHA-256 contents, meaning 2,178 repeated records beyond the first copy. Eight exact-content groups contain both labels, involving 241 records. These conflicting labels must be retained as an explicit data-quality issue and handled by a prespecified policy before modeling; do not silently deduplicate them.
- There are 7 exact duplicate URL rows and 101 duplicate rows after canonicalization (lowercase host, remove trailing host dot and fragment, drop default ports, and normalize an empty path to `/`; scheme and query remain significant). No canonical URL group has mixed labels.

### Domain/template grouping

For the provisional connected-group manifest, URLs were grouped by registrable domain using the offline PSL with private suffixes included. Hosts that have no registrable suffix were grouped by exact host. The template fingerprint records DOM start/end tags, selected stable attribute values (`class`, `id`, `role`, `type`, `name`, `rel`, `method`, `aria-label`, `itemprop`), and visible text after case and whitespace normalization. Digit runs in those selected attribute values become `#`; other attribute values, comments, and script/style contents are omitted. Rows sharing either a domain group or a template fingerprint are merged transitively.

This produced 10,318 connected components from 15,358 rows (median size 1, 95th percentile 2, 99th percentile 6, maximum 337). Twenty-nine components contain both labels; twelve contain over 100 rows. These are provisional grouping results, not a final split. Grouping assumptions and component-size effects should be checked before allocating the train/development/method-validation/final sets.

### Provenance and time limits

The release describes phishing records as sourced from PhishTank/OpenPhish and legitimate records from DataForSEO Top-1000. The mapping and feature table have no row-level source field, so source cannot be audited or controlled per record and acquisition source is confounded with label. The record/article describe collection from September 2024 through August 2025, but the files do not provide verified per-row timestamps; this does not support a temporal holdout.

The feature-extractor bundle was inspected as text but not executed. It calls `pickle.load` at module import. Its bundled pickle was disassembled statically: protocol 4, with no `GLOBAL`, `STACK_GLOBAL`, `REDUCE`, `BUILD`, `NEWOBJ`, or extension opcodes. This lowers the specific pickle execution concern but is not a substitute for reviewing the extractor before running it.

## Reproduction

Install the two pinned audit dependencies, then run:

```sh
python3 -m pip install -r requirements-step2-audit.txt
python3 scripts/audit_compphish_v4.py \
  --data-dir data/raw/compphish_v4 \
  --release-manifest data/manifests/compphish_v4_release.json \
  --output-json data/manifests/compphish_v4_audit.json \
  --group-csv data/manifests/compphish_v4_groups.csv
```

The script verifies checksums, workbook joins, labels, missingness, archive-to-mapping coverage, exact HTML duplicates, and connected domain/template groups. The per-record group CSV contains serials, labels, and hashed domain/template/group IDs; it contains no URLs or raw HTML.

## Step 2 decision

**Conditional go to Step 3.** The release files, labels, and serial mapping pass integrity checks, and the grouped dataset has enough connected components to attempt a group-aware split. Before training, Step 3 must resolve the 28 missing dictionary rules using inspected extractor logic and independent recomputation, establish how the 241 cross-label exact-HTML records will be handled, freeze the group/template policy, and document the source and timestamp limitations. Institutional artifact-handling requirements also remain applicable. No model training, attack simulation, or final split was performed in this step.

## References

- [CompPhish v4, Mendeley Data](https://data.mendeley.com/datasets/fmbs4kp9wz/4), DOI `10.17632/fmbs4kp9wz.4`.
- [Goenka et al., “CompPhish: A comprehensive dataset for diversified phishing detection,” Data in Brief](https://doi.org/10.1016/j.dib.2026.113219), DOI `10.1016/j.dib.2026.113219`.
