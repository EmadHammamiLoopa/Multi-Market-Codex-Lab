# Multi-Market Codex Lab — R27P25 Preexecution GREEN / Local Execution Handoff

Updated: 2026-09-12

## R27P24 immutable classification

`DEV045-D6R26A-P2-R27P24` remains frozen as `INVALID_ENGINEERING_PRECONDITION_SOURCE_PATH`.

- not a scientific memory FAIL
- no real July source opened
- no scientific RSS result
- no rerun authorized
- `P2_ATTEMPT_CONSUMED=NO`

Frozen invalid artifact commit:

`f86134bc067477f0f4cee686af09e0d6e51845b7`

Preserve R27P24 scratch for forensics; do not reuse or auto-delete:

`/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_r27p24_jul_full_day_rss`

## R27P25 corrected successor

Experiment:

`DEV045-D6R26A-P2-R27P25`

Original preexecution branch:

`research/dev045-m6-d6r26a-p2-r27p25-corrected-july-source-worst-case-full-day-rss-preexecution`

Exact GREEN HEAD:

`c2633066a2543ffc1ed997caed6641e0b48f5ca9`

Frozen branch at the same exact SHA:

`research/dev045-m6-d6r26a-p2-r27p25-corrected-july-source-worst-case-full-day-rss-preexecution-frozen`

Dedicated CI:

- workflow run: `34706453008`
- job: `103587262200`
- status: `completed`
- conclusion: `success`
- exact head SHA: `c2633066a2543ffc1ed997caed6641e0b48f5ca9`
- preexecution tests: PASS
- CI real-execution closure proof: PASS

## Frozen corrected July source

- path: `/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy`
- day: `2026-07-01`
- rows: `181,084,390`
- bytes: `11,589,401,216`
- SHA256: `85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f`

## R27P25 immutable memory contract

- one corrected frozen July source only
- candidate-only full-day context build
- raw file-backed capacity: `47,987,363,350 bytes`
- disk headroom: `16 GiB`
- minimum free disk: `65,167,232,534 bytes`
- worker RSS ceiling: `12 GiB`
- pre-run `MemAvailable >= 12 GiB`
- hard system-memory abort if `MemAvailable < 8 GiB`
- watchdog poll interval: `0.25 s`
- one supervised Python worker
- source SHA256 rehash required before processing
- scratch root: `/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_r27p25_jul_full_day_rss`
- scratch reuse forbidden
- scratch auto-delete forbidden

## Execution interpretation

Return code `0` with `R27P25_RESULT=PASS_JUL_WORST_CASE_FULL_DAY_RSS_GATE` is the only PASS outcome.

Return code `3` is a valid scientific memory FAIL and must be frozen; do not rerun or widen thresholds.

Return code `2` is an INVALID/engineering error. Preserve scratch and inspect before any successor decision; do not silently rerun R27P25.

## Binding governance

- R27P24 rerun: forbidden
- R27P25 local execution: run once only after this GREEN/freeze
- reference rerun: forbidden
- durable Jan-Jul materialization: not authorized by this stage
- simulator lane: forbidden
- attempt marker write: forbidden
- canonical labels: forbidden
- model fit: forbidden
- PnL: forbidden
- August: sealed
- Sep-01+: sealed
- non-BTC: sealed
- market raw archive: sealed
- `P2_ATTEMPT_CONSUMED=NO`

After the one local R27P25 execution, freeze the exact observed result before deciding whether worst-case Jan-Jul bounded-memory engineering is proven and whether a later durable-context materialization stage can be designed.
