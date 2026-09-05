# DEV045 D6R7A — Canonical Jan hftbacktest Ingestion Contract

Status: CONTRACT ONLY

Parent:

`56c46cd2f60e300a3a406d5ff81d9db068d2ecee`

D6R6B synthetic memmap binding is independently green in both:

- repository default CI;
- dedicated patched-hftbacktest 2.4.4 CI.

## Purpose

D6R7 defines the first real canonical Jan `.npy` ingestion into
hftbacktest.

D6R7A freezes the contract only.

It does not open the Jan file and does not run hftbacktest.

## Exact source

Only:

- binance-futures
- BTCUSDT
- 2026-01-01
- 64,314,723 rows
- 4,116,142,528 bytes
- exact frozen SHA-256
- read-only NumPy memmap

No alternate path is permitted.

## Resource gate

D6R5C observed full-Jan read-only validation peak RSS:

`4,221,472,768` bytes.

D6R7B requires two times that observed peak as current MemAvailable:

`8,442,945,536` bytes.

Swap does not count.

If this precheck fails, the canonical hftbacktest ingestion attempt has
not started.

## Canonical attempt boundary

Pre-attempt:

1. verify resource gate;
2. verify/open exact canonical Jan source through the frozen D6R5
   entrypoint.

The canonical attempt starts exactly when the verified live memmap is
passed to the frozen D6R6 lifetime-safe hftbacktest binding.

One attempt only.

The first PASS or FAIL after that boundary is frozen.

## Feed-only canary

No strategy is executed.

No order is submitted or cancelled.

No PnL is computed.

The backtest may only consume market data through
`wait_next_feed(False, ...)` until hftbacktest returns EndOfData.

A wakeup count equal to the source row count is NOT required.

D6R6B established that the terminal data event can be applied before
the EndOfData return rather than appearing as a separate market-wakeup
return.

## PASS requirements

PASS requires:

- exact canonical source identity;
- read-only memmap;
- exact patched hftbacktest 2.4.4;
- at least one market wakeup;
- nondecreasing strategy-visible market timestamps;
- terminal EndOfData return;
- valid terminal book;
- zero position;
- zero working orders;
- backtest closed before memmap unmap;
- source file identity unchanged;
- resource and peak RSS evidence recorded.

## Still closed

D6R7 does not authorize:

- policy execution;
- order placement;
- PnL;
- economic arena;
- other dates;
- Feb-Jul;
- August;
- September or later;
- non-BTC;
- raw CSV;
- converter rerun;
- canonical NPY modification;
- network acquisition;
- Railway;
- live trading.
