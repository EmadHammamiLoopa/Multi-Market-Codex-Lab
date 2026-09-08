# DEV045 D6R26A P2 R15 — Sequential same-engine lane preexecution

Parent R14 GREEN HEAD:

`7f95b3f4e4173e0118d486681075f01f6c6b85e7`

R14 proved the full side × distance candidate grid using the exact patched
real engine.

R15 proves the remaining lane-lifecycle property before historical binding:
multiple isolated candidates must run sequentially inside the **same**
backtest instance.

Synthetic decision times:

- 31.000s
- 36.000s
- 41.000s

They are exactly five seconds apart, matching the frozen maximum candidate
lifetime.

For every candidate:

- post-only placement is acknowledged with exact 250ms + 250ms latency;
- no-fill candidate remains working until its frozen cancel request;
- cancel response occurs exactly at decision + 5s;
- the corrected R11 cancel-latency first-field semantics remain frozen;
- the prior order is terminal before another order is submitted.

The critical boundary is explicitly tested:

`previous terminal response local timestamp == next candidate decision timestamp`

This freezes the P0 requirement that expiry/cancel completion precedes the
next placement at the equal timestamp.

R15 also carries the earlier D6R13/D6R14 anti-regression rules:

- no fixed event target;
- no fixed wakeup target;
- natural end-of-source is valid;
- total RSS is not the boundedness gate.

And it adds an explicit EOF-label regression:

- candidates near end-of-source are retained;
- fully observed no-fill horizons remain `NOT_FILLED_WITHIN_TAU`;
- unobservable horizons become `CENSORED`;
- censoring is never converted into no-fill.

R15 is synthetic PREEXECUTION only.

It opens no Jan-Jul historical source, writes no attempt marker, writes no
canonical labels, fits no model, and computes no PnL.

`P2_ATTEMPT_CONSUMED=NO`.

After R15 GREEN, the next stage is the final historical one-shot
binding/preflight. That stage may wire the frozen real source, bounded
dual-stream decoder, rolling features, same-engine sequential lane primitive,
atomic partition writer, and R4 campaign state machine — but historical
execution remains separately unauthorized until that final surface is GREEN.
