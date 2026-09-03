# DEV042 — H1800/B32 Predictive Family Screen

Status:

`DESIGN_FROZEN_BEFORE_ANY_DEV042_REAL_PREDICTIVE_RESULT`

Date: 2026-09-03

## 1. Frozen parent geometry

DEV041 survivor:

`H1800_B32`

Meaning:

- vertical horizon = 1800 seconds
- executable barrier = 32 bps
- entry latency = 250 ms
- response latency = 250 ms

DEV041 canonical artifact identity:

- path:
  `/home/emadh/Multi-Market/evidence/dev041_p2_model_free_headroom_v1/DEV041_P2_MODEL_FREE_HEADROOM_RESULT.json`
- bytes = `429239`
- SHA256 =
  `542117791966f9049cb49e5b578d7857b3e1178f44be83172c7edfac56244a15`

DEV041 MUST NEVER BE RERUN.

No second target-geometry grid is permitted.

## 2. Data boundary

Development data:

- BTCUSDT only
- Jan-Jul 2026 consumed first-day lineage only

Outer evaluation folds:

- train Jan-Mar -> evaluate Apr
- train Jan-Apr -> evaluate May
- train Jan-May -> evaluate Jun
- train Jan-Jun -> evaluate Jul

All feature construction must be causal at the exact decision timestamp.

Forbidden:

- Sep-01+
- ETH
- SOL
- every other market
- forward-bucket analytics

## 3. Prediction target

Exactly three classes:

- LONG_FIRST
- SHORT_FIRST
- NONE

using the frozen H1800/B32 executable first-passage semantics.

Ambiguous and invalid rows are excluded from model support.

No label definition may change after results.

## 4. Deployable action rule

For every candidate:

- predict class probabilities for LONG_FIRST, SHORT_FIRST, NONE;
- if NONE has the largest probability -> ABSTAIN;
- otherwise act in the higher-probability direction;
- ties -> ABSTAIN.

No probability threshold search.

No quantile threshold search.

No controller/window search.

This is intentionally simple to avoid converting DEV042 into another policy
optimization exercise.

## 5. Deployable trade semantics

When an action is taken:

### Entry

- decision time t
- executable entry at t + 250 ms
- LONG buys ask
- SHORT sells bid

### Exit

The trade watches BOTH executable 32-bp barriers for up to 1800 seconds.

For a predicted LONG:

- +32 bps executable LONG barrier first -> TP event;
- -32 bps executable opposite barrier first -> SL event.

For a predicted SHORT:

- +32 bps executable SHORT barrier first -> TP event;
- opposite +32-bp LONG barrier first -> SL event.

For either TP or SL:

- event timestamp is first executable barrier row;
- fill is NOT assumed at barrier;
- realized exit occurs at event + 250 ms response latency;
- LONG exits bid;
- SHORT exits ask.

If neither barrier occurs before horizon:

- forced exit at entry + 1800 s + 250 ms;
- LONG exits bid;
- SHORT exits ask.

Missing/invalid required exit row:

- trade is execution-invalid;
- canonical candidate fails integrity rather than silently dropping the trade.

## 6. Overlap

Exactly:

`FLAT_ONLY`

Process actions chronologically within each day.

While a trade is open:

- ignore later actions;
- no pyramiding;
- no reversal;
- no concurrent BTC position.

No trade crosses the UTC day boundary.

## 7. Frozen economic envelopes

C1:

- 8 bps round-trip fees
- +1 bp per side slippage
- total explicit deduction = 10 bps

C2 primary:

- 12 bps round-trip fees
- +2 bp per side slippage
- total explicit deduction = 16 bps

Primary ranking/gates use C2.

C1 is secondary diagnostic.

## 8. Feature families

All features are causal and derived only from information at or before the
decision timestamp.

### F0 — PRICE_MOMENTUM

Mandatory baseline.

Includes only price-derived state:

- lagged executable/mid returns at frozen multi-scale windows;
- realized volatility;
- realized absolute movement/range;
- short-vs-long momentum contrasts.

No BOOK, OFI, or trade-flow feature.

### F1 — PRICE_PLUS_OFI

F0 plus directional microstructure flow:

- L1 OFI;
- MLOFI;
- trade quantity imbalance;
- trade count imbalance;
- causal rolling aggregates/means over frozen short/medium windows.

This tests literature-supported incremental OFI information.

### F2 — PRESSURE_CAPACITY

Economically interpretable local state:

- near-touch bid/ask depth;
- depth imbalance;
- trade-flow pressure;
- pressure divided by opposite-side absorption capacity;
- replenishment/depletion imbalance;
- spread;
- microprice displacement;
- liquidity fragility / depth-concentration proxies available from the
  consumed feature lineage.

No price-only baseline features beyond normalization/reference terms required
to construct these variables.

### F3 — COMBINED_LINEAR

Union of F0 + F1 + F2.

### F4 — COMBINED_NONLINEAR

Same exact feature set as F3.

No additional feature engineering.

## 9. Frozen estimators

### F0-F3

Pipeline:

- training-only StandardScaler
- multinomial LogisticRegression
- C = 1.0
- L2 penalty
- max_iter = 3000
- deterministic solver compatible with multinomial classification

No C-grid.

No class-weight grid.

### F4

HistGradientBoostingClassifier:

- learning_rate = 0.05
- max_iter = 200
- max_leaf_nodes = 15
- min_samples_leaf = 20
- l2_regularization = 1.0
- random_state = 20260903

No tree-parameter search.

No XGBoost/LightGBM rescue after results.

## 10. Candidate IDs

Exactly five:

- C0_PRICE_LOGIT
- C1_OFI_LOGIT
- C2_PRESSURE_CAPACITY_LOGIT
- C3_COMBINED_LOGIT
- C4_COMBINED_HGB

This five-candidate universe is frozen.

## 11. Required statistical outputs

Per fold and pooled:

- support rows
- class prevalence
- confusion matrix
- macro F1
- balanced accuracy
- multiclass log loss
- per-class precision/recall
- action coverage
- predicted LONG/SHORT counts
- abstain count

These are diagnostics.

No candidate advances on classification metrics alone.

## 12. Required economic outputs

Per fold and pooled for C1 and C2:

- raw actions
- accepted FLAT_ONLY trades
- ignored overlap actions
- LONG/SHORT trades
- TP / SL / forced-horizon exits
- execution-invalid count
- trades/day
- gross bp/trade
- net bp/trade
- total net bps
- win rate
- profit factor
- max drawdown
- max losing streak
- per-day net bps
- positive days
- exposure
- cumulative net curve

## 13. Hard eligibility gates

A candidate is `DEV042_PREDICTIVE_ELIGIBLE` only if ALL:

1. exact four outer folds completed;
2. zero execution-invalid trades;
3. accepted trades >= 100 pooled;
4. accepted trades on every Apr-Jul fold;
5. LONG trades > 0;
6. SHORT trades > 0;
7. pooled C2 mean net bp/trade > 0;
8. pooled C2 total net bps > 0;
9. pooled C2 PF > 1.05;
10. C2 positive folds >= 3/4;
11. minimum fold C2 mean net bp/trade > -2.0;
12. every leave-one-fold-out C2 mean net bp/trade > 0;
13. pooled C1 mean net bp/trade > 0;
14. pooled C1 total net bps > 0;
15. no single fold contributes > 60% of positive pooled C2 net;
16. action coverage pooled in [0.05, 0.80].

These absolute gates determine whether any new predictive family exists.

## 14. Frozen ranking

Among eligible candidates:

1. highest minimum fold C2 mean net bp/trade;
2. highest median fold C2 mean net bp/trade;
3. highest pooled C2 mean net bp/trade;
4. highest minimum LOO C2 mean net bp/trade;
5. highest pooled C2 PF;
6. highest pooled C2 total net bps;
7. lower model complexity:
   C0 < C1 < C2 < C3 < C4;
8. candidate ID.

Advance exactly one.

If none qualifies:

`DEV042_NO_PREDICTIVE_SURVIVOR_FOR_H1800_B32`

## 15. Interpretation

A DEV042 survivor is a consumed-data OOF predictive/economic survivor.

It is NOT final forward evidence.

No Sep-01+ data may be opened until the complete predictor + execution policy
is frozen.

## 16. Hard anti-rescue

After DEV042 canonical results begin:

- NO sixth candidate
- NO neural model
- NO Transformer
- NO XGBoost
- NO LightGBM
- NO alternate class threshold
- NO quantile controller
- NO alternate barrier
- NO alternate horizon
- NO new feature family
- NO model hyperparameter grid
- NO gate weakening
- NO other-market rescue

If all five fail, this H1800/B32 predictive family closes.

## 17. Stage structure

### DEV042-P0

Feature/schema feasibility audit + implementation design.

No labels/results.

### DEV042-P1

Feature materialization implementation + synthetic/unit CI.

### DEV042-P2

No-result real-data feature/support preflight.

### DEV042-P3

Exactly one canonical five-candidate OOF predictive/economic screen.

From canonical P3 start:

`DEV042-P3 MUST NEVER BE RERUN`

## 18. Current state

`DEV042_H1800_B32_DESIGN_FROZEN_P0_FEATURE_SCHEMA_AUDIT_NEXT`
