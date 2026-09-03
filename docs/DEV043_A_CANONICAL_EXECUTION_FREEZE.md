# DEV043-A Canonical Execution Freeze

Status:

`EXECUTION_FROZEN_AFTER_GREEN_CI_SINGLE_CANONICAL_TOUCH_SCREEN_NEXT`

Date: 2026-09-03

Scientific execution commit:

`342547b45f1fecd361a17daad5c7450a755c6330`

Execution branch:

`research/dev043-a-execution-frozen`

Later documentation/handoff commits are intentionally excluded from the
scientific execution identity.

## Frozen parent

DEV043-P0 canonical artifact:

`/home/emadh/Multi-Market/evidence/dev043_p0_parent_schema_audit_v1/DEV043_P0_PARENT_SCHEMA_AUDIT_RESULT.json`

- bytes = `6387`
- SHA256 =
  `5d6b704dba88f43a681a73d9cca637bdb3f8d565ec96aaf389ee46302a15bf3e`

Frozen P0 status:

`DEV043_P0_PARENT_SCHEMA_AUDIT_PASS`

P0 MUST NEVER BE RERUN.

## Frozen Stage-A target

Binary target:

- TOUCH
- NONE

where TOUCH means:

`LONG_FIRST or SHORT_FIRST`

under frozen H1800/B32 first-passage semantics.

Invalid and ambiguous records are excluded.

## Frozen data / folds

BTCUSDT consumed Jan-Jul 2026 first-day lineage only.

Outer folds:

1. Jan-Mar -> Apr
2. Jan-Apr -> May
3. Jan-May -> Jun
4. Jan-Jun -> Jul

All A0-A2 candidates use the exact same ordered validation timestamps and exact
same Stage-A labels in every fold.

## Frozen candidates

Exactly three:

1. `A0_TOUCH_PRICE_LOGIT`
2. `A1_TOUCH_PRESSURE_LOGIT`
3. `A2_TOUCH_COMBINED_HGB`

No fourth Stage-A candidate is permitted.

## Frozen estimators

A0/A1:

- StandardScaler
- LogisticRegression
- solver = lbfgs
- penalty = L2
- C = 1.0
- max_iter = 3000
- class_weight = None

A2:

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

## Frozen Stage-A endpoint

Primary endpoint:

`TOUCH average precision`

Required diagnostics include:

- support
- TOUCH/NONE prevalence
- TOUCH AP
- AP lift over prevalence
- ROC AUC
- Brier
- prior Brier
- log loss
- balanced accuracy
- confusion matrix

## Frozen eligibility

A candidate survives only if ALL:

1. exact four outer folds;
2. pooled AP > pooled TOUCH prevalence;
3. pooled AP lift >= 0.05;
4. positive AP lift in >=3/4 folds;
5. all four LOO AP lifts > 0;
6. pooled ROC AUC > 0.60;
7. pooled Brier < prior Brier;
8. temporal max-stat FWER p <= 0.05;
9. observed AP lift > joint max-stat q95.

## Frozen joint temporal null

- 1999 replicates
- seed = 20260903
- same fold-local circular target shift applied to A0-A2
- no model refit under the null
- statistic = pooled TOUCH AP lift over pooled TOUCH prevalence
- replicate statistic = maximum AP lift across A0-A2
- q95 = quantile(method="higher")
- plus-one denominator = 2000
- minimum circular displacement = 60 validation positions
- folds with <=120 validation rows fail closed

## Frozen ranking

Among final eligible candidates:

1. highest minimum outer-fold AP lift;
2. highest pooled AP lift;
3. highest minimum LOO AP lift;
4. highest pooled ROC AUC;
5. lowest pooled Brier;
6. lower complexity A0 < A1 < A2;
7. lexical candidate ID.

Advance exactly one.

If none survives:

`DEV043_A_NO_TOUCH_SURVIVOR`

If one survives:

`DEV043_A_TOUCH_SURVIVOR_<CANDIDATE_ID>`

## Stop logic

If Stage A has no survivor:

`STOP DEV043`

DEV043-B is not authorized.

If Stage A has exactly one survivor:

DEV043-B implementation + synthetic/unit CI becomes authorized.

## Permanent canonical rule

From canonical Stage-A start:

`DEV043-A MUST NEVER BE RERUN`

No second canonical attempt is permitted after the start marker.

After results:

- no fourth Stage-A model
- no threshold search
- no calibration layer
- no hyperparameter search
- no target change
- no null redesign
- no gate weakening
- no other-market rescue
- no Sep-01+ development access

## Forward reserve

Sep-01+ remains analytically sealed.

All non-BTC markets remain analytically sealed.

## Current state

`DEV043_A_EXECUTION_FROZEN_SINGLE_CANONICAL_TOUCH_SCREEN_NEXT`
