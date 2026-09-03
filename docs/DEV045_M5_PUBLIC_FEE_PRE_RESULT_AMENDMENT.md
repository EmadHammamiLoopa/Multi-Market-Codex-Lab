# DEV045-M5 Public Fee Pre-Result Amendment

Status: `FROZEN_PRE_RESULT_AMENDMENT`

Date: 2026-09-04

Original M5 scientific identity:

`cbffd48a9eea77a7ace843f9c830ac96bd39a071`

## Why this amendment exists

M5 was frozen before any maker economics with one unresolved prerequisite: the user's personal Binance USD-M Futures maker/taker fee schedule. The personal commission endpoint requires an activated account/API path that the user does not want to fund or activate at this stage.

No M01-M08 historical maker PnL, fill-rate comparison, ranking, survivor, bootstrap result, or other economic output has been observed. Therefore this is a transparent pre-result protocol amendment, not a post-result rescue.

## Frozen public conservative fee schedule

Official Binance USD-M Futures fee table, Regular User, USDT, no BNB discount:

- maker: `0.0200%` = `0.0002`
- taker: `0.0500%` = `0.0005`

Evidence URL checked before M6:

`https://www.binance.com/en-BH/fee/futureFee`

No BNB discount, VIP discount, LP rebate, referral adjustment, or maker rebate is assumed.

## Adverse fee stress

Frozen before any economic output:

- rule: `1.5 x primary fee on every executed leg`
- stress maker: `0.0003` = `0.0300%`
- stress taker: `0.00075` = `0.0750%`

The previously preregistered zero-maker-fee case remains diagnostic only and cannot promote a policy.

## Relationship to the original personal fee gate

`docs/DEV045_M5_PERSONAL_BINANCE_FUTURES_FEE_FREEZE.json` remains unchanged and continues to state that personal account fees are not verified.

This amendment does not claim that public fees are personal fees. Instead, for the historical M6 development experiment only, the official Regular User no-discount schedule becomes the frozen canonical primary fee assumption.

This is deliberately conservative. If a future personal account receives lower fees, canonical M6 MUST NOT be rerun using the lower fees to improve or rescue the result.

If a future live account has fees higher than the frozen public schedule, live deployment remains blocked until the higher fee schedule is separately evaluated. Historical M6 is not silently rewritten.

## What remains unchanged

All M5 scientific rules remain frozen:

- seven BTCUSDT development days exactly as preregistered;
- M01-M08 family unchanged;
- Q0 RiskAdverse primary and Q1 LogProb diagnostic-only;
- 250/250 ms primary latency;
- 500/500 ms mandatory latency stress;
- 100/100 ms diagnostic latency only;
- flat-to-flat realized inventory-cycle accounting;
- executable forced/terminal flattening;
- 4h UTC blocks, 42 x 8 matrix;
- 20,000 max-stat bootstrap reps, seed 450045, alpha 0.05;
- all conjunctive survivor gates;
- no rescue after first historical economic output;
- SEP01_PLUS_SEALED;
- NON_BTC_SEALED.

## Authorization

After this amendment itself passes CI and is frozen, historical DEV045-M6 economics may proceed using exactly the public fee schedule above.

This amendment authorizes historical development economics only. It does not authorize live trading, account funding, API trading, leverage, or deployment.
