# CompPhish frozen results demo

A standalone, local HTML dashboard for presenting the **frozen Step 11 aggregate results**. It lives entirely in `demo/` on a separate research branch. No raw URLs, HTML pages, feature rows, model files, or individual attack outcomes are bundled into the browser.

## Open the demo

Open `demo/index.html` directly in a browser, or serve **only the demo folder**:

```sh
cd demo
python3 -m http.server 8000
```

Then open `http://localhost:8000/`. Never serve the repository root: it contains local raw data, model files, and row-level logs. The page has no network dependencies and does not execute the PoC, contact a website, or change the final results.

## Verify/rebuild the displayed results

From the repository root, with the local ignored final row log and pinned modeling packages:

```sh
"$HOME/.venvs/fyp-poc-step3/bin/python" -m pip install -r requirements-step6-models.txt
"$HOME/.venvs/fyp-poc-step3/bin/python" demo/reproduce.py
```

The verifier checks the final manifest against the freeze hash and the row log SHA-256. It independently recalculates the selected-point paired V/S/M rates, M−S differences, and 10,000 connected-group bootstrap replicates with the frozen seeds, rejecting any discrepancy. It then regenerates `demo/data.js` with aggregate values only. A successful run here checked both model contrasts exactly against the frozen manifest. The budget curves and detector metrics are shown from that manifest, which was created by the one-time final evaluation; they are not recalculated from the selected-point row log.

On a machine without the ignored row log, the committed `data.js` still displays the aggregate results. `python3 demo/reproduce.py --render-only` rebuilds the page data from the committed final manifest, but **does not verify the paired bootstrap**. The page's “Recalculate displayed differences” control checks arithmetic in the browser; it is not a substitute for the Python row-log verification.

The final evaluation script intentionally refuses to overwrite its existing result manifest. Do not remove or rerun the final result to alter a finding. For a full independent reproduction, use a separate research checkout and the pinned raw dataset, regenerate the frozen pipeline there, and compare hashes and aggregate results; keep all dataset-derived files and query logs local.

## Interpretation

The experiment measures binary prediction flips under an abstract feature-vector grammar, on same-family eligible starts. It does not prove a valid phishing webpage can be changed. The final 2% development-selected benign FPR target was slightly exceeded on the held-out split. Source confounding, eligibility coverage, and missing normalized perturbation magnitude are recorded in the [Step 11 report](../docs/step-11-frozen-final-results.md).
