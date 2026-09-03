# DEV042-P3 Canonical Execution Freeze

Status:

`EXECUTION_FROZEN_AFTER_FINAL_GREEN_CI_SINGLE_CANONICAL_PREDICTIVE_SCREEN_NEXT`

Date: 2026-09-03

Scientific execution commit:

`1558d2090b8d4e269b67ddb8bb7687069087f410`

Execution branch:

`research/dev042-p3-execution-frozen`

Later documentation/handoff commits are intentionally excluded from the
scientific execution identity.

## Parent evidence

DEV042-P0:

`DEV042_P0_FEATURE_SCHEMA_AUDIT_PASS`

Canonical P0 artifact:

- path:
  `/home/emadh/Multi-Market/evidence/dev042_p0_feature_schema_audit_v1/DEV042_P0_FEATURE_SCHEMA_AUDIT_RESULT.json`
- bytes = `12989`
- SHA256 =
  `d9259a53d24492f478615c986ed73981f052d483a764935a8dfd68d17212b882`

DEV042-P2:

`DEV042_P2_NO_RESULT_PREFLIGHT_PASS_WITH_FROZEN_WRAPPER_SERIALIZATION_DEFECT`

Canonical raw P2 artifact:

- path:
  `/home/emadh/Multi-Market/evidence/dev042_p2_no_result_preflight_v1/DEV042_P2_NO_RESULT_PREFLIGHT_RESULT.json`
- bytes = `5606`
- SHA256 =
  `7a9f190323430d357e3febef16edfd9e5a8971342265c3f24a01d5797f00c6dd`

Frozen valid P2 JSON payload prefix:

- bytes = `5604`
- SHA256 =
  `8201733ec069b304d575ffea0b89e95e134d7853eae755027c91320dbb349981`

P2 scientific checks:

- 131 PASS / 0 FAIL

P2 forensic verification:

- 108 PASS / 0 FAIL
- rerun required = NO
- rerun permitted = NO

## Frozen target

`H1800_B32`

- horizon = 1800 seconds
- barrier = 32 bps
- entry latency = 250 ms
- response latency = 250 ms
- target classes = NONE / LONG_FIRST / SHORT_FIRST
- same-row first-touch tie = AMBIGUOUS_EXCLUDED

## Frozen data

BTCUSDT only.

Consumed historical lineage only:

- Jan 01 2026
- Feb 01 2026
- Mar 01 2026
- Apr 01 2026
- May 01 2026
- Jun 01 2026
- Jul 01 2026

Outer chronological folds:

1. Jan-Mar -> Apr
2. Jan-Apr -> May
3. Jan-May -> Jun
4. Jan-Jun -> Jul

All candidates use the exact same ordered common-support timestamps and exact
same target labels in each fold.

Runtime assertions fail closed on any cross-candidate timestamp, label, or
record-count mismatch.

## Frozen candidates

Exactly five:

1. `C0_PRICE_LOGIT`
2. `C1_OFI_LOGIT`
3. `C2_PRESSURE_CAPACITY_LOGIT`
4. `C3_COMBINED_LOGIT`
5. `C4_COMBINED_HGB`

No sixth candidate is permitted.

## Frozen estimators

C0-C3:

- StandardScaler on outer-train only
- LogisticRegression
- solver = lbfgs
- penalty = L2
- C = 1.0
- max_iter = 3000
- class_weight = None

C4:

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

## Frozen action rule

- NONE unique argmax -> ABSTAIN
- LONG_FIRST unique argmax -> LONG
- SHORT_FIRST unique argmax -> SHORT
- any maximum-probability tie -> ABSTAIN

No threshold search or controller search.

## Frozen execution

Entry:

- decision +250 ms
- LONG ask
- SHORT bid

Exit:

- predicted-direction 32-bp barrier first -> TP
- opposite 32-bp barrier first -> SL
- neither by 1800 s -> forced horizon exit
- barrier-triggered exit realized at event +250 ms
- forced exit realized at horizon +250 ms
- LONG exits bid
- SHORT exits ask

FLAT_ONLY:

- no overlap
- no pyramiding
- no reversal
- no concurrent BTC positions
- no cross-day trade

Cached execution paths are an implementation optimization only and are
synthetically verified equal to direct execution.

## Frozen costs

C1:

`10 bps`

C2 primary:

`16 bps`

## Frozen absolute eligibility

All 16 V2 economic/activity gates are immutable.

## Frozen joint temporal null

- 1999 replicates
- seed = 20260903
- same fold-local circular shift applied to all five candidates
- full ABSTAIN/LONG/SHORT action stream shifted
- no model refit
- exact frozen FLAT_ONLY C2 execution re-evaluated
- legal shifts preserve at least 60 common-support positions from zero in
  either circular direction
- replicate statistic = maximum C2 mean net bp/trade across C0-C4
- q95 = quantile(method="higher")
- plus-one empirical denominator = 2000

Final null eligibility requires:

- observed C2 mean > joint q95
- max-stat FWER p <= 0.05

## Frozen ranking

Among final eligible candidates:

1. highest minimum fold C2 mean net bp/trade
2. highest median fold C2 mean net bp/trade
3. highest pooled C2 mean net bp/trade
4. highest minimum LOO C2 mean net bp/trade
5. highest pooled C2 PF
6. highest pooled C2 total net bps
7. lower complexity
8. candidate ID

Advance exactly one.

If none qualifies:

`DEV042_NO_PREDICTIVE_SURVIVOR_FOR_H1800_B32`

## Required outputs

Classification diagnostics include:

- class prevalence
- confusion matrix
- macro F1
- balanced accuracy
- multiclass log loss
- per-class precision/recall/F1/AP
- macro one-vs-rest AP
- action coverage
- LONG/SHORT/ABSTAIN counts

Economic outputs include:

- raw actions
- accepted FLAT_ONLY trades
- ignored overlap
- LONG/SHORT trades
- TP/SL/forced exits
- trades/day
- gross/net bps
- total net
- PF/win rate
- max drawdown
- max losing streak
- per-fold net
- positive folds
- exposure
- cumulative net curve

## Permanent canonical rule

From the P3 canonical start marker:

`DEV042-P3 MUST NEVER BE RERUN`

No second canonical attempt is permitted even if execution fails after that
marker.

After results:

- NO sixth candidate
- NO model/hyperparameter tuning
- NO alternate threshold/controller
- NO new feature family
- NO H1800/B32 target modification
- NO null redesign
- NO gate weakening
- NO other-market rescue
- NO Sep-01+ development access

## Forward reserve

Sep-01+ remains analytically sealed for BTC and every other market.

All non-BTC markets remain analytically sealed.

## Current state

`DEV042_P3_EXECUTION_FROZEN_SINGLE_CANONICAL_SCREEN_NEXT`
