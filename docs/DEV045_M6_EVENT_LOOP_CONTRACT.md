# DEV045-D1 Historical Event-Loop Contract

Date: 2026-09-04

Status:

STRUCTURAL / SYNTHETIC ONLY

No historical file was opened.
No historical replay was executed.
No historical PnL was computed.

## Parent

DEV045-M5B:

`3cb169308354951ca9ed5794371f7f544d3a1a9c`

Dedicated M5B CI:

`33892202327`

Conclusion:

`SUCCESS`

## Clock-domain resolution

The policy clock is explicitly bound to:

`LOCAL_STRATEGY_TIME`

This is not an arbitrary choice.

Frozen feature/A0 lineage reads the analytical timestamp from:

`local_timestamp_us`

The pinned hftbacktest local processor exposes local market events at:

`event.local_ts`

Therefore:

- M2 1-second maker cadence -> local strategy clock
- M5B exact-minute adapter cadence -> local strategy clock
- A0 exact support -> local strategy clock

Exchange timestamps MUST NOT trigger policy decisions.

## Separate economic fill clock

Frozen M4->M6 binding continues to timestamp fills using:

`ReplayOrderView.exch_timestamp`

Therefore two timestamp domains intentionally coexist:

### Strategy/risk causality

LOCAL strategy time.

Used for:

- one-second maker decisions;
- exact-minute M06/M07 adapter decisions;
- local book state;
- local order responses;
- inventory knowledge;
- inventory age / 60-second timeout.

### Economic execution record

EXCHANGE execution time.

Used for:

- M6 FillRecord timestamp;
- flat-to-flat economic accounting;
- frozen block assignment through cycle-start execution time.

The event-loop must never substitute one domain for the other.

## Same-local-timestamp ordering

At one identical local timestamp:

1. local market data
2. local order response
3. policy decision

The policy therefore sees all strategy-visible data and responses at timestamp
`t` before evaluating the decision epoch at `t`.

Exchange-only events never become strategy-visible merely because their
exchange timestamp is earlier.

## Inventory age

Inventory age begins when the local strategy state first observes nonzero
position after an order response.

It does NOT begin at exchange fill time.

Reason:

the strategy cannot react to a fill before the fill response is locally known.

The nonzero-start time persists through same-sign partial fills.

It resets only when local position becomes flat.

A direct observed sign flip without flat is fail-closed.

## Fill consumption

Every local order-response wakeup receives one driver response sequence.

A response sequence may be consumed exactly once.

The driver MUST NOT deduplicate maker executions from:

- order id;
- exchange timestamp;
- price;
- quantity

because two legitimate partial executions can share those values.

Fill binding occurs once per actual response wakeup.

Forced MARKET flatten remains the already-frozen special case:

it binds through simulator state deltas, not final ReplayOrderView quantity.

## Cancel/replace lifecycle

Replacement submission is impossible while cancellation is pending.

Required lifecycle:

WORKING
-> CANCEL_PENDING
-> cancel response
-> REPLACEMENT_READY
-> replacement submit
-> WORKING

No cancel/submit overlap.

## M5B multi-rate relationship

D1 does not alter M5B.

M5B remains:

- maker/risk cadence = local 1 second;
- M06/M07 candidate adapter epochs = exact local minute;
- Jan-Mar adapter absent;
- intermediate Apr-Jul seconds do not query A0;
- no probability carry.

D1 only binds those rates to the correct simulator clock domain.

## Still closed

D1 performs no:

- raw historical file I/O;
- Tardis conversion;
- historical strategy replay;
- M6 arena execution;
- PnL computation;
- canonical result write;
- network acquisition;
- Railway access;
- live/testnet/paper trading.

## Next after D1 local + CI green

Implement the historical driver itself against synthetic converted events first.

That driver must use:

- `bt.current_timestamp` only as strategy-local scheduler state;
- exact local 1-second epochs;
- exact local minute adapter epochs;
- simulator local depth at decision time;
- causal rolling trade-flow state;
- exact M5A/M5B support rules;
- response-sequence fill consumption;
- cancel-response-replacement gates;
- local inventory age;
- frozen M4/M6 exchange-timestamp fill binding;
- executable terminal flatten.

Historical raw provenance verification remains a later gate before the first
one-shot arena.
