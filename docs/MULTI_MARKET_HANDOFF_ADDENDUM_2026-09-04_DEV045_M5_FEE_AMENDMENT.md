# Multi-Market Project Handoff Addendum — DEV045 M5 Fee Amendment

Date: 2026-09-04

## Frozen prior state

- DEV045-M5 scientific identity remains `cbffd48a9eea77a7ace843f9c830ac96bd39a071`.
- M01-M08 historical maker economics have NOT been observed before this amendment.
- Existing personal-fee evidence file remains pending and unmodified.
- No live trading is authorized.

## Pre-result fee amendment

The user does not want to fund/activate Binance merely to obtain a personal API commission rate before historical development testing.

Before observing any M01-M08 historical economics, the project freezes the official Binance USD-M Futures Regular User USDT schedule with no BNB/VIP/LP discount as the canonical historical M6 fee assumption:

- maker `0.0002` (0.0200%)
- taker `0.0005` (0.0500%)

Evidence: official Binance USD-M Futures fee table checked 2026-09-03 UTC.

Mandatory adverse fee stress is frozen simultaneously at 1.5x primary:

- maker `0.0003`
- taker `0.00075`

If future personal fees are lower, M6 must not be rerun with lower fees to rescue/improve results. If live fees are higher, live deployment remains blocked pending evaluation.

## Next

After dedicated and general CI are green for this amendment, proceed directly to DEV045-M6 historical maker economics under the unchanged M5 design plus this fee amendment. Do not open Sep-01+ or non-BTC data.
