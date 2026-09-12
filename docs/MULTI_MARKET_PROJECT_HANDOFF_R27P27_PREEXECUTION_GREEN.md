# Multi-Market Codex Lab — Current Handoff through R27P30

Updated: 2026-09-12

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

Purpose: prove full logical raw-output files can be written byte-for-byte through bounded row mappings without mapping the full files concurrently.

GREEN HEAD:

`0792fd992870081a9880a37aa6f5a0e05ffe41f3`

Frozen branch:

`research/dev045-m6-d6r26a-p2-r27p28-windowed-file-backed-synthetic-preflight-frozen`

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
- exact bytes, dtypes, shapes, row offsets and full file sizes are proven synthetically;
- stateful raw-kernel chunking was intentionally not claimed at R27P28.

## R27P29 — stateful windowed raw synthetic parity

Experiment: `DEV045-D6R26A-P2-R27P29`

Purpose: preserve the exact R27P6 raw semantics while carrying book/timestamp state across bounded input chunks and bounded independent output mappings.

GREEN HEAD:

`ee53aa5f9fc597e253d73ddbcf1f241a8bd1c9cb`

Frozen branch:

`research/dev045-m6-d6r26a-p2-r27p29-stateful-windowed-raw-synthetic-parity-frozen`

Dedicated CI:

- run `34716655575`
- job `103615006481`
- status `completed`
- conclusion `success`
- `4 passed in 1235.04s`
- `R27P29_CI_EXECUTION_SURFACES_CLOSED=PASS`

R27P29 proves synthetically:

- stateful bid/ask books survive chunk boundaries;
- pending local/exchange timestamp state survives chunk boundaries;
- no artificial flush occurs at a chunk boundary;
- only the final chunk performs final flush semantics;
- book, flow and midpoint outputs use independent bounded offsets;
- exact raw byte parity against R27P6;
- exact counts, error code and observed-exchange semantics;
- one logical raw-event pass semantics.

The CI intentionally exercises very small chunk sizes including `1`, which is expensive because it repeatedly maps, flushes and unmaps output windows. This was a semantics stress test, not the intended real execution chunk size. The target default remains `262,144` rows.

## R27P30 — windowed raw corrected-context synthetic parity

Experiment: `DEV045-D6R26A-P2-R27P30`

Branch:

`research/dev045-m6-d6r26a-p2-r27p30-windowed-raw-corrected-context-synthetic-parity`

Current HEAD:

`64fe4292c06bb19df5117f5a474f099fe7f513ca`

Dedicated CI:

- run `34718235901`
- current state at handoff update: `in_progress`
- HEAD identity verified: `64fe4292c06bb19df5117f5a474f099fe7f513ca`

Purpose: integrate the frozen R27P29 windowed raw producer into the already corrected R27P18 context path and prove exact synthetic parity for the final corrected semantics:

- exact corrected 25-feature context parity;
- exact context digest;
- exact midpoint-index bytes/hash;
- exact R27P9 `l5_obi` amendment changed-cell count;
- exact R27P16/R10 volatility amendment changed-cell count;
- exactly one logical raw-event pass.

Important limitation: R27P30 uses synthetic rehydration of the compact R27P29 written prefixes into the historical R27P6-shaped raw tuple so the existing R27P18 downstream path can be compared exactly. Therefore R27P30 proves integration semantics only. It does NOT yet prove that downstream corrected-context residency is bounded for a full July day.

Binding R27P30 state:

- `SYNTHETIC_ONLY=True`
- `REAL_HISTORICAL_OPEN_AUTHORIZED=False`
- `DOWNSTREAM_FULL_DAY_BOUNDED_CONTEXT_COMPLETE=False`
- `FULL_DAY_BOUNDED_MEMORY_PROVEN=False`
- `GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN=False`
- `CANONICAL_EXECUTION_READY=False`
- `P2_ATTEMPT_CONSUMED=False`
- readiness blocker: `DOWNSTREAM_CONTEXT_RESIDENCY_NOT_YET_BOUNDED_FOR_FULL_DAY`

Do not freeze R27P30 or proceed to a historical July probe until its exact HEAD dedicated CI is `completed/success` and execution-surface closure passes.

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

## Global governance

The following remain forbidden unless a later frozen experiment explicitly authorizes them:

- R27P26 or R27P27 rerun;
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
