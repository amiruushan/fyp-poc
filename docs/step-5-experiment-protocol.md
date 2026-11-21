# Step 5: Pretraining experimental protocol v1

Status: pretraining design fixed for review; final evaluation is NOT authorized by this document. No detector has been trained and no attack results are reported. Pilot-dependent numerical choices remain pending. This is a repository protocol, not an external preregistration.

## Research question and scope

Follow the concept note dated 21 November 2026, especially sections 7–11: estimate the incremental bounded feature-space bypass advantage of a truthful model-selected cue over a truthful fact selected independently of relevance from the same preassigned feature family. Positive, null, reversed, and inconclusive outcomes must all be reported. Feature-space flips cannot establish operational website evasion or user benefit.

## Inputs and exclusions

Use the frozen 12-feature registry and the source-derived Step 4 matrix. Require its hash to match the tracked matrix manifest before training. Select only `included_primary == 1`; never provide identifiers, URL text, labels, split/group metadata, or HTML hashes as model inputs. Feature order follows the registry JSON. No resplitting or deduplication changes are permitted without a versioned amendment.

There are 9,214 train, 2,303 development, 1,535 method-validation, and 2,303 final primary records. Fit transformations and models on train only. Select hyperparameters and thresholds on development only. Method validation checks the frozen implementation and any explicitly registered secondary policy settings; it is not another model-tuning partition. Final features already exist locally, but no final distributions, labels-versus-predictions, cue coverage, or attacks may be inspected until the final gate passes.

The concept note proposed broad URL/HTML deduplication. Step 3 instead collapsed only identical URL/HTML/label triplets and retained distinct URLs sharing HTML, including conflicting labels. Record this as a methodological deviation. Report a sensitivity analysis excluding mixed-label exact-HTML groups, without replacing the primary population or choosing the more favorable result.

## Two detectors and development selection

Both models use all 12 features, the same training rows, CPU execution, seed 20261121, and no class weighting or oversampling in the primary analysis.

* Logistic regression: train-only standardization; L2 penalty; C in {0.01, 0.1, 1, 10}; solver lbfgs; max iterations 2000. A convergence warning blocks selection until resolved and logged.
* Shallow gradient boosting: depth in {1, 2, 3}; number of estimators in {100, 200}; learning rate 0.05; full-row sampling; minimum leaf size 20; no scaling and no early stopping. This is six configurations, not an unbounded search.

Select each family's configuration by greatest development average precision. Break ties within 1e-12 by smaller C for logistic regression, or shallower depth then fewer trees for boosting. Report every candidate result. Do not select configurations by attack success or cue effects. Pin Python and modeling-library versions in the training implementation before fitting; no package version is assumed by this protocol.

Choose the smallest development score threshold for which empirical benign FPR is at most 1%, using prediction positive iff score >= threshold. Evaluate unique score boundaries and the next representable value above them, including the all-negative operating point. Report achieved FPR, its interval, recall, precision, ROC-AUC, and average precision (explicitly label this PR summary). This is an empirical development target, not a population FPR guarantee. If recall at this point is below 50%, flag detector feasibility as failed: report the outcome and amend the protocol before further experiments rather than silently changing thresholds. Freeze the trained model and threshold; do not refit on development before the final experiment.

## Disclosure and paired populations

V returns only the binary verdict. S returns one source-grounded fact selected without model relevance. M returns one factual cue selected by a frozen relevance rule. A cue contains the feature's factual value and a fixed template, never scores, coefficients, thresholds, gradients, or editing instructions.

Use the existing registry families. Preassign a family by SHA-256 of `20261121:serial_number`, interpreted as a big-endian integer modulo the number of lexicographically sorted families. Choose S by first available factual feature in registry order within that family, without consulting labels, relevance, or attack outcomes. Choose M-family as the highest-relevance eligible feature distinct from S in that same family; break ties by registry order. Make eligibility decisions before generating any arm outcomes. A singleton family cannot support the distinct matched contrast: `html_content` currently contains only `has_missing_title`. Count these exclusions and do not redraw families to improve coverage.

Relevance candidate rule for the pilot: positive reduction in the model's phishing score when the feature is replaced by its train-only reference (median for numeric values, mode for binary flags; ties select 0). Require a reduction greater than 1e-12. The evaluator alone computes this; it is never attacker feedback. Dependency-invalid replacements are ineligible. This is a local replacement relevance measure, not a causal or SHAP attribution claim. Independently check factual statements against archived sources; parser recovery must follow Step 4 and be recorded. Failures cause cue abstention, not removal of the start from policy-level denominators.

The primary denominator is initially detected phishing starts with a factual S and a distinct eligible M-family. Supporting unrestricted M-minus-V includes all initially detected phishing starts; M abstention falls back to V. S-minus-V uses the declared factual-cue subset. Also report initial detector misses, one-cue and two-cue coverage, factuality failures, abstention, eligibility by family, and independent group counts. Do not mix these denominators.

## Knowledge, grammar, and development pilot

K0 receives anonymous coordinates, types, legal ranges, the initial vector, and binary verdicts. K1 additionally receives the URL feature definitions. K2 receives the complete registry definitions. None receives fitted parameters, training records, labels, scores, or final membership. The evaluator has those data only for orchestration and analysis.

Confirmatory cells are two detectors crossed with K0/K2; K1 is sensitivity only. If the implemented search does not use the semantic knowledge differently, the conditions are operationally equivalent: report that fact instead of claiming a knowledge interaction. A cue identifies its coordinate in every knowledge condition.

Before the attack pilot, implement and version a grammar specifying types, train-derived bounds, mutable coordinates, candidate values, dependent-feature rules, rejected-candidate behavior, and normalized change cost. URL features are jointly dependent; independent coordinate edits must not be called feasible URL edits. Unresolved dependencies must either exclude a move or be explicitly scoped as an abstract feature-space relaxation. All arms receive the same legal candidates, search procedure, seed, compute cap, and stopping rule; only cue-driven coordinate prioritization differs. Freeze exact search pseudocode and any alternative strategy before comparing arm outcomes.

Proposed budget grid: coordinate limits 1–5 and total binary-query budgets 5, 10, 20, 40. Count the initial verdict and every attempted target query, including repeated/rejected requests. Track invalid proposals separately as well. Stop at first flip or budget exhaustion. Share start/seed and candidate tie-breaking across arms. Timeouts and unavailable candidates count as no observed success within budget and are reported, not silently dropped.

Select one primary operating point from development by pooled success across disclosure arms, with differences blinded during selection: among points with pooled success between 10% and 90%, choose the one closest to 50%, breaking ties by fewer changed coordinates then fewer queries. If none qualifies, the headroom gate fails and an amendment is required. Do not pick different points after seeing final results. Report the whole grid as sensitivity results.

## Analysis plan and final gate

For each confirmatory cell, estimate paired mean bypass difference M-family minus S. Resample connected group IDs with replacement, retaining all paired rows within each selected group, for 10,000 bootstrap replicates with seed 20261123. Report row-weighted estimates, 95% percentile intervals, rates, row/group denominators, and discordant pairs. Report 98.75% intervals for the four primary contrasts as a Bonferroni familywise adjustment; label the ordinary 95% intervals descriptive. If a replicate has no eligible pairs, report its frequency; sparse support blocks confirmatory inference rather than silently discarding replicates.

Use all eligible final starts, not a sample chosen by observed attack outcomes. Before unlocking final evaluation, use development cluster/discordance estimates to project interval widths at the planned group counts. Record an equivalence margin and target precision justified for this FYP before final evaluation. These remain pending pilot quantities, not invented power claims. A nonsignificant effect alone is inconclusive; equivalence requires the adjusted interval wholly inside the frozen margin. H3 interaction inference is secondary and requires its own adequate-precision pilot justification.

Final gate requires: source/handling requirements resolved; pinned runtime and reproducible extraction; usable detector operating points; verified cue fidelity and grammar; non-saturated development headroom; adequate paired group support and projected precision; versioned model/threshold hashes, budgets, seeds, logs, and analysis settings. Record all values and commit a final-freeze manifest before opening final results. If the primary matched contrast lacks support, report a narrower M-minus-V/coverage study and explicitly mark H2 infeasible. Never manufacture or tune toward the expected direction.

The conditional minimax selector and inert HTML-edit check are deferred secondary extensions. Do not claim H5 or fit the selector under this v1 protocol. They require a separately versioned, development-informed feasibility decision and method-validation plan before final access. Their omission does not block the primary contrast.

## Execution record and next step

Step 5 creates this protocol and a machine-readable pretraining configuration only. It does not train models, select an attack budget, estimate effects, or freeze unresolved pilot values. Next implement the bounded two-model training/evaluation pipeline on train/development, publish candidate metrics and frozen detector artifacts, and preserve final-set isolation. Carry source confounding, missing timestamps, provisional grouping, and the single-document HTML parser recovery into the eventual IEEE Access limitations section.
