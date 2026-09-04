# DEV045 D6R2 Real 10-Minute Parity Contract

## Purpose

D6R2 is the first real-data parity gate for the frozen bounded-memory
converter.

D6R2A freezes the execution contract only.

It does not open raw market data and does not execute either converter.

The execution itself is a later one-shot D6R2B gate after this contract
commit and its CI are GREEN.

## Frozen prerequisite

Canonical synthetic parity is frozen PASS at:

`c0647ef3ad32db199401643aa0324fe3e12133b8`

D6R1B evidence SHA-256:

`3788b76b48b98efc4b1d9491d35c6c7f5620de8308fc017f2d16942027168fdd`

Canonical synthetic parity passed exactly for:

- chunk_rows = 1
- chunk_rows = 2
- chunk_rows = 3
- chunk_rows = 7

## Frozen implementation

Bounded implementation SHA-256:

`8f79ec81c664f1762a87bfcf8757564abbe2d7f5fd89b1c83fc78de0ac4b94ac`

Production chunk size:

`500,000 rows`

No implementation change is permitted during D6R2B.

## Real-data scope

Only these frozen raw inputs are in scope:

- exchange: `binance-futures`
- symbol: `BTCUSDT`
- day: `2026-01-01`
- trades:
  `trades/BTCUSDT/2026-01-01.csv.gz`
- depth:
  `incremental_book_L2/BTCUSDT/2026-01-01.csv.gz`

Raw root:

`/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw`

No other day, symbol, exchange, or window may be opened.

## Fixed 10-minute selection

The window was frozen before this real-data execution:

`[2026-01-01 00:00:00 UTC, 2026-01-01 00:10:00 UTC)`

Selection uses only `local_timestamp`.

Exact microsecond bounds:

- start: `1767225600000000`
- end: `1767226200000000`

A row is included iff:

`start <= local_timestamp < end`

Exchange timestamp is not used to select rows.

No PnL, policy result, model output, or economic criterion selected this
window.

The window may not be extended or shortened after opening the data.

## Sequential extraction

Both gzip files are read sequentially.

D5B already proved physical local timestamps are nondecreasing.

The extractor:

1. preserves the exact original header;
2. preserves exact selected row text and row order;
3. skips rows below the lower bound if any;
4. writes rows inside the fixed interval;
5. stops at the first row with local timestamp greater than or equal to
   the fixed upper bound.

Temporary slice files are gzip CSV files with deterministic gzip
`mtime=0`.

Their SHA-256 values and row counts are recorded in result evidence.

Temporary slice files are never committed.

## Fail-closed slice gates

Both slices must be nonempty.

All selected rows must retain:

- exchange `binance-futures`;
- symbol `BTCUSDT`.

The depth slice must begin with the SOD snapshot and contain at least one
snapshot row.

The fixed window must terminate outside a snapshot batch.

If the fixed ten-minute boundary cuts a snapshot batch, D6R2B freezes
FAIL.

The window must not be extended to repair that failure.

## Upstream oracle

Frozen oracle:

- hftbacktest `2.4.4`;
- upstream commit
  `a244a14250b42d97fc305569c93c4117cd5e1dff`;
- Tardis converter blob
  `1ca038895d30f320561d6b28ffa13c1d788ea6bf`.

The oracle receives:

1. temporary trades slice;
2. temporary depth slice.

Arguments remain:

- `output_filename=None`
- `base_latency=0`
- `snapshot_mode="process"`

Buffer sizing is calculated from the real slice before conversion:

`trade_rows + depth_rows + 2 * snapshot_batches + 32`

Snapshot buffer:

`max(max_snapshot_side_rows + 16, 1024)`

The upstream oracle runs in a fresh Python subprocess.

Its returned array may be written to a temporary `.npy` solely so the
parent parity harness can compare outputs.

That temporary `.npy` is not an alternative converter output.

## Bounded candidate

The exact frozen D6R1A implementation receives the same two temporary
slice files.

Production:

`chunk_rows=500000`

It writes its normal disk-backed `.npy` output in a fresh temporary
directory.

It also runs in a fresh Python subprocess.

## Exact parity

The oracle and bounded output must have:

- identical shape;
- identical dtype;
- itemsize 64;
- identical row order;
- exact equality for all integer fields;
- exact equality for all floating fields;
- NaN equal to NaN.

No tolerance is permitted.

No post-conversion row sorting or reordering is permitted.

Compared fields:

- ev
- exch_ts
- local_ts
- px
- qty
- order_id
- ival
- fval

## Resource observation

D6R2B records bounded-converter peak resident memory from its fresh
subprocess using Linux:

`resource.getrusage(resource.RUSAGE_SELF).ru_maxrss`

Linux reports this value in KiB.

Evidence converts it to bytes by multiplying by 1024.

Only the bounded converter subprocess measurement is eligible as the
input to the later full-day resource gate.

The upstream oracle's memory use is not used for that gate.

This observation does not itself authorize a full-day conversion.

## One-shot discipline

D6R2B has exactly one canonical attempt.

Its first PASS or FAIL is frozen.

No retry, alternative slice, changed boundary, changed chunk size, or
changed implementation is permitted after observing the result.

## After a PASS

A real-parity PASS still does NOT authorize full January conversion.

The next phase must separately freeze and pass a full-day resource
preflight.

## Explicitly closed

D6R2 does not authorize:

- any other real-data window;
- any other day;
- August;
- September or later;
- non-BTC data;
- policy execution;
- M01-M08;
- historical replay;
- PnL;
- economic arena;
- canonical PnL;
- network market-data acquisition;
- Railway;
- live trading.
