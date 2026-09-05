# DEV045-D6R12 — Memory-attributed real diagnostic design

Status: **DESIGN + CONTRACT + SYNTHETIC TESTS ONLY**

No canonical data is opened and no hftbacktest execution is authorized by this
stage.

## Frozen lineage

- D6R10 execution code: `0f2129e1cc0f8b75377fb0fb01b01857b24ab18c`
- D6R10 frozen failure: `50663457ca3e12506160025ccd045bf9abeec197`
- D6R11 implementation PASS: `22f20b506c9d1a52fae523a758e29588df33161b`
- D6R11 frozen PASS: `9b342a6e08fe51771a7125e823d76c927b1c3d7d`
- D6R11 freeze manifest SHA256:
  `aa9128a7c0fbfbec94912a70bfbba21b04822fec9d94b837fa6179486ec03327`

D6R10 remains a consumed, permanent failure. D6R12 uses a new runtime,
evidence schema, and one-shot marker namespace.

## Deliberately bounded diagnostic

A future separately authorized D6R12 attempt will use the established verified
read-only memmap adapter and the D6R6 no-copy lifetime-safe feed-only binding.
It will stop immediately after processing exactly **7,500,000 market
wakeups**. Overshooting that target is an error; EndOfData before it is not a
successful diagnostic. A full-day attempt or validation is forbidden.

The target crosses the last D6R10 heartbeat at 6,500,000 by about 15 percent,
which is enough to observe memory composition beyond the old failure region
without broadening exposure into a full-day run.

## Snapshot schedule

Lifecycle snapshots are required:

1. before source open;
2. after verified memmap open;
3. after hftbacktest binding creation;
4. immediately before close;
5. after backtest close;
6. after memmap close.

Traversal snapshots occur at the first market wakeup and every 250,000
wakeups through 7,500,000. This includes 6,000,000, 6,250,000, 6,500,000,
6,750,000, 7,000,000, 7,250,000, and 7,500,000.

Each snapshot uses the frozen D6R11 parser and records process RSS classes,
virtual/data/swap sizes, system `MemAvailable`, resident-component sum and
decomposition delta, plus `smaps_rollup` fields when readable.

## Measurement, hard abort, and terminal condition

These are intentionally separate:

- Measurement: `VmRSS`, `RssAnon`, `RssFile`, `RssShmem`, and the other
  snapshot fields describe composition. No measurement alone authorizes a
  full-day run.
- Pre-execution safety: the existing D6R10 requirement
  (`MemAvailable >= 8,442,945,536` bytes) is retained only as the pre-open gate
  it originally was.
- Runtime hard safety: attribution failure is fatal. Baseline-relative process
  `VmSwap` growth is the sole candidate runtime guard because it detects this
  process beginning to swap without inventing an absolute memory limit. Its
  final use must still be confirmed by the execution preflight.
- Terminal condition: exactly 7,500,000 wakeups produces
  `BOUNDED_WAKEUP_TARGET_REACHED`, followed by the frozen close order.

There is no total-RSS abort threshold and the old 10 GiB value is not raised or
repurposed. Runtime `MemAvailable` is measured and summarized but has no abort
threshold: file-backed residency may reduce it during the diagnostic. There is
also no hindsight-derived anonymous-memory threshold. Before a real attempt,
the preflight must either justify and freeze an anonymous-growth safety rule
independently or keep execution closed.

File-backed mmap residency is reclaimable by Linux under memory pressure. It
is therefore not equivalent to anonymous heap growth and cannot by itself
trigger a D6R12 abort.

## One-shot and lifecycle requirements

Any existing D6R12 attempt marker or evidence consumes the attempt and forbids
a rerun. The supported future lifecycle remains:

1. verified memmap opens;
2. no-copy hftbacktest binding is built;
3. bounded feed-only traversal runs;
4. hftbacktest closes;
5. only then does the memmap close.

This design contains no runnable canonical entrypoint. Strategy, orders, PnL,
the economic arena, conversion, raw CSV, full-day execution, August,
September+, non-BTC data, network acquisition, Railway, and live trading all
remain closed.
