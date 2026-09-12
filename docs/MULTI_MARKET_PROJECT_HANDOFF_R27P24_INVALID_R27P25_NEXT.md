# Multi-Market Codex Lab — R27P24 INVALID / R27P25 Binding Successor

Updated: 2026-09-12

## R27P24 classification

`DEV045-D6R26A-P2-R27P24` is frozen as `INVALID_ENGINEERING_PRECONDITION_SOURCE_PATH`.

This is not a scientific memory FAIL.

Frozen invalid artifact branch:

`research/dev045-m6-d6r26a-p2-r27p24-source-path-precondition-invalid`

Invalid artifact commit:

`f86134bc067477f0f4cee686af09e0d6e51845b7`

Evidence:

- preregistered source path: `/home/emadh/Multi-Market/runtime/dev045_d6r4b/output/BTCUSDT_2026-07-01.npy`
- preregistered path existed at execution: `NO`
- actual discovered July source: `/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy`
- actual discovered bytes: `11,589,401,216`
- worker result: `R27P24Error source_missing`
- worker result JSON: absent
- source opened: `NO`
- source SHA rehash completed: `NO`
- context build started: `NO`
- scientific RSS result: absent
- scientific RSS gate: not evaluated
- P2 attempt consumed: `NO`

The R27P24 scratch residue must be preserved and must not be reused or auto-deleted:

`/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_r27p24_jul_full_day_rss`

R27P24 must not be rerun.

## Frozen July identity remains unchanged

- day: `2026-07-01`
- rows: `181,084,390`
- bytes: `11,589,401,216`
- SHA256: `85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f`

Correct local source path discovered by read-only forensic:

`/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy`

## Binding successor

Use a new experiment ID: `DEV045-D6R26A-P2-R27P25`.

R27P25 must repeat the intended July worst-case full-day candidate-only RSS proof, but with the corrected source path and a new scratch root.

No scientific threshold may change from R27P24:

- process RSS ceiling: `12 GiB`
- start admission: `MemAvailable >= 12 GiB`
- hard system-memory abort: `MemAvailable < 8 GiB`
- watchdog interval: `0.25 s`
- raw file-backed capacity: `47,987,363,350 bytes`
- disk headroom: `16 GiB`
- worker count: one Python worker

New R27P25 scratch must not reuse R27P24 residue.

All execution restrictions remain binding:

- no reference rerun
- no durable Jan-Jul materialization
- no simulator lane
- no attempt marker
- no canonical labels
- no model fit
- no PnL
- no August
- no Sep-01+
- no non-BTC
- `P2_ATTEMPT_CONSUMED=NO`

R27P25 must have dedicated preexecution tests and CI GREEN before any real July source open.
