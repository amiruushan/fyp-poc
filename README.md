# Truthful Model-Selected Phishing Cues and Bounded Feature-Space Evasion: A Paired Disclosure Study

This repository is the proof of concept (PoC) for a Final Year Project on **what a phishing detector reveals when it gives a factual reason for its verdict**. It tests whether a truthful cue selected for local model relevance helps a bounded search more than a truthful fact selected independently of model relevance from the **same preassigned feature family**. The comparison is about the *choice of fact*, not merely whether any extra fact is disclosed.

**Scope of the result:** this is an offline experiment on abstract URL/HTML **feature vectors**. A “bypass” means that a frozen classifier's binary prediction flipped within the query and feature-change budget. The altered vector was not shown to correspond to a valid URL or functioning webpage. The PoC does not demonstrate deployable phishing-page evasion, a live attack, or a benefit to people reading explanations.

Start with the [concept note](docs/Updated_CompPhish_FYP_Research_Concept_Note_2026-11-21-2.pdf) for the original idea, [Step 11 report](docs/step-11-frozen-final-results.md) for the completed finding, and [protocol v3](configs/experiment_protocol_v3.json) for the frozen confirmatory scope. The concept note proposes more than the completed experiment tests; the versioned protocol and final aggregate manifest describe what was actually run.

## Research design at a glance

| Item | Implemented design |
|---|---|
| Data | [CompPhish v4](https://data.mendeley.com/datasets/fmbs4kp9wz/4), DOI `10.17632/fmbs4kp9wz.4`; archived URL/HTML pairs handled locally and offline |
| Primary rows | 15,355 of 15,358 original rows after excluding three exact URL + HTML + label duplicates |
| Inputs | The same 12 source-recomputed URL/HTML features for both detectors; identifiers, raw URL text, labels, hashes, and split metadata are not model features |
| Split | Connected domain/template groups allocated atomically to train, development, method validation, and final |
| Detectors | Standardized L2 logistic regression and shallow gradient boosting, trained on train only |
| Disclosures | **V:** binary verdict; **S:** one truthful fact chosen without model relevance; **M-family:** a distinct truthful, locally model-selected cue in S's preassigned family |
| Primary comparison | Paired M-family minus S bypass rate among initially detected phishing starts eligible for both distinct, factual cues |
| Frozen budget | One changed coordinate; five total binary queries, including the initial verdict |
| Uncertainty | 10,000 connected-group bootstrap resamples; 97.5% intervals for two detector contrasts (Bonferroni familywise 5%) |

The feature family is assigned by a seeded hash before the attack outcomes are known. S uses the first factual feature in that family. M-family uses a distinct eligible feature with the largest positive local reduction in the frozen model's phishing score when replaced by its train-only median or mode. That score is used by the evaluator to choose the cue; the simulated attacker receives only the factual cue and binary verdicts. Numeric search candidates use train-derived 5th/95th percentiles and binary candidates toggle. All arms share the same candidates and search budget; the cue changes coordinate priority. The single-feature HTML-content family cannot produce a distinct same-family pair.

The source-derived features are listed with definitions and families in the [feature registry](data/manifests/compphish_v4_feature_registry.json). Three published HTML feature columns disagreed with the archived HTML on sampled rows, so the PoC recomputes those values from source. An independent check of the final partition found **0 mismatches in 27,636 feature comparisons** against the frozen source-derived matrix.

### Data partitions

| Partition | Primary rows | Phishing | Legitimate | Connected groups | Role |
|---|---:|---:|---:|---:|---|
| Train | 9,214 | 4,321 | 4,893 | 4,955 | Fit transformations and detectors |
| Development | 2,303 | 1,080 | 1,223 | 1,952 | Select model settings, thresholds, and one attack budget |
| Method validation | 1,535 | 720 | 815 | 1,459 | Check frozen implementation without retuning |
| Final | 2,303 | 1,080 | 1,223 | 1,952 | One-time held-out evaluation after the freeze |

The split counts and duplicate policy come from [the split manifest](data/manifests/compphish_v4_split_stats.json). The dataset's phishing and legitimate examples come from different acquisition sources, which are confounded with class. Verified row-level timestamps are unavailable; these splits do not establish temporal or cross-source generalization.

## Frozen final results

The originally planned 1% empirical development false-positive-rate (FPR) target gave logistic regression only **38.43%** phishing recall, below the planned 50% feasibility floor. A [documented development-stage amendment](docs/step-7-feasibility-and-amendment.md) changed the target to **2%** before method validation or final evaluation. It was an empirical development target, not a population FPR guarantee. The final FPRs slightly exceeded it.

| Detector | Final benign FPR | Final phishing recall | ROC-AUC | Average precision |
|---|---:|---:|---:|---:|
| Logistic regression | 2.13% (26/1,223) | 54.54% (589/1,080) | 0.9212 | 0.9226 |
| Gradient boosting | 2.21% (27/1,223) | 70.28% (759/1,080) | 0.9608 | 0.9586 |

The **primary paired comparison** uses the same eligible starts for V, S, and M-family *within each detector row*:

| Detector | Matched starts (groups) | V bypass | S bypass | M-family bypass | Paired M−S | Adjusted 97.5% group-bootstrap interval |
|---|---:|---:|---:|---:|---:|---:|
| Logistic regression | 344 (268) | 43.60% | 23.84% | 77.03% | **+53.20 points** | +45.79 to +60.56 points |
| Gradient boosting | 299 (237) | 66.89% | 60.20% | 73.91% | **+13.71 points** | +8.87 to +18.75 points |

Both intervals exclude zero for this frozen abstract search. Coverage is limited: the matched comparison includes **344/589 (58.4%)** initially detected logistic starts and **299/759 (39.4%)** initially detected boosted starts. The [final aggregate JSON](data/manifests/compphish_v4_final_results.json) also reports all-start V/S/M-global-with-V-fallback rates, query costs, discordances, and the full budget grid; those all-start rates use different denominators and a different M cue, so they are not interchangeable with the primary table. At **one coordinate and 40 queries**, V, S, and M-family converge to 98.84% bypass for logistic regression and 89.97% for boosting. The cue-priority advantage measured here is tied to the tight five-query setting.

### Interpretation limits

- URL/HTML dependencies are not fully enforced by the candidate grammar; no candidate was validated as a working page or URL.
- One dataset, class-confounded acquisition sources, unavailable row timestamps, two detector families, and provisional domain/template grouping limit generalization.
- The K0/K2 knowledge interaction and proposed conditional minimax selector were **not tested**. K0 is the confirmatory knowledge condition.
- The frozen log records changed-coordinate count and query cost, but **not normalized perturbation magnitude**. No magnitude distribution can be reported.
- The student reported supervisor acceptance of a Class 1 declaration for this PoC and local processing. The declaration itself was not independently inspected here; this repository is not an institutional approval record.

## View the results now (no dataset required)

The committed [HTML demo](demo/README.md) displays frozen **aggregate** results only. Open `demo/index.html` in a browser. If your browser requires a local server, serve **only `demo/`**, never the repository root, because this checkout may contain ignored raw data and row-level logs:

```sh
cd demo
python3 -m http.server 8000
```

Then visit `http://localhost:8000/`. Stop the server with `Ctrl+C`. The dashboard's browser-side recalculation checks displayed arithmetic; it does not rerun models or independently verify the bootstrap. The [IEEE Access manuscript draft](paper/README.md) provides a paper-format view of the findings; it remains a draft with author and approval details to confirm.

To see the committed primary values in the terminal from the repository root, using only Python's standard library:

```sh
python3 - <<'PY'
import json
from pathlib import Path

result = json.loads(Path('data/manifests/compphish_v4_final_results.json').read_text())
for name, model in result['models'].items():
    rates = model['matched_rates']
    low, high = model['paired_group_bootstrap_97_5']
    print(name)
    print('  matched rows/groups:', model['matched_rows'], model['matched_groups'])
    print('  V / S / M-family bypass:', *(f'{rates[arm]:.2%}' for arm in ('V', 'S', 'M_family')))
    print('  paired M-S:', f"{100 * model['paired_M_family_minus_S']:+.2f} percentage points")
    print('  adjusted interval:', f'{100 * low:.2f} to {100 * high:.2f} points')
PY
```

## Verify the saved result locally

The raw dataset and row-level selected-point log are intentionally **not in Git**. If this is the original research machine and those ignored files are still present, create or activate a Python 3.14 environment with the pinned parser and modeling packages:

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements-step3-validation.txt -r requirements-step6-models.txt
.venv/bin/python demo/reproduce.py
```

`demo/reproduce.py` verifies the final manifest against the freeze and the local selected-point log's SHA-256, then independently recomputes the matched rates, paired differences, and 10,000 group-bootstrap draws before regenerating `demo/data.js`. It fails if the ignored log is absent or differs. On a clone without that log, the committed dashboard remains viewable; `.venv/bin/python demo/reproduce.py --render-only` can rebuild its aggregate data from the committed final manifest, **without** independently verifying the paired bootstrap. See [the demo guide](demo/README.md) for the precise distinction.

For an offline implementation check that opens no dataset files, run:

```sh
.venv/bin/python scripts/run_step10_method_validation.py --self-check
```

If the local source-derived matrix and model files are present, check the ten frozen artifact hashes:

```sh
.venv/bin/python scripts/verify_compphish_final_freeze.py
```

Its “final evaluation has not run” message describes the historical freeze manifest, which was intentionally written *before* the later final run; the completed final evaluation is recorded separately in `compphish_v4_final_results.json`.

## Rebuild the PoC in a separate checkout

Use a **separate clone or worktree** to regenerate the pipeline, so the committed final result and local research record remain intact. Obtain CompPhish **version 4** from the [publisher](https://data.mendeley.com/datasets/fmbs4kp9wz/4) and place the seven used files listed in [the release manifest](data/manifests/compphish_v4_release.json) under `data/raw/compphish_v4/`. The creator scraper bundle was inventoried but not used. Keep archived HTML inert and offline; do not open archived URLs in a browser or visit them. Use the pinned dependencies above (and `requirements-step2-audit.txt`) with the Python version recorded in [the baseline manifest](data/manifests/compphish_v4_baselines.json) if exact hash comparison is needed.

Run the stages in order from that checkout's root. Each stage's report explains its inputs, outputs, and assumptions:

| Stage | Entry point | Report / main output |
|---|---|---|
| 2. Release integrity and grouping | `scripts/audit_compphish_v4.py` | [Step 2](docs/step-2-dataset-audit.md), `compphish_v4_audit.json`, groups CSV |
| 3. Splits and feature audit | `scripts/create_compphish_splits.py`, `scripts/validate_feature_registry.py` | [Step 3](docs/step-3-feature-registry-and-splits.md), split/recompute manifests |
| 4. Source-derived matrix | `scripts/build_compphish_feature_matrix.py` | [Step 4](docs/step-4-full-feature-matrix.md), ignored matrix and tracked hash manifest |
| 5. Protocol | Versioned `configs/experiment_protocol_v1.json` to `v3.json` | [Step 5](docs/step-5-experiment-protocol.md), [Step 9 amendment](docs/step-9-scope-and-precision-decision.md) |
| 6–7. Detectors and feasibility | `scripts/train_baseline_detectors.py`, `scripts/audit_detector_feasibility.py` | [Step 6](docs/step-6-baseline-detectors.md), [Step 7](docs/step-7-feasibility-and-amendment.md) |
| 8–9. Development pilot and precision | `scripts/run_step8_development_pilot.py`, `scripts/project_step9_precision.py` | [Step 8](docs/step-8-development-cue-attack-pilot.md), [Step 9](docs/step-9-scope-and-precision-decision.md) |
| 10. Method check and final freeze | `scripts/run_step10_method_validation.py`, `scripts/verify_compphish_final_freeze.py` | [Step 10](docs/step-10-method-validation-and-final-freeze.md), freeze manifest |
| 11. One-time held-out run | `scripts/run_step11_final_evaluation.py` | [Step 11](docs/step-11-frozen-final-results.md), final aggregate JSON and ignored row log |

With the seven publisher files in place, install all stage requirements and run Stages 2–9 in that **separate checkout**:

```sh
.venv/bin/python -m pip install -r requirements-step2-audit.txt -r requirements-step3-validation.txt -r requirements-step6-models.txt
.venv/bin/python scripts/audit_compphish_v4.py --data-dir data/raw/compphish_v4 --release-manifest data/manifests/compphish_v4_release.json --output-json data/manifests/compphish_v4_audit.json --group-csv data/manifests/compphish_v4_groups.csv
.venv/bin/python scripts/create_compphish_splits.py --data-dir data/raw/compphish_v4 --group-csv data/manifests/compphish_v4_groups.csv --output-csv data/manifests/compphish_v4_splits.csv --output-json data/manifests/compphish_v4_split_stats.json
.venv/bin/python scripts/validate_feature_registry.py --data-dir data/raw/compphish_v4 --split-csv data/manifests/compphish_v4_splits.csv --registry-json data/manifests/compphish_v4_feature_registry.json --output-json data/manifests/compphish_v4_feature_recompute.json
.venv/bin/python scripts/build_compphish_feature_matrix.py --data-dir data/raw/compphish_v4 --split-csv data/manifests/compphish_v4_splits.csv --registry-json data/manifests/compphish_v4_feature_registry.json
.venv/bin/python scripts/train_baseline_detectors.py
.venv/bin/python scripts/audit_detector_feasibility.py
.venv/bin/python scripts/run_step8_development_pilot.py
.venv/bin/python scripts/project_step9_precision.py
```

These commands recalculate tracked manifests in the separate checkout. Compare them with the committed records and investigate differences before proceeding; exact hashes require the pinned data and runtime. The real method-validation runner requires a **local, ignored ethics-status record** accepted for this PoC and local processing, supplied with `--ethics-record`; do not fabricate one or commit an approval document. With that record and matching frozen artifacts, run `.venv/bin/python scripts/run_step10_method_validation.py --ethics-record PATH_TO_LOCAL_RECORD`, then `.venv/bin/python scripts/verify_compphish_final_freeze.py`.

Verify the freeze before any independent final run. The Step 11 script intentionally refuses to overwrite an existing final result manifest. In a separate checkout, preserve a copy of the committed manifest, make the output path free **there only**, run `.venv/bin/python scripts/run_step11_final_evaluation.py` once, and compare the new aggregate and hashes to the preserved record. Do not rerun the final split to select a more favorable result.

## Repository map

- `docs/`: concept note, literature/release audit, and chronological decisions through final evaluation.
- `configs/`: versioned experiment and attack protocols.
- `scripts/`: offline audits, extraction, training, pilot, validation, and final evaluator.
- `data/manifests/`: tracked release inventory, registry, split/group metadata, hashes, and aggregate results. Some CSVs contain dataset-derived serials and labels; handle them as research records.
- `data/raw/` and `data/processed/`: local, Git-ignored dataset files, matrix, model files, ethics-status record, and row-level logs.
- `demo/`: standalone aggregate-only HTML dashboard and verification script.
- `paper/`: IEEE Access LaTeX draft, compiled PDF, figure source, and build instructions.

The primary frozen numerical source is [`data/manifests/compphish_v4_final_results.json`](data/manifests/compphish_v4_final_results.json). If a historical step note and that manifest differ, investigate the version and population before citing either number.
