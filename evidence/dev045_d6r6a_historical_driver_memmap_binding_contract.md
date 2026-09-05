# DEV045 D6R6A — Historical Driver Memmap Binding Contract

Status: CONTRACT ONLY / NO CANONICAL HFTBACKTEST INGESTION / NO POLICY REPLAY

## Frozen parent

`4be133e52d8392da1e91fce4b72fc69995545c58`

This is the frozen PASS result of D6R5C, the one-shot Jan read-only
memmap validation.

D6R5C validated all 64,314,723 Jan rows in 129 bounded chunks without
changing the canonical file.

## Purpose

D6R6 connects the already-frozen Jan memmap source to the already-frozen
historical execution stack without reopening raw CSV data, rerunning the
converter, changing event order, or authorizing economic replay.

D6R6A freezes only the binding and lifetime rules.

It does not open the canonical Jan NPY.

## Existing execution boundary

The frozen historical orchestration remains synthetic-only.

The frozen event-loop kernel remains synthetic-only.

Historical policy replay, historical PnL, the economic arena, and
canonical PnL writing remain disabled.

## Exact data source

The only production source entrypoint is:

`multimarket.dev045_d6r5_memmap_adapter.open_canonical_jan()`

It accepts no caller path.

The canonical identity remains:

- exchange: binance-futures
- symbol: BTCUSDT
- day: 2026-01-01
- rows: 64,314,723
- bytes: 4,116,142,528
- mmap mode: read-only
- pickle: disabled

## Frozen hftbacktest binding finding

The exact upstream simulator remains hftbacktest 2.4.4 at:

`a244a14250b42d97fc305569c93c4117cd5e1dff`

Its Python ndarray registration passes the NumPy data pointer and length
to Rust.

Rust wraps that pointer through `DataPtr::from_ptr`.

That pointer is explicitly non-owning: the caller remains responsible
for the underlying memory.

The Reader path stores and checks out `Data` through shared pointer
clones rather than copying the event bytes.

Therefore the binding contract is lifetime-critical.

## Mandatory lifetime

The order is frozen as:

1. open verified read-only memmap;
2. build BacktestAsset from the same live memmap;
3. build backtest;
4. use the backtest only in a separately authorized later gate;
5. close backtest;
6. only then close memmap.

Closing/unmapping the memmap before the backtest is forbidden.

## Read-only protection

Feed latency offset is frozen at zero.

No feed preprocessor is authorized.

Feed-data mutation is forbidden.

`parallel_load(False)` is required for the historical binding.

No array copy, concatenate, full-file materialization, sorting, or
reordering is authorized.

## D6R6B

After D6R6A commit and CI are independently GREEN, D6R6B may implement
the lifetime-safe driver binding using a small synthetic read-only
memmap.

D6R6B still may not open the canonical Jan NPY inside hftbacktest.

D6R6B still may not execute M01-M08, historical PnL, or the economic
arena.

A later separately frozen gate is required before the first canonical
Jan hftbacktest ingestion.

## Closed surfaces

No:

- raw CSV opening
- converter rerun
- canonical NPY rewrite
- Jan policy replay
- Feb-Jul opening
- Aug opening
- Sep+ opening
- non-BTC opening
- historical PnL
- economic arena
- canonical PnL write
- network market-data acquisition
- Railway access
- live trading
