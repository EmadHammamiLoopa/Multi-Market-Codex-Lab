# Multi-Market Codex Lab — Current Handoff through R27P32

Updated: 2026-09-13

## Immutable prior outcomes

- R27P24: `INVALID_ENGINEERING_PRECONDITION_SOURCE_PATH`; rerun forbidden.
- R27P25: `INVALID_RESULT_NOT_DURABLY_CAPTURED`; rerun forbidden.
- R27P26: valid `SCIENTIFIC_MEMORY_FAIL`; rerun forbidden.
  - frozen result commit: `4aeacf59ad296456410215ac52f9ee9184fa0a87`
  - peak worker RSS: `12,887,650,304 bytes` = `12.002559661865234 GiB`
  - excess over 12 GiB: `2,748,416 bytes` = `2.62109375 MiB`
- R27P27: valid `SCIENTIFIC_MEMORY_FAIL`; rerun forbidden.
  - execution HEAD: `a62579c6952dd140621675c5c4794eaf1cf27e8f`
  - frozen result commit: `30c645f3fba1eda011c8f5ca6f96a3721052a7aa`
  - frozen result branch: `research/dev045-m6-d6r26a-p2-r27p27-july-worst-case-rss-result-frozen`
  - peak worker RSS: `12,888,293,376 bytes` = `12.003158569335938 GiB`
  - excess over 12 GiB: `3,391,488 bytes` = `3.234375 MiB`
  - minimum system MemAvailable: `35,697,651,712 bytes` = `33.246028900146484 GiB`
  - worker return code: `-15`
  - worker result absent; stdout/stderr empty
  - `P2_ATTEMPT_CONSUMED=NO`
- The 12 GiB worker RSS ceiling remains binding. Threshold widening is forbidden as a rescue.

## R27P28 — windowed file-backed synthetic preflight

Experiment: `DEV045-D6R26A-P2-R27P28`

GREEN HEAD: `0792fd992870081a9880a37aa6f5a0e05ffe41f3`

Frozen branch: `research/dev045-m6-d6r26a-p2-r27p28-windowed-file-backed-synthetic-preflight-frozen`

Dedicated CI:
- run `34715145539`
- job `103610947812`
- conclusion `success`
- `6 passed`
- `R27P28_CI_EXECUTION_SURFACES_CLOSED=PASS`

Key design:
- full logical output capacity remains unchanged: 11 raw buffers, `265 bytes/event`;
- full-capacity files are created on disk;
- only bounded row windows are memmapped at a time;
- each window is flushed and unmapped before the next;
- exact bytes, dtypes, shapes, row offsets and full file sizes are proven synthetically.

## R27P29 — stateful windowed raw synthetic parity

Experiment: `DEV045-D6R26A-P2-R27P29`

GREEN HEAD: `ee53aa5f9fc597e253d73ddbcf1f241a8bd1c9cb`

Frozen branch: `research/dev045-m6-d6r26a-p2-r27p29-stateful-windowed-raw-synthetic-parity-frozen`

Dedicated CI:
- run `34716655575`
- job `103615006481`
- conclusion `success`
- `4 passed in 1235.04s`
- `R27P29_CI_EXECUTION_SURFACES_CLOSED=PASS`

R27P29 proves exact R27P6 raw semantics while carrying book/timestamp state across bounded input chunks and independent bounded output mappings. It preserves no-flush-at-ordinary-boundary semantics, final-only flush, exact raw bytes/counts/errors/observed-exchange, and one logical event pass.

## R27P30 — windowed raw corrected-context synthetic parity

Experiment: `DEV045-D6R26A-P2-R27P30`

GREEN HEAD: `64fe4292c06bb19df5117f5a474f099fe7f513ca`

Dedicated CI run: `34718235901`

R27P30 integrates the frozen R27P29 windowed raw producer into the corrected R27P18 context path and proves exact synthetic parity for corrected 25-feature semantics, context digest, midpoint index, R27P9 l5 amendment, R27P16/R10 volatility amendment, and one logical raw-event pass.

R27P30 remains a semantic integration proof only because its bridge rehydrates compact written prefixes into the historical downstream shape.

## R27P31 — stateful corrected-feature window synthetic parity

Experiment: `DEV045-D6R26A-P2-R27P31`

GREEN/frozen HEAD: `8492cca69ae6902cb6167f3e86fae44707fb6bc2`

Dedicated CI:
- run `34720214998`
- job `103624590789`
- conclusion `success`

R27P31 proves the corrected downstream feature path can be processed with bounded decision windows while preserving corrected feature semantics across window boundaries. This removes the downstream full-context residency blocker that remained after R27P30.

## R27P32 — real 5M composed RSS engineering proof

Experiment: `DEV045-D6R26A-P2-R27P32`

Preexecution/frozen runner HEAD: `a00be6fc5379caf0557106c93818d129e006b0b4`

Frozen result branch: `research/dev045-m6-d6r26a-p2-r27p32-5m-composed-rss-result-frozen`

Frozen result commit: `3df52a7d2a2ae98ba3757141715bc7af0eb0110d`

Frozen result artifact: `evidence/dev045_d6r26a_p2_r27p32_5m_composed_rss_result.json`

Classification: `ENGINEERING_5M_COMPOSED_PASS`

Exact scope:
- frozen July source only;
- first `5,000,000` source rows;
- no source rehash;
- R27P29 windowed raw + R27P31 stateful corrected-feature composition;
- raw input chunk rows `262,144`;
- feature decision chunk rows `64`;
- 12 GiB worker RSS ceiling;
- watchdog `0.25 s`;
- P2 remains unconsumed.

Observed memory:
- peak worker RSS: `652,070,912 bytes` = `0.6072883605957031 GiB`;
- peak PSS: `639,624,192 bytes`;
- peak Private_Clean: `482,115,584 bytes`;
- peak Private_Dirty: `149,401,600 bytes`;
- minimum MemAvailable: `36,610,191,360 bytes` = `34.09589767456055 GiB`;
- watchdog trip: `null`;
- worker return code: `0`.

Observed workload/output:
- raw book rows: `106,032`;
- raw flow rows: `4,275,511`;
- raw midpoint rows: `106,032`;
- raw chunks: `20`;
- max active raw output mapping: `69,468,160 bytes`;
- requested decisions: `2,828`;
- eligible decisions: `2,827`;
- feature chunks: `45`;
- max active feature output mapping: `103,936 bytes`;
- feature digest SHA256: `75609a77f8489d03798287f3244b98a56628ea940e4f8013518631f788f0a994`.

Timing:
- raw stage: `41.83454069799336 s`;
- feature stage: `2.0887714279961074 s`;
- worker logical elapsed: `43.92575191699143 s`;
- supervisor wall elapsed: `203.63205470200046 s` (includes process startup/Numba compile/watchdog lifecycle).

Interpretation:
- R27P32 is the first real historical composed proof that the new bounded architecture stays far below the unchanged 12 GiB ceiling on a nontrivial 5M-row prefix.
- Compared with R27P27 peak `12.003158569335938 GiB`, R27P32 peak is only `0.6072883605957031 GiB`.
- This does NOT yet prove full-July bounded memory; the next experiment must be a new full-day engineering RSS proof, not an R27P32 rerun.
- R27P32 rerun is forbidden after durable freeze.

## Frozen source and scientific thresholds

- source day: `2026-07-01`
- source: `/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy`
- rows: `181,084,390`
- bytes: `11,589,401,216`
- SHA256: `85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f`
- raw logical file-backed capacity: `47,987,363,350 bytes`
- worker RSS ceiling: `12 GiB`
- start admission: `MemAvailable >= 12 GiB`
- hard system abort: `MemAvailable < 8 GiB`
- watchdog poll interval: `0.25 s`
- worker count: one

## Next authorized direction

Create a fresh experiment ID for a single full-July engineering RSS proof using the frozen bounded architecture. Preserve the same source identity, 12 GiB RSS ceiling, start-memory admission, 8 GiB hard system abort, 0.25 s watchdog and one-worker rule. Do not turn this into P2 execution, labels, simulation, model fitting or PnL.

## Global governance

The following remain forbidden unless a later frozen experiment explicitly authorizes them:
- R27P26, R27P27 or R27P32 rerun;
- threshold widening;
- full Jan-Jul materialization;
- simulator lane;
- attempt marker;
- canonical labels;
- model fit;
- PnL;
- August;
- Sep-01+;
- non-BTC;
- `market-raw-archive` access.

`P2_ATTEMPT_CONSUMED=NO` remains binding.
