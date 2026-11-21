# Step 1: Dataset release and literature audit

**Status:** Desk audit complete; direct file inspection and institutional approval remain gates before data processing or experiment setup.
**Date checked:** 2026-11-21
**Research concept:** `Updated_CompPhish_FYP_Research_Concept_Note_2026-11-21-2.pdf`

## 1. Proposed question and scope

The study's narrow question is whether a truthful, model-selected cue gives a simulated attacker additional bounded feature-space evasion advantage over a truthful fact selected independently of model relevance from the same preassigned feature family. The key contrast is model-cue versus matched-fact; comparing only with verdict-only access would mix the value of model relevance with the value of receiving any additional fact. Verdict-only and matched-fact arms remain important controls.

The proposed outcome is a binary detector flip after a bounded change to an input feature vector. It is not evidence that an attacker can transform a real page into a valid, visible, functioning, deployable phishing site. Any secondary HTML check should only establish whether a deterministic inert edit changes a registered extracted feature.

## 2. CompPhish v4 release record

The [Mendeley Data v4 record](https://data.mendeley.com/datasets/fmbs4kp9wz/4) identifies version 4, DOI `10.17632/fmbs4kp9wz.4`, published 24 August 2026. It reports 15,358 labeled URL/HTML pairs (7,204 phishing and 8,154 legitimate), 70 extracted features, phishing-source feeds PhishTank/OpenPhish, and legitimate URLs from DataForSEO Top-1000. It gives the collection period as September 2024 through August 2025. The record lists `All_Features_threshold90.xlsx`, `All_HTML.zip`, `Data_Dictionary.xlsx`, `dataset Creator.zip`, `feature extractor.zip`, `Mapping_File.xlsx`, `Readme.docx`, and `requirements.txt`; it says the README and data dictionary document reproduction and feature computation. The record states a [CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/).

These are release-record claims, not yet verification of archive contents. Directly download and inspect v4 before using it: validate archive integrity and file inventory, table row counts and schema, duplicate and missing IDs, label values, mapping uniqueness, URL-to-HTML file correspondence, requirements pins, README reproduction instructions, feature dictionary definitions, and any auxiliary feature files. Do not treat the 70-column table as ground truth until selected features are independently recomputed from pinned archived inputs. Do not execute archived HTML or allow live network access during inspection.

The [CompPhish Data in Brief article](https://pmc.ncbi.nlm.nih.gov/articles/PMC13583946/) describes potential source-specific bias and that archived HTML was released unsanitized as plain text, advising use in a controlled environment. This supports keeping the work offline and auditing source shortcuts. The article and the v4 record do not establish an official benchmark split. The concept note's connected domain/template group split and untouched final evaluation remain necessary design choices.

**Release finding:** Suitable for a candidate offline research dataset based on its published description and license, subject to direct file verification and institutional review. Do not redistribute modified raw artifacts unless permissions are separately confirmed.

## 3. Closest-work comparison and novelty boundary

| Work | Established overlap | Implication for this project |
|---|---|---|
| Gressel et al., [FIGA](https://arxiv.org/abs/2106.14815) (2021) | Feature-importance-guided, gradient-free tabular evasion includes phishing datasets and separates feature-space from phishing problem-space outcomes. | Feature-importance-guided attacks, phishing evasion, and feature-space/problem-space comparisons are not new contributions. Keep claims about the specific disclosure contrast. |
| Apruzzese et al., [SpacePhish](https://doi.org/10.1145/3564625.3567980) (ACSAC 2022) | Formalizes evasion spaces, threat-model knowledge/capability, and compares feature-space and website-space phishing attacks. | Explicitly bound the attacker and endpoint; do not equate feature-vector success with website evasion. |
| Yuan et al., [Multi-SpacePhish](https://doi.org/10.1145/3638253) (DTRAP 2024) | Broad, statistically validated evaluation of phishing detector evasion across multiple spaces, datasets/models, and attack families, with raw-page perturbations. | Statistical design and feasibility distinctions are established. The proposed study must explain its narrower estimand and not present generic evasion evaluation as novel. |
| Apruzzese & Subrahmanian, [LNU-Phish / gray-box attacks](https://lnu-phish.github.io/) (TDSC 2023) | Varies attacker feature knowledge across multiple datasets, classifiers, and gray-box attacks; releases dataset and code resources. | Attacker-knowledge variation alone is not novel. Define K0/K1/K2 precisely and only claim an interaction specific to disclosure of the selected truthful cue. |
| Quan et al., [post-hoc explanation risks](https://arxiv.org/abs/2206.14004) (2022 preprint) | Explanation-guided black-box attacks in other ML settings show explanation information can improve attack efficiency. | The general claim that explanations may aid attacks is already known; the possible contribution is phishing-specific measurement of incremental cue identity beyond a matched truthful fact. |
| Nguyen et al., [XRand](https://doi.org/10.1609/aaai.v37i10.26401) (AAAI 2023) | Studies randomized attribution disclosure and a local differential privacy defense against explanation-guided attacks. | Randomization or privacy defenses alone are not a novelty claim; the optional policy in the concept must remain an empirical selector, not a privacy guarantee. |

This comparison is based on the cited full texts/records available during this desk audit. It is not an exhaustive systematic literature review. In particular, the exact model-cue versus same-family independently selected truthful-fact contrast still requires a wider citation and keyword search before any strong priority claim. The gap therefore remains **provisional**: a paired phishing-specific estimate of cue identity's incremental effect under matched access, attack algorithm, query budget, and feature-change budget. The work is an experimental comparison, not a new universal attack, privacy theorem, or safe-disclosure guarantee.

## 4. Ethics, handling, and implementation gates

- The dataset record states CC BY 4.0; attribute the release and its companion article. Confirm institutional research, cybersecurity, and artifact-handling requirements before processing.
- Keep raw HTML inert, offline, and non-executable. Never visit archived URLs or retrieve current pages for this experiment.
- Avoid publishing raw phishing artifacts or a deployment-ready attack recipe. Publish protocol, code, feature grammar, seeds, query logs that do not expose sensitive artifacts, and aggregate results as permitted.
- Do not claim temporal generalization unless usable per-record timestamps are verified. Do not infer timestamps from source feed names.
- Preserve an untouched final group split. Direct dataset inspection and development decisions must not leak into final evaluation.

## 5. Step 1 decision

**Conditional go** to Step 2 (dataset acquisition and audit), contingent on institutional requirements being acceptable. No final go for training or attacks yet. Required next evidence: v4 archive checks and row-level mapping/schema audit, direct data dictionary/README review, exact groupability assessment, and confirmation of the project's permitted storage/handling conditions. The closest-work review supports continuing only with the narrow, matched-cue contrast and expressly bounded claims described above.

## Sources

- [CompPhish v4, Mendeley Data](https://data.mendeley.com/datasets/fmbs4kp9wz/4), DOI `10.17632/fmbs4kp9wz.4`.
- [Goenka et al., CompPhish, Data in Brief](https://doi.org/10.1016/j.dib.2026.113219), DOI `10.1016/j.dib.2026.113219`.
- [Gressel et al., FIGA](https://arxiv.org/abs/2106.14815), arXiv:2106.14815.
- [Apruzzese et al., SpacePhish](https://doi.org/10.1145/3564625.3567980), DOI `10.1145/3564625.3567980`.
- [Yuan et al., Multi-SpacePhish](https://doi.org/10.1145/3638253), DOI `10.1145/3638253`.
- [LNU-Phish project and paper resources](https://lnu-phish.github.io/), DOI `10.1109/TDSC.2022.3210029`.
- [Quan et al., post-hoc explanation risks](https://arxiv.org/abs/2206.14004), arXiv:2206.14004.
- [Nguyen et al., XRand](https://doi.org/10.1609/aaai.v37i10.26401), DOI `10.1609/aaai.v37i10.26401`.
- [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).
