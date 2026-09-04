# DEV045-D1 Historical Event-Loop Contract Handoff

Date: 2026-09-04

## Status

STRUCTURAL / SYNTHETIC EVENT-LOOP CONTRACT READY FOR FREEZE

No historical data opened.
No historical replay executed.
No historical PnL computed.
No canonical M6 result written.

## Parent

DEV045-M5B:

`3cb169308354951ca9ed5794371f7f544d3a1a9c`

Dedicated M5B CI:

`33892202327`

Conclusion:

`SUCCESS`

## Local D1 verification

Before freeze:

- D1 contract tests: 32 passed
- M5B regression: 32 passed
- M5A regression: 222 passed
- compile: PASS
- prohibited execution surfaces: absent
- frozen M3 blob: PASS
- frozen M4 blob: PASS
- frozen M5A blob: PASS
- frozen M5B blob: PASS
- no historical file opened
- no historical strategy replay
- no PnL

The only initial STOP was an incorrect expected M4 hash typed in the
verification command.

Expected typo:

`7f6a321b4512dd1ecdf94c79416e176ee75e1c`

Actual frozen M4 blob:

`7f6a321b4512dd1ec1edf94c79416e176ee75e1c`

The corrected identity gate passed.

No project file was modified to resolve that STOP.

## Clock-domain contract

### Policy / A0 clock

`LOCAL_STRATEGY_TIME`

Frozen feature/A0 lineage derives its analytical clock from
`local_timestamp_us`.

Therefore:

- base maker decisions use local time;
- M06/M07 adapter candidate epochs use local time;
- A0 exact support uses local time.

Exchange execution timestamps cannot manufacture policy epochs.

### Inventory age clock

`LOCAL_POSITION_KNOWLEDGE_TIME`

Inventory age begins only when the strategy-local state receives the
fill/order response and observes nonzero position.

It does not start at exchange execution timestamp.

Same-sign partial fills retain the original nonzero inventory clock.

The clock resets when local inventory becomes flat.

Direct sign flip without observed flat fails closed.

### Economic fill clock

`EXCHANGE_EXECUTION_TIME`

Frozen M4->M6 accounting continues to use exchange execution timestamp
for M6 FillRecord timestamps.

Therefore local causal timing and economic execution timing remain
intentionally separate.

## Same-local-timestamp ordering

At identical local timestamp:

1. local market data
2. local order response
3. policy decision

Thus the decision at local time `t` observes all strategy-visible market
data and responses at `t`.

Market events alone never trigger policy decisions.

## Frozen multi-rate schedule

Inherited unchanged from M5B:

Base maker/risk decision:

`1 second`

M06/M07 adapter candidate:

`exact minute`

Jan-Mar:

adapter unavailable all day.

Apr-Jul intermediate seconds:

`NO_ALPHA_UPDATE`

No A0 query.
No probability carry.
No interpolation.
No artificial fallback pulse.

## Fill-response consumption

The driver must assign one strictly increasing response sequence to each
local order-response wakeup.

Each response sequence is consumed exactly once.

Do not deduplicate fills from:

- order id
- timestamp
- price
- quantity

because legitimate partial fills can share these values.

Forced MARKET flatten remains the frozen exception:

bind it from simulator state deltas, because one MARKET request may execute
across multiple levels.

## Cancel / replacement lifecycle

Required:

WORKING
-> CANCEL_PENDING
-> cancel response
-> REPLACEMENT_READY
-> replacement submit
-> WORKING

Replacement before cancel response is forbidden.

No cancel/submit overlap.

## Frozen lineage preserved

Unchanged:

- M3 policy
- M4 replay adapter
- M5 preregistration
- M5A A0-support semantics
- M5B multi-rate clock
- M4->M6 binding
- M6 economic arena

## Next gate after dedicated D1 CI green

Build the actual historical event-loop driver against synthetic converted
events only.

The driver must prove structurally:

1. simulator local clock schedules policy decisions;
2. market events do not manufacture policy decisions;
3. all visible events at an epoch are processed before the policy;
4. exact 1-second base clock;
5. exact-minute Apr-Jul adapter clock;
6. Jan-Mar base-only M06/M07 behavior;
7. intermediate Apr-Jul seconds never query A0;
8. causal legacy state only;
9. no probability carry;
10. dynamic simulator L1 book state;
11. causal aggressive trade-flow windows;
12. response-sequence fill consumption exactly once;
13. cancel-response-replacement ordering;
14. local inventory age;
15. exact 60-second timeout;
16. M4 forced executable flatten;
17. M4->M6 exchange-timestamp fill binding;
18. terminal zero inventory.

Still forbidden at that next gate:

- opening Jan-Jul raw historical files;
- historical economic replay;
- M6 economic arena;
- historical PnL;
- canonical result writing.

After that driver is frozen, verify immutable provenance for the 14 intended
Jan-Jul raw Tardis files.

Only after provenance and a final prereg/handoff reread may the first
historical one-shot be authorized.

The first historical result is evidence and cannot authorize retuning.
