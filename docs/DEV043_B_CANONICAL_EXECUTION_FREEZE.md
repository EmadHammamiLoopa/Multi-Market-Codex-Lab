# DEV043-B Canonical Execution Freeze

Status:

`EXECUTION_FROZEN_AFTER_GREEN_CI_SINGLE_CANONICAL_DIRECTION_SCREEN_NEXT`

Date: 2026-09-03

Scientific execution commit:

`ccf345984b4668e80bebd4b2ecdd5746851de470`

Execution branch:

`research/dev043-b-execution-frozen`

Later documentation/handoff commits are intentionally excluded from the
scientific execution identity.

## Frozen Stage-A parent

DEV043-A canonical artifact:

`/home/emadh/Multi-Market/evidence/dev043_a_touch_screen_v1/DEV043_A_TOUCH_SCREEN_RESULT.json`

- bytes = `89918`
- SHA256 =
  `38ee159618a1ed13727eb6a86df83b93c92c2aad50251fcfb1618d890efd2eb7`

Frozen Stage-A status:

`DEV043_A_TOUCH_SURVIVOR_A0_TOUCH_PRICE_LOGIT`

Frozen Stage-A survivor:

`A0_TOUCH_PRICE_LOGIT`

DEV043-A MUST NEVER BE RERUN.

## Frozen Stage-B target

Binary conditional target:

- SHORT_FIRST = 0
- LONG_FIRST = 1

Support:

`ACTUAL HISTORICAL TOUCH ROWS ONLY`

NONE rows are excluded.

Predicted TOUCH is NOT used to create Stage-B training or evaluation support.

## Frozen data / folds

BTCUSDT consumed Jan-Jul 2026 first-day lineage only.

Outer folds:

1. Jan-Mar -> Apr
2. Jan-Apr -> May
3. Jan-May -> Jun
4. Jan-Jun -> Jul

All B0-B2 candidates use the exact same ordered conditional-TOUCH validation
timestamps and exact same direction labels in every fold.

## Frozen candidates

Exactly three:

1. `B0_DIR_PRICE_LOGIT`
2. `B1_DIR_PRESSURE_LOGIT`
3. `B2_DIR_COMBINED_HGB`

No fourth Stage-B candidate is permitted.

## Frozen estimators

B0/B1:

- StandardScaler
- LogisticRegression
- solver = lbfgs
- penalty = L2
- C = 1.0
- max_iter = 3000
- class_weight = None

B2:

- HistGradientBoostingClassifier
- learning_rate = 0.05
- max_iter = 200
- max_leaf_nodes = 15
- max_depth = None
- min_samples_leaf = 20
- l2_regularization = 1.0
- max_bins = 255
- categorical_features = None
- class_weight = None
- early_stopping = False
- monotonic_cst = None
- random_state = 20260903

No hyperparameter tuning is permitted.

## Frozen Stage-B endpoint

Primary endpoint:

`balanced accuracy`

Required diagnostics:

- support
- LONG/SHORT prevalence
- balanced accuracy
- BA lift over 0.50
- ROC AUC
- Brier
- log loss
- binary prior log loss
- AP LONG
- AP SHORT
- macro AP
- confusion matrix

## Frozen eligibility

A candidate survives only if ALL:

1. exact four outer folds;
2. LONG and SHORT present in every validation fold;
3. pooled balanced accuracy > 0.55;
4. pooled ROC AUC > 0.60;
5. positive BA lift over 0.50 in >=3/4 folds;
6. all four leave-one-fold-out balanced accuracies > 0.50;
7. pooled log loss < binary class-prior log loss;
8. temporal max-stat FWER p <= 0.05;
9. observed BA lift > joint max-stat q95.

## Frozen joint temporal null

- 1999 replicates
- seed = 20260903
- same fold-local circular direction-label shift applied to B0-B2
- no model refit
- statistic = pooled balanced accuracy - 0.50
- replicate statistic = maximum BA lift across B0-B2
- q95 = quantile(method="higher")
- plus-one denominator = 2000
- minimum circular displacement = 60 conditional-TOUCH validation positions
- folds with <=120 Stage-B validation rows fail closed

## Frozen ranking

Among final eligible candidates:

1. highest minimum outer-fold BA lift;
2. highest pooled balanced accuracy;
3. highest minimum leave-one-fold-out balanced accuracy;
4. highest pooled ROC AUC;
5. lowest pooled log loss;
6. lower complexity B0 < B1 < B2;
7. lexical candidate ID.

Advance exactly one.

If none survives:

`DEV043_B_NO_DIRECTION_SURVIVOR`

If one survives:

`DEV043_B_DIRECTION_SURVIVOR_<CANDIDATE_ID>`

## Stop logic

If Stage B has no survivor:

`STOP DEV043`

DEV043-C is not authorized.

If Stage B has exactly one survivor:

DEV043-C single-composition implementation + synthetic/unit CI becomes
authorized.

## Permanent canonical rule

From canonical Stage-B start:

`DEV043-B MUST NEVER BE RERUN`

No second canonical attempt is permitted after the start marker.

After results:

- no fourth Stage-B model
- no threshold search
- no calibration layer
- no hyperparameter search
- no target change
- no null redesign
- no gate weakening
- no predicted-TOUCH support substitution
- no other-market rescue
- no Sep-01+ development access

## Forward reserve

Sep-01+ remains analytically sealed.

All non-BTC markets remain analytically sealed.

## Current state

`DEV043_B_EXECUTION_FROZEN_SINGLE_CANONICAL_DIRECTION_SCREEN_NEXT`
