# DEV034-G3 — Layered Opportunity/Volatility Context Group Design v1

Status: `DESIGN_FROZEN_NO_G3_MATERIALIZATION_OR_PREDICTIVE_FIT`

Date: 2026-09-02

Permanent governance:
`docs/LAYERED_STRATEGY_SEARCH_GOVERNANCE.md`

## 1. Layered-search position

The frozen direction-stage base remains:

`DEV030-P3 A / 120s / 16bp / 32s / PRICE / S1`

DEV033-G2B-R1 tested 24 raw-temporal microstructure additions on top of this
base and ended:

`DEV033_G2B_R1_FROZEN_VERIFIED_ALL_24_REJECTED_NO_SURVIVOR`

Therefore:

- P3 remains unchanged;
- no G2 failure is promoted;
- no G2 refinement is permitted;
- Group-3 must be scientifically distinct.

## 2. Why opportunity/volatility context is Group-3

The strongest independently confirmed upstream signal in the project is the
prospective opportunity-ranking mechanism:

`EXP024-P1 = PASS_PROSPECTIVE_VOLATILITY_RANKING_CONFIRMED`

Its single legitimate feature was:

`rv_30m_bps`

on the same BTCUSDT Jan-Jul Phase0DL historical lineage later used by the
DEV030 development program.

EXP024-P1 proved opportunity ranking, not direction.

DEV034-G3 therefore asks a new layered question:

> Does causal longer-horizon opportunity/volatility market state add stable
> direction-given-touch information on top of the frozen P3 short-horizon
> PRICE32 direction success?

This is a composition of a successful direction base with an independently
successful upstream information family. It does not use any failed G2 layer.

## 3. Frozen historical input

Only the already-consumed Jan-Jul 2026 BTCUSDT finalized Phase0DL 250 ms files:

`/home/emadh/Multi-Market/evidence/v23/phase0dl_features250/BTCUSDT/`

No acquisition.

No August.

No Sep-01+.

No Railway/archive access.

The exact R-feature formulas are inherited from:

`src/multimarket/codex_exp004_p1.py`

No feature formula is invented after observing G2 results.

## 4. Frozen R-feature universe

The exact pre-existing `R_FEATURE_NAMES` universe contains 22 causal fields:

### Signed returns

- ret_1m_bps
- ret_3m_bps
- ret_5m_bps
- ret_10m_bps
- ret_30m_bps

### Absolute returns

- abs_ret_1m_bps
- abs_ret_3m_bps
- abs_ret_5m_bps
- abs_ret_10m_bps
- abs_ret_30m_bps

### Realized volatility

- rv_5m_bps
- rv_15m_bps
- rv_30m_bps

### Spread regime

- spread_bps
- spread_mean_1m_bps
- spread_mean_5m_bps

### Range state

- range_5m_bps
- range_15m_bps
- range_30m_bps

### Range position

- range_position_5m
- range_position_15m
- range_position_30m

All definitions, validity rules, exact-minute sampling, and no-interpolation
semantics are inherited unchanged from the frozen EXP004/EXP022/EXP024
lineage.

## 5. Exact Group-3 candidate count

Exactly 16 primary candidates.

Every candidate is:

`P3 PRICE32 S1 base + one frozen R-context block`

No candidate is evaluated standalone.

### G3C01 — EXACT_EXP024_RV30

Features:

- rv_30m_bps

This is the exact information variable prospectively confirmed by EXP024-P1.

### G3C02 — RV_TERM_STRUCTURE

Features:

- rv_5m_bps
- rv_15m_bps
- rv_30m_bps

### G3C03 — ABS_RETURN_TERM_STRUCTURE

Features:

- abs_ret_1m_bps
- abs_ret_3m_bps
- abs_ret_5m_bps
- abs_ret_10m_bps
- abs_ret_30m_bps

### G3C04 — SIGNED_RETURN_TERM_STRUCTURE

Features:

- ret_1m_bps
- ret_3m_bps
- ret_5m_bps
- ret_10m_bps
- ret_30m_bps

### G3C05 — SPREAD_REGIME

Features:

- spread_bps
- spread_mean_1m_bps
- spread_mean_5m_bps

### G3C06 — RANGE_TERM_STRUCTURE

Features:

- range_5m_bps
- range_15m_bps
- range_30m_bps

### G3C07 — RANGE_POSITION_TERM_STRUCTURE

Features:

- range_position_5m
- range_position_15m
- range_position_30m

### G3C08 — SHORT_VOLATILITY_STATE

Features:

- abs_ret_1m_bps
- abs_ret_3m_bps
- abs_ret_5m_bps
- rv_5m_bps
- range_5m_bps

### G3C09 — MEDIUM_VOLATILITY_STATE

Features:

- abs_ret_5m_bps
- abs_ret_10m_bps
- rv_15m_bps
- range_15m_bps

### G3C10 — LONG_VOLATILITY_STATE

Features:

- abs_ret_10m_bps
- abs_ret_30m_bps
- rv_30m_bps
- range_30m_bps

### G3C11 — SIGNED_PLUS_ABSOLUTE_RETURN_STATE

Features:

all five signed-return fields plus all five absolute-return fields.

### G3C12 — VOLATILITY_PLUS_RANGE_STATE

Features:

- rv_5m_bps
- rv_15m_bps
- rv_30m_bps
- range_5m_bps
- range_15m_bps
- range_30m_bps

### G3C13 — OPPORTUNITY_REGIME_CORE

Features:

- rv_30m_bps
- abs_ret_30m_bps
- range_30m_bps
- spread_mean_5m_bps

### G3C14 — MAGNITUDE_CONTEXT

Features:

all five absolute-return fields,
all three realized-volatility fields,
all three range fields.

Total = 11.

### G3C15 — UNSIGNED_FULL_R_CONTEXT

Features:

all R fields except the five signed-return fields.

Total = 17.

### G3C16 — FULL_FROZEN_R_CONTEXT

All 22 frozen R_FEATURE_NAMES.

Candidate order is immutable.

## 6. Stage split

### DEV034-G3A — exact context materialization only

Before any G3 predictive fit:

- reconstruct exact P3 support timestamps/labels;
- exact-join those timestamps to the frozen Phase0DL FEATURES250 files;
- materialize all 16 context blocks;
- verify every required R feature is valid and finite;
- no support shrink;
- verify the exact `rv_30m_bps` values against the frozen EXP022/EXP024
  historical helper semantics where technically possible;
- store daily and campaign hashes;
- no direction model fit;
- no direction metric;
- no null;
- no PnL.

If any P3 support timestamp lacks a required causal R context field, G3A fails
closed rather than deleting the row.

### DEV034-G3B — incremental direction screen

Only after G3A is frozen and read-only verified.

## 7. Candidate construction for G3B

For every candidate:

`X_candidate = concatenate([X_P3_PRICE32_S1, X_G3A_context_block])`

P3 base feature order first.

Context feature order exactly as listed in this design.

No PCA/SVD.

No feature subset search.

No interaction expansion.

No additional opportunity model is fit in G3.

This intentionally tests information value before policy gating.

## 8. P3 reproduction gate

Before interpreting any G3 candidate, reproduce frozen P3 exactly using the
same contract as DEV033-G2B-R1:

- 23 base features
- fold supports 159 / 64 / 126 / 224
- C values 10.0 / 10.0 / 0.1 / 0.01
- four exact frozen prediction hashes
- pooled BA within frozen tolerance

Any mismatch invalidates G3B before candidate interpretation.

## 9. Model lineage

Same P3 model lineage:

- train-only StandardScaler
- L2 LogisticRegression
- solver = lbfgs
- l1_ratio = 0.0
- class_weight = None
- max_iter = 1000
- fit_intercept = True
- random_state = 20260825

C grid:

`0.01, 0.1, 1.0, 10.0`

Same chronological inner C-selection:

1. max balanced accuracy
2. max macro F1
3. min C

No model-family multiplication.

## 10. Primary endpoint

Primary:

`delta_BA = pooled_BA(candidate) - pooled_BA(P3)`

Also report:

- pooled macro F1
- MCC
- ROC AUC diagnostic
- four fold BAs
- four fold delta_BA
- positive fold count
- four LOO pooled delta_BA values
- all-LOO-positive
- both classes predicted in every fold
- predicted minority fraction
- minimum/median fold delta

## 11. Joint temporal null

Exactly:

- seed = 20260902
- 1999 replicates
- exactly 16 candidates jointly controlled

Per replicate:

- one legal circular shift in each validation fold;
- same four shifts applied to P3 and all 16 candidates;
- fitted predictions fixed;
- statistic = shifted BA(candidate) - shifted BA(P3);
- retain all 16 candidate-specific null values;
- retain max across 16.

Artifact MUST serialize:

- all 1999 shift tuples
- all 16 candidate-specific null vectors
- max-stat null vector
- raw plus-one p
- max-stat FWER plus-one p
- max-stat q95
- observed-minus-q95

## 12. Strong G3 survivor gate

A candidate is `G3_LAYER_SURVIVOR` only if ALL:

1. pooled BA(candidate) > pooled BA(P3)
2. pooled BA(candidate) >= 0.54
3. pooled delta_BA >= +0.02
4. >=3/4 fold delta_BA positive
5. >=3/4 candidate fold BA > 0.50
6. both classes predicted in every fold
7. pooled predicted-minority fraction >= 0.10
8. all four LOO pooled delta_BA values > 0
9. observed delta_BA > joint 16-candidate max-stat q95
10. max-stat FWER p <= 0.05
11. all provenance/support/finiteness/reproduction guards PASS

## 13. Inconclusive / rejected

`G3_LAYER_INCONCLUSIVE` only if:

- pooled delta_BA > 0
- >=3/4 positive fold deltas
- all four LOO deltas > 0

but one or more strong-survivor gates fail.

Otherwise:

`G3_LAYER_REJECTED`.

Only a true survivor may change the frozen direction base.

## 14. Advancement

At most three candidates may advance.

Highly overlapping candidate blocks are not automatically concatenated.

If multiple overlapping blocks survive, the frozen leaderboard selects the
representative by:

1. smaller FWER p
2. larger minimum fold delta
3. larger median fold delta
4. larger pooled delta
5. fewer added features
6. candidate ID

Any union/composition of multiple G3 survivors requires a separately frozen
next experiment.

## 15. Stop rule

If zero G3 survivors:

- DEV030-P3 remains unchanged;
- no G3 failure/inconclusive is promoted;
- do not refine the best G3 failure;
- move to the next scientifically distinct group.

If one or more G3 survivors:

- only true survivors may define the next successful direction base;
- no forward holdout yet;
- composition of survivors is separately preregistered.

## 16. Forward/economic guards

Remain closed:

- Aug-01 new analysis
- Aug-30 reuse
- Sep-01+
- Railway
- market-raw-archive
- abundant-love
- new acquisition/download
- PnL
- threshold optimization
- calibration rescue
- feature subset search
- alternate model family

Current state:

`DEV034_G3_DESIGN_FROZEN_G3A_IMPLEMENTATION_NEXT_NO_MODEL_FIT`
