# DEV034-G3B-R1 — Matched Common-Support Volatility-Context Direction Screen v1

Status: `DESIGN_FROZEN_BEFORE_ANY_G3B_R1_PREDICTIVE_FIT`

Date: 2026-09-02

Permanent governance:
`docs/LAYERED_STRATEGY_SEARCH_GOVERNANCE.md`

Parent group design:
`docs/DEV034_G3_OPPORTUNITY_VOLATILITY_CONTEXT_DESIGN.md`

Frozen materialization parent:
`DEV034-G3A-R1`

## 1. Scientific question

The frozen successful direction-stage base lineage remains:

`DEV030-P3 / A / 120s / 16bp / 32s / PRICE / S1 / M1 LogisticRegression`

DEV034-G3B-R1 asks:

> On one exact deterministic common support, does any of the 16 frozen
> opportunity/volatility R-context blocks add stable incremental
> direction-given-touch information beyond a P3-lineage PRICE32/S1 comparator
> refit under the same common-support protocol?

Every G3 candidate is:

`P3 PRICE32 S1 base + one frozen G3A-R1 context block`

No candidate is evaluated standalone.

No failed/inconclusive G2 representation is used.

## 2. Why G3B-R1 is required

The original DEV034-G3 design required no support shrink.

Original DEV034-G3A failed closed before execution because causal 30-minute
R-context did not exist for every one of the 1374 P3 T1 rows.

The separately preregistered DEV034-G3A-R1 recovery then froze one deterministic
common support:

- original P3 T1 rows = 1374
- common R-eligible rows = 1341
- removed = 33
- common LONG = 665
- common SHORT = 676

Therefore original frozen P3 predictions, trained under the 1374-row support,
cannot be used as the direct comparator for G3 candidates trained under the
1341-row support.

G3B-R1 changes only the support-comparison protocol required for a fair matched
comparison:

- reconstruct the exact P3 PRICE32/S1 base;
- apply exactly the frozen G3A-R1 common-support mask;
- refit a P3-lineage comparator on that exact support;
- fit every G3 candidate on that exact same support;
- compare only matched validation rows.

The original P3 artifact remains the frozen upstream scientific success and is
not overwritten or redefined.

## 3. Frozen G3A-R1 identity

Canonical artifact:

`/home/emadh/Multi-Market/evidence/dev034_g3a_r1_common_support_context_v1/DEV034_G3A_R1_COMMON_SUPPORT_CONTEXT.json`

SHA256:

`43f4460d6990846218f3d0618a261d3852d3a198a50420ff05afbc97c832425e`

bytes:

`28890`

Deep read-only verification:

- checks PASS = 185
- checks FAIL = 0
- all seven daily CSVs reproduced exactly
- all 16 campaign candidate hashes reproduced
- exclusion ledger reproduced exactly
- no rerun occurred

Permanent rule:

`DEV034-G3A-R1 MUST NEVER BE RERUN`

## 4. Frozen common-support identity

Campaign:

- rows = 1341
- LONG = 665
- SHORT = 676

Hashes:

- support SHA256 =
  `caa61e84281061d00e4244e4f9b30ed2096e5acb95df9906aa7de0f28750ab75`
- label SHA256 =
  `fcb1b8f6c5f7994ca8c611cb3381146f401be7623ef36ae316a9a2e477a83385`
- full-R SHA256 =
  `b98239fdf22de77a476c7d4b13d4a677c06de101faedd42cbf8e11da0b145763`

Per-day support:

- 2026-01-01 = 4 = 3 LONG / 1 SHORT
- 2026-02-01 = 422 = 200 LONG / 222 SHORT
- 2026-03-01 = 356 = 160 LONG / 196 SHORT
- 2026-04-01 = 156 = 85 LONG / 71 SHORT
- 2026-05-01 = 64 = 40 LONG / 24 SHORT
- 2026-06-01 = 121 = 55 LONG / 66 SHORT
- 2026-07-01 = 218 = 122 LONG / 96 SHORT

Excluded:

- total = 33
- START_OF_DAY_30M_BOUNDARY = 30
- BOOK_INVALID_IN_30M_HISTORY = 3

The mask is immutable, candidate-independent, and label-independent.

No additional row may be deleted for any candidate.

## 5. Frozen P3 parent lineage

Canonical P3 artifact:

`/home/emadh/Multi-Market/evidence/dev030_p3_campaign1_v1/DEV030_P3_CAMPAIGN1_RESULT.json`

SHA256:

`f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`

Selected upstream identity:

- target = A
- horizon = 120 s
- barrier = 16 bp
- window = 32 s
- block = PRICE
- representation = S1
- base feature count = 23
- model family = regularized logistic regression

Before the first G3B-R1 estimator fit, implementation must verify:

1. exact P3 artifact SHA;
2. exact selected-survivor identity;
3. exact P3 base feature names and order;
4. original P3 T1 support reconstruction = 1374 / 684 LONG / 690 SHORT;
5. original-support hashes match the frozen G3A-R1 original-support record;
6. G3A-R1 artifact identity and common-support hashes;
7. common timestamps are an exact ordered subset of original P3 T1 timestamps;
8. labels are exactly identical on the matched common timestamps.

Any failure invalidates G3B-R1 before predictive fitting.

## 6. Frozen candidate universe

Exactly 16 candidates, inherited unchanged from the frozen G3 registry:

- G3C01 EXACT_EXP024_RV30 — 1 added feature
- G3C02 RV_TERM_STRUCTURE — 3
- G3C03 ABS_RETURN_TERM_STRUCTURE — 5
- G3C04 SIGNED_RETURN_TERM_STRUCTURE — 5
- G3C05 SPREAD_REGIME — 3
- G3C06 RANGE_TERM_STRUCTURE — 3
- G3C07 RANGE_POSITION_TERM_STRUCTURE — 3
- G3C08 SHORT_VOLATILITY_STATE — 5
- G3C09 MEDIUM_VOLATILITY_STATE — 4
- G3C10 LONG_VOLATILITY_STATE — 4
- G3C11 SIGNED_PLUS_ABSOLUTE_RETURN_STATE — 10
- G3C12 VOLATILITY_PLUS_RANGE_STATE — 6
- G3C13 OPPORTUNITY_REGIME_CORE — 4
- G3C14 MAGNITUDE_CONTEXT — 11
- G3C15 UNSIGNED_FULL_R_CONTEXT — 17
- G3C16 FULL_FROZEN_R_CONTEXT — 22

Candidate order is immutable:

`G3C01 ... G3C16`

No candidate may be added, removed, renamed, merged, or feature-selected after
predictive results are observed.

## 7. Exact candidate construction

For each day:

1. reconstruct the exact selected P3 CandidateDayDataset;
2. extract the original 23-column P3 PRICE32/S1 T1 matrix;
3. exact-join it to the frozen G3A-R1 daily timestamps;
4. require labels to match exactly;
5. load/reconstruct the frozen 22-column G3A-R1 full-R matrix;
6. select the candidate block using the frozen G3 registry;
7. concatenate:

`X_candidate = [X_P3_COMMON_23, X_G3_BLOCK]`

Feature order is immutable:

1. the exact 23 P3 PRICE32/S1 feature columns;
2. the candidate context block in exact frozen G3 registry order.

Total candidate widths therefore are:

- G3C01 = 24
- G3C02 = 26
- G3C03 = 28
- G3C04 = 28
- G3C05 = 26
- G3C06 = 26
- G3C07 = 26
- G3C08 = 28
- G3C09 = 27
- G3C10 = 27
- G3C11 = 33
- G3C12 = 29
- G3C13 = 27
- G3C14 = 34
- G3C15 = 40
- G3C16 = 45

No PCA, SVD, interactions, feature subset search, imputation, interpolation,
candidate-specific filtering, or support shrink is allowed.

## 8. Matched common-support comparator

The G3B-R1 baseline is a new analysis object:

`P3_COMMON_SUPPORT_REFIT`

It is not the original frozen P3 prediction vector.

It uses exactly:

- the frozen 23 P3 PRICE32/S1 features;
- the exact same 1341 common-support rows used by all candidates;
- the same chronological folds;
- the same train-only scaling;
- the same model family;
- the same inner C-selection rule.

This comparator exists only to make the incremental G3 test support-matched.

It does not replace the original DEV030-P3 scientific success.

## 9. Frozen chronological outer folds

Exactly the original P3 day partitions, after applying the common-support mask.

### Fold 1

Outer train:

- Jan-Mar
- rows = 782
- LONG = 363
- SHORT = 419

Outer validation:

- Apr
- rows = 156
- LONG = 85
- SHORT = 71

Inner fit:

- Jan-Feb
- rows = 426
- LONG = 203
- SHORT = 223

Inner validation:

- Mar
- rows = 356
- LONG = 160
- SHORT = 196

### Fold 2

Outer train:

- Jan-Apr
- rows = 938
- LONG = 448
- SHORT = 490

Outer validation:

- May
- rows = 64
- LONG = 40
- SHORT = 24

Inner fit:

- Jan-Mar
- rows = 782
- LONG = 363
- SHORT = 419

Inner validation:

- Apr
- rows = 156
- LONG = 85
- SHORT = 71

### Fold 3

Outer train:

- Jan-May
- rows = 1002
- LONG = 488
- SHORT = 514

Outer validation:

- Jun
- rows = 121
- LONG = 55
- SHORT = 66

Inner fit:

- Jan-Apr
- rows = 938
- LONG = 448
- SHORT = 490

Inner validation:

- May
- rows = 64
- LONG = 40
- SHORT = 24

### Fold 4

Outer train:

- Jan-Jun
- rows = 1123
- LONG = 543
- SHORT = 580

Outer validation:

- Jul
- rows = 218
- LONG = 122
- SHORT = 96

Inner fit:

- Jan-May
- rows = 1002
- LONG = 488
- SHORT = 514

Inner validation:

- Jun
- rows = 121
- LONG = 55
- SHORT = 66

Pooled outer-validation support:

- rows = 559
- LONG = 302
- SHORT = 257

These support counts are hard gates.

## 10. Model lineage

Both the common-support comparator and every candidate use exactly:

- StandardScaler fit on training data only;
- L2 LogisticRegression;
- solver = `lbfgs`;
- l1_ratio = 0.0;
- class_weight = None;
- max_iter = 1000;
- fit_intercept = True;
- random_state = 20260825;
- threshold = 0.5.

Fixed C grid:

`(0.01, 0.1, 1.0, 10.0)`

No alternate model family is permitted.

## 11. Inner C selection

C is selected independently for each representation:

- once for the common-support P3 comparator in each outer fold;
- once for each G3 candidate in each outer fold.

The protocol is identical for all representations.

For each outer fold:

- inner validation day = final outer-training day;
- inner fit days = all earlier outer-training days.

For each C:

1. fit StandardScaler on inner-fit only;
2. transform inner validation;
3. fit the frozen LogisticRegression;
4. predict p(LONG);
5. classify at 0.5;
6. compute balanced accuracy and macro F1.

Select lexicographically:

1. maximum balanced accuracy;
2. maximum macro F1;
3. minimum C.

Selected C values are results and are not required to equal the original
1374-support P3 C values.

No candidate-specific tuning beyond this fixed protocol is allowed.

## 12. Final outer fit

After representation-specific C selection:

1. fit StandardScaler on the full outer-training rows for that representation;
2. transform the matched outer-validation rows;
3. fit the frozen LogisticRegression;
4. emit p(LONG);
5. classify at threshold 0.5.

Comparator and candidate validation timestamps/labels must be bit-identical in
every fold before any delta is computed.

## 13. Primary benchmark

Primary endpoint for candidate c:

`delta_BA(c) = pooled_BA(c) - pooled_BA(P3_COMMON_SUPPORT_REFIT)`

Balanced accuracy is primary.

Also serialize:

- pooled macro F1
- MCC
- ROC AUC diagnostic
- predicted LONG count
- predicted SHORT count
- predicted minority fraction
- confusion matrix
- per-class metrics where supported
- all selected C values
- all inner-C ledgers
- deterministic prediction hashes

The original frozen P3 BA = 0.5419424831488764 is provenance/context only and
must not be substituted for the matched common-support comparator BA.

## 14. Stability diagnostics

For every candidate store:

- four candidate fold BAs;
- four comparator fold BAs;
- four fold delta_BA values;
- number of positive fold deltas;
- number of candidate folds with BA > 0.50;
- both-classes-predicted flag in every fold;
- pooled predicted-minority fraction;
- four leave-one-fold-out pooled delta_BA values;
- all-LOO-positive flag;
- worst candidate fold BA;
- median fold delta_BA;
- minimum fold delta_BA.

## 15. Joint 16-candidate temporal max-stat null

Exactly:

- seed = 20260902
- replicates = 1999
- candidates = exactly G3C01..G3C16 jointly controlled

For each outer-validation fold, legal circular shifts are:

- Fold 1, n=156: 10..146 inclusive
- Fold 2, n=64: 10..54 inclusive
- Fold 3, n=121: 10..111 inclusive
- Fold 4, n=218: 10..208 inclusive

Implementation must use:

`numpy.random.default_rng(20260902)`

For each replicate:

1. draw one legal shift independently for each fold in fold order 1..4;
2. use the same four shifts for the comparator and all 16 candidates;
3. keep all fitted predictions/probabilities fixed;
4. circularly shift labels within each validation fold;
5. compute shifted BA(candidate) - shifted BA(comparator);
6. retain all 16 candidate-specific deltas;
7. retain the maximum delta across all 16 candidates.

Artifact must serialize:

- all 1999 four-fold shift tuples;
- all 16 complete candidate-specific null vectors;
- complete max-stat null vector;
- per-candidate raw plus-one empirical p;
- per-candidate max-stat FWER plus-one p;
- max-stat q95 using empirical higher quantile;
- observed-minus-q95.

Artifact-completeness tests for all null vectors are mandatory before canonical
execution.

## 16. Strong G3 survivor gate

A candidate is `G3_LAYER_SURVIVOR` only if ALL:

1. pooled BA(candidate) > pooled BA(common-support comparator);
2. pooled BA(candidate) >= 0.54;
3. pooled delta_BA >= +0.02;
4. at least 3/4 fold delta_BA values are positive;
5. at least 3/4 candidate fold BA values are > 0.50;
6. both classes are predicted in every fold;
7. pooled predicted-minority fraction >= 0.10;
8. all four leave-one-fold-out pooled delta_BA values are > 0;
9. observed delta_BA > joint 16-candidate max-stat q95;
10. max-stat FWER p <= 0.05;
11. every provenance/support/finiteness/alignment/comparator guard passes.

No gate may be relaxed after results are observed.

## 17. Inconclusive and rejected

`G3_LAYER_INCONCLUSIVE` only if:

- pooled delta_BA > 0;
- at least 3/4 fold deltas are positive;
- all four LOO delta_BA values are > 0;

but one or more strong-survivor gates fail.

Otherwise:

`G3_LAYER_REJECTED`.

Only a true survivor may alter the frozen direction-development path.

## 18. Advancement and deterministic ranking

At most three true survivors may advance.

No weak slot filling.

Among true survivors, rank globally by:

1. smaller max-stat FWER p;
2. larger minimum fold delta_BA;
3. larger median fold delta_BA;
4. larger pooled delta_BA;
5. fewer added features;
6. lexicographically smaller candidate ID.

Advance only the first three true survivors, if that many exist.

This ranking clarification is frozen before any G3B-R1 predictive result.

Overlapping survivors are not automatically concatenated.

Any multi-survivor union/composition requires a separately preregistered next
experiment.

## 19. Stop rule

If zero true G3 survivors:

- DEV030-P3 remains the frozen direction base unchanged;
- the common-support refit is only a matched comparator and is not promoted;
- no G3 failure/inconclusive candidate is promoted;
- do not refine the best G3 failure;
- move to the next scientifically distinct strategy group.

If one or more true survivors:

- only the preregistered true survivors may advance;
- no forward holdout is opened yet;
- any composition is separately preregistered.

## 20. Required canonical artifact contents

The eventual G3B-R1 result artifact must contain at minimum:

- experiment/design/execution identity;
- P3 artifact identity;
- G3A-R1 artifact identity;
- exact common-support hashes;
- exact base feature names/order;
- exact 16-candidate registry;
- all four fold support/class counts;
- common-support comparator:
  - inner C ledgers
  - selected C values
  - fold metrics
  - pooled metrics
  - validation timestamps/labels
  - prediction hashes
- every candidate:
  - exact feature count
  - inner C ledgers
  - selected C values
  - fold metrics
  - pooled metrics
  - prediction hashes
  - matched-comparator deltas
  - LOO diagnostics
  - status
- complete 1999-replicate joint null ledger;
- all 16 candidate null vectors;
- max-stat null vector;
- FWER statistics;
- deterministic survivor ranking;
- forward/economic guards.

## 21. Canonical identity reserved for later execution

Experiment ID:

`DEV034-G3B-R1`

Canonical output directory:

`/home/emadh/Multi-Market/evidence/dev034_g3b_r1_common_support_screen_v1`

Artifact filename:

`DEV034_G3B_R1_COMMON_SUPPORT_SCREEN_RESULT.json`

These names are reserved now, but no real execution is authorized by this
design freeze.

## 22. Guards

Must remain false through design/implementation/CI/preflight:

- Sep-01+ opened
- Aug-01 new analysis
- Aug-30 reuse
- Railway opened
- archive bucket opened
- abundant-love opened
- new acquisition/download
- PnL
- threshold optimization
- calibration rescue
- feature subset search
- PCA/SVD
- interaction expansion
- alternate model family
- candidate-specific support shrink
- post-result candidate addition/removal
- post-result gate relaxation

## 23. Execution discipline

Stages remain separate:

1. design/preregistration freeze;
2. implementation only;
3. unit/synthetic CI;
4. execution freeze;
5. local real-data preflight;
6. one single canonical G3B-R1 predictive execution;
7. read-only verification.

This design freeze does not authorize any real-data G3B-R1 estimator fit.

Current state:

`DEV034_G3B_R1_DESIGN_FROZEN_IMPLEMENTATION_NEXT_NO_REAL_FIT`
