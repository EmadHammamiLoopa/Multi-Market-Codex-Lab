# Multi-Market Codex Lab — R27P29 Pending Synthetic Parity

Updated: 2026-09-12

## Immutable prior outcomes

- R27P24: `INVALID_ENGINEERING_PRECONDITION_SOURCE_PATH`; rerun forbidden.
- R27P25: `INVALID_RESULT_NOT_DURABLY_CAPTURED`; rerun forbidden.
- R27P26: valid `SCIENTIFIC_MEMORY_FAIL`; rerun forbidden.
- R27P27: valid `SCIENTIFIC_MEMORY_FAIL`; rerun forbidden.
  - execution HEAD: `a62579c6952dd140621675c5c4794eaf1cf27e8f`
  - frozen result commit: `30c645f3fba1eda011c8f5ca6f96a3721052a7aa`
  - peak worker RSS: `12,888,293,376 bytes` = `12.003158569335938 GiB`
  - excess over 12 GiB: `3,391,488 bytes` = `3.234375 MiB`
  - minimum system MemAvailable: `35,697,651,712 bytes` = `33.246028900146484 GiB`
  - `P2_ATTEMPT_CONSUMED=NO`
- The 12 GiB worker RSS ceiling remains binding. No threshold widening is authorized.

## R27P28 frozen GREEN

Experiment: `DEV045-D6R26A-P2-R27P28`

Purpose: synthetic proof that the existing 11 raw output buffers can be represented as full-capacity files while only bounded row windows are mapped at one time, preserving exact bytes/dtypes/shapes.

Branch:

`research/dev045-m6-d6r26a-p2-r27p28-windowed-file-backed-synthetic-preflight`

Exact GREEN HEAD:

`0792fd992870081a9880a37aa6f5a0e05ffe41f3`

Frozen branch:

`research/dev045-m6-d6r26a-p2-r27p28-windowed-file-backed-synthetic-preflight-frozen`

Dedicated CI:

- run `34715145539`
- job `103610947812`
- status `completed`
- conclusion `success`
- tests: `6 passed`
- execution-surface closure: `R27P28_CI_EXECUTION_SURFACES_CLOSED=PASS`

R27P28 remains synthetic-only and does not establish full-day bounded memory or canonical readiness.

## R27P29 current state

Experiment: `DEV045-D6R26A-P2-R27P29`

Design version: `stateful-windowed-raw-kernel-synthetic-parity-v1`

Branch:

`research/dev045-m6-d6r26a-p2-r27p29-stateful-windowed-raw-synthetic-parity`

Current HEAD:

`ee53aa5f9fc597e253d73ddbcf1f241a8bd1c9cb`

Dedicated CI run:

`34716655575`

Current CI state at handoff update: `queued`; conclusion not yet available.

R27P29 purpose is synthetic-only stateful raw-kernel parity across input chunk boundaries. It carries:

- local and exchange books across chunks;
- pending local/exchange timestamps and changed flags across chunks;
- last-local / last-exchange monotonicity state;
- observed-exchange state;
- independent output offsets for book, flow and midpoint streams;
- no synthetic flush at chunk boundaries;
- final flush only on the final chunk;
- bounded output mappings rather than full-file output mappings.

Parity requirements bind exact raw bytes, counts, error code and observed exchange against the existing R27P6 reference raw kernel, including boundary-stress chunk sizes.

## Governance

R27P29 is synthetic-only. It does not authorize real historical opening, source rehash, durable context publication, simulator lane, attempt markers, canonical labels, full Jan-Jul materialization, model fit, PnL, August, Sep+, non-BTC, or market-raw-archive access.

`P2_ATTEMPT_CONSUMED=NO` remains binding.

Do not freeze R27P29 or advance to downstream corrected-context windowing until the dedicated CI on exact HEAD `ee53aa5f9fc597e253d73ddbcf1f241a8bd1c9cb` is verified GREEN.
