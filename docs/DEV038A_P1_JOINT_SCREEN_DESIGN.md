# DEV038-A-P1 — Joint Opportunity Representation Screen

Status: `DESIGN_FROZEN_BEFORE_ANY_DEV038A_P1_MODEL_FIT`

Date: 2026-09-03

## 1. Objective

DEV038-A-P1 jointly compares five frozen causal TOUCH_VS_NONE representations
on the exact common support established by DEV038-A-P0.

This is a development-stage representation screen.

Jan-Jul has already been consumed by earlier project stages and therefore no
DEV038-A-P1 result may be called forward-confirmed or production-ready.

## 2. Frozen parent

DEV038-A-P0 canonical artifact:

`/home/emadh/Multi-Market/evidence/dev038a_p0_common_support_v1/DEV038A_P0_COMMON_SUPPORT_RESULT.json`

SHA256:

`fd4639c003c4888a7316386b4ddb0031bf9bfb59d1d05afe0dc3fcb08b1ea6a5`

Bytes:

`8464`

Terminal parent status:

`DEV038A_P0_COMMON_SUPPORT_PASS`

## 3. Frozen target

Exactly:

- symbol = BTCUSDT
- target = A
- horizon = 120 seconds
- barrier = 16 bps

Binary target:

- TOUCH = LONG_FIRST or SHORT_FIRST within 120s / 16bp
- NONE = no directional first-passage touch

No target geometry search is allowed.

## 4. Frozen common support

Aggregate:

`10016 rows`

Retained fraction vs native A0 support:

`0.9957252211949498`

Per-day common support:

- Jan: 1436 = 4 TOUCH / 1432 NONE
- Feb: 1434 = 434 / 1000
- Mar: 1436 = 362 / 1074
- Apr: 1428 = 158 / 1270
- May: 1430 = 62 / 1368
- Jun: 1424 = 118 / 1306
- Jul: 1428 = 220 / 1208

All five candidates must use exactly these rows.

No candidate-specific support is permitted.

## 5. Frozen candidate family

Exactly:

### A0 — PRICE32

- window = 32s
- block = PRICE
- feature count = 23
- common-support incumbent comparator

### A1 — PRICE_BOOK32

- window = 32s
- block = PRICE_BOOK
- feature count = 89

### A2 — PRICE_BOOK_FLOW32

- window = 32s
- block = PRICE_BOOK_FLOW
- feature count = 209

### A3 — FULL32

- window = 32s
- block = PRICE_BOOK_FLOW_DYNAMICS
- feature count = 341

### A4 — FULL60

- window = 60s
- block = PRICE_BOOK_FLOW_DYNAMICS
- feature count = 341

No candidate may be added or removed after any P1 predictive result is seen.

## 6. Frozen estimator lineage

For every candidate:

- representation = sequence-summary S1 features from its frozen block/window;
- StandardScaler;
- LogisticRegression;
- C grid exactly the existing P4 T2 C grid;
- solver = lbfgs;
- L2;
- class_weight = None;
- fit_intercept = True;
- max_iter = 1000;
- random_state unchanged from P4 lineage.

C selection must use the existing P4 nested training-only procedure.

No estimator-family search.

## 7. Outer folds

Exactly four expanding folds:

### Fold 1

- outer train = Jan-Mar
- outer validation = Apr
- inner validation = Mar
- inner fit = Jan-Feb

### Fold 2

- outer train = Jan-Apr
- outer validation = May
- inner validation = Apr
- inner fit = Jan-Mar

### Fold 3

- outer train = Jan-May
- outer validation = Jun
- inner validation = May
- inner fit = Jan-Apr

### Fold 4

- outer train = Jan-Jun
- outer validation = Jul
- inner validation = Jun
- inner fit = Jan-May

All inner/outer matrices must be built from the frozen 10016-row common-support
ledger only.

## 8. Primary endpoint

Primary endpoint:

`Average Precision (AP)`

Primary comparator:

`A0 PRICE32`

For challenger A:

`Delta_AP(A) = pooled_AP(A) - pooled_AP(A0)`

The pooled AP is calculated on the concatenated four outer-validation
prediction vectors in chronological order.

## 9. Required secondary metrics

Serialize pooled and per-fold:

- ROC AUC
- Brier
- log loss
- touch prevalence
- top-decile precision
- top-decile lift vs prevalence

Top-decile definition:

- select the highest 10% of candidate probabilities within each validation
  fold using deterministic descending probability rank;
- pooled top-decile statistics are computed by concatenating those fold-level
  selections.

No threshold optimization.

## 10. Calibration safeguard

A challenger cannot survive if pooled AP improves while either required
calibration metric worsens.

Required:

- pooled Brier <= A0 pooled Brier
- pooled log loss <= A0 pooled log loss

## 11. Minimum practical effect

Required:

`pooled Delta_AP >= +0.015`

absolute AP.

This is frozen before any P1 predictive metric is observed.

## 12. Fold stability

Required:

- at least 3/4 fold Delta_AP values > 0;
- all four leave-one-fold-out pooled Delta_AP values > 0.

## 13. Joint temporal falsification

All four challengers A1-A4 are tested jointly against A0.

Predictions remain fixed.

Within each outer validation fold:

1. circularly shift the binary TOUCH/NONE label sequence;
2. use the same shifted labels for A0-A4;
3. recompute pooled AP for every candidate;
4. compute each challenger Delta_AP vs A0;
5. record the maximum challenger Delta_AP.

Legal shift range:

- minimum = 30 rows
- maximum = n_fold - 30 rows

Parameters:

- seed = 20260903
- replicates = 1999
- q95 method = higher
- empirical p uses plus-one denominator 2000

This controls the family-wise false-discovery risk across A1-A4.

## 14. Survivor gate

A challenger A1-A4 is a DEV038-A development survivor only if ALL pass:

1. pooled AP > A0;
2. pooled Delta_AP >= +0.015;
3. >= 3/4 positive fold Delta_AP values;
4. all four LOO Delta_AP values > 0;
5. pooled Brier <= A0;
6. pooled log loss <= A0;
7. observed Delta_AP > joint max-stat q95;
8. max-stat FWER empirical p <= 0.05.

No gate may be weakened after results are seen.

## 15. Survivor ranking

If multiple challengers survive, advance exactly one.

Ranking:

1. smaller FWER p;
2. larger minimum fold Delta_AP;
3. larger median fold Delta_AP;
4. larger pooled Delta_AP;
5. lower pooled Brier;
6. lower pooled log loss;
7. lower complexity:
   A1 < A2 < A3 < A4;
8. lexicographic candidate ID.

## 16. Terminal outcomes

If one or more challengers survive:

`DEV038A_P1_DEVELOPMENT_SURVIVOR_FOUND`

Advance rank 1 only.

If none survive:

`DEV038A_P1_NO_CHALLENGER_SURVIVOR_RETAIN_A0`

Advance A0.

## 17. Meaning of advancement

Advancement means only:

The selected representation is the best frozen Jan-Jul development
representation under common support and joint falsification.

It does NOT mean:

- forward-confirmed;
- profitable;
- economically executable;
- production-ready.

## 18. Mandatory next stage

After P1:

1. freeze the selected opportunity representation;
2. integrate it with the already-frozen BTC45 direction logic and selective
   decision controller without reopening Jan-Jul selection;
3. freeze an untouched forward-confirmation protocol before opening new data;
4. only after forward confirmation proceed to full economic evaluation.

If no challenger survives, A0 remains the opportunity representation.

## 19. Strict prohibitions

DEV038-A-P1 must not:

- use candidate-specific support;
- change target horizon/barrier;
- change model family;
- tune W120;
- tune BTC45 direction;
- score S1/S2/S5 policy variants;
- use ETH/G4;
- calculate PnL;
- use fees/slippage;
- open Sep-01+ forward data;
- reuse Aug-30 as fresh holdout.

## 20. Permanent no-rerun rules

`DEV038-A-P0 MUST NEVER BE RERUN`

`DEV037-P1-R1 MUST NEVER BE RERUN`

`DEV037-P0-R2 MUST NEVER BE RERUN`

`DEV037-P0-R1 MUST NEVER BE RERUN`

`DEV036-C1 MUST NEVER BE RERUN`

`DEV035-G4B MUST NEVER BE RERUN`

`DEV034-G3B-R1 MUST NEVER BE RERUN`

`DEV034-G3A-R1 MUST NEVER BE RERUN`

## 21. Execution discipline

Stages:

1. P1 design freeze
2. implementation only
3. synthetic/unit CI
4. execution freeze
5. real-data no-result matrix/support preflight
6. one canonical P1 joint development screen
7. deep read-only verification
8. result freeze

No DEV038-A-P1 real model fit is authorized by this design freeze alone.

## 22. Current state

`DEV038A_P1_JOINT_SCREEN_DESIGN_FROZEN_IMPLEMENTATION_NEXT_NO_REAL_FIT`
