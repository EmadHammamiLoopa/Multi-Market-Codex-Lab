# Multi-Market Codex Lab — R26P1 Pre-Attempt Performance Stop

Updated: 2026-09-11

This milestone records the first real DEV045 D6R26A P2 R26P1 durable Jan–Jul materialization attempt and its intentional pre-attempt performance stop. It is documentation only and does not alter the experiment execution lineage.

## Exact execution lineage

- Branch: `research/dev045-m6-d6r26a-p2-r26p1-real-durable-materializer-preexecution`
- HEAD: `9b6b130a9663f5803c5a986fc22746cb5507fd0b`
- R26P1 dedicated CI was GREEN before real execution.
- Exact runtime: CPython 3.13.15, NumPy 2.2.6, PyArrow 25.0.1, hftbacktest 2.4.4 patched wheel.

## Real source verification

All seven frozen Jan–Jul BTC sources passed exact rows/bytes/SHA256 verification before any build began.

Frozen source registry SHA256 remains:

`97c631d621118d5cd4d294825dec545c92d85c62456403a6974ca38a70ece3f4`

No source identity defect was observed.

## R26P1 real build start

- Build log: `/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_execution_logs/r26p1_durable_materialization_9b6b130a9663f5803c5a986fc22746cb5507fd0b_20260910T174955Z.log`
- First batch: `2026-01-01,2026-02-01`
- Dynamic admission selected exactly 2 workers.
- Initial MemAvailable approximately 47.1 GB.
- Swap remained effectively zero.
- Both workers remained runnable at approximately 99.9% of one CPU core each.

After approximately 14.5 hours:

- completed durable days: `0/7`
- January: still IN_PROGRESS
- February: still IN_PROGRESS
- March–July: PENDING
- no global R26P1 completion manifest
- no simulator lane
- no canonical labels
- no model fit
- no PnL

The implementation was therefore judged operationally too slow for iterative research use. This is a performance/architecture finding, not a scientific hypothesis failure.

## Intentional stop snapshot

Snapshot time:

`2026-09-11T10:20:50+02:00`

Snapshot artifact:

`/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_execution_logs/R26P1_PREATTEMPT_PERFORMANCE_STOP_20260911T082050Z.txt`

January partial midpoint spool:

- path: `/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_durable_context_v1/.build/2026-01-01.52053.c0636a0b2bcf4cc69c006afd7b6b6815/exchange_midpoints.bin.tmp`
- bytes: `22020096`
- SHA256: `2ad78889c32a8dcd9f32cb1518b77e6a23bfa8256418f7d0926f64d77e9c8fba`

February partial midpoint spool:

- path: `/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_durable_context_v1/.build/2026-02-01.52054.6bf77e900e2a4692a35ff3b53e3c2428/exchange_midpoints.bin.tmp`
- bytes: `19922944`
- SHA256: `307f0b958594b88280e1cecb85adccbad5c28e09351289c1f9ccf032209707e6`

All three exact R26P1 PIDs were stopped deliberately. SIGINT did not fully stop the process tree, so SIGTERM was sent only to the exact recorded PIDs. Final wrapper return code was `143`, which records the intentional SIGTERM termination and is not a scientific FAIL.

Partial `.build` residue must remain preserved as forensic evidence. It is not a valid durable bundle and must never be reused as completed data.

## Canonical P2 attempt state after stop — CRITICAL

Verified after stop:

- `P2_ATTEMPT_CONSUMED=NO`
- canonical attempt marker absent
- canonical failure artifact absent
- canonical manifest absent
- completed durable day bundles: 0
- simulator run: NO
- canonical labels written: NO
- model fit: NO
- PnL: NO

Therefore the unique canonical P2 simulator attempt remains completely unconsumed.

The R26P1 wrapper printed `R26P1_REAL_MATERIALIZATION=FAIL` only because the deliberately terminated subprocess returned RC 143. Treat this as `PREATTEMPT_PERFORMANCE_ABORT`, not as a scientific experiment failure and not as canonical P2 attempt consumption.

## Performance diagnosis direction

Repository inspection of the frozen reference path shows the likely dominant cost is the Python raw-event execution surface, not memory pressure:

- R20 loops in Python over every raw event.
- Each row feeds both local and exchange streaming decoders.
- R9 `_BookState.observation()` sorts the full bid and ask dictionaries to construct full `BookObservation` tuples whenever a local timestamp group changed.
- `_BookState.valid()` and exchange midpoint emission repeatedly call `max(bids)` / `min(asks)`.
- R10 feature computation needs only the feature-semantic information, notably BBO/top-5/near-candidate depth plus bounded rolling windows; it does not require repeatedly materializing the entire L2 book history.

This strongly motivates a compiled/fused successor with exact output parity rather than simply increasing day-level worker count.

## Binding next step

Do NOT rerun R26P1 current real implementation automatically.

Next controlled successor must be an optimized R20-equivalent context builder, developed before any new full Jan–Jul materialization.

Requirements:

1. Preserve R9/R10/R13A/R17/R18/R19/R20 scientific semantics exactly.
2. Preserve one-pass causal ordering, local-group ordering, exchange-group ordering, EOF behavior, eligibility/warmup behavior, dense cache dtype/shape, midpoint record layout, and exact markout lookup semantics.
3. Use a compiled or otherwise substantially accelerated stateful event loop; Rust/PyO3 is a preferred candidate because the exact runtime already freezes Rust 1.98.1 and maturin 1.15.0.
4. Avoid repeated full-book Python sorting/materialization when only top-of-book/top-5/near-candidate state is required, while proving exact parity of the final durable surfaces.
5. Add deterministic synthetic parity tests against frozen R20, including clears, snapshots, depth updates, trades, same-timestamp groups, EOF, warmup boundaries, candidate distances, and midpoint output.
6. No historical source opening in CI.
7. Before a full real Jan–Jul rerun, perform a bounded benchmark/parity gate and freeze an explicit minimum speedup requirement.
8. Preserve current January/February partial residue; do not delete it automatically.
9. P2 attempt remains unconsumed throughout optimization work.

Recommended successor naming:

`DEV045-D6R26A-P2-R27P0` — accelerated context-engine design/parity freeze.

Then implementation successor:

`DEV045-D6R26A-P2-R27P1` — compiled accelerated context engine preexecution.
