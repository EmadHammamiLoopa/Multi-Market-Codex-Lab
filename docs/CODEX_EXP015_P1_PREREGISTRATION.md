# CODEX-EXP-015-P1 Preregistration

Status: **PREREGISTERED BEFORE ANY EXP015 TARGET/MODEL/AUC OUTPUT**

Date: 2026-08-26

Experiment ID: `CODEX-EXP-015-P1`

Parent preserved commit:

`7bb69fc43fe47181f92a7d9f6ed2b510a180e25c`

Parent readiness result:

`CODEX-EXP-014-P0 = DATA_READY_CORRECTED_EXPIRY_SEGMENTED_BTC_OPTIONS_FLOW_SANDBOX`

Frozen parent artifact:

`evidence/codex/exp014_p0_exp013_artifact_adjudication/EXP013_ARTIFACT_ADJUDICATION_P0.json`

Parent artifact SHA-256:

`ff67b0ffddd60e54cf95ecc1ed0f445574b4ed1a9c757287abd543871fea61ff`

Frozen corrected-expiry source artifact:

`evidence/codex/exp013_p0_corrected_expiry_segmented_options_flow/CORRECTED_EXPIRY_SEGMENTED_OPTIONS_FLOW_P0_AUDIT.json`

Corrected-expiry source SHA-256:

`fa590862c00d207917e720e0157db495b67cbf3209bac6301f3568008ac0ce4b`

## Scientific question

> Does causally available, moneyness × maturity segmented BTC Deribit options trade flow add stable incremental information about the timing of the frozen 10-minute >=24 bp executable-opportunity target beyond the existing BTC regime baseline R?

EXP015 is the predictive follow-up authorized by EXP014 structural readiness.

It tests only incremental opportunity-timing information.

It does not predict direction.

It does not compute trading PnL.

It does not open sealed August.

## Why EXP015 is distinct from EXP011

EXP011 tested a 24-feature aggregate BTC option-flow block pooled across strikes and maturities and failed to establish incremental timing information.

EXP015 changes only the option-flow representation to the structurally validated segmentation from EXP013/EXP014.

The target, baseline R, outer folds, model family, training protocol, controls, falsification track, and promotion gates remain aligned with EXP011.

EXP011 remains a frozen valid failure and is not relabeled or rescued.

## Frozen target market

Only:

`BTCUSDT`

No ETH and no other market.

## Frozen supervised dates

Only:

- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

Outer walk-forward test folds:

- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

For each outer fold, training uses all strictly earlier supervised days.

No August file may be accessed.

## Frozen target and horizon

Use exactly the same executable-opportunity target as EXP011:

At decision time `t`:

- reaction/entry = `t + 250 ms`
- exit = entry + 600 seconds
- long gross bps = `10000 * log(bid_exit / ask_entry)`
- short gross bps = `10000 * log(bid_entry / ask_exit)`
- oracle gross bps = `max(long_gross_bps, short_gross_bps)`
- binary target = `1[oracle_gross_bps >= 24]`

The oracle direction and gross bps are available only to label construction and the positive-control canary.

Direction is hidden from all legitimate predictive tracks.

## Frozen baseline R

Use exactly the existing EXP004/EXP011 R feature block and causal pipeline.

No baseline feature is added, removed, or retuned.

## Frozen option raw inputs

Use only the already-preserved Deribit option trade files:

- 2026-03-01 SHA-256 `34835b3e3a022fac0e7270b3e1aca643b01e63b3bbffdab50c99c70dea9af6ba`
- 2026-04-01 SHA-256 `175b24f76bceb68b68c8b6caa04682cb4523bc2e5becc39c41fcf92456a1b605`
- 2026-05-01 SHA-256 `287aaf1a1c62b597c1d46f9f408eef9a0d7c1a73d47ef9edb809f9dc53adda78`
- 2026-06-01 SHA-256 `6076038bb1c07ed4e70a5ca696e04213a5e7e9ab9bfa835360764901925fc6a7`
- 2026-07-01 SHA-256 `02be481f94ac9b66dd43c9f185488b0c2af8f0517f7538d30c6dea565f866bc2`

No network acquisition is allowed.

## Frozen option universe and expiry semantics

Eligible BTC vanilla options only:

- standard/inverse BTC options
- BTC_USDC linear options
- calls and puts
- no futures
- no perpetuals
- no combos
- no ETH
- no malformed instruments

Deribit option expiry timestamp is frozen at:

`YYYY-MM-DD 08:00:00 UTC`

## Frozen causal moneyness reference

For each option trade with local timestamp `u`, use BTCUSDT Phase-L `mid` from the greatest Phase-L timestamp `s` satisfying:

`s < u`

Equal-time or future Phase-L references are forbidden.

The reference row must have:

- valid book
- finite positive mid

No external underlying source is allowed.

## Frozen segmentation

Let:

`m = log(K / S(u))`

Moneyness buckets:

- ATM if `|m| <= 0.025`
- OTM call if call and `m > 0.025`
- OTM put if put and `m < -0.025`
- other/ITM moneyness excluded from the six predictive segments

The numerical equality tolerance remains exactly `1e-12` only for floating-point reconstruction at the ±0.025 boundary.

Maturity uses corrected 08:00 UTC expiry:

- short: `0 < DTE <= 7 days`
- medium: `7 < DTE <= 30 days`
- >30 days excluded from the six predictive segments

Exactly six segments:

1. `atm_short`
2. `atm_medium`
3. `otm_call_short`
4. `otm_call_medium`
5. `otm_put_short`
6. `otm_put_medium`

## Frozen decision grid and flow windows

Decision grid:

- one-minute spacing
- 00:30 through 23:49 UTC
- 1400 candidate decisions/day before common-support filtering

Flow windows:

- 1 minute
- 5 minutes
- 15 minutes
- 30 minutes

Each window is causal:

`[t-W, t)`

A trade exactly at `t` is excluded.

## Frozen segmented flow feature block F

For each of 4 windows and each of 6 segments, compute exactly 4 metrics:

1. `log1p_trade_count`
2. `log1p_amount`
3. `aggressor_amount_imbalance`
4. `abs_aggressor_amount_imbalance`

where:

`aggressor_amount_imbalance = (buy_amount - sell_amount) / (buy_amount + sell_amount)`

when that segment has positive amount in the window.

If an individual segment has no trades in the window, all four metrics for that segment are exactly zero.

This zero is frozen as structural no-flow information and is not missing-data imputation.

Total F dimensionality:

`4 windows × 6 segments × 4 metrics = 96 features`

No call-put imbalance feature is included because OTM call and OTM put are already separate segments; adding call-put imbalance inside those segments would be deterministic/redundant.

No IV, delta, gamma, vega, option-pricing-model output, trade-size bucket, time-of-day interaction, or additional feature may be added under EXP015.

## Frozen common support

A decision is eligible only when:

1. the frozen R baseline is valid;
2. the decision is on the frozen 00:30–23:49 grid;
3. the aggregate eligible BTC vanilla option universe has at least one valid trade in the causal 1-minute window `[t-1m, t)`;
4. all option trades used for segmentation have valid strictly-earlier Phase-L underlying references.

Because the larger windows are nested, the 1-minute aggregate support condition is the support gate for the segmented F block.

Zero flow in any individual segment is allowed and encoded as structural zeros.

The exact same common-support rows must be used for R, F, RF, VOL, RF_F_TIME_PERMUTED, and CANARY_R outer evaluation.

## Frozen predictive tracks

Score exactly:

- `R`: existing regime baseline
- `F`: 96-feature segmented option-flow block only
- `RF`: R + segmented F
- `VOL`: same single R volatility diagnostic used by EXP011
- `RF_F_TIME_PERMUTED`: R plus time-permuted complete segmented F vector
- `CANARY_R`: R plus oracle gross bps positive-control canary

VOL is diagnostic only and cannot replace R after results are observed.

CANARY_R is a positive control and cannot be promoted as a legitimate model.

## Frozen model

Use the same fixed logistic model as EXP011:

- logistic regression
- `C = 1.0`
- solver = `lbfgs`
- class_weight = none
- max_iter = 1000
- scaling fit on training data only by the existing fixed pipeline
- seed = `20260825`

No hyperparameter tuning.

No threshold tuning.

No feature selection after output.

## Frozen permutation falsification

For `RF_F_TIME_PERMUTED`:

- permute the complete 96-dimensional F vector as a block
- independently within each BTC day
- train-day F vectors are permuted only within their own day
- outer-test-day F vectors are permuted only within the outer day
- R remains unpermuted
- labels remain unpermuted
- use deterministic seed derived from the same frozen seed/day mechanism as EXP011

## Frozen metrics

For each legitimate/control track compute the same EXP011 metrics:

- ROC AUC
- average precision
- Brier score
- log loss
- top-decile precision

Report:

- pooled outer-test
- each outer fold
- pooled non-overlapping 10-minute decisions

## Frozen promotion gates

All of the following must pass, using exactly the same thresholds as EXP011:

1. pooled RF AUC - R AUC >= 0.01
2. pooled RF average precision - R average precision >= 0.01
3. pooled RF top-decile precision >= R
4. pooled RF log loss < R
5. pooled RF Brier score < R
6. RF AUC > R in at least 3 of 4 outer folds
7. pooled RF AUC >= 0.60
8. non-overlap RF AUC - R AUC >= 0.01
9. non-overlap RF AUC >= 0.57
10. pooled RF AUC - RF_F_TIME_PERMUTED AUC >= 0.01
11. CANARY_R AUC - R AUC >= 0.10
12. all implementation/provenance/causality invariants pass

PASS only if every gate passes.

PASS status:

`PREDICTABLE_INCREMENTAL_SEGMENTED_BTC_OPTIONS_FLOW_SANDBOX`

Otherwise, with valid execution:

`FAIL_SEGMENTED_BTC_OPTIONS_FLOW_NO_INCREMENTAL_TIMING_INFORMATION`

Any leakage, provenance, causality, hash, common-support, fold, expiry, or implementation invariant failure:

`INVALID`

## Scientific guards

Must remain:

- sealed August opened = false
- direction scored = false
- PnL scored = false

No direction or PnL experiment is authorized unless EXP015 first passes the full opportunity-timing gate set.

## No-rescue rule

After EXP015 output exists, do not:

- change any segment
- change ±0.025 moneyness boundary
- change 7/30-day maturity boundaries
- change corrected 08:00 UTC expiry
- change any window
- change the 96-feature family
- add/remove a feature
- alter common support
- alter target
- alter model or regularization
- alter folds
- alter permutation
- alter gates
- remove a month
- access August
- score direction or PnL

Any materially different hypothesis requires a new Experiment ID.
