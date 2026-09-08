# DEV045 D6R26A P2 R20 — Combined once/day context + exact midpoint index

Parent R19 GREEN HEAD:

`7a86630e5662e1ae6c7dc47f77836d31cb7d0a95`

## Why R20 exists

R19 closed the production once/day feature-cache gap.

One remaining per-day context was still missing before a generic historical
lane executor can be frozen: exact exchange-time BBO midpoint lookup for
markout labels.

The frozen label rule is:

`LAST_BBO_MID_WITH_EXCHANGE_TS_LE_TARGET`

A naive implementation would either:

- materialize millions of Python `MidObservation` objects;
- perform a second Python full-day pass for midpoints;
- or rescan the raw ~180M-row source separately for each lane.

All three are forbidden by R20.

## One combined raw pass

R20 uses the already-frozen R13A dual decoder.

During one and only one Python traversal of the opened day's raw events:

- local emissions feed the exact R19/R10 feature-cache logic;
- exchange emissions are immediately appended to a file-backed midpoint
  index.

Therefore:

`COMBINED_RAW_EVENT_PASSES_PER_DAY = 1`

There is no separate midpoint pass.

There is no per-lane raw feature rescan.

There is no per-lane raw midpoint rescan.

## Feature-cache parity

R20 does not redefine feature semantics.

It binds directly to the frozen R19 case-matrix/eligibility surface and
produces the exact R18 dense cache:

- int64 decision timestamp;
- int64 best bid tick;
- int64 best ask tick;
- float64 `[N, 8, 25]`.

Synthetic CI proves byte-for-byte NumPy value parity against the frozen R19
builder.

The R19 leading-preeligible rule remains unchanged.

## Exact midpoint index

Every final exchange-time BBO midpoint emitted by R13A is reduced to:

- `exchange_ns: int64`
- `mid_tick_sum: int64`

Each record is exactly 16 bytes.

The future mid is reconstructed exactly as:

`0.5 * (best_bid_tick + best_ask_tick) * TICK_SIZE`

which is algebraically identical to the frozen `MidObservation.mid`.

The index is:

- written incrementally;
- buffered with only 65,536 records (~1 MiB);
- fsync'd;
- atomically renamed;
- opened read-only as a NumPy memmap;
- kept file-backed while the day's 40 lanes execute;
- deleted after the day context is closed.

No full midpoint history exists as a Python object graph.

## Exact lookup

`midpoint_asof()` implements the same lookup as P1:

`LAST_BBO_MID_WITH_EXCHANGE_TS_LE_TARGET`

If the source has not been observed through the requested exchange target,
the lookup returns `None`, preserving markout censoring.

CI proves parity with `p1.mid_asof()` against the full synthetic R9 reference
series.

## Historical-failure protections retained

R20 preserves all earlier guards:

- natural EOF, not fixed event/wakeup quotas;
- no decisions after actual feed EOF;
- leading preeligible epochs audited;
- no post-eligibility missing feature rows;
- no total-RSS boundedness gate;
- file-backed large state;
- one day at a time.

## Scope

R20 is PREEXECUTION ONLY.

It does not:

- open Jan-Jul;
- start historical hftbacktest candidate simulation;
- write the P2 attempt marker;
- write canonical historical partitions;
- fit models;
- calculate PnL;
- open August;
- open September+;
- open non-BTC data.

`P2_ATTEMPT_CONSUMED=False`.

## Next

After R20 GREEN, R21 may finally freeze the generic historical-lane executor:

`shared day context -> one lane -> exact engine -> fills -> exact midpoint
lookups -> LabelBundle -> R18 canonical partition`

That executor will still be tested against synthetic data only.

Only after R21 GREEN will the final R4 successor runner/binding be frozen.
