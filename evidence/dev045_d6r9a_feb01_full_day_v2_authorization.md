# DEV045 D6R9A — Feb 1 Full-Day V2 Resource Proof

Status: **EXECUTION-READY AFTER EXACT CI GREEN / ONE LOCAL CANONICAL ATTEMPT ONLY**

Parent D6R8EG execution head: `e8d87ed29998e1af5a037ff2290c72cdfe967344`, canonical PASS and never rerun.

D6R9A opens only the already-provenanced BTCUSDT raw files for `2026-02-01`. Frozen D4 identities are:

- trades: 57,631,972 bytes, SHA256 `dfd19ab53abbc90118ce3c861521ecb17dbed6ce7bcc7410c07f296460454508`;
- incremental_book_L2: 865,907,076 bytes, SHA256 `a1e9fc0fcc20d309d171ed1b6367ebe17948c84dd025a07a5d13c80f0b023cc4`.

Frozen D5B raw rows are 172,721,707. The D6R8C structural resource formula therefore requires at least 127,721,761,664 bytes (~118.95 GiB) free scratch on the same device as output, MemAvailable >= 8 GiB, and soft/hard RLIMIT_NOFILE >= 128. V2 retains the frozen 6 GiB RSS abort guard, production chunk size 250,000, merge fan-in 8, bounded sequential NPY I/O, bounded validation and streaming SHA256.

The canonical attempt marker is `/home/emadh/Multi-Market/runtime/dev045_d6r9a/ATTEMPT_STARTED.json`; evidence is `evidence/dev045_d6r9a_feb01_full_day_v2.json`; output is `/home/emadh/Multi-Market/runtime/dev045_d6r9a/output/BTCUSDT_2026-02-01.npy`.

Resource preflight, file existence/size, pinned hftbacktest binding, and frozen D6R8EG evidence identity are checked before the attempt marker. Raw file contents are not opened before the marker. After the marker, exact raw SHA256 is verified and V2 runs once in a child process. A failure stores bounded child diagnostics. Final validation uses only the V2 bounded validation already inside the converter plus a header-only NPY check; no full-day `np.load`, whole-file memmap, old converter, or upstream converter is allowed.

The first D6R9A result freezes PASS or FAIL. No rerun is allowed after the marker exists.

Other Feb-Jul days, Jan rerun, August, September+, non-BTC, policy replay, historical PnL, Railway and live trading remain closed.
