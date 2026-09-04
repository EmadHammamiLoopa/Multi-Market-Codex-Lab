# DEV045-M5B Multi-Rate Decision Clock Handoff

Date: 2026-09-04

## Status

PRE-EXECUTION MULTI-RATE CLOCK CONTRACT FROZEN LOCALLY

No historical data was opened.
No historical maker replay was executed.
No historical PnL was computed.

## Parent

`c3e4931ac3096ef5e4901d64a34af904e4ca909e`

DEV045-M5A remains frozen and unchanged.

## Why M5B exists

A pre-execution timing audit discovered two legitimate frozen rates:

1. DEV045-M2 maker policy authority:
   - decision cadence = 1 second;
   - quote maintenance occurs at each 1-second decision.

2. Frozen A0 lineage:
   - A0 common-support decisions are exact-minute timestamps;
   - DEV042 materialization uses `exact_minute_decision_indices`;
   - legitimate A0 support is therefore sparse and minute-based.

Treating the absence of an A0 row on every intermediate second as
`A0 unavailable` would create an artificial one-second alpha pulse and
quote churn.

M5B freezes the correct multi-rate semantics before PnL.

## Frozen clocks

### Market-event clock

Replay events update:

- book;
- queue;
- fills;
- latency;
- order lifecycle.

A market event is not automatically a policy decision.

### Base maker/risk clock

Frozen cadence:

`1 second`

Deterministic UTC phase:

`timestamp_us % 1_000_000 == 0`

This clock governs ordinary quote maintenance and risk controls.

### M06/M07 legacy adapter clock

Adapter candidate epochs:

`exact UTC minute`

Deterministic phase:

`timestamp_us % 60_000_000 == 0`

This is a strict subset of the maker 1-second clock.

## Jan-Mar

A0 OOF support does not exist.

Therefore M06/M07 remain base-only for the entire day:

`M06 == M02`
`M07 == M02`

subject to their already-frozen M3 behavior.

## Apr-Jul exact-minute behavior

At an exact adapter candidate minute:

- exact A0 score + causal legacy state:
  `APPLY_ADAPTER`

- missing exact A0 score or causal legacy state:
  `FALLBACK_TO_M02`

The previous minute's probability is never carried forward.

## Apr-Jul intermediate seconds

At exact one-second maker epochs that are not minute adapter epochs:

`NO_ALPHA_UPDATE`

This is NOT:

- `A0 unavailable`;
- an imputed probability;
- a zero probability;
- forward-fill;
- interpolation;
- a new A0 decision.

No A0 lookup occurs.

An order already issued earlier may remain alive through normal M4 lifecycle.

Order persistence is execution state, not probability persistence.

## Frozen prohibitions

No:

- A0 refit;
- A0 retraining;
- interpolation;
- probability forward-fill;
- backfill;
- probability carry;
- nearest-neighbor timestamp substitution;
- future data;
- synthetic prediction.

## Local verification

Before freeze:

- M5B tests: 32 passed
- M5A regression: 222 passed
- M3 regression: 18 passed
- compile: PASS
- prohibited execution surfaces: absent
- M3 blob unchanged
- M4 blob unchanged
- M5 blob unchanged
- M5A blob unchanged
- DEV042 materialization blob unchanged

## Experiment family unchanged

Still exactly:

- M01-M08
- 8 policies
- 7 development days
- 6 aligned 4-hour UTC blocks/day
- 42 blocks/policy/scenario
- Q0 Risk-Adverse primary
- 250/250ms primary latency
- 500/500ms stress latency
- frozen fees
- 20,000 centered max-stat bootstrap repetitions
- seed 450045
- FWER alpha 0.05
- original promotion gates

## Diagnostic only

Apr-Jul paired deltas:

- M06 - M02
- M07 - M02

remain:

- diagnostic-only;
- non-promotional;
- no model selection;
- no rescue authorization.

## Next gate after dedicated M5B CI green

Implement the actual historical event-loop contract, but initially:

- structural/synthetic only;
- no historical PnL;
- no economic arena execution.

The event-loop must prove:

1. market events are processed independently from policy epochs;
2. exact 1-second maker epochs are deterministic;
3. exact-minute M06/M07 adapter epochs are deterministic;
4. intermediate seconds never query or clear A0;
5. no probability carry;
6. current simulator L1 is used causally;
7. causal legacy state is supplied only where legitimate;
8. cancel -> response -> replacement ordering is preserved;
9. each fill is bound exactly once;
10. inventory age and 60s timeout are exact;
11. forced terminal flatten uses the frozen M4/M6 binding;
12. terminal inventory is zero.

Only after that driver is frozen and provenance is verified may the first
one-shot M6 historical arena be authorized.
