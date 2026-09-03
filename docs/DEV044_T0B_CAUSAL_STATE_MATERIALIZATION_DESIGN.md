# DEV044-T0B — Causal Strategy-State Materialization Design

Status:

`IMPLEMENTED_CI_PENDING_NO_PNL`

Date: 2026-09-03

## Purpose

T0B builds the exact causal state vectors used by the frozen DEV044 T01-T16
strategy contracts.

This stage remains NO-PNL.

## Sources

Primary 250 ms source:

- frozen BTCUSDT FEATURES250 lineage.

Raw-event source for deeper states:

- the same authorized BTCUSDT raw L2 files used by DEV031/DEV032;
- the same DEV032 E1A C++ extractor source:
  `tools/dev032_e1a_raw_features.cpp`.

No new exchange download is introduced.

## Direct causal formulas

Frozen mechanical constants:

- base grid = 250 ms;
- lookback = 32 s;
- EMA fast tau = 4 s;
- EMA slow tau = 32 s;
- round-number step = $100.

T01-T05, T06-T08, T11 and T15 are built from current/past-only FEATURES250
history.

Window semantics:

- 32 s inclusive return/RV history uses 129 250-ms points including current;
- prior-only 32 s breakout/z-score history uses 128 points ending at t-250ms;
- no future rows are used.

## DEV032 raw adapter

Implementation:

`src/multimarket/dev044_t0b_raw_adapter.py`

The adapter compiles/reuses the exact DEV032 E1A C++ extractor and materializes
the DEV044 support timestamps.

Only the required frozen DEV032 blocks are consumed:

- S05
- S06
- S21
- S30
- S31
- S32

Mappings:

### T09

- OBI_L20 = S05 f5 because S05 depth order is L1,L2,L3,L5,L10,L20,L50.
- weighted OBI = S06 f0, inverse-bp weighted OBI.

### T12

S21 order is event type insert/delete/replenish/deplete × near/deep.

- cancellation pressure = mean(delete near, delete deep)
- depletion pressure = mean(deplete near, deplete deep)

The DEV032 sign convention for delete/deplete is already bullish-positive.

### T13

- tau-1 directional event intensity =
  0.5 × (S30 add imbalance tau1 + S31 remove imbalance tau1)
- tau-8 directional event intensity =
  0.5 × (S30 add imbalance tau8 + S31 remove imbalance tau8)

S30 and S31 are both signed so positive means bullish pressure.

### T14

S32 = bid recovery, ask recovery, bid-shock age, ask-shock age.

- most recent bid depth shock -> SHORT;
- most recent ask depth shock -> LONG;
- recovery fraction is the corresponding side recovery;
- no shock within 32 s -> no signal;
- exact age tie -> no signal.

## Remaining blockers

### T10

T10 remains fail-closed.

Reason:

- frozen contract expects normalized 1s/16s/32s directional flow with
  +/-0.05 dead zones;
- DEV032 S15 contains raw signed totals whose magnitude is not directly
  comparable to those thresholds;
- substituting raw magnitudes after freezing T0 would change the strategy.

A normalization rule must be frozen before T1 PnL.

### T16

T16 remains fail-closed until a causal toxicity/VPIN stream is defined.

No toxicity=0 shortcut is allowed.

## Implementation

State materializer:

`src/multimarket/dev044_t0b_state_materializer.py`

Raw adapter:

`src/multimarket/dev044_t0b_raw_adapter.py`

Tests:

- `tests/test_dev044_t0b_state_materializer.py`
- `tests/test_dev044_t0b_raw_adapter.py`

## T1 authorization rule

T1 is NOT authorized while any core strategy readiness flag is false.

Currently unresolved:

- T10
- T16

No PnL may be opened to decide how to resolve these blockers.

## Forward guards

- DEV044 PnL: unopened
- Sep-01+: sealed
- non-BTC markets: sealed
- maker arena: separate DEV045-M

## Current state

`DEV044_T0B_IMPLEMENTED_CI_PENDING_T10_T16_BLOCKED_NO_PNL`
