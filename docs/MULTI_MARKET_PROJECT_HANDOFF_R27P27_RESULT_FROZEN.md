# Multi-Market Codex Lab — R27P27 Result Frozen

Updated: 2026-09-12

## Immutable prior outcomes

- R27P24: `INVALID_ENGINEERING_PRECONDITION_SOURCE_PATH`; rerun forbidden.
- R27P25: `INVALID_RESULT_NOT_DURABLY_CAPTURED`; rerun forbidden.
- R27P26: valid `SCIENTIFIC_MEMORY_FAIL`; rerun forbidden.
  - result commit: `4aeacf59ad296456410215ac52f9ee9184fa0a87`
  - peak worker RSS: `12,887,650,304 bytes` = `12.002559661865234 GiB`
  - excess over 12 GiB: `2,748,416 bytes` = `2.62109375 MiB`

## R27P27 immutable execution identity

Experiment: `DEV045-D6R26A-P2-R27P27`

Design: `thin-isolated-worker-rss-preexecution-v1`

Authorized execution/frozen preexecution HEAD:

`a62579c6952dd140621675c5c4794eaf1cf27e8f`

Frozen preexecution branch:

`research/dev045-m6-d6r26a-p2-r27p27-thin-worker-rss-preexecution-frozen`

Dedicated CI before local execution was GREEN:

- run `34713035325`
- job `103605151266`
- conclusion `success`

## R27P27 local July worst-case result

Classification: `SCIENTIFIC_MEMORY_FAIL`

Return code: `3`

Durable supervisor observation:

- supervisor peak worker RSS: `12,888,293,376 bytes` = `12.003158569335938 GiB`
- unchanged ceiling: `12,884,901,888 bytes` = `12 GiB`
- excess over ceiling: `3,391,488 bytes` = `3.234375 MiB`
- minimum system MemAvailable: `35,697,651,712 bytes` = `33.246028900146484 GiB`
- poll count: `6,266`
- approximate elapsed from 0.25 s polling: `1,566.5 s`
- trip reason: `worker_rss_above_12_gib:12888293376`
- telemetry state: `TRIP_RECORDED_BEFORE_TERMINATE`
- worker return code: `-15`
- worker result: absent because supervisor terminated after the scientific RSS trip
- worker stdout: empty
- worker stderr: empty

This is a valid scientific memory failure, not an invalid engineering run.

## Comparison with R27P26

- R27P26 peak: `12,887,650,304 bytes`
- R27P27 peak: `12,888,293,376 bytes`
- R27P27 minus R27P26: `643,072 bytes` = `0.61328125 MiB`

Interpretation: the thin-worker/import/heap trimming architecture did not establish bounded-memory operation under the frozen 12 GiB gate and did not materially reduce the observed peak. The next engineering successor should target the dominant full-day/file-backed resident-memory path, not repeat import-only or heap-only trimming.

## Frozen result artifact

Result branch:

`research/dev045-m6-d6r26a-p2-r27p27-july-worst-case-rss-result`

Frozen result commit:

`30c645f3fba1eda011c8f5ca6f96a3721052a7aa`

Frozen result branch:

`research/dev045-m6-d6r26a-p2-r27p27-july-worst-case-rss-result-frozen`

Artifact:

`evidence/dev045_d6r26a_p2_r27p27_july_worst_case_rss_result.json`

R27P27 rerun is forbidden. Threshold widening under R27P27 is forbidden.

## Source and scientific memory contract remain unchanged

- source day: `2026-07-01`
- source: `/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy`
- rows: `181,084,390`
- bytes: `11,589,401,216`
- SHA256: `85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f`
- raw file-backed capacity: `47,987,363,350 bytes`
- worker RSS ceiling: `12 GiB`
- start admission: `MemAvailable >= 12 GiB`
- system abort: `MemAvailable < 8 GiB`
- watchdog: `0.25 s`
- worker count: one

## P2 and sealed-surface governance

Observed after R27P27:

- P2 attempt marker: absent
- P2 failure marker: absent
- canonical manifest: absent
- `P2_ATTEMPT_CONSUMED=NO`

Still forbidden:

- simulator
- canonical label write
- full Jan-Jul materialization
- model fit
- PnL
- August
- Sep-01+
- non-BTC
- market-raw-archive

## Engineering diagnosis for successor design

R27P20 allocates eleven full-length `numpy.memmap` outputs totaling `265 bytes/event`; for the July source this is about `47.99 GB` of file-backed address space. R27P21 writes those mappings directly in a single compiled pass. File-backed mappings avoid anonymous allocation, but pages dirtied by sequential writes can still become resident and count toward process RSS. R27P27 changed process isolation/import timing and heap trimming but left this full-length write architecture unchanged.

Therefore the next successor must receive a new experiment ID and should test a residency-control architecture while preserving exact raw/context semantics. Candidate engineering directions include bounded window/chunk mappings with deterministic flush/unmap/reopen, or explicit page-residency release between bounded regions if parity can be proven. Do not change the 12 GiB gate as a rescue.

## Binding next step

Create a new preexecution successor after proving synthetic exact parity for the chosen bounded-residency architecture. Do not rerun R27P27 and do not consume P2 during engineering validation.
