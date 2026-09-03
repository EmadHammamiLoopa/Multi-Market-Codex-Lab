# DEV042 — H1800/B32 Predictive Family Screen V2

Status:

`DESIGN_V2_FROZEN_BEFORE_ANY_DEV042_LABEL_OR_MODEL_RESULT`

Date: 2026-09-03

Supersedes before any DEV042 label construction, fit, or real predictive result:

`docs/DEV042_H1800_B32_PREDICTIVE_FAMILY_DESIGN.md`

The V1 design remains preserved in Git history.

## 1. Parent geometry

Frozen DEV041 survivor:

`H1800_B32`

- vertical horizon = 1800 s
- executable barrier = 32 bps
- entry latency = 250 ms
- response latency = 250 ms

DEV041 canonical artifact:

- bytes = 429239
- SHA256 =
  `542117791966f9049cb49e5b578d7857b3e1178f44be83172c7edfac56244a15`

No target-geometry reopening is permitted.

## 2. Data boundary

Development only:

- BTCUSDT
- consumed Jan-Jul 2026 first-day lineage

Outer OOF evaluation:

- Jan-Mar -> Apr
- Jan-Apr -> May
- Jan-May -> Jun
- Jan-Jun -> Jul

Forbidden:

- Sep-01+
- ETH/SOL/other markets
- forward-bucket analytics

## 3. Mandatory common-support contract

All five candidates MUST be trained and scored on the exact same timestamp
support.

### Feature common support

Before labels or fitting, build a feature-valid mask requiring:

- every frozen F0 PRICE feature finite;
- every frozen F1 OFI feature finite;
- every frozen F2 PRESSURE_CAPACITY feature finite;
- all shared reference columns finite/valid;
- exact decision timestamp on the frozen minute grid.

C3 and C4 use the union feature set but receive no support advantage.

### Label/evaluation support

After label construction becomes authorized, final model support is:

`FEATURE_COMMON_SUPPORT ∩ TARGET_VALID ∩ NOT_AMBIGUOUS`

The exact same ordered timestamp array is passed to C0-C4 in every fold.

C0 MUST be re-fit/re-scored on common support; native C0 support may be
reported only as a diagnostic.

No candidate may be compared on a larger or different timestamp set.

### Support identity

P0/P2 must freeze:

- ordered feature names per family;
- ordered common timestamp hashes per day;
- common-support counts per day;
- common-support retention versus exact minute decisions;
- finite/NaN contracts.

No label metrics are allowed during P0.

## 4. Target and tie semantics

Classes:

- LONG_FIRST
- SHORT_FIRST
- NONE

Strict executable first-passage:

LONG:
- entry ask at decision +250 ms;
- upward barrier evaluated on executable bid.

SHORT:
- entry bid at decision +250 ms;
- downward barrier evaluated on executable ask.

The first exact 250 ms executable timestamp wins.

If both directional barriers are first satisfied on the same timestamp:

`AMBIGUOUS_EXCLUDED`

No heuristic tie breaking.

If replay cannot determine a strict first event consistently:

`AMBIGUOUS_EXCLUDED`

If neither barrier occurs by the vertical horizon:

`NONE`

This rule is immutable.

## 5. Candidate universe

Exactly five:

1. `C0_PRICE_LOGIT`
2. `C1_OFI_LOGIT`
3. `C2_PRESSURE_CAPACITY_LOGIT`
4. `C3_COMBINED_LOGIT`
5. `C4_COMBINED_HGB`

No sixth candidate after real results begin.

## 6. Action rule

For each common-support row:

- predict P(LONG_FIRST), P(SHORT_FIRST), P(NONE);
- if NONE is unique argmax -> ABSTAIN;
- if LONG is unique argmax -> LONG;
- if SHORT is unique argmax -> SHORT;
- any probability tie for maximum -> ABSTAIN.

No probability threshold search.

No quantile controller.

No coverage tuning.

## 7. Frozen estimators and hyperparameters

### C0-C3 LogisticRegression

Exactly:

- StandardScaler fit on outer-train rows only
- LogisticRegression
- solver = `lbfgs`
- penalty = `l2`
- C = `1.0`
- max_iter = `3000`
- class_weight = `None`
- random_state = not used for deterministic lbfgs fit

No C grid or class-weight tuning.

### C4 HistGradientBoostingClassifier

Exactly:

- learning_rate = `0.05`
- max_iter = `200`
- max_leaf_nodes = `15`
- max_depth = `None`
- min_samples_leaf = `20`
- l2_regularization = `1.0`
- max_bins = `255`
- categorical_features = `None`
- class_weight = `None`
- early_stopping = `False`
- monotonic_cst = `None`
- random_state = `20260903`

No validation_fraction is used because early stopping is disabled.

No chronological inner tuning is needed because there is exactly one frozen HGB
specification.

No HGB parameter may change after real results.

## 8. Why early_stopping is disabled

scikit-learn HGB can enable early stopping automatically and its random_state
controls the internal train/validation split when early stopping is active.

A random internal validation split is not acceptable for this time-series
experiment.

Therefore:

`early_stopping=False`

is mandatory.

Monotonic constraints are also explicitly absent:

`monotonic_cst=None`

because multiclass HGB does not support monotonic constraints and DEV042 has
three target classes.

## 9. Deployable trade semantics

When the model acts:

Entry:
- decision +250 ms
- LONG ask / SHORT bid

Monitor both executable ±32 bps first-passage barriers for up to 1800 s.

Predicted direction barrier first:
- TP event.

Opposite barrier first:
- SL event.

For either:
- event timestamp = first exact executable row;
- realized exit = event +250 ms;
- LONG exits bid / SHORT exits ask.

Neither by horizon:
- forced exit at entry +1800 s +250 ms;
- executable opposite-side quote.

Missing/invalid required execution row:
- execution-invalid;
- candidate fails integrity rather than dropping trade.

FLAT_ONLY:
- no overlap
- no pyramiding
- no reversal
- no cross-day trade

## 10. Cost envelopes

C1 diagnostic:
- 10 bps total explicit cost

C2 primary:
- 16 bps total explicit cost

All promotion ranking and null testing use C2.

## 11. Statistical diagnostics

Per fold and pooled:

- class prevalence
- confusion matrix
- macro F1
- balanced accuracy
- multiclass log loss
- one-vs-rest AP per class
- macro one-vs-rest AP
- per-class precision/recall
- action coverage
- LONG/SHORT/ABSTAIN counts

These are interpretation diagnostics only.

No classification metric is a primary promotion gate.

## 12. Economic outputs

Per fold and pooled, C1/C2:

- actions
- accepted FLAT_ONLY trades
- ignored overlap actions
- LONG/SHORT
- TP/SL/forced exits
- execution-invalid
- trades/day
- gross bp/trade
- net bp/trade
- total net
- win rate
- PF
- max drawdown
- max losing streak
- per-day/fold net
- positive folds
- exposure
- cumulative net curve

## 13. Absolute economic eligibility gates

A candidate must satisfy ALL:

1. four outer folds completed;
2. zero execution-invalid trades;
3. accepted trades >=100 pooled;
4. trades on every Apr-Jul fold;
5. LONG >0;
6. SHORT >0;
7. pooled C2 mean net >0;
8. pooled C2 total net >0;
9. pooled C2 PF >1.05;
10. positive C2 folds >=3/4;
11. minimum fold C2 mean net > -2.0 bps/trade;
12. every leave-one-fold-out C2 mean net >0;
13. pooled C1 mean net >0;
14. pooled C1 total net >0;
15. no fold contributes >60% of positive pooled C2 net;
16. pooled action coverage in [0.05,0.80].

These are necessary but not sufficient.

## 14. Joint temporal null with multiplicity control

A candidate must ALSO pass a frozen joint temporal null.

Purpose:

- test whether the observed OOF economic alignment exceeds what could arise
  from timing luck;
- control family-wise multiplicity across C0-C4.

### Null object

Use each candidate's complete OOF three-state action stream:

- ABSTAIN
- LONG
- SHORT

on the exact common evaluation support.

No model is re-fit under the null.

This is explicitly a temporal-alignment / candidate-multiplicity null, not a
full model-training permutation test.

### Replicates

- repetitions = `1999`
- seed = `20260903`
- plus-one denominator = `2000`

For each replicate and each outer fold:

1. draw one legal nonzero circular shift for that fold;
2. apply the SAME fold shift to all five candidates;
3. circularly shift the full action stream, preserving each candidate's
   abstention/direction sequence and dependence;
4. remap shifted actions to the same ordered common-support timestamps;
5. rerun exact frozen FLAT_ONLY execution and C2 economics.

Legal shift positions:

- minimum absolute circular displacement = 60 common-support positions;
- maximum = n_fold - 60.

If a fold has <=120 common-support positions, canonical execution fails closed.

### Joint max-statistic

For every replicate:

`M_r = max_j mean_C2_net_bps(candidate_j, shifted replicate r)`

across all five candidates.

Frozen q95:

`quantile(M, 0.95, method="higher")`

Candidate-specific FWER p-value:

`p_j = (1 + count(M_r >= observed_mean_C2_j)) / 2000`

A candidate passes the null only if BOTH:

- observed pooled C2 mean net bps > joint max-stat q95;
- FWER p <=0.05.

No candidate may advance without this gate.

## 15. Final eligibility

`DEV042_PREDICTIVE_ELIGIBLE`

requires:

- all 16 absolute economic gates;
- joint max-stat q95 exceedance;
- FWER p <=0.05.

Classification diagnostics cannot rescue a failed economic/null gate.

## 16. Frozen ranking

Among final eligible candidates only:

1. highest minimum fold C2 mean net;
2. highest median fold C2 mean net;
3. highest pooled C2 mean net;
4. highest minimum LOO C2 mean net;
5. highest pooled C2 PF;
6. highest pooled C2 total net;
7. lower complexity:
   C0 < C1 < C2 < C3 < C4;
8. candidate ID.

Advance exactly one.

If none survives:

`DEV042_NO_PREDICTIVE_SURVIVOR_FOR_H1800_B32`

## 17. Hard anti-rescue

After canonical DEV042 results begin:

- NO sixth model
- NO C grid
- NO HGB tuning
- NO early-stopping change
- NO threshold search
- NO controller search
- NO new feature family
- NO new barrier/horizon
- NO neural rescue
- NO XGBoost/LightGBM rescue
- NO null redesign
- NO gate weakening
- NO other-market rescue

If all five fail, close this H1800/B32 predictive family.

## 18. Stage structure

### DEV042-P0

Feature/schema feasibility only:

- causal buildability
- lookback bounds
- exact feature ordering
- feature-family hashes
- common feature support
- common-support retention
- finite/NaN contracts

NO labels.

NO model fit.

NO economic output.

### DEV042-P1

Feature materialization implementation + synthetic/unit CI.

Still no canonical predictive scoring.

### DEV042-P2

No-result real-data feature/support preflight.

Label construction may be mechanically verified only without displaying class
prevalence or candidate results.

### DEV042-P3

Exactly one canonical five-candidate OOF predictive/economic/null screen.

From canonical P3 start:

`DEV042-P3 MUST NEVER BE RERUN`

## 19. Current state

`DEV042_DESIGN_V2_GUARDS_FROZEN_P0_FEATURE_SCHEMA_AUDIT_NEXT`
