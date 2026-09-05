# DEV045 D6R8C — Structurally Bounded Converter Redesign Contract

Status: **FROZEN DESIGN ONLY**

Parent: `4a7df3e85f4cf495ebe244fceb03c14996d933c7` (D6R8B static memory-scaling audit)

This phase freezes architecture and resource gates only. It opens no market
data and runs no converter, policy, PnL or replay.

## Why V2 is separate

The old converter remains immutable at SHA256
`8f79ec81c664f1762a87bfcf8757564abbe2d7f5fd89b1c83fc78de0ac4b94ac`.
D6R8D will implement a new module
`src/multimarket/dev045_d6r8_structurally_bounded_converter.py`. The frozen old
converter is retained as a parity oracle on synthetic fixtures and, only after
a separate exact path/hash freeze, the already-approved D6R2B Jan 10-minute
slice. D6R4B full-day Jan is never rerun.

## Frozen semantic invariants

V2 must preserve hftbacktest 2.4.4, base latency 0, the exact 64-byte event
dtype, the 72-byte temporary record including `source_seq`, and exact sort keys:

- exchange axis: `(exch_ts, source_seq)`;
- local axis: `(local_ts, source_seq)`.

Corrected-event semantics are unchanged. Exact exchange/local timestamp pairs
must refer to the same source sequence and collapse to one event carrying both
clock flags; otherwise events are emitted according to the same frozen clock
ordering as the old converter.

## Fixed production bounds

The following values are preregistered and may not be tuned after observing a
new full-day outcome:

- initial CSV/run chunk: **250,000 rows**;
- hierarchical merge fan-in: **8**;
- per-input merge read window: **16,384 temp records**;
- merge output buffer: **65,536 temp records**;
- corrected-merge input window: **32,768 temp records per axis**;
- final output buffer: **65,536 events**;
- validation window: **65,536 events**;
- SHA256 userspace block: **1 MiB**.

Smaller values may be used only in synthetic tests to force many runs and merge
levels. Production constants remain frozen.

## Hierarchical external merge

Initial conversion still creates bounded sorted runs. V2 then reduces each
axis independently through fixed fan-in merge passes. At most eight input run
file handles are live for a merge group. Every reader parses the NPY header and
loads sequential windows with bounded `np.fromfile`; **whole-file memmap is
forbidden**.

For each group, the exact output shape is known from the input headers. The
group output is written through a bounded 65,536-record buffer. Only after that
output is closed successfully may the consumed group inputs be deleted. The
process repeats until exactly one exchange-sorted run and one local-sorted run
remain.

This removes D6R8B's all-runs-live mapping failure mode. Run count and disk use
may scale with day size, but simultaneously live reader payload does not.

## Corrected stream and final output

The two final axis runs are read through bounded windows. The corrected stream
is traversed twice: the first bounded pass determines the exact final row count;
the second bounded pass writes exactly that many 64-byte events. Two passes are
accepted because they preserve semantics while keeping memory bounded.

The final NPY uses format version 1.0 and a sequential header + payload writer.
A full-shape writable memmap is forbidden. The partial final file stays in
scratch until payload write, bounded validation and streaming SHA256 all pass.
Only then may `os.replace` atomically promote it to the destination. Scratch and
output must therefore be on the same device.

## Bounded validation

Validation reads 65,536-event windows without a root full-file mapping. Each
window must verify dtype/fields/itemsize, non-negative feed latency and M4 event
order, while carrying the last exchange and local timestamps across window
boundaries. SHA256 remains a bounded streaming pass.

## Fixed memory and FD gates

The canonical preflight requires `/proc/meminfo` `MemAvailable >= 8 GiB` and
does not count swap. The exact check is repeated immediately before any future
canonical attempt. V2 also carries a **6 GiB current-RSS abort guard** sampled
after each CSV chunk, initial-run flush, merge-buffer/group boundary,
corrected-output flush and validation window. The 8 GiB value is deliberately a
fixed conservative safety gate; it is not a claim that V2 requires 8 GiB.

Both soft and hard `RLIMIT_NOFILE` must be at least 128. With fan-in 8, the
algorithm's live FD demand is structurally fixed rather than proportional to
number of daily runs.

## Scratch gate from structure, not Jan ratio

Scratch is disk and may scale with rows. Let `R` be an already-frozen raw row
count. Base rows are conservatively bounded near `2R` because raw rows are
preserved and snapshot batches add at most two clear records per batch.
Corrected rows are at most two per base row. The largest large-file coexistence
is therefore bounded near 544 bytes per raw row before headers/bookkeeping.

The preregistered gate is intentionally more conservative:

`required_scratch = 640 * frozen_raw_rows + 16 GiB`.

Using the already-frozen D5B Jan–Jul metadata gives:

| Day | Frozen raw rows | Required scratch bytes | Approx GiB |
|---|---:|---:|---:|
| 2026-02-01 | 172,721,707 | 127,721,761,664 | 118.95 |
| 2026-03-01 | 145,757,298 | 110,464,539,904 | 102.88 |
| 2026-04-01 | 129,067,640 | 99,783,158,784 | 92.93 |
| 2026-05-01 | 104,234,425 | 83,889,901,184 | 78.13 |
| 2026-06-01 | 165,502,465 | 123,101,446,784 | 114.65 |
| 2026-07-01 | 172,067,693 | 127,303,192,704 | 118.56 |

No raw file is opened to compute these values.

## Required proof sequence

D6R8C does not authorize implementation execution. After CI green:

1. **D6R8D** — implement V2 and test synthetic-only. Fixtures must force more
   than eight runs and at least three hierarchical merge levels, verify exact
   fieldwise parity with the old converter, exercise cleanup/atomic promotion,
   and record the RSS guard behavior.
2. **D6R8E** — separately freeze exact D6R2B Jan 10-minute paths and hashes,
   then perform old-vs-V2 real-slice parity. Full-day Jan stays untouched.
3. **D6R8F** — only after the above pass, freeze full-day resource preflight and
   the first new-day attempt contract.

Only after those gates can any Feb–Jul raw day be considered for opening.

## Closed surfaces

D6R8C authorizes no market-data open, no Jan canonical NPY open, no D6R4B or
D6R5C rerun, no Feb–Jul conversion, no August, no September+, no non-BTC, no
112 replay, no policy execution, no historical PnL, no economic arena, no
network acquisition, no Railway, and no live trading.
