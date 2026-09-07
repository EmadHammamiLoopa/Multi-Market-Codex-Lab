# DEV045-D6R25-R1 — Artifact-only economic forensic execution contract

Parent design: `da088950d8602cd6bec681d127050e636d00b2d9`  
Parent D6R24 freeze: `06eff337e4a039cf47c8b10a41aa91e52df4c792`

## Purpose

Decompose the frozen D6R24 loss using only the seven immutable D6R24 day artifacts. This is observational accounting forensics, not a replay, strategy run, fee amendment, or promotion test.

## Input and safety contract

- Input surface: frozen D6R24 day artifacts only.
- One day artifact is loaded at a time; the previous day is discarded before the next.
- Each day file must match the frozen byte count and SHA-256 recorded in the D6R24 freeze metadata before its JSON is interpreted.
- No historical market source is opened or hashed.
- No hftbacktest simulator is started.
- D6R24, D6R23-Q1, D6R22, D6R21 and Q8 are never rerun.
- `run_economic_arena` is never called.
- Frozen Binance fees are never amended.
- No M01-M08 policy is retuned or promoted.
- No live trading, August, September+, or non-BTC access.

## Frozen strata before artifact opening

Cycle type:
- `PURE_MAKER`
- `TAKER_CONTAINING`

Maker-notional share:
- `PURE_MAKER_100`
- `MAKER_90_TO_LT100`
- `MAKER_50_TO_LT90`
- `MAKER_LT50`

Fill count:
- `FILL_2`
- `FILL_3_TO_4`
- `FILL_5_TO_8`
- `FILL_9_PLUS`

Holding time:
- `HOLD_LE_1S`
- `HOLD_GT1_TO_5S`
- `HOLD_GT5_TO_30S`
- `HOLD_GT30S`

Support regime:
- `DIRECT_SUPPORT_ACTIVE` only for M06/M07 on Apr-Jul.
- `NO_DIRECT_SUPPORT` otherwise.

## Core accounting

For each flat-to-flat cycle:

- `gross_bps = 10000 * cash_pnl_before_fees / entry_notional`
- `fee_drag_bps = 10000 * fees / entry_notional`
- `net_bps = 10000 * net_pnl / entry_notional`
- enforce `gross_bps - fee_drag_bps == net_bps` within floating-point tolerance.
- independently reconstruct fee components from frozen maker/taker notionals and frozen scenario fee rates.

Report cycle-mean and entry-notional-weighted gross/fee/net metrics, quantiles, positive-cycle shares, maker/taker notionals, fee components, zero-fee expectancy and uniform fee-multiplier break-even.

Also report the same decomposition by policy, scenario, day, four-hour block, cycle type, maker-share bucket, fill-count bucket, holding-time bucket, and support regime.

## Identifiability limits

The following are explicitly `NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACT`:

- exact forced-flatten PnL attribution;
- exact forced-flatten fee attribution;
- adverse-selection markout;
- spread-capture versus subsequent-price-move decomposition;
- queue-position edge attribution.

`forced_flatten_count` may be reported only as replay context; it is not joined to fills or cycles.

## Decision classes

- If every primary policy has zero-fee gross expectancy <= 0: `ZERO_FEE_GROSS_EDGE_NEGATIVE_POLICY_FAMILY_REJECT`.
- If gross edge is positive but primary net remains negative: `POSITIVE_GROSS_EDGE_FEE_DOMINATED_REDESIGN_EXECUTION_ECONOMICS`.
- Otherwise: `MIXED_BY_POLICY_OR_REGIME_NEW_PREREGISTERED_FAMILY_REQUIRED`.

Any rejection applies only to **M01-M08 quoting family as instantiated**. It is not a claim that market making generally is invalid.

## Next gate

Only after the D6R25-R1 result is frozen may D6R26A formal Generation-2 conditional maker edge design begin.
