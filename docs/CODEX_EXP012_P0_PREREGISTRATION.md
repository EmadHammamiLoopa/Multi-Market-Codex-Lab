# CODEX-EXP-012-P0 Preregistration

Status: **PREREGISTERED BEFORE ANY EXP012 SEGMENTED-FLOW OUTPUT**

Date: 2026-08-26

Experiment ID: `CODEX-EXP-012-P0`

Parent frozen result commit:

`019bcfc85a2e5ffe2bfd38204a033c533b332dad`

Parent result:

`CODEX-EXP-011-P1 = FAIL_BTC_OPTIONS_TRADE_FLOW_NO_INCREMENTAL_TIMING_INFORMATION`

## Scientific question

Can the already-frozen BTC Deribit option-trade data and frozen BTCUSDT Phase-L market data causally and completely construct a preregistered **moneyness × maturity segmented options-flow representation** on the same one-minute decision grid used by EXP011, without imputation, future information, or new data acquisition?

This is a data/feature-readiness audit only.

It does **not** score the opportunity target, fit a predictive model, compute AUC/AP, predict direction, or compute trading PnL.

## Motivation and separation from EXP011

EXP011 tested aggregate BTC option flow pooled across all eligible strikes and expiries and failed to establish incremental 10-minute opportunity-timing information beyond R.

EXP012 tests a materially different representation: whether flow can be separated into economically interpretable regions of the option surface by moneyness and time to maturity.

EXP012 does not rescue or alter EXP011. EXP011 remains a frozen valid failure.

## Frozen inputs

No network access or acquisition is allowed.

Use only the immutable option-trade raw files already preserved from EXP009:

- 2026-03-01 SHA-256 `34835b3e3a022fac0e7270b3e1aca643b01e63b3bbffdab50c99c70dea9af6ba`
- 2026-04-01 SHA-256 `175b24f76bceb68b68c8b6caa04682cb4523bc2e5becc39c41fcf92456a1b605`
- 2026-05-01 SHA-256 `287aaf1a1c62b597c1d46f9f408eef9a0d7c1a73d47ef9edb809f9dc53adda78`
- 2026-06-01 SHA-256 `6076038bb1c07ed4e70a5ca696e04213a5e7e9ab9bfa835360764901925fc6a7`
- 2026-07-01 SHA-256 `02be481f94ac9b66dd43c9f185488b0c2af8f0517f7538d30c6dea565f866bc2`

Use the existing frozen BTCUSDT Phase-L `FEATURES250` file for each corresponding day only.

EXP011 result artifact must remain unchanged and its SHA-256 must equal:

`ba203504d413c59a6ac09cc4f622d7c10554bd62c34b8eb0736202d27c917826`

## Frozen dates and symbol

Only BTCUSDT paired with BTC options on:

- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

August remains sealed.

ETH is not part of EXP012.

## Decision grid

Exactly the EXP011 grid:

- 00:30 UTC through 23:49 UTC inclusive;
- one decision per minute;
- 1,400 decision minutes per day.

## Causal underlying reference

Each option trade must be classified using a BTCUSDT underlying reference available **strictly before that option trade became locally available**.

For option trade local timestamp `u`, define `S(u)` as the BTCUSDT Phase-L `mid` at the greatest Phase-L timestamp `s` satisfying:

`s < u`.

The Phase-L grid is 250 ms.

The Phase-L row at exactly `u` is not usable for classifying a trade timestamped `u`.

`S(u)` must be finite and strictly positive and the corresponding Phase-L book row must be valid.

No future or equal-time market row may classify an option trade.

No external spot/index/perpetual price may replace missing Phase-L support.

## Option universe

Accept the same BTC vanilla option families validated in EXP010/EXP011:

1. standard/inverse symbols such as `BTC-27MAR26-100000-C`;
2. USDC-linear symbols such as `BTC_USDC-27MAR26-100000-C`.

Reject non-BTC, perpetual, future, combo, malformed, or non-vanilla symbols.

The frozen raw files must remain nondecreasing in `local_timestamp`, preserve valid trade IDs, valid aggressor side (`buy`/`sell`), positive finite amount, and positive finite price.

## Frozen moneyness definition

For strike `K` and causal underlying `S(u)`, define:

`m = log(K / S(u))`.

Use exact fixed boundaries:

### ATM

`abs(m) <= 0.025`

### OTM call

call option and:

`m > 0.025`

### OTM put

put option and:

`m < -0.025`

Vanilla trades not satisfying one of those three categories are classified as `other_moneyness` and are not used in the future segmented feature block.

The ±2.5% boundary may not be changed after this preregistration.

## Frozen maturity definition

At option trade local timestamp `u`, define:

`DTE = (expiration_timestamp - u) / 86,400,000,000`

using microseconds.

A trade with `DTE <= 0` is invalid.

Eligible maturity buckets:

### Short

`0 < DTE <= 7`

### Medium

`7 < DTE <= 30`

Trades with `DTE > 30` are classified as `longer_than_30d` and are not used in the future segmented feature block.

The 7-day and 30-day boundaries may not be changed under EXP012.

## Frozen six surface segments

Exactly six segments are allowed:

1. `atm_short`
2. `atm_medium`
3. `otm_call_short`
4. `otm_call_medium`
5. `otm_put_short`
6. `otm_put_medium`

No strike interpolation, delta estimation, implied-volatility estimation, option pricing model, or surface fit is used.

## Flow windows

Exactly the EXP011 windows:

- 1 minute
- 5 minutes
- 15 minutes
- 30 minutes

For decision time `t`, every option trade used in a window must satisfy:

`t - W <= local_timestamp < t`.

A trade timestamped at `t` is never usable at `t`.

No lookback longer than 30 minutes is allowed.

## Zero-flow semantics

EXP012 does **not** require each of the six surface segments to contain a trade in every window.

If the overall eligible BTC option-flow window contains at least one valid BTC option trade but a particular segment contains zero trades, that segment's count and amount are valid zeros.

This is a structural zero, not missing data, and must not be imputed.

A decision is unsupported only if the complete 1-minute aggregate BTC option-flow window contains no eligible valid BTC option trade, or if causal classification/integrity fails.

## P0 constructability outputs

For each date report:

- total raw rows;
- valid BTC vanilla option trades;
- trades with causal Phase-L underlying reference;
- trades rejected for missing/invalid causal reference;
- counts by option family;
- counts by moneyness bucket;
- counts by maturity bucket;
- counts in each of the six frozen surface segments;
- counts outside the six eligible segments;
- number and fraction of the 1,400 decision minutes with complete segmented-flow constructability;
- longest consecutive constructable run;
- causal-reference age distribution in milliseconds (minimum, median, p95, maximum);
- integrity errors, duplicate conflicts, outside-day rows, and parse errors.

## Frozen readiness gates

Every one of the five days must satisfy all gates:

1. all expected option raw hashes match;
2. EXP011 result SHA-256 matches;
3. Phase-L data are present and structurally valid;
4. no August access;
5. no network access;
6. no target/model/AUC/direction/PnL activity;
7. zero eligible BTC parse errors;
8. zero conflicting trade IDs;
9. zero outside-requested-day rows;
10. every valid BTC vanilla trade used for segmentation has a strictly earlier valid Phase-L underlying reference;
11. at least 1,120 of 1,400 decision minutes (80%) are constructable under the frozen aggregate 1-minute-support rule;
12. longest consecutive constructable run is at least 120 minutes;
13. at least one trade exists in each of the six frozen surface segments during the day.

Gate 13 is a day-level existence sanity check only. It does not require every segment to trade every minute.

## PASS

`DATA_READY_SEGMENTED_BTC_OPTIONS_FLOW_SANDBOX`

All five dates and all invariants pass.

This authorizes a separately preregistered predictive EXP012-P1 or later Experiment ID using only the frozen segmented representation.

It does not establish predictability.

## FAIL

`FAIL_SEGMENTED_BTC_OPTIONS_FLOW_DATA_NOT_READY`

At least one frozen readiness gate fails while protocol integrity remains intact.

A valid P0 failure cannot be repaired under the same Experiment ID by changing moneyness boundaries, maturity buckets, support thresholds, or segment definitions.

## INVALID

Any future/equal-time underlying reference, August access, raw-hash mismatch, target/model/AUC/direction/PnL activity, or material protocol/implementation violation produces `INVALID` rather than PASS/FAIL.

## No-rescue rule

After EXP012-P0 output is opened, do not:

- widen ATM beyond ±2.5%;
- change 7d or 30d maturity cutoffs;
- remove a sparse segment;
- add trade-size buckets;
- add delta, gamma, IV, or option-price features;
- alter the 1/5/15/30m windows;
- reduce the 80% or 120-minute support gates;
- change BTC-only scope;
- use another source to fill missing information.

Any such materially new hypothesis requires a new Experiment ID and preregistration.