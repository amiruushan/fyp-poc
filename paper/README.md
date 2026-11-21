# IEEE Access manuscript draft

`manuscript.tex` is an editable draft prepared with the official IEEE Access LaTeX class downloaded from [IEEE Access, Preparing Your Article](https://ieeeaccess.ieee.org/authors/preparing-your-article/) on 22 November 2026. `template/` holds only support files needed to compile it; the sample article and sample author portraits are omitted. `figures/frozen_matched_results.pdf` is generated directly from the frozen final aggregate JSON by `figures/make_results_figure.py`.

## Build

From `paper/`, with pdfLaTeX installed (for example, BasicTeX on macOS):

```sh
./build.sh
```

The generated `manuscript.pdf` should be inspected page by page before circulation. IEEE Access requires matching LaTeX/Word source and PDF in its two-column template for submission. This repository artifact is a research draft, not an IEEE submission.

## Frozen evidence and author checks

The numeric statements come from `../data/manifests/compphish_v4_final_results.json`, `../data/manifests/compphish_v4_split_stats.json`, `../data/manifests/compphish_v4_method_validation.json`, and the versioned protocol/Step 7 notes. The final split was opened once. Re-running or retuning it is not part of drafting.

Before any external submission, the author must confirm the full legal author list, institutional affiliation wording, email addresses, biographies, acknowledgement/funding details, exact ethics declaration reference and scope, bibliographic metadata, and whether the manuscript meets IEEE Access's current policy. The student reported Class 1 supervisor acceptance; no approval document was independently inspected in this work. The draft describes an abstract feature-vector experiment, not a valid page-space attack.
