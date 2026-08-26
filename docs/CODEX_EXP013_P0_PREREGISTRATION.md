# CODEX-EXP-013-P0 Preregistration

Status: **PREREGISTERED BEFORE ANY EXP013 OUTPUT**

Date: 2026-08-26

Experiment ID: `CODEX-EXP-013-P0`

Parent frozen result commit:

`af3da1b6d453f14a6e85058d15f425cf8d763270`

Parent result:

`CODEX-EXP-012-P0 = INVALID`

Parent invalid artifact SHA-256:

`c30329af81c84a4dc1973c32fcf06a544fb91340aaadedf6ca810d29f18735fe`

## Scientific question

After correcting the Deribit option expiry timestamp from an incorrect midnight interpretation to the exchange-specified **08:00 UTC** expiry time, can the already-frozen BTC Deribit option trades and frozen BTCUSDT Phase-L data causally construct the same preregistered moneyness × maturity segmented options-flow representation on all five March-July sandbox days?

This is a readiness/provenance audit only.

It does **not** score the opportunity target, fit a predictive model, compute AUC/AP, predict direction, or compute PnL.

## Single allowed change from EXP012

EXP012 parsed the date encoded in the option symbol as:

`YYYY-MM-DD 00:00:00 UTC`

That interpretation was incorrect for Deribit options and caused otherwise valid trades between 00:00 and 08:00 UTC on expiry day to be classified as expired.

EXP013 changes only the expiry timestamp interpretation to:

`YYYY-MM-DD 08:00:00 UTC`

No other segmentation threshold, readiness gate, universe rule, raw input, grid, causality rule, or date is changed.

## Frozen inputs

No network acquisition is allowed.

Option-trade raw SHA-256:

- 2026-03-01: `34835b3e3a022fac0e7270b3e1aca643b01e63b3bbffdab50c99c70dea9af6ba`
- 2026-04-01: `175b24f76bceb68b68c8b6caa04682cb4523bc2e5becc39c41fcf92456a1b605`
- 2026-05-01: `287aaf1a1c62b597c1d46f9f408eef9a0d7c1a73d47ef9edb809f9dc53adda78`
- 2026-06-01: `6076038bb1c07ed4e70a5ca696e04213a5e7e9ab9bfa835360764901925fc6a7`
- 2026-07-01: `02be481f94ac9b66dd43c9f185488b0c2af8f0517f7538d30c6dea565f866bc2`

Use the same frozen BTCUSDT Phase-L FEATURES250 files for the corresponding days.

The frozen EXP012 invalid artifact must be present unchanged with SHA-256:

`c30329af81c84a4dc1973c32fcf06a544fb91340aaadedf6ca810d29f18735fe`

## Frozen scope

- BTC only
- supervised/readiness dates: 2026-03-01 through 2026-07-01 monthly first days only
- no August access
- decision grid: 00:30 through 23:49 UTC, one-minute spacing, 1400 decisions/day
- flow windows: 1, 5, 15, 30 minutes
- option trade causality: local_timestamp < decision time
- underlying reference for moneyness: latest valid BTCUSDT Phase-L mid strictly before each option trade local_timestamp

## Frozen segmentation

Moneyness:

- ATM if `|log(K/S)| <= 0.025`
- OTM call if call and `log(K/S) > 0.025`
- OTM put if put and `log(K/S) < -0.025`
- ITM/other-moneyness trades are outside the six primary segments

The numerical equality tolerance remains exactly `1e-12` and exists only to absorb floating-point reconstruction error at the exact ±0.025 boundary.

Maturity uses the corrected Deribit expiry timestamp at **08:00:00 UTC**:

- short: `0 < DTE <= 7 days`
- medium: `7 < DTE <= 30 days`
- >30 days remain outside the six primary segments

Six primary segments:

1. atm_short
2. atm_medium
3. otm_call_short
4. otm_call_medium
5. otm_put_short
6. otm_put_medium

A primary segment is permitted to have zero trades in an individual lookback window. Zero within a segment means no flow in that region and is not missing-data imputation.

## Frozen readiness gates

For each of the five days:

1. frozen raw hash verified
2. Phase-L structurally valid
3. option local_timestamp nondecreasing
4. no outside-day raw rows
5. zero eligible BTC vanilla parse errors
6. zero conflicting duplicate trade IDs
7. zero BTC vanilla trades classified expired under the corrected 08:00 UTC expiry timestamp
8. every used underlying reference is strictly earlier than the option trade
9. aggregate constructable 1-minute support >= 1120 / 1400
10. longest consecutive constructable run >= 120 minutes
11. all six primary segments exist at least once during the day

PASS only if all five days pass integrity and readiness:

`DATA_READY_CORRECTED_EXPIRY_SEGMENTED_BTC_OPTIONS_FLOW_SANDBOX`

If integrity passes but any readiness gate fails:

`FAIL_CORRECTED_EXPIRY_SEGMENTED_BTC_OPTIONS_FLOW_DATA_NOT_READY`

If provenance, parsing, causality, support accounting integrity, or corrected expiry semantics fail:

`INVALID`

## Scientific guards

Must remain false:

- network_accessed
- sealed_august_opened
- target_scored
- model_fit
- auc_scored
- direction_scored
- pnl_scored

## No-rescue rule

After EXP013 output exists, do not:

- change 08:00 expiry interpretation
- alter ATM threshold or numerical tolerance
- alter maturity boundaries
- drop a segment
- change the grid or support gates
- change windows
- remove a month
- access August
- score target/model/AUC/direction/PnL

Any materially different hypothesis requires a new Experiment ID.
