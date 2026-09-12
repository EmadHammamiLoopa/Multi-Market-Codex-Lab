# Multi-Market Codex Lab — R27P26 Preexecution GREEN

Updated: 2026-09-12

## Prior immutable results

- R27P24: `INVALID_ENGINEERING_PRECONDITION_SOURCE_PATH`; rerun forbidden.
- R27P25: `INVALID_RESULT_NOT_DURABLY_CAPTURED`; rerun forbidden.
- `P2_ATTEMPT_CONSUMED=NO` remains binding.

## R27P26 preexecution

Experiment: `DEV045-D6R26A-P2-R27P26`

Purpose: rerun the intended July worst-case full-day candidate-only RSS proof under a new experiment ID while durably persisting supervisor telemetry and final outcome so terminal closure cannot erase classification evidence.

Original branch:

`research/dev045-m6-d6r26a-p2-r27p26-durable-supervisor-telemetry-preexecution`

Exact GREEN HEAD:

`4a2190032bf68d990d5cb0ffdb09a7844f14495a`

Frozen branch:

`research/dev045-m6-d6r26a-p2-r27p26-durable-supervisor-telemetry-preexecution-frozen`

Dedicated CI:

- run `34710406795`
- job `103598026513`
- status `completed`
- conclusion `success`
- preexecution tests `success`
- CI real-execution closure proof `success`

## Frozen source and thresholds

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

`/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_r27p26_jul_full_day_rss`

Durable evidence written during execution:

- `supervisor_telemetry.json` — atomically updated every watchdog poll and before any watchdog termination.
- `supervisor_outcome.json` — atomically written before terminal-dependent reporting.
- `worker_result.json` — written on successful worker completion.

## Governance

No reference rerun, durable Jan-Jul materialization, simulator lane, attempt marker, canonical labels, model fit, PnL, August, Sep-01+, non-BTC, or market raw archive access is authorized by R27P26.

After the one authorized local R27P26 run, preserve scratch regardless of PASS/FAIL/INVALID and freeze the exact durable outcome before any successor decision.
