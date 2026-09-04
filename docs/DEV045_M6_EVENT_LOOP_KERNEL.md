# DEV045-D2 Actual Event-Loop Kernel

Date: 2026-09-04

Status:

SYNTHETIC / IN-MEMORY ONLY

No historical file I/O.
No historical replay.
No historical PnL.
No M6 economic arena.

## Parent

DEV045-D1:

`d7650e26f2ff9069206fcea27542cb98b19111f6`

Dedicated D1 CI:

`33893854676`

Conclusion:

`SUCCESS`

## D1.5 diagnostic conclusion

The same-timestamp two-half-lot diagnostic did not reveal maker-accounting
collapse.

Observed:

- final order exec_qty = 0.001
- state volume delta = 0.001
- state position delta = 0.001
- state num_trades delta = 1

The assertion expecting two simulator trades was incorrect.

This is consistent with the frozen M3 maker quantity contract:

- LOT_SIZE = 0.001
- BASE_ORDER_QTY = 0.001
- every executable quote is exactly one lot

Therefore no separate D2 maker state-delta binding amendment is introduced.

The frozen passive M4->M6 ReplayOrderView binding remains authoritative.

## What this kernel proves

D2 now exercises the real patched hftbacktest event loop with:

- asynchronous submit requests;
- asynchronous cancel requests;
- exact local one-second policy timers;
- local market events;
- local order responses;
- exchange events hidden until locally visible;
- dynamic simulator L1 depth;
- causal one-second aggressive trade-flow storage;
- maker fill binding exactly once;
- local inventory-knowledge clock;
- exact 60-second timeout;
- cancellation of working passive quotes;
- no cancel/submit overlap;
- executable forced MARKET flatten;
- M4->M6 taker state-delta binding;
- terminal zero inventory.

## Synthetic fixture

The existing frozen M4 fill fixture is shifted onto an authorized day.

Its last non-trading event is extended beyond 70 seconds solely to keep the
synthetic simulator clock alive while the 60-second timeout is exercised.

No historical file is opened.

## D2 policy scope

The first actual-engine probe is intentionally limited to M01/M02.

This freezes the common execution kernel before layering:

- M03/M04 dynamic book alpha;
- M05 causal trade-flow behavior;
- M06/M07 M5A/M5B multi-rate legacy adapter;
- M08 hysteresis.

Those policy-specific semantics belong to the next driver layer.

## Still forbidden

D2 does not:

- call dev045_m6_tardis_feed.convert_day;
- read Jan-Jul raw files;
- call run_economic_arena;
- account historical cycles;
- compute historical PnL;
- write canonical results;
- touch Railway;
- acquire network data;
- trade live/testnet/paper.
