# DEV045-M4 — Replay Adapter and Execution-Integrity Synthetic Tests

Status:

`IMPLEMENTED_SYNTHETIC_CI_PENDING_NO_PNL`

Date: 2026-09-03

## Parent

DEV045-M3 final green identity:

`dbfd7e1effd3264a6e045019fa0274b585125c77`

M3 policy semantics are frozen.

## Purpose

Bind the pure M3 policy engine to the M1 safety-patched hftbacktest replay
engine and verify actual order lifecycle behavior before any historical maker
PnL is authorized.

M4 remains synthetic and NO-PNL.

## Implementation

`src/multimarket/dev045_m4_adapter.py`

Tests:

`tests/test_dev045_m4_adapter.py`

Dedicated workflow:

`.github/workflows/dev045-m4.yml`

## Safety-pinned simulator

Exact upstream source:

`a244a14250b42d97fc305569c93c4117cd5e1dff`

Mandatory frozen M1 corrections:

- issue #312 exact-final-fill cleanup;
- issue #316 partial-fill local accounting.

Unpatched PyPI 2.4.4 is forbidden for all M4 fill/accounting tests.

## Synthetic execution gates

M4 verifies:

1. M3 bid/ask targets are rejected by the adapter if they improve inside or
   cross the spread.
2. M01 passive bid submission becomes a real GTC LIMIT order.
3. RiskAdverse queue semantics preserve touch/trade-before-fill behavior.
4. A real maker fill changes engine position by exactly the response-ledger
   filled quantity.
5. Maker fee accounting equals an independent calculation.
6. The same one-lot fill lifecycle succeeds at 100/250/500ms latency.
7. M02 cancel/reprice is truly two phase:
   cancel response first, replacement submission second.
8. No cancel/submit overlap is allowed.
9. The 60s inventory timeout emits the M3 forced-flatten decision.
10. Forced flatten is submitted as a taker MARKET order and returns engine
    inventory to exactly zero.
11. Combined maker+taker fee accounting equals an independent calculation.
12. Synthetic event order and positive feed latency remain valid.

## Deliberate scope

M4 does not:

- open Jan-Jul historical files;
- calculate strategy return;
- calculate spread-capture PnL;
- rank M01-M08;
- choose a fee tier;
- alter queue assumptions;
- tune policy parameters;
- open Sep-01+;
- open non-BTC.

## Next stage

Only after dedicated M4 CI and general regression are green:

`DEV045-M5 MAKER ECONOMIC ARENA PREREGISTRATION + FEE FREEZE`

M5 still performs NO canonical PnL initially.

Before the first historical economic run, M5 must freeze:

- actual personal Binance Futures maker/taker fee tier;
- exact authorized Jan-Jul development-day scope;
- Q0/Q1 reporting rules;
- exact aligned block/bootstrap family-control method;
- eligibility thresholds already defined by M2;
- evidence paths and execution identity.

## Current state

`DEV045_M4_IMPLEMENTED_SYNTHETIC_CI_PENDING_NO_PNL`
