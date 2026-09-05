# DEV045 D6R8ED — New Semantic Real-Parity Contract

Status: **FROZEN CONTRACT ONLY**

Parent: `4d86b93ab083c78446c6ad8a19877cc607b8be0a` (D6R8EC semantic-slice identity amendment; exact CI green required).

D6R8ED is a successor contract. It does not rerun or rescue D6R8EB. D6R2B remains a historical PASS and D6R8EB remains a permanently frozen FAIL.

## Exact source and semantic slice

Only the frozen D4 Jan 1 BTCUSDT trades and incremental-book files are eligible. Their exact byte sizes and SHA256 values must be verified before content selection. The selection window remains exactly `1767225600000000 <= local_timestamp < 1767226200000000`.

Before any converter launches, the reconstructed slice must match the D6R8EC semantic identities exactly: trades 13,073 rows / 1,137,750 decompressed bytes / SHA256 `cb6a1d37e4422fa99e563969b3750487a3ca3d01956a45973085f26352a220fe`; depth 483,149 rows / 39,147,846 decompressed bytes / SHA256 `5c5d8de09c1a38083f151f632fce568fb80b9df1485f5688d2dab20431869f93`, plus the frozen endpoints and snapshot structure. Compressed-gzip SHA is diagnostic only.

## Three-way parity

The exact same two reconstructed physical slice files must be supplied to three fresh subprocesses:

1. frozen upstream hftbacktest 2.4.4 oracle;
2. frozen old bounded converter (`8f79ec81...`, production chunk 500,000);
3. frozen V2 structurally bounded converter (implementation commit `3d304429...`, production chunk 250,000, fan-in 8).

All three outputs must agree fieldwise exactly, NaN equal, with identical shape/dtype/64-byte itemsize and no tolerance, post-sort, or row reordering. Required pairwise comparisons are upstream-old, upstream-V2, and old-V2.

The old D6R2B output SHA remains historical evidence only and is not the sole oracle for this new semantic slice.

## Resource protection

Before the future attempt, `MemAvailable >= 8 GiB`; swap does not count. V2 retains the 6 GiB runtime RSS abort and its peak RSS must be recorded.

## Attempt separation

The future real attempt is **DEV045-D6R8EF**, not D6R8EB. It has a new runtime root, attempt marker, and evidence path, exactly one canonical attempt, and the first PASS or FAIL freezes permanently.

D6R8ED itself authorizes no real execution. After D6R8ED CI green, D6R8EE must implement a fail-closed runner and pass synthetic/static CI. Only after D6R8EE exact CI green can the one new D6R8EF local successor attempt be considered authorized.

## Closed surfaces

Jan full-day, Feb-Jul, August, September+, non-BTC, 112 replay, policy execution, PnL/economic arena, network acquisition, Railway and live trading remain closed.
