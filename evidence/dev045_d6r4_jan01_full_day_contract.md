# DEV045 D6R4 Jan-01 Full-Day Bounded Conversion Contract

## Purpose

D6R4 is the first complete real-day execution of the frozen bounded
Tardis converter.

D6R4A freezes the execution contract only.

It does not open raw content and does not run the converter.

D6R4B is authorized only after the D6R4A commit and CI are GREEN.

## Frozen prerequisites

D6R2B real ten-minute oracle parity is frozen PASS.

D6R3B full-day resource preflight is frozen PASS.

Observed machine resources at D6R3B included:

- MemAvailable: about 9.40 GiB
- scratch free: about 710 GiB
- soft RLIMIT_NOFILE: 1,048,576
- CPU count / affinity: 24 / 24

The frozen bounded converter implementation is unchanged.

## Exact real input

Only:

- exchange: binance-futures
- symbol: BTCUSDT
- day: 2026-01-01

Trades:

`trades/BTCUSDT/2026-01-01.csv.gz`

Compressed bytes:

`9,691,108`

SHA-256:

`e4aaee2b9f85016a5198e0cace5755dbd789c0f6f47ac0fc802c8f4b533833f6`

Depth:

`incremental_book_L2/BTCUSDT/2026-01-01.csv.gz`

Compressed bytes:

`347,513,061`

SHA-256:

`0488a2204c9070b1e6a8769af48d54fb36e6a5658613267e2615cd3228002ded`

Both raw size and SHA-256 must match before canonical conversion.

No other market file may be opened.

## Frozen converter

Implementation SHA-256:

`8f79ec81c664f1762a87bfcf8757564abbe2d7f5fd89b1c83fc78de0ac4b94ac`

Production chunk size:

`500,000`

Expected full-day base events:

`63,666,276`

Expected temporary sort runs:

`256`

## Resource recheck

Immediately before any raw opening, execution must recheck:

- MemAvailable >= 1,805,762,560 bytes
- scratch free >= 24,447,849,984 bytes
- soft RLIMIT_NOFILE >= 320

Swap does not count.

A temporary resource drift stops execution before a canonical converter
attempt begins.

## Runtime filesystem

The frozen implementation creates its final partial `.npy` inside the
scratch temporary directory and then uses `os.replace()` to move it to
the final output path.

Therefore scratch and output are frozen onto the same filesystem.

Previously measured device id:

`2096`

Runtime root:

`/home/emadh/Multi-Market/runtime/dev045_d6r4b`

Scratch root:

`/home/emadh/Multi-Market/runtime/dev045_d6r4b/scratch`

Output root:

`/home/emadh/Multi-Market/runtime/dev045_d6r4b/output`

Final output:

`/home/emadh/Multi-Market/runtime/dev045_d6r4b/output/BTCUSDT_2026-01-01.npy`

After creating the runtime directories, their `st_dev` values must all
equal the frozen probed filesystem device id.

This prevents cross-filesystem `os.replace()` / EXDEV behavior without
modifying the frozen implementation.

## Runtime cleanliness

Before canonical converter invocation:

- final output must not already exist;
- scratch root must be empty.

The converter's own temporary work directory must be removed after the
run.

On PASS the final `.npy` is retained locally for later validation/replay
work.

The `.npy` is never committed to Git.

## CPU / v24

No artificial CPU cap is imposed.

The frozen converter may use available machine capacity.

The implementation itself is not changed merely to increase
parallelism.

## Canonical attempt boundary

D6R4B has one canonical converter attempt.

The canonical attempt starts exactly when the frozen converter is
invoked.

Pre-execution resource and raw-identity checks occur before that
boundary.

Once converter invocation begins, the first PASS or FAIL is frozen.

No converter rerun is allowed after observing the canonical result.

## Required PASS evidence

A PASS requires:

- exact base-event count;
- exact temporary-sort-run count;
- nonempty final output;
- exact event dtype / itemsize 64;
- no source_seq in final dtype;
- converter internal bounded M4 validation completed;
- output SHA-256 cross-check;
- scratch cleanup;
- runtime device identity.

The result evidence records the observed full-day final row count and
output SHA-256.

## Still prohibited

D6R4 does not authorize:

- any other date;
- August;
- September or later;
- non-BTC;
- M01-M08;
- policy execution;
- historical replay;
- PnL;
- economic arena;
- canonical PnL;
- network market-data acquisition;
- Railway;
- live trading.
