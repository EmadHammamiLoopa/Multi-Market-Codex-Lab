# DEV045-D6R12 — Real diagnostic execution preflight

Status: **PREFLIGHT + SYNTHETIC WRAPPER ONLY; REAL EXECUTION DISABLED**

## Frozen lineage

- D6R12 design freeze head: `544dba4a2428e957049a46edb15d3558826f4ab7`
- D6R12 design head: `2aa65ad0cbfe3fdceaa4b76550ec14a35f25fe97`
- D6R12 design freeze manifest SHA256:
  `1f893eb9307bbc4ef52739a8674efeec97d10969ae3bc664e3de8c40092d3039`

The D6R10 failure and D6R11/D6R12 frozen artifacts remain unchanged.

## Preflight boundary

Preflight may `stat` the frozen Feb-01 NPY to verify that it is a regular file
with exactly 11,493,385,088 bytes. It never opens or hashes NPY content.
Expected SHA and 179,584,138 rows are instead checked against the frozen D6R9A
lineage evidence. Content identity remains deferred to the existing verified
memmap adapter inside a future separately authorized execution.

Preflight also checks frozen artifact hashes, exact Git ancestry, tracked/index
cleanliness, hftbacktest distribution version 2.4.4, required procfs
attribution, `VmSwap` availability, the inherited pre-open `MemAvailable` gate,
the distinct D6R12 namespace, and absence of both D6R12 marker and evidence.
It performs no write.

## Independent execution locks

The wrapper requires:

`DEV045_D6R12_AUTHORIZE=YES_FEB01_BOUNDED_MEMORY_DIAGNOSTIC`

It is additionally blocked by `REAL_EXECUTION_ENABLED=False`. Supplying the
token cannot create a marker or start a child while that contract lock is
false. There is no Mar–Jul sequence.

## Prepared bounded child

The dependency-injected child core is tested on synthetic objects. A later
authorized binding will:

1. capture `before_source_open`;
2. open through the frozen verified read-only memmap adapter;
3. capture `after_verified_memmap_open`;
4. retain D6R10's conditional `MADV_SEQUENTIAL` behavior;
5. build the D6R6 no-copy feed-only binding;
6. capture `after_hftbacktest_binding_creation`;
7. stop immediately at exactly 7,500,000 wakeups;
8. capture wakeup 1 and every 250,000 wakeups;
9. atomically replace `MEMORY_HEARTBEAT.json` at every capture;
10. fail on early EndOfData, overshoot, attribution failure, or baseline-relative
    process `VmSwap` growth.

Runtime `MemAvailable`, `VmRSS`, and `RssFile` are measurements only. The old
10 GiB value is not a guard. No runtime MemAvailable, total-RSS, or anonymous-
RSS threshold exists.

## Split close snapshots

Frozen D6R6 is not modified. D6R12 directly performs the same required owner
lifecycle on its already-built binding:

1. call `binding.bt.close()` once;
2. append `backtest_closed` and capture `after_backtest_close`;
3. call `binding.source.close()` once;
4. append `memmap_closed` and capture `after_memmap_close`;
5. mark the binding closed so repeated cleanup is idempotent.

The memmap therefore remains alive until hftbacktest has released its
non-owning pointer, while the two required snapshots remain distinct.

## Parent failure evidence

Only a later authorized parent may create the one-shot marker. It launches a
separate child and always writes final evidence, including bounded stdout and
stderr tails. If the child fails, the parent retains the latest atomic
heartbeat SHA256, complete heartbeat payload, and available snapshot history.
Any marker or evidence consumes the attempt and blocks rerun.

No canonical data content, hftbacktest feed, full day, strategy, order, policy,
PnL, converter, raw CSV, August, September+, non-BTC data, network acquisition,
Railway, or live trading is opened or executed in this stage.
