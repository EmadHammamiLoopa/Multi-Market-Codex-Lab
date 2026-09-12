# Multi-Market Codex Lab — R27P27 Preexecution GREEN

Updated: 2026-09-12

## Prior immutable outcomes

- R27P24: `INVALID_ENGINEERING_PRECONDITION_SOURCE_PATH`; rerun forbidden.
- R27P25: `INVALID_RESULT_NOT_DURABLY_CAPTURED`; rerun forbidden.
- R27P26: valid `SCIENTIFIC_MEMORY_FAIL`; rerun forbidden.
  - authorized execution HEAD: `4a2190032bf68d990d5cb0ffdb09a7844f14495a`
  - frozen result commit: `4aeacf59ad296456410215ac52f9ee9184fa0a87`
  - supervisor peak worker RSS: `12,887,650,304 bytes` = `12.002559661865234 GiB`
  - excess over 12 GiB ceiling: `2,748,416 bytes` = `2.62109375 MiB`
  - minimum system MemAvailable: `35,323,023,360 bytes` = `32.89712905883789 GiB`
  - poll count: `7,383`
  - trip reason: `worker_rss_above_12_gib:12887650304`
  - `P2_ATTEMPT_CONSUMED=NO`
- The 12 GiB worker RSS ceiling remains binding; threshold widening is not authorized as a rescue.

## R27P27 preexecution

Experiment: `DEV045-D6R26A-P2-R27P27`

Purpose: engineering memory-reduction successor to R27P26. Preserve the same July source, scientific semantics, memory thresholds, watchdog cadence, and governance while reducing avoidable process/import memory before the full-day build.

Original branch:

`research/dev045-m6-d6r26a-p2-r27p27-thin-worker-rss-preexecution`

Exact GREEN HEAD:

`a62579c6952dd140621675c5c4794eaf1cf27e8f`

Frozen branch:

`research/dev045-m6-d6r26a-p2-r27p27-thin-worker-rss-preexecution-frozen`

The frozen branch points exactly to the GREEN HEAD above.

Dedicated CI:

- run `34713035325`
- job `103605151266`
- status `completed`
- conclusion `success`
- fast preexecution contract tests: `success`
- CI real-execution closure proof: `success`

## Engineering-only memory reduction

R27P27 does not change the scientific gate. The worker is isolated and thin:

- supervisor does not import the heavy execution stack;
- worker verifies preattempt governance and source identity before heavy imports;
- worker does not import R27P25 or R27P26 execution modules;
- heavy execution modules are imported only after source/governance verification;
- `gc.collect()` is called before the full-day build;
- `malloc_trim(0)` is attempted before the full-day build;
- durable supervisor telemetry/outcome semantics are retained.

## Frozen source and thresholds

- source day: `2026-07-01`
- source: `/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy`
- rows: `181,084,390`
- bytes: `11,589,401,216`
- SHA256: `85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f`
- raw file-backed capacity: `47,987,363,350 bytes`
- worker RSS ceiling: `12 GiB`
- start admission: `MemAvailable >= 12 GiB`
- hard system abort: `MemAvailable < 8 GiB`
- watchdog poll interval: `0.25 s`
- worker count: one

New scratch root:

`/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_r27p27_jul_full_day_rss`

Durable execution evidence:

- `supervisor_telemetry.json`
- `supervisor_outcome.json`
- `worker_result.json` on successful worker completion
- `worker.stdout.log`
- `worker.stderr.log`

## Governance

R27P27 authorizes exactly one local July worst-case full-day candidate-only RSS proof from the frozen HEAD above. It does not authorize a reference rerun, R27P26 rerun, full Jan-Jul materialization, simulator lane, attempt marker, canonical labels, model fit, PnL, August, Sep-01+, non-BTC, or market-raw-archive access.

`P2_ATTEMPT_CONSUMED=NO` remains binding.

Preserve the R27P27 scratch directory and durable outcome regardless of PASS / SCIENTIFIC_MEMORY_FAIL / INVALID_OR_ENGINEERING_ERROR. Do not rerun R27P27 after an outcome exists without a separately frozen successor decision.