# Multi-Market Codex Lab — R27P30 GREEN / R27P31 Preexecution

Updated: 2026-09-12

## Immutable prior outcomes

- R27P24: `INVALID_ENGINEERING_PRECONDITION_SOURCE_PATH`; rerun forbidden.
- R27P25: `INVALID_RESULT_NOT_DURABLY_CAPTURED`; rerun forbidden.
- R27P26: `SCIENTIFIC_MEMORY_FAIL`; rerun forbidden.
- R27P27: `SCIENTIFIC_MEMORY_FAIL`; rerun forbidden.
- R27P28: synthetic bounded-row file-backed output mapping GREEN and frozen.
- R27P29: stateful windowed raw-kernel synthetic parity GREEN and frozen.

`P2_ATTEMPT_CONSUMED=NO` remains binding.

## R27P30 GREEN and frozen

Experiment: `DEV045-D6R26A-P2-R27P30`

Branch:

`research/dev045-m6-d6r26a-p2-r27p30-windowed-raw-corrected-context-synthetic-parity`

Exact GREEN HEAD:

`64fe4292c06bb19df5117f5a474f099fe7f513ca`

Frozen branch:

`research/dev045-m6-d6r26a-p2-r27p30-windowed-raw-corrected-context-synthetic-parity-frozen`

Dedicated CI:

- run `34718235901`
- job `103619204229`
- status `completed`
- conclusion `success`
- corrected-context parity tests: `4 passed in 1398.74s`
- `R27P30_CI_EXECUTION_SURFACES_CLOSED=PASS`

R27P30 proved that the R27P29 stateful windowed raw path reproduces the exact corrected context semantics on the synthetic integration fixture, including:

- corrected 25-feature context parity;
- exact context digest;
- exact midpoint index bytes/hash;
- R27P9 CPython 3.13 compensated `l5_obi` amendment semantics;
- R27P16/R10 corrected rolling-volatility semantics;
- one logical raw-event pass.

R27P30 intentionally did **not** claim full-day bounded-memory readiness because downstream feature construction still contained O(full-day) allocations and whole-values copies.

## Downstream memory diagnosis after R27P30

Exact code inspection identified the remaining downstream residency hazards:

1. R27P5 allocates full-book `transition_ofi` and `transition_vol` arrays.
2. R27P5 allocates full requested-grid `out_dec`, `out_bid`, `out_ask`, and `out_values` arrays in RAM.
3. R27P9 applies the L5 amendment via `values.copy()`.
4. R27P16 precomputes another full-book transition-squared array and then applies volatility via `base.values.copy()`.

Therefore merely switching `out_values` to memmap would be insufficient. The successor must remove all known O(full-day) transition arrays/copies while preserving exact add/subtract order and the corrected amendment semantics.

## R27P31 preexecution

Experiment: `DEV045-D6R26A-P2-R27P31`

Design version:

`stateful-corrected-feature-window-synthetic-parity-v1`

Branch:

`research/dev045-m6-d6r26a-p2-r27p31-stateful-corrected-feature-window-synthetic-parity`

Current preexecution HEAD:

`80ba3c6bafbf3b16957835350eaaa11692c17396`

Dedicated CI run:

`34720089079`

Current status at handoff write: `queued`.

### R27P31 architecture

R27P31 is synthetic-only. It introduces a stateful corrected-feature successor with:

- state carried across decision chunks;
- file-backed final output files;
- bounded output mappings per decision chunk;
- inline CPython 3.13 compensated L5 semantics;
- inline corrected R10 volatility semantics;
- OFI transition values recomputed on demand rather than stored in full-day transition arrays;
- volatility transition-squared values materialized only for the bounded interval needed by each chunk;
- no R27P9 whole-values copy;
- no R27P16 whole-values copy;
- no full requested-grid feature output arrays in RAM.

Synthetic parity cases intentionally use decision chunk sizes `1`, `3`, and `7` to force state carry across boundaries.

### R27P31 readiness state

R27P31 does **not** authorize real historical data and does **not** claim the composed July pipeline is memory-safe yet.

Current explicit blockers:

- raw-input bounded-window mapping for the composed pipeline is not yet proven;
- density-sensitive RSS behavior across a larger synthetic/engineering fixture is not yet proven;
- full-day bounded memory is not yet proven;
- global worst-case full-day bounded memory is not yet proven;
- canonical execution is not ready.

`READINESS_BLOCKER=RAW_INPUT_MAPPING_AND_COMPOSED_PIPELINE_RSS_NOT_YET_PROVEN`

All real execution surfaces remain closed:

- no July source open;
- no Jan-Jul rerun;
- no simulator;
- no PnL;
- no model fit;
- no attempt marker;
- no canonical labels;
- no August;
- no Sep+;
- no non-BTC;
- no `market-raw-archive`.

`P2_ATTEMPT_CONSUMED=NO`.

## Next decision

Do not freeze R27P31 until its dedicated CI on exact HEAD `80ba3c6bafbf3b16957835350eaaa11692c17396` is `completed/success` and the execution-surface closure proof passes.

If R27P31 is GREEN, freeze that exact HEAD. The next successor should bind bounded raw-input mapping to the R27P29 raw producer and the R27P31 corrected feature consumer, then perform a synthetic/engineering composed-pipeline RSS proof before any new real July authorization.
