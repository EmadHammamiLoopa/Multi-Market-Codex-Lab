# CODEX-EXP-010-P0 Preregistration — Unified Deribit Options Trade-Flow Readiness

## Scientific status

New Experiment ID. This experiment is not a rescue or modification of CODEX-EXP-009-P0, which remains frozen as `FAIL_OPTIONS_TRADE_FLOW_DATA_NOT_READY`.

## Question

When the Deribit BTC/ETH options universe is defined to include both the standard inverse option symbols and the official USDC-linear option symbols present in the already-frozen Tardis `trades/OPTIONS` files, is causal options trade-flow structurally available at the preregistered 1m/5m/15m/30m windows for both BTC and ETH across all five sandbox dates?

## Data provenance

Reuse only the immutable raw files preserved by CODEX-EXP-009-P0:

- 2026-03-01 SHA-256 `34835b3e3a022fac0e7270b3e1aca643b01e63b3bbffdab50c99c70dea9af6ba`
- 2026-04-01 SHA-256 `175b24f76bceb68b68c8b6caa04682cb4523bc2e5becc39c41fcf92456a1b605`
- 2026-05-01 SHA-256 `287aaf1a1c62b597c1d46f9f408eef9a0d7c1a73d47ef9edb809f9dc53adda78`
- 2026-06-01 SHA-256 `6076038bb1c07ed4e70a5ca696e04213a5e7e9ab9bfa835360764901925fc6a7`
- 2026-07-01 SHA-256 `02be481f94ac9b66dd43c9f185488b0c2af8f0517f7538d30c6dea565f866bc2`

No network acquisition is permitted under EXP010-P0.

## Frozen universe

BTC options:

- inverse/standard family: `BTC-<expiry>-<strike>-C/P` or underscore-equivalent separators accepted by the frozen parser;
- USDC-linear family: `BTC_USDC-<expiry>-<strike>-C/P`.

ETH options:

- inverse/standard family: `ETH-<expiry>-<strike>-C/P` or underscore-equivalent separators accepted by the frozen parser;
- USDC-linear family: `ETH_USDC-<expiry>-<strike>-C/P`.

No SOL, other underlying, combo instrument, perpetual, future, or non-option row is eligible.

## Causal clock

At decision minute `t`, a trade is usable only if `local_timestamp < t`.

No future trade, forward fill, interpolation, or data from another day is allowed.

## Frozen windows

Exactly:

- 1 minute
- 5 minutes
- 15 minutes
- 30 minutes

A window is structurally supported at `t` when at least one eligible positive-amount trade exists in `[t-window, t)`.

The P0 readiness calculation is presence/support only. It does not score a target or fit a model.

## Frozen decision grid

For each frozen date:

- 00:30 UTC through 23:49 UTC inclusive;
- 1-minute cadence;
- exactly 1400 decision minutes.

## Readiness gates

For each of the ten currency-days independently:

1. complete support across all four windows on at least 1120/1400 minutes (80%);
2. at least one consecutive run of 120 minutes with complete support.

All ten currency-days must satisfy both gates for:

`DATA_READY_UNIFIED_OPTIONS_TRADE_FLOW_SANDBOX`

Otherwise:

`FAIL_UNIFIED_OPTIONS_TRADE_FLOW_DATA_NOT_READY`

## Integrity gates

- exact frozen raw hashes must match;
- local timestamps nondecreasing;
- no rows outside requested source day;
- no conflicting duplicate trade IDs;
- eligible BTC/ETH option rows must have parseable timestamp, local_timestamp, id, side, positive finite price, and positive finite amount;
- standard and USDC-linear families are counted separately in diagnostics;
- raw source bytes are immutable.

## Prohibited under EXP010-P0

- no August data;
- no future returns;
- no opportunity target;
- no model fit;
- no AUC/AP/Brier/log-loss;
- no direction score;
- no PnL;
- no changing the 1m/5m/15m/30m windows;
- no changing the 80% or 120-minute gates after the result;
- no dropping ETH after the result;
- no predictive scoring under this P0.

A PASS only authorizes a separately preregistered predictive experiment. It is not evidence of predictability or profitability.
