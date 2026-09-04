# DEV045-D3 Policy-Specific Synthetic Integration Handoff

Date: 2026-09-04

## Status

FROZEN LOCALLY — DEDICATED CI PENDING

Parent D2:

`74bc4f7a14076e1dd08a24b3e46eab7858f34983`

D2 dedicated CI:

`33898102230`

Generic repository test CI:

`33898102097`

Both are GREEN.

## Scope

D3 is synthetic / in-memory only.

No historical raw file is opened.
No Tardis historical conversion is run.
No historical replay is run.
No historical PnL is computed.
No M6 economic arena is executed.
No canonical result is written.
No live trading is authorized.

## Purpose

D3 connects all eight frozen M3 policies to the already-proven D2 patched
hftbacktest execution kernel.

## M01 / M02

Reuse the D2 common execution lifecycle unchanged.

## M03

Uses current simulator L1 depth directly.

Synthetic depth is deliberately asymmetric so the frozen L1 OBI thresholds
produce a nonzero shift and can be asserted.

## M04

Uses the current simulator L1 to compute the frozen microprice skew.

The synthetic spread/depth fixture is deliberately constructed so the
microprice shift is exactly nonzero and auditable.

## M05

Uses only the inherited D2 local one-second aggressive trade-flow window.

The synthetic fixture puts the queue-consuming trade and maker fill between
two policy epochs so the maker fill is causal and the following policy epoch
observes the negative one-second trade-flow imbalance.

No future trade is used.

## M06 / M07 multi-rate integration

Frozen M5A/M5B semantics are preserved.

### Jan-Mar

M06 and M07 remain base-only for the full day.

Behavior is M02-equivalent.

### Apr-Jul exact-minute adapter epoch

The exact M5B adapter candidate minute is resolved using:

- exact A0 support;
- exact causal legacy StrategyState.

Joint support:

`APPLY_ADAPTER`

Missing either:

`FALLBACK_TO_M02`

### Intermediate exact seconds

Mode:

`NO_ALPHA_UPDATE`

D3 freezes the operational integration needed to combine this with the
1-second maker/risk clock:

1. the exact-minute M3 adapter decision is reduced to one execution-state
   integer only:
   - LONG
   - SHORT
   - ABSTAIN

2. the probability is immediately discarded;

3. the StrategyState is immediately discarded;

4. on intermediate seconds, fresh M02 inventory/risk state is recomputed;

5. only the already-resolved direction integer remains unchanged until the
   next exact adapter candidate minute;

6. the one-sided frozen M06/M07 retreat is applied to that fresh base state.

This is execution-state persistence, not probability persistence.

No p_touch is carried.
No StrategyState is carried.
No A0 row is carried.
No A0 lookup occurs on intermediate seconds.
No interpolation or forward-fill occurs.

At each exact supported adapter minute, the D3 integrated decision is checked
for behavioral identity against frozen M3/M5A `decision_at_epoch`.

At fallback, behavioral identity against M02 is checked.

## M08

Frozen queue-preserve hysteresis is asserted directly:

a one-tick target change is KEEP for M08 and CANCEL for M02.

## Real simulator lifecycle

All M01-M08 are exercised on patched hftbacktest under:

- primary 250/250ms latency;
- stress 500/500ms latency;
- RiskAdverse queue;
- PartialFillExchange;
- asynchronous submit/cancel;
- no request overlap;
- one-lot maker fill;
- local inventory knowledge clock;
- exact 60-second timeout;
- cancel before forced flatten;
- MARKET terminal flatten;
- M4->M6 fill binding;
- terminal zero inventory.

## Still forbidden after local D3 implementation

Until D3 is frozen and dedicated CI is GREEN:

- no historical raw file opening;
- no historical Tardis conversion;
- no historical replay;
- no M6 economic arena;
- no historical PnL;
- no canonical artifact.

## Next gate after D3 freeze + CI GREEN

Build immutable provenance for exactly 14 intended raw historical files:

7 authorized BTCUSDT days ×

- trades;
- incremental_book_L2.

The provenance phase comes before historical content opening/replay.

Only after immutable provenance and a final preregistration/handoff reread may
the first one-shot historical replay be authorized.


## Final local freeze gate

Before commit:

- D3 policy-specific tests: 40 passed
- frozen regressions: 335 passed
- generic import without hftbacktest: PASS
- compile: PASS
- prohibited-surface audit: PASS
- diff check: PASS
- all frozen input blobs: PASS

Policies structurally proven:

- M01 common symmetric join
- M02 inventory reservation
- M03 dynamic simulator L1 OBI
- M04 dynamic simulator microprice
- M05 causal one-second aggressive-flow window
- M06 M5A/M5B T10 adapter semantics
- M07 M5A/M5B T05 adapter semantics
- M08 queue-preserve hysteresis

Both frozen latency scenarios were exercised:

- primary 250/250ms
- stress 500/500ms

No historical data was opened.
No Tardis historical conversion was run.
No historical replay was executed.
No historical PnL was computed.
No M6 economic arena was executed.
No canonical PnL artifact was written.

After dedicated D3 CI is GREEN, the next phase is immutable provenance for
exactly 14 intended BTCUSDT raw files:

7 authorized Jan-Jul days ×

- trades
- incremental_book_L2

That provenance gate precedes historical content opening and the first
one-shot replay.
