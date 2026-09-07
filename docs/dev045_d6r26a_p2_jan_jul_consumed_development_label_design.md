# DEV045-D6R26A-P2 — Jan–Jul Consumed-Development Candidate-Label Materialization Design

Parent P1: `e085c2cdfe5e7e1588bb3ce434389b3b014b0403`.

## Data role amendment

All currently available real BTCUSDT Jan–Jul days are explicitly classified as:

`DATA_ROLE = CONSUMED_DEVELOPMENT`

No Jan–Jul subset may be described as fresh replication, untouched qualification, or final holdout. The final real bucket remains unassigned, unopened, and outside Jan–Jul.

## Purpose

P2 will materialize causal candidate-level fill and markout labels plus local-only decision features for Gen-2 development. P2 does not fit models, select thresholds, run a quote engine, compute PnL, or run an economic arena.

## Frozen candidate surface

At every valid 1-second decision epoch after a 30-second causal feature warmup:

- sides: BID, ASK
- passive distances: 0, 1, 2, 4 ticks
- size: 0.001 BTC
- order type: LIMIT
- time in force: GTX post-only
- primary latency: 250/250 ms
- queue model: risk-adverse
- exchange model: partial-fill

Five phase cohorts per side/distance isolate 5-second candidate lifetimes, giving 40 lanes/day and 280 Jan–Jul lanes total.

## Row grain

One row represents exactly:

`decision_epoch × side × distance`

Fill/markout horizons are represented as columns/structured fields on that row rather than duplicated rows.

## Fill labels

P1 semantics remain binding:

- fill horizons originate at decision-local time
- any-fill state is FILLED / NOT_FILLED / CENSORED
- partial fills remain first-class
- end-of-source candidates are retained with censoring
- censored values are never converted to observed no-fill
- post-only exchange rejection is an observed no-fill

## Markout labels

Markout horizons originate at each fill's exchange execution timestamp. The target is side-signed fill-price-to-future-BBO-mid movement. Spread capture is already contained in fill price and is not added separately.

## Features

Only the P0 local A0 feature families are materialized. Every value must satisfy:

`feature_observable_local_time <= decision_local_time`

Rows with invalid or incomplete causal feature history are not silently dropped; materializer output must retain explicit eligibility/missingness state so support can be audited.

## Output

Canonical output format is Parquet with Zstandard compression, partitioned by:

`day × side × distance × phase`

Every partition receives byte-count and SHA256 identity in an immutable per-day manifest. Processing is one day at a time and bounded-memory. Independent lanes may run in parallel up to eight workers without changing label semantics.

## Historical source identity

P2-R1 must inherit exact frozen DEV045 Jan–Jul source identities. Any path/hash/size mismatch fails closed before that source is opened. Reconversion, rematerialization, backfill, interpolation, or network acquisition is not authorized.

## Development-only interpretation

After P2 materialization, Jan–Jul may be used for temporal/blocked OOF Gen-2 development. Random-row splitting is forbidden. No result from Jan–Jul may be called independent replication.

Independent evidence remains reserved for:

1. frozen Gen-2 champion;
2. frozen synthetic/adversarial robustness suite;
3. final untouched one-shot real bucket;
4. forward;
5. paper/shadow;
6. tiny real.

## Closed in P2 design commit

- historical source open/hash: NO
- candidate simulation: NO
- canonical label write: NO
- model fit/selection: NO
- threshold tuning: NO
- PnL/economic arena: NO
- final real bucket open: NO
- August: NO
- September+: NO
- non-BTC: NO
- network acquisition: NO
- live trading: NO

Next gate: `D6R26A_P2_R1_CANONICAL_LABEL_MATERIALIZER_IMPLEMENTATION_PREAUTH`.
