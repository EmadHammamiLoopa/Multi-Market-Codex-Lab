# DEV031-P1A — Raw Event-Time / Deep-Depth Feature Materialization Research Note

Status: `PREREGISTERED_BEFORE_REAL_MATERIALIZATION`

Parent result:
- DEV031-P0A = `DATA_READY_EVENT_DEPTH_RAW_L2`
- canonical artifact SHA256 =
  `97f43dccd6a119867aced5de372121a87bc912c20b26b6f032333b761c82cc01`

## Scientific role

P1A is a causal representation/materialization stage only.

It asks:

> Can a bounded raw-event/deep-depth feature family be reconstructed from the
> consumed Jan-Jul BTCUSDT raw L2 files and aligned exactly to the frozen P3
> selected T1 support without changing labels, decision timestamps, folds, or
> forward-data boundaries?

P1A does not fit a predictive model and does not report predictive metrics.

## Frozen successful anchors retained

The project does not discard successful experiments.

### DEV030-P3 — directional baseline retained

Frozen selected configuration:

`A / 120s / 16bp / 32s / PRICE / S1`

Task:

`T1 = DIRECTION_GIVEN_TOUCH`

Frozen pooled OOF support:
- 573
- LONG = 309
- SHORT = 264

Frozen validation support:
- Fold 1 Apr = 159 (86 LONG / 73 SHORT)
- Fold 2 May = 64 (40 LONG / 24 SHORT)
- Fold 3 Jun = 126 (60 LONG / 66 SHORT)
- Fold 4 Jul = 224 (123 LONG / 101 SHORT)

P3 remains the future P1B comparator.

### EXP024-P1 — opportunity-ranking success retained

Official status:

`PASS_PROSPECTIVE_VOLATILITY_RANKING_CONFIRMED`

This success is preserved for a later policy/composition stage.

It is deliberately NOT used in P1A/P1B as:
- a sample filter;
- a feature;
- a rank;
- a threshold;
- an eligibility gate.

Direction information must first improve independently.

### DEV030-P4 touch-head success retained

The T2 touch-vs-none head remains evidence that touch occurrence is learnable.
The failed two-head composition is also retained.

P1A/P1B do not rerun or compose the P4 head.

## Failure constraints carried forward

- P7 showed aggregated multiscale L1 OFI did not add stable incremental value.
- P8/P9/P10 closed the Jan-Jul PRICE-only sequence-representation family.
- Therefore P1A must not be another PRICE lag/sequence architecture.
- P1A must not merely restate the same aggregated L1 OFI feature family.

The new information family is raw event-time + deeper-than-top10 book structure.

## Research basis

The frozen representation is motivated by three established microstructure
findings:

1. queue imbalance can predict near-term price direction;
2. multi-level order-flow imbalance can contain information beyond L1;
3. stationary order-flow representations can outperform raw price-level state.

References:
- Gould & Bonart, Queue Imbalance as a One-Tick-Ahead Price Predictor in a
  Limit Order Book.
- Xu, Gould & Howison, Multi-Level Order-Flow Imbalance in a Limit Order Book.
- Kolm, Turiel & Westray, Deep Order Flow Imbalance: Extracting Alpha at
  Multiple Horizons from the Limit Order Book.

These references motivate the fixed family. They do not authorize feature
shopping after materialization or prediction results are observed.

## Why materialization precedes prediction

Raw L2 contains hundreds of millions of rows per development day.

Before any model fit, P1A must prove:
- exact causal raw reconstruction;
- deterministic event classification;
- finite feature values;
- exact P3 timestamp/label preservation;
- deterministic output hashes;
- no support shrink;
- no forward-data access.

If P1A fails, P1B is not authorized.

## Interpretation boundary

P1A PASS means only:
- the new raw event/depth feature family exists;
- it can be aligned exactly to frozen P3 support;
- it is ready for a separately frozen incremental predictive test.

It does not mean:
- higher accuracy;
- positive AUC delta;
- profitability;
- execution readiness;
- forward generalization.
