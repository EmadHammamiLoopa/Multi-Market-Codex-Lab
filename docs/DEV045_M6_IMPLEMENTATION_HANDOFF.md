# DEV045-M6 Maker Economic Arena — Implementation Handoff

Date: 2026-09-04
Status: PRE-EXECUTION IMPLEMENTATION / NO HISTORICAL M6 OUTPUT YET

## Lineage

Branch:
`research/dev045-m6-maker-economic-arena`

Frozen parent:
`f0bc4b36eb1657e5a3cf1d1b62add9c6cf192a9a`

Parent meaning:
`Freeze DEV045 M5 public fee pre-result amendment`

Original M5 prereg identity:
`cbffd48a9eea77a7ace843f9c830ac96bd39a071`

## Frozen fee schedule

Primary, Regular User USDⓈ-M, no BNB discount:
- maker = 0.0002 = 2 bp per side
- taker = 0.0005 = 5 bp per side

Pre-result adverse fee stress:
- multiplier = 1.5x
- maker = 0.0003 = 3 bp per side
- taker = 0.00075 = 7.5 bp per side

Historical M6 economics are authorized by the frozen M5 amendment.
Live trading remains forbidden.

## Frozen M5 arena geometry retained unchanged

- Venue: Binance Futures
- Symbol: BTCUSDT
- Development days exactly: 2026-01-01, 2026-02-01, 2026-03-01, 2026-04-01, 2026-05-01, 2026-06-01, 2026-07-01
- Policy family exactly: M01..M08
- Primary queue: Q0 Risk-Adverse
- Q1 LogProb diagnostic only and cannot rescue
- Primary latency: 250/250 ms
- Stress latency: 500/500 ms
- 4h UTC blocks, 6/day, 42/policy
- 42x8 family matrix
- centered joint max-stat bootstrap
- 20,000 repetitions
- seed 450045
- FWER alpha 0.05
- flat-to-flat realized inventory-cycle accounting
- executable terminal flatten only; no terminal mark-to-mid

Eligibility remains conjunctive:
- primary net expectancy > 0
- PF > 1.0
- at least 4/7 positive days
- positive-day concentration <= 0.50
- 500/500 ms stress net expectancy > 0
- execution-integrity failures = 0
- terminal inventory executable-flat
- family-wise max-stat p <= 0.05

## M6 implementation added

Source:
`src/multimarket/dev045_m6_economic_arena.py`

Tests:
`tests/test_dev045_m6_economic_arena.py`

CI:
`.github/workflows/dev045-m6.yml`

The M6 core consumes replay fill/audit outputs only. It deliberately does not:
- scan historical files
- run hftbacktest
- change M01-M08
- change M5 inference or eligibility definitions
- open Sep-01+ data
- open non-BTC data
- authorize live trading

Fail-closed accounting rules include:
- execution-order validation; no silent sorting
- exact authorized policy/day/venue/symbol checks
- partial fills stay within the same flat-to-flat cycle
- inventory sign flip without observed zero inventory is invalid
- non-flat terminal inventory is invalid
- maker/taker fees come only from the frozen M5 fee amendment
- block assignment uses cycle-start UTC 4h block
- exact complete primary+stress replay audit matrix required before an arena result can be emitted

## Current boundary

At this handoff:

`M6_HISTORICAL_OUTPUT_GENERATED = NO`

`M6_CANONICAL_PNL_ARTIFACT_WRITTEN = NO`

`SEP01_PLUS_OPENED = NO`

`NON_BTC_OPENED = NO`

`LIVE_TRADING_AUTHORIZED = NO`

The next action, only after M6 contract CI is green, is to bind the frozen M4 patched-simulator replay path to this accounting core, validate that binding synthetically, freeze it, and then perform the first one-shot Jan-Jul M6 historical arena execution. The first historical output is evidence and must not trigger retuning of the frozen arena.
