# DEV045-D6R11 — Memory attribution successor

Status: **NON-CANONICAL / SYNTHETIC-ONLY / NO HFTBACKTEST EXECUTION**

## Frozen parent

This successor starts from the permanent D6R10 failure commit:

`50663457ca3e12506160025ccd045bf9abeec197`

D6R10 remains a consumed, frozen failure. Its evidence, attempt marker, and
heartbeat are not modified or reinterpreted.

## Purpose

D6R11 isolates Linux memory measurement from any ingestion loop. It records
process memory from `/proc/self/status`, system availability from
`/proc/meminfo`, and, when readable, proportional/private/shared rollups from
`/proc/self/smaps_rollup`.

All Linux `kB` values are converted with the frozen identity:

`bytes = kB * 1024`

The primary attribution is kept as distinct values:

- total resident memory: `VmRSS`;
- anonymous resident memory: `RssAnon`;
- file-backed resident memory: `RssFile`;
- shared-memory resident memory: `RssShmem`;
- available system memory: `MemAvailable`.

Linux describes `VmRSS` as an approximate counter composed from `RssAnon`,
`RssFile`, and `RssShmem`. D6R11 records both their sum and the signed delta.
The exact-match flag is diagnostic: no guessed tolerance and no successor
abort threshold is introduced here.

The status fields required for attribution fail closed if missing, duplicated,
malformed, negative, or expressed in a unit other than `kB`. `VmSize`,
`VmData`, and `VmSwap` are retained when present. `smaps_rollup` is optional
because kernels and permission models differ; if it is readable, `Rss` and
`Pss` are required and all recognized fields are parsed strictly.

## Synthetic mmap proof

Tests create a small temporary file, map it read-only, fault its pages, and use
`/proc/self/smaps` only to locate that exact temporary mapping. This proves the
attribution layer can observe file-backed residency without opening any
canonical market artifact.

## Execution boundary

D6R11 does not import or invoke hftbacktest and has no market-data entrypoint.
It does not authorize a canonical run or select a replacement safety limit.
Any future successor remains feed-only/no-strategy and must preserve the D6R6
lifecycle rule: hftbacktest closes before the caller-owned memmap closes.

No canonical Feb–Jul NPY, raw CSV, converter, policy, PnL, order path, August,
September+, non-BTC data, network acquisition, Railway, or live trading is
opened or executed by this stage.
