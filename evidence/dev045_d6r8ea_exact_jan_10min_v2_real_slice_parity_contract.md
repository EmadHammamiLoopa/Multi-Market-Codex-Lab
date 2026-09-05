# DEV045 D6R8EA — Exact Jan 10-Minute V2 Real-Slice Parity Contract

Status: **FROZEN CONTRACT ONLY**

Parent: `3d304429a825d50bf3b0f292632fc35e7a92a947` (D6R8D V2 synthetic implementation, CI green required)

D6R8EA opens no market data and executes no converter. It freezes the only real
slice that D6R8EB may reopen and the immutable oracle that V2 must match.

## Immutable old real-slice oracle

D6R2B is frozen at commit
`4ff70ec50e39da432a70bf0444907f536586ed3e` and PASS attempt 1. We do **not**
rerun either the old bounded converter or the upstream hftbacktest converter.
The frozen D6R2B result itself is the oracle.

The old result is:

- base events: 496,224;
- final events: 503,934;
- itemsize: 64 bytes;
- output SHA256:
  `60ebc2aec273976c12526f7c49159d005368388a0f9d5993af269cc9753ffaf7`;
- parity mode: fieldwise exact, NaN equal, no tolerance.

## Only permitted raw inputs

Raw root:
`/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw`

Only:

- `trades/BTCUSDT/2026-01-01.csv.gz`;
- `incremental_book_L2/BTCUSDT/2026-01-01.csv.gz`.

No other file, day, symbol, market or time window is permitted.

## Exact selection

Selection is by `local_timestamp` only:

`1767225600000000 <= local_timestamp < 1767226200000000`

which is exactly `[2026-01-01 00:00:00 UTC, 00:10:00 UTC)`.

The deterministic D6R2B slices that must be reproduced before V2 may execute are:

| Slice | Rows | SHA256 |
|---|---:|---|
| trades | 13,073 | `a7595b2d6ce750eaf032f8f693683a42c008bd59a2cd3d7035928c39da2a4e0d` |
| depth | 483,149 | `e52a325096ddad2ac28b4f299d1e522f61e9e1dc50a7275d75e07833e4ba2848` |

The depth slice begins with the SOD snapshot, contains one snapshot batch with
2,002 snapshot rows, and the fixed upper boundary does not cut a snapshot batch.
The window may not be changed to rescue a failure.

## D6R8EB one-shot execution

After this contract's exact commit CI is green, D6R8EB may perform exactly one
canonical V2 real-slice attempt. The steps are frozen:

1. verify the two exact raw paths exist without modifying them;
2. sequentially extract only the exact fixed window with deterministic gzip
   `mtime=0` and preserve original headers/row text/order;
3. require exact selected row counts and exact slice SHA256 values above;
4. if any slice identity differs, freeze FAIL before running V2;
5. run only the V2 converter in a fresh Python subprocess using its frozen
   production tuning (250,000-row initial chunk, fan-in 8 and the D6R8C window
   constants);
6. require base rows 496,224 and final rows 503,934;
7. require the exact final output SHA256
   `60ebc2aec273976c12526f7c49159d005368388a0f9d5993af269cc9753ffaf7`;
8. record V2 peak RSS from `ru_maxrss`, require normal return, cleanup and raw
   source identity unchanged;
9. freeze the first PASS or FAIL. No retry, alternate tuning or alternate window.

The old converter is not rerun. This is deliberately V2-only against an
immutable old real-result oracle.

## Resource gates

The run requires `MemAvailable >= 8 GiB`, swap does not count, and the V2
runtime RSS abort remains 6 GiB. These are fixed D6R8C protections, not values
derived from the real-slice outcome.

## After PASS

A D6R8EB PASS still does not open Feb–Jul. The next step is D6R8F: freeze the
full-day/new-day resource preflight and first new-day attempt contract.

## Closed surfaces

This contract opens nothing. It authorizes no Jan full-day rerun, no D6R4B or
D6R5C rerun, no Feb–Jul raw open or conversion, no August, no September+, no
non-BTC, no 112 replay, no policy/PnL/economic execution, no network acquisition,
no Railway and no live trading.
