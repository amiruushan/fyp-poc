# Proposed fresh evaluation: model-selected versus random factual cues

**Status:** Design and data-pool feasibility review only. No new split, model, cue, or attack result has been generated. Protocol proposal: `configs/random_cue_evaluation_protocol_v1.json`.

## Why this is a useful next experiment

The original primary comparator is the first factual feature in a preassigned family. That rule is reproducible and model-independent, but it may be a weak selector. A stronger control asks whether the model-selected cue beats a cue drawn at random from the same factual candidate set. Keep first-available as a secondary arm so the next study directly diagnoses how much of the original contrast depends on that comparator.

This narrows the claim to a randomized cue-selection comparison. It does not make the project novel merely by adding a random arm: prior importance-guided feature attacks and phishing evasion-space work remain close. Any novelty statement should be limited to the specific paired, same-family factual-disclosure contrast and checked against a current literature search.

## Which records can support a new held-out evaluation?

The original group manifest has 10,318 connected components. The groups assigned to the original train split contain 9,214 primary rows in 4,955 groups. Development, method-validation, and original-final groups total 5,363 groups; attack outcomes were examined in those partitions. Exclude all of them from the proposed new confirmatory test.

The 4,955 original-train groups are the only pool with no previous attack-pilot, method-validation, or final attack outcomes. Some were used to fit the old models, so those old models cannot score a new test drawn from this pool. The proposed design therefore freezes a new test subset of original-train groups first, then refits new models using only the remaining original-train groups. All old development, method-validation, and final groups are excluded from this new confirmatory experiment.

This creates a new held-out group evaluation on CompPhish v4, not a fully independent replication. The dataset, feature definitions, grouping method, earlier development decisions, and researcher's knowledge of the release remain shared. It improves independence from previously observed attack outcomes and prevents model-training leakage into the new test cohort, but does not provide cross-dataset generalization.

## Proposed comparison

For each detector and eligible test start, define three factual cue rules within the same hash-preassigned family:

1. **First available:** first factual feature in registry order, independent of model relevance (the original S rule).
2. **Seeded random:** uniform draw from factual, distinct, same-family cue candidates, selected before any arm's search. The recommended candidate set is the features that satisfy the frozen factual and non-baseline eligibility rules. A draw can coincide with M; keep the row paired and report collision rate.
3. **Model-selected:** eligible same-family feature with the greatest positive local score reduction under the frozen median/mode replacement diagnostic (the original M-family rule).

Use identical input vectors, candidate values, coordinate limits, cue-first order, binary feedback, and query budgets across arms. The primary estimand should be **M minus seeded random at one changed coordinate and five total queries**, separately for each detector. M minus first-available is secondary on the same rows. Report the 10-, 20-, and 40-query cells as sensitivity outcomes, without choosing a favorable budget after seeing test results.

For the two primary detector-specific M-minus-random contrasts, use paired row differences and connected-group bootstrap intervals with 97.5% coverage (Bonferroni familywise 5%). Secondary contrasts and budgets should be labeled exploratory or have a separately declared multiplicity plan. Report each detector's initial detections, eligibility denominator, matched rows and groups, factuality/abstention, random/model cue collisions, and V/first/random/model rates on the same population.

## Preliminary size assessment

The starting pool contains 4,955 groups, enough to consider a group split. Its largest component has 337 rows, and 26 components contain both labels (1,174 rows), so split balance must account for whole-group sizes and mixed labels. A reproducible but deliberately simple shuffled illustration (seed 8675309, 20% of group IDs assigned to test, then 25% of remaining IDs to development) gives:

| Provisional partition | Groups | Rows | Phishing | Legitimate | Mixed-label groups |
|---|---:|---:|---:|---:|---:|
| New train | 2,973 | 5,453 | 2,557 | 2,896 | 14 |
| New development | 991 | 1,758 | 761 | 997 | 4 |
| New test | 991 | 2,003 | 1,003 | 1,000 | 8 |

This demonstrates that row counts and class balance are plausible, even with atomic components. It is **not** the proposed frozen allocation; it has not been optimized or selected for cue eligibility, and no detector or attack result was computed from it. The final split allocator should balance group size and labels using only pool-level group metadata, record actual counts and hashes, and be frozen before model fitting. Detector recall, random/model cue eligibility, and paired-group support must then be projected using development only.

The prior Step 9 precision projection does **not** establish precision for M-minus-random. It used the old development M-minus-first contrast and a different cohort. Before opening the new test set, implement the three selectors on the remaining pool's development groups, run the random draw with a predeclared seed, and project M-minus-random coverage and adjusted interval width by resampling connected groups. The old pilot can inform rough scale only; it cannot stand in for this new comparator.

Proposed gate: at least 200 eligible connected groups per detector and projected adjusted interval half-width no greater than eight percentage points for each primary contrast. If this fails, do not inspect test outcomes. Revisit the split fraction or narrow the claim using development-only evidence. A larger test share lowers training size, so any move needs model and class-balance feasibility checks before the split is frozen.

## Freeze sequence

1. Verify the actual supervisor declaration covers this added evaluation and its local dataset processing. Preserve its status locally; do not commit the declaration.
2. Write a deterministic, group-only allocator over the original-train pool. Freeze a new seed, membership CSV, split statistics, and hashes. Confirm test group IDs do not overlap any earlier partition and old final results remain untouched.
3. Refit the same registered model families using only the new train groups. Select hyperparameters and 2% empirical development FPR thresholds using only the new development groups. Record recall and FPR uncertainty; the target is not a population guarantee.
4. Implement and validate first/random/model cue rules on development only. Freeze random sampling, tie-breaking, collision handling, cue eligibility, and candidate grammar.
5. Compute development-only M-minus-random projected coverage and interval widths. Freeze confirmatory contrasts, budgets, multiplicity, seeds, and stop/go gate.
6. Hash all data membership and experiment artifacts. Only then evaluate the new test groups once.
7. Report the original Step 11 study separately as the original evaluation. Do not combine its final rows with the new cohort or retune either study from the other's result.

## Remaining design decision

The main implementation choice is the random-cue candidate pool. Recommended: draw uniformly among factual, distinct same-family candidates that satisfy the same frozen eligibility rules as a potential M cue; do not condition the draw on attack success. Permit a draw to equal M and report its frequency. This answers whether the score-selected policy beats a random choice from plausible alternatives, with collisions making the comparison conservative. First-available remains a separate comparator and may coincide with either selector; report those overlaps too.

This document is a feasibility proposal, not an authorization to open any new test outcomes. The next implementation step is to generate the proposed group-only allocation and train/development/test counts from the 4,955 eligible groups, then assess development-only feasibility before the split is frozen.
