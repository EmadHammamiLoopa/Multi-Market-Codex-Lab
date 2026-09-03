# DEV043 — Event-Conditioned H1800/B32 Predictive Decomposition

Status:

`DESIGN_FROZEN_BEFORE_ANY_DEV043_REAL_LABEL_OR_MODEL_RESULT`

Date: 2026-09-03

## 1. Frozen parent

Parent target geometry:

`H1800_B32`

Frozen DEV041 oracle survivor.

DEV042 direct three-class family is permanently closed as:

`DEV042_NO_PREDICTIVE_SURVIVOR_FOR_H1800_B32`

DEV043 does not reopen DEV042.

## 2. Data boundary

BTCUSDT only.

Consumed Jan-Jul 2026 first-day lineage only.

Exact outer folds:

1. Jan-Mar -> Apr
2. Jan-Apr -> May
3. Jan-May -> Jun
4. Jan-Jun -> Jul

Sep-01+ remains sealed.

All non-BTC markets remain sealed.

## 3. Frozen common support

Reuse the exact DEV042 frozen common feature support.

Per day:

`1409`

Pooled Jan-Jul:

`9863`

The same ordered support rows are used across all DEV043 candidate models.

No candidate-specific support advantage is allowed.

## 4. Factorized target

### Stage A — event occurrence

Binary target:

- TOUCH
- NONE

Where:

`TOUCH = LONG_FIRST or SHORT_FIRST`

under exact frozen H1800/B32 first-passage semantics.

Ambiguous/invalid rows remain excluded exactly as before.

### Stage B — conditional direction

Stage B support is restricted to rows where the frozen target is TOUCH.

Binary target:

- LONG_FIRST
- SHORT_FIRST

Stage B never sees NONE rows.

No Stage B sample is created from predicted TOUCH; training/evaluation uses
actual historical TOUCH rows inside each strictly chronological fold.

### Stage C — deployable composition

For each OOF validation row:

`p_touch = P(TOUCH)`

`p_long_touch = P(LONG_FIRST | TOUCH)`

`p_short_touch = 1 - p_long_touch`

Frozen joint probabilities:

`p_none = 1 - p_touch`

`p_long = p_touch * p_long_touch`

`p_short = p_touch * p_short_touch`

Action rule:

- unique argmax NONE -> ABSTAIN
- unique argmax LONG -> LONG
- unique argmax SHORT -> SHORT
- probability tie -> ABSTAIN

No threshold search.

No q80 controller.

No probability calibration layer.

No meta-filter.

## 5. Stage A candidate universe

Exactly three binary TOUCH/NONE candidates:

### A0_TOUCH_PRICE_LOGIT

Features:

DEV042 F0 PRICE_MOMENTUM, 15 features.

Estimator:

- StandardScaler
- LogisticRegression
- solver = lbfgs
- C = 1.0
- max_iter = 3000
- class_weight = None

### A1_TOUCH_PRESSURE_LOGIT

Features:

DEV042 F2 PRESSURE_CAPACITY, 51 features.

Same fixed logistic specification.

### A2_TOUCH_COMBINED_HGB

Features:

DEV042 combined 111 features.

Estimator:

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

No tuning.

## 6. Stage B candidate universe

Exactly three conditional LONG/SHORT candidates:

### B0_DIR_PRICE_LOGIT

DEV042 F0 PRICE_MOMENTUM, 15 features.

Fixed StandardScaler + LogisticRegression C=1.0.

### B1_DIR_PRESSURE_LOGIT

DEV042 F2 PRESSURE_CAPACITY, 51 features.

Fixed StandardScaler + LogisticRegression C=1.0.

### B2_DIR_COMBINED_HGB

DEV042 combined 111 features.

Same fixed HGB specification as Stage A A2.

No tuning.

## 7. Why only 3 + 3

The design tests two hypotheses cleanly:

1. whether pressure/liquidity state improves event occurrence versus price;
2. whether pressure/liquidity state improves conditional direction versus
   price.

The nonlinear challenger tests whether the same information requires a
nonlinear boundary.

No model zoo is permitted.

## 8. Stage A required diagnostics

Per fold and pooled:

- support
- TOUCH/NONE prevalence
- AP for TOUCH
- ROC AUC
- Brier
- log loss
- balanced accuracy
- confusion matrix

Primary Stage A endpoint:

`TOUCH average precision`

Stage A is predictive-only; no PnL yet.

## 9. Stage A eligibility

A Stage A candidate survives only if ALL:

1. exact 4 outer folds;
2. AP > TOUCH prevalence pooled;
3. AP lift over prevalence >= 0.05 absolute;
4. positive AP lift in >=3/4 folds;
5. all four leave-one-fold-out AP lifts >0;
6. pooled ROC AUC >0.60;
7. pooled Brier < prevalence*(1-prevalence);
8. temporal max-stat FWER p <=0.05;
9. observed AP lift > joint max-stat q95.

Joint temporal null:

- 1999 replicates
- seed = 20260903
- same fold-local circular target shift for A0-A2
- max-stat across three Stage A candidates
- no model refit under null

Advance exactly one Stage A candidate.

If none survives:

`DEV043_A_NO_TOUCH_SURVIVOR`

and DEV043 closes immediately.

## 10. Stage B required diagnostics

Evaluated only on actual TOUCH rows.

Per fold and pooled:

- support
- LONG/SHORT prevalence
- balanced accuracy
- ROC AUC
- log loss
- Brier
- macro AP
- confusion matrix

Primary Stage B endpoint:

`balanced accuracy`

## 11. Stage B eligibility

A Stage B candidate survives only if ALL:

1. exact 4 outer folds;
2. both LONG and SHORT present every validation fold;
3. pooled balanced accuracy >0.55;
4. pooled ROC AUC >0.60;
5. positive balanced-accuracy lift over 0.50 in >=3/4 folds;
6. all four leave-one-fold-out balanced accuracies >0.50;
7. pooled log loss < binary class-prior log loss;
8. temporal max-stat FWER p <=0.05;
9. observed BA lift > joint max-stat q95.

Joint temporal null:

- 1999 replicates
- seed = 20260903
- same fold-local circular direction-label shift for B0-B2
- max-stat across three Stage B candidates
- no model refit under null

Advance exactly one Stage B candidate.

If none survives:

`DEV043_B_NO_DIRECTION_SURVIVOR`

and DEV043 closes.

## 12. Stage C composition eligibility

Stage C runs only if both A and B produce a survivor.

Exactly one composition exists:

`A_SURVIVOR + B_SURVIVOR`

No 3x3 post-hoc combination grid.

Joint probabilities are composed exactly as frozen in Section 4.

Action rule is argmax with NONE abstention.

## 13. Stage C executable semantics

Exactly reuse DEV042 executable semantics:

- entry at decision +250 ms
- LONG enters ask
- SHORT enters bid
- predicted-direction +32bp first -> TP
- opposite barrier first -> SL
- neither within 1800s -> forced horizon exit
- exit response latency = 250 ms
- LONG exits bid
- SHORT exits ask
- FLAT_ONLY
- no cross-day trade

## 14. Stage C costs

C1:

`10 bps`

C2 primary:

`16 bps`

No cost tuning.

## 15. Stage C economic eligibility

The single composition survives only if ALL:

1. zero execution-invalid trades;
2. accepted trades >=100 pooled;
3. trades in every Apr-Jul fold;
4. LONG >0;
5. SHORT >0;
6. pooled C2 mean net >0;
7. pooled C2 total net >0;
8. pooled C2 PF >1.05;
9. positive C2 folds >=3/4;
10. minimum fold C2 mean > -2 bps/trade;
11. every LOO C2 mean >0;
12. pooled C1 mean net >0;
13. pooled C1 total net >0;
14. no fold >60% of positive C2 net;
15. pooled action coverage in [0.05,0.80];
16. economic temporal-null FWER p <=0.05;
17. observed C2 mean > economic joint-null q95.

The economic null uses the final composed action stream only:

- 1999 fold-local circular action shifts
- seed = 20260903
- exact FLAT_ONLY executable C2 re-evaluation
- no refit

## 16. Advancement

If Stage C passes:

`DEV043_EVENT_CONDITIONED_SURVIVOR`

If Stage C fails:

`DEV043_EVENT_CONDITIONED_COMPOSITION_FAIL`

No secondary composition is attempted.

## 17. Anti-rescue

After any real DEV043 result begins:

- NO fourth Stage A model
- NO fourth Stage B model
- NO 3x3 composition search
- NO threshold tuning
- NO q80 controller
- NO class-weight search
- NO hyperparameter search
- NO calibration layer
- NO meta-filter
- NO alternate horizon
- NO alternate barrier
- NO cost weakening
- NO null redesign
- NO gate weakening
- NO other-market rescue
- NO Sep-01+ development access

## 18. Stage structure

### DEV043-P0

Schema/parent/common-support audit only.

No labels/model fit.

### DEV043-A

Binary TOUCH/NONE implementation, CI, no-result preflight, one canonical screen.

### DEV043-B

Conditional LONG/SHORT implementation, CI, no-result preflight, one canonical
screen.

B is only authorized if A has a survivor.

### DEV043-C

Single frozen A+B composition economic screen.

C is only authorized if both A and B have survivors.

## 19. Stop logic

This family is deliberately sequential.

If A fails:

`STOP DEV043`

If A passes and B fails:

`STOP DEV043`

If A and B pass but C fails:

`STOP DEV043`

No rescue stage is permitted.

## 20. Current state

`DEV043_DESIGN_FROZEN_P0_PARENT_SCHEMA_AUDIT_NEXT`
