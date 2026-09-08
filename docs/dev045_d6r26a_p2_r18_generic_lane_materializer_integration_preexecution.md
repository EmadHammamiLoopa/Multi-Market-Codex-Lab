# DEV045 D6R26A P2 R18 — Generic lane materializer integration preexecution

Parent R17 GREEN HEAD:

`0ec427c4466200d0f14626609e02a535d0738bdf`

## Purpose

R18 freezes the final per-lane materialization pipeline before the complete
R4 campaign binding exists.

It composes already-frozen components rather than replacing them:

1. R4 `LaneArtifact` identity and partition contract.
2. R8A write-temp → fsync → hash verify → atomic rename-once publisher.
3. R14 exact real-engine fill-path semantics.
4. R15 sequential same-engine lane lifecycle.
5. R16 exact R1 canonical-row and bounded Parquet serialization.
6. R17 feed-bound EOF policy and shared dense once/day feature-cache contract.

## Dense shared-cache consumer

R18 implements the consumer shape for the R17 cache:

- int64 decision timestamps;
- int64 best bid/ask ticks;
- float64 `[decision, 8 side×distance cases, 25 features]`;
- no raw event array retained in the lane cache;
- no decoder/book/flow Python history retained;
- read-only NumPy arrays;
- exact R17 byte accounting;
- maximum 256 MiB frozen by R17.

R18 does **not** implement another historical raw-feature pass.

The production cache must still be built exactly once per opened day by the
future final binding. Every one of the 40 lanes must consume that same cache.

## Generic lane materializer

`materialize_lane_partition` accepts:

- a frozen source identity;
- one R1 LaneSpec;
- feed bounds;
- the shared dense cache;
- an iterable of already-frozen candidate execution records;
- a destination root.

Rows are generated lazily and handed directly to the R16 serializer.
There is no full-day Python row list.

Only one compressed partition payload is retained at a time because this is
the already-frozen R16/R8A interface.

The resulting object is the exact R4 `LaneArtifact`.

## Exact-engine CI

R18 has two synthetic exact-engine integration probes.

### Sequential no-fill lane

R15 runs three decisions:

- 31 s
- 36 s
- 41 s

on the same patched hftbacktest engine.

The results then pass through:

`dense shared cache → R16 rows → Parquet → R8A atomic artifact`

The three no-fill rows must remain exact canonical R1 rows.

### Fill path

R14 runs the exact BID/D0 real-engine fill probe.

Its frozen fill and markout labels pass unchanged through the same canonical
row/Parquet/atomic artifact path.

Therefore R18 verifies both no-fill and fill materialization.

## Still sealed

R18 does NOT:

- bind the complete R4 RunnerHooks;
- verify/open Jan–Jul historical sources;
- build the real once/day cache;
- create the R3 execution authorization;
- write the attempt marker;
- start any historical candidate lane;
- write canonical Jan–Jul labels;
- fit models;
- calculate PnL;
- open August;
- open September+;
- open non-BTC data.

Explicitly:

`P2_ATTEMPT_CONSUMED = False`

## Next after R18 GREEN

The next layer is the final R4 execution-binding preauthorization surface.

That layer may bind:

- seven-source precheck;
- one source open per day;
- once/day real feature-cache construction;
- forty sequential lane executors consuming the shared cache;
- R18 partition materialization;
- partition verification;
- source/backtest/memmap close ordering.

It must still remain historical-sealed until a separate explicit one-shot
authorization step.

No Jan–Jul historical execution is authorized by R18.
