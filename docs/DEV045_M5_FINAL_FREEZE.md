# DEV045-M5 Final Economic Preregistration Freeze

Status:

`DEV045_M5_GREEN_FROZEN_FEE_EVIDENCE_NEXT_NO_PNL`

Date: 2026-09-03

Final M5 identity:

`cbffd48a9eea77a7ace843f9c830ac96bd39a071`

Dedicated CI:

- workflow: `dev045-m5-economic-prereg`
- run #1
- run id: `33805142060`
- conclusion: `SUCCESS`

General regression:

- workflow: `test`
- run #1251
- run id: `33805141928`
- conclusion: `SUCCESS`

The following are now frozen before first maker economics:

- exactly seven BTCUSDT development days, 2026-01-01 through 2026-07-01 on
  the first day of each month;
- policy family M01-M08;
- Q0 RiskAdverse primary / Q1 LogProb diagnostic-only hierarchy;
- 250/250ms primary latency;
- 500/500ms mandatory latency stress;
- realized flat-to-flat inventory-cycle accounting;
- executable terminal flattening;
- 4h aligned UTC blocks;
- 42 x 8 family matrix;
- joint centered-null max-stat bootstrap;
- 20,000 repetitions;
- seed 450045;
- FWER alpha 0.05;
- conjunctive survivor gates;
- permanent no-rescue rule after economic output is observed.

No canonical maker PnL has been run.

The only unresolved pre-M6 blocker is the user's actual personal Binance Futures
maker/taker fee schedule.

M6 remains unauthorized until fee evidence is explicitly verified and frozen.
