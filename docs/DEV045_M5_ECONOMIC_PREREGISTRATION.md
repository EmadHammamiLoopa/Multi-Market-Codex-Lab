# DEV045-M5 — Maker Economic Arena Preregistration

Status:

`PREREGISTRATION_FROZEN_FEE_EVIDENCE_PENDING_NO_PNL`

Date: 2026-09-03

## 1. Parent

DEV045-M4 final green identity:

`6d8113b2128206cc192e60e167d47ec0add1cdd7`

M0-M4 remain frozen.

## 2. Purpose

Freeze the complete first maker economic-arena contract before historical
policy economics are observed.

M5 does not execute canonical maker PnL.

The only unresolved prerequisite is the user's actual personal Binance Futures
maker/taker fee schedule.

## 3. Authorized historical scope

Exactly seven BTCUSDT development days already audited by M0:

- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

No Aug.

No Sep-01+.

No non-BTC.

All seven days remain development evidence, not forward-validation evidence.

## 4. Policy family

Exactly eight:

`M01..M08`

All eight must be executed.

No policy may be removed from multiplicity control because it has low activity
or poor economics.

No M09.

## 5. Queue-model hierarchy

Primary:

`Q0 = RISK_ADVERSE`

Diagnostic only:

`Q1 = LOG_PROB`

A Q1-positive/Q0-negative policy is a FAIL for promotion.

Q1 can quantify queue-model sensitivity but cannot rescue Q0.

## 6. Simulator

All fill/accounting/PnL paths must use:

- exact upstream hftbacktest 2.4.4 source
  `a244a14250b42d97fc305569c93c4117cd5e1dff`
- frozen fail-closed patches for issues #312 and #316.

Unpatched PyPI hftbacktest 2.4.4 is forbidden.

## 7. Latency

Primary:

- entry = 250ms
- response = 250ms

Mandatory stress:

- entry = 500ms
- response = 500ms

100/100ms remains diagnostic only.

## 8. Fee gate

Canonical maker economics are BLOCKED until actual personal Binance Futures
fees are verified from the user's account/exchange fee display.

The fee record must include:

- maker rate;
- taker rate;
- evidence source description;
- explicit verified=true.

Primary economics use the actual account schedule.

Required fee scenarios:

1. verified actual maker/taker schedule — PRIMARY;
2. maker rate = 0 only — diagnostic, never promotional;
3. adverse fee stress — frozen after actual schedule is known and before PnL.

No optimistic rebate may be invented.

No policy-specific fees.

## 9. Economic accounting unit

The primary family-comparison series is realized **flat-to-flat inventory-cycle
PnL**.

A cycle:

- starts when inventory moves from zero to nonzero;
- includes every maker fill, partial fill, fee/rebate, cancellation consequence,
  and any forced taker liquidation cost while inventory remains nonzero;
- closes only when inventory returns to zero.

No open inventory is marked to mid for cycle profit.

At day/replay end:

- working orders are canceled;
- remaining inventory is flattened executably;
- the resulting costs belong to the closing cycle.

This prevents artificial terminal mark-to-market gains.

## 10. Primary metrics

Per policy under Q0 primary fees/latency:

- completed flat-to-flat cycles;
- maker submitted orders;
- maker fills;
- partial fills;
- maker fill ratio;
- cancel count;
- cancel/fill ratio;
- average queue wait;
- forced taker liquidations;
- average/max absolute inventory;
- gross maker spread capture;
- maker fees/rebates;
- taker liquidation cost;
- net cycle bps;
- mean/median net cycle bps;
- total net bps;
- PF;
- max drawdown on realized cycles;
- daily net;
- positive-day count;
- worst day;
- positive-day concentration;
- 1s/5s/30s signed post-fill markouts.

## 11. Eligibility gates

A policy can become a development survivor only if under Q0:

- primary net expectancy > 0;
- primary PF > 1.0;
- at least 4 of 7 days positive;
- positive-day concentration <= 0.50;
- 500/500ms stress net expectancy > 0;
- execution-integrity failures = 0;
- terminal inventory is always flattened executably;
- family-wise max-stat p <= 0.05.

These gates are conjunctive.

## 12. Family-wise control

Use the same defensive joint centered-null max-stat structure proven in DEV044,
adapted only to the frozen M5 geometry.

Aligned UTC blocks:

- 4h block length;
- 6 blocks/day;
- 7 days;
- 42 blocks/policy;
- matrix = 42 x 8.

Block value:

sum of realized net flat-to-flat cycle PnL assigned to the UTC 4h block
containing the cycle start timestamp.

Joint bootstrap:

- centered null;
- identical resampled block indices across all 8 policies;
- studentized mean block PnL statistic;
- 20,000 repetitions;
- seed = 450045;
- FWER alpha = 0.05.

All eight policies stay in the family.

## 13. Diagnostics that cannot promote

Report but do not use to rescue:

- Q1 LogProb economics;
- 100/100ms latency;
- zero-maker-fee diagnostic;
- gross spread capture before adverse markout;
- individual best day;
- isolated best regime.

## 14. No-rescue rules

After first historical maker economic output, forbidden changes include:

- policy family;
- M01-M08 constants;
- quote size;
- inventory cap;
- inventory timeout;
- A0 threshold;
- T05/T10 definitions;
- OBI/TFI thresholds;
- queue hierarchy;
- primary latency;
- stress latency;
- verified primary fee schedule;
- block length;
- bootstrap repetitions;
- bootstrap seed;
- FWER alpha;
- eligibility gates;
- terminal liquidation rule;
- flat-to-flat accounting definition.

A failed first arena is evidence, not permission to retune the same arena.

## 15. Promotion meaning

Any M5/M6 survivor is only a **development survivor**.

It is NOT capital-ready.

Later required:

- independent historical replication on genuinely unused data;
- prospective live/shadow fill calibration;
- Sep-01+ forward evidence only under separately frozen authorization;
- then, if still robust, small-capital unlevered deployment.

## 16. Current blocker

`ACTUAL_PERSONAL_BINANCE_FUTURES_FEE_SCHEDULE_UNVERIFIED`

Therefore:

`NO_CANONICAL_MAKER_PNL_AUTHORIZED`

## Next

After verified fee evidence is frozen:

`DEV045-M6 FIRST MAKER ECONOMIC ARENA IMPLEMENTATION + ONE-SHOT EXECUTION`
