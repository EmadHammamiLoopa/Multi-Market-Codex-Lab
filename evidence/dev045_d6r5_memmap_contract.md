# DEV045-D6R5A — Canonical Jan read-only memmap adapter contract

Status at this commit: **CONTRACT FROZEN; EXECUTION NOT AUTHORIZED UNTIL THIS COMMIT'S CI IS GREEN.**

## Lineage

- Parent commit: `cd9cc4aaf7ab873a1b57af2876e3aaadca3aff14`
- Parent message: `research(dev045): freeze D6R4B Jan01 full-day conversion`
- Parent evidence: `evidence/dev045_d6r4b_jan01_full_day_conversion.json`
- This child gate does not modify, rerun, or reinterpret D6R4B.

## Sole canonical input

Only this already-created file may be opened by D6R5B:

`/home/emadh/Multi-Market/runtime/dev045_d6r4b/output/BTCUSDT_2026-01-01.npy`

Frozen identity:

- exchange: `binance-futures`
- symbol: `BTCUSDT`
- day: `2026-01-01`
- SHA256: `8f0a4fbd56ecdc261dbe2041ce138a09456423074925d495272716219a1d4da1`
- bytes: `4,116,142,528`
- rows: `64,314,723`
- ndim: `1`
- itemsize: `64`
- dtype, in exact field order:
  - `ev <u8`
  - `exch_ts <i8`
  - `local_ts <i8`
  - `px <f8`
  - `qty <f8`
  - `order_id <u8`
  - `ival <i8`
  - `fval <f8`

The identity must be checked fail-closed. SHA256, when checked, must be streamed in bounded blocks; the file must never be read into memory as a whole for hashing.

## Required D6R5B open semantics

D6R5B must use the equivalent of:

`np.load(path, mmap_mode="r", allow_pickle=False)`

The mapped array must be read-only. Production traversal is in physical row order using slices of at most `500,000` rows. The final short slice is allowed. No global `np.asarray`, `np.array`, concatenation, copy, sort, argsort, reorder, or equivalent whole-file materialization is allowed.

D6R5B may validate bounded slices, including M4/upstream event invariants, provided global cross-slice ordering state is explicitly preserved where required. Validation must not mutate the canonical file.

## Explicitly prohibited

D6R5A and D6R5B do not authorize:

- opening Tardis raw CSV;
- invoking or rerunning any converter;
- rewriting, replacing, moving, truncating, or deleting the canonical Jan NPY;
- selecting another Jan window or another Jan file;
- opening Feb–Jul;
- opening August or September+;
- non-BTC data;
- sorting/reordering canonical events;
- policy execution;
- historical PnL;
- economic arena execution;
- network market-data acquisition;
- Railway;
- live trading.

`src/multimarket/dev045_m6_tardis_feed.py` is not the D6R5 input path because its conversion path would reopen raw files and rerun the upstream converter.

## Gate discipline

This commit freezes only the contract. D6R5B implementation is authorized only after the exact D6R5A commit and its CI are independently verified green.

After a green D6R5B implementation + CI, the next separate gate is bounded historical-driver validation on this same canonical Jan NPY. That validation remains non-economic: no policy and no PnL.
