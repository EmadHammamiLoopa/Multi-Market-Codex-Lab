# DEV031-P1A — Frozen Raw Event-Time / Deep-Depth Materialization Design

Status: `DESIGN_FROZEN_BEFORE_IMPLEMENTATION_OR_REAL_RAW_READ`

Experiment:
`DEV031-P1A`

Design version:
`event-depth-materialization-v1`

## 1. Exact task lineage

P1A inherits exactly the frozen DEV030-P3 selected T1 configuration:

- symbol = BTCUSDT
- task = `DIRECTION_GIVEN_TOUCH`
- target = A
- horizon = 120 seconds
- barrier = 16 bp
- sequence window = 32 seconds
- P3 representation = PRICE S1
- P3 PRICE feature count = 23

No target/window/task search is allowed.

## 2. Exact development days

Only the already-consumed development days:

- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

Raw root:

`/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw/incremental_book_L2/BTCUSDT`

Forbidden:
- Aug-01
- Aug-30
- Sep-01+
- Railway
- archive bucket
- abundant-love
- ETH/SOL
- trades
- external data

## 3. Frozen provenance dependencies

P1A canonical execution must verify:

### P0A

Artifact:
`/home/emadh/Multi-Market/evidence/dev031_p0a_event_depth_raw_l2_v1/DEV031_P0A_EVENT_DEPTH_RAW_L2_RESULT.json`

SHA256:
`97f43dccd6a119867aced5de372121a87bc912c20b26b6f032333b761c82cc01`

Required terminal status:
`DATA_READY_EVENT_DEPTH_RAW_L2`

### P2C

Artifact:
`/home/emadh/Multi-Market/evidence/dev030_p2c_direction_materialization_v1/DIRECTION_DATASET_MATERIALIZATION.json`

SHA256:
`a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0`

### P3

Artifact:
`/home/emadh/Multi-Market/evidence/dev030_p3_campaign1_v1/DEV030_P3_CAMPAIGN1_RESULT.json`

SHA256:
`f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`

The selected configuration must reconcile exactly to:
`A / 120 / 16 / 32 / PRICE`.

## 4. Causal time semantics

P1A uses the frozen practical availability semantics of the historical
Phase0DL reconstruction used to create the P3 inputs:

- raw rows are required to have nondecreasing `local_timestamp`;
- rows sharing identical `local_timestamp` form one complete atomic group;
- all rows in a group with `local_timestamp <= decision_timestamp` are
  available at that decision;
- a decision never consumes a group with local timestamp greater than the
  decision timestamp;
- exchange timestamp is recorded for provenance/diagnostics but does not move
  a row earlier than its local availability time.

Snapshot groups reset and rebuild the book exactly as in P0A.

Snapshot rows are not counted as market-event flow observations.

## 5. Raw event classification

For each non-snapshot L2 update at side/price:

Let:
- `q_old` = quantity immediately before the update;
- `q_new` = supplied amount;
- `delta_q = q_new - q_old`.

Classification:

- insertion:
  `q_old == 0 and q_new > 0`
- deletion:
  `q_old > 0 and q_new == 0`
- replenishment:
  `q_old > 0 and q_new > q_old`
- depletion:
  `q_old > q_new > 0`
- unchanged:
  `q_new == q_old`

Unchanged updates do not contribute to quantity-flow numerators/denominators
but remain part of raw-update intensity.

For quantity flow:
- bid side sign = +1
- ask side sign = -1
- signed flow = side_sign * delta_q

This makes:
- bid additions/increases positive;
- ask additions/increases negative;
- bid removals/decreases negative;
- ask removals/decreases positive.

## 6. Distance-to-mid classification

For each non-snapshot update, distance is frozen using the valid book mid
immediately before its local-timestamp group is applied.

Distance in bps:

`10000 * abs(event_price - pre_group_mid) / pre_group_mid`

Fixed cumulative bands:

- <= 5 bp
- <= 15 bp
- <= 50 bp

If the pre-group book is not valid, the update cannot contribute to
distance-banded quantity-flow features.

No alternative band is permitted after real materialization begins.

## 7. Frozen 26-feature EVENT_DEPTH block

### A. Deep static book state at decision time — 8 features

1. `obi_l20`
2. `obi_l50`
3. `log1p_bid_depth_l20`
4. `log1p_ask_depth_l20`
5. `log1p_bid_depth_l50`
6. `log1p_ask_depth_l50`
7. `bid_depth_concentration_l10_l50`
8. `ask_depth_concentration_l10_l50`

Definitions:

`OBI_k = (bid_depth_k - ask_depth_k) / (bid_depth_k + ask_depth_k)`

Concentration:

`depth_l10 / depth_l50`

Depth sums use the best k live price levels on each side.

### B. Raw multi-depth quantity-flow imbalance — 12 features

Frozen trailing horizons:

- 1 second
- 4 seconds
- 16 seconds
- 32 seconds

For each horizon and each cumulative distance band 5/15/50 bp:

`flow_imbalance = sum(signed_delta_q) / sum(abs(delta_q))`

If the denominator is zero, the feature is exactly 0.0.

Feature order is horizon-major, then band-major:

- `flow_imbalance_1s_5bp`
- `flow_imbalance_1s_15bp`
- `flow_imbalance_1s_50bp`
- `flow_imbalance_4s_5bp`
- `flow_imbalance_4s_15bp`
- `flow_imbalance_4s_50bp`
- `flow_imbalance_16s_5bp`
- `flow_imbalance_16s_15bp`
- `flow_imbalance_16s_50bp`
- `flow_imbalance_32s_5bp`
- `flow_imbalance_32s_15bp`
- `flow_imbalance_32s_50bp`

### C. Event-type directional pressures over 32 seconds — 4 features

Count-based, bounded to [-1,1]:

- `insert_pressure_32s = (bid_insert - ask_insert)/(bid_insert + ask_insert)`
- `delete_pressure_32s = (ask_delete - bid_delete)/(ask_delete + bid_delete)`
- `replenish_pressure_32s = (bid_replenish - ask_replenish)/(bid_replenish + ask_replenish)`
- `deplete_pressure_32s = (ask_deplete - bid_deplete)/(ask_deplete + bid_deplete)`

Zero denominator => 0.0.

### D. Event intensity over 32 seconds — 2 features

- `log1p_non_snapshot_updates_32s`
- `log1p_distinct_local_groups_32s`

Total EVENT_DEPTH features = 26.

No additional feature is allowed inside P1A/P1B.

## 8. Frozen P3 support contract

P1A must reconstruct the exact selected P3 candidate using the frozen
DEV030 dataset builder.

For every day, P1A takes only rows where the frozen selected P3 candidate has:

`t1_common_valid == True`

P1A must preserve exactly:
- decision timestamp;
- T1 label;
- chronological order;
- class count;
- support SHA256.

No support shrink is allowed.

If any P3 T1 row lacks a finite 26-feature EVENT_DEPTH vector:

`FAIL_EVENT_DEPTH_EXACT_P3_SUPPORT_NOT_PRESERVED`

No matched-subset rescue is allowed.

## 9. Expected selected-candidate support

Before real materialization, the frozen lineage expects the selected A/32/PRICE
candidate to contain approximately 1,374 T1 rows across the seven development
days and exactly these OOF validation supports:

- Apr = 159
- May = 64
- Jun = 126
- Jul = 224

The canonical run must derive and verify exact values from frozen P2C/P3
provenance rather than trusting these prose counts.

## 10. Output representation

Canonical output directory:

`/home/emadh/Multi-Market/evidence/dev031_p1a_event_depth_materialization_v1`

Primary manifest:

`DEV031_P1A_EVENT_DEPTH_MATERIALIZATION.json`

Seven deterministic day data artifacts are also written, one per Jan-Jul day.

Each day artifact must contain exactly:
- selected P3 T1 decision timestamps;
- T1 labels;
- frozen 23 P3 PRICE S1 features;
- frozen 26 EVENT_DEPTH features.

No target outcomes beyond the frozen T1 labels are added.

## 11. Determinism

The canonical manifest records:
- execution commit;
- source hashes;
- raw input SHA256 per day;
- P3 aggregated input SHA256 per day;
- P0A/P2C/P3 artifact identities;
- feature-name order;
- per-day row/class counts;
- timestamp support SHA256;
- label SHA256;
- P3 PRICE matrix SHA256;
- EVENT_DEPTH matrix SHA256;
- day-artifact SHA256/bytes;
- fold support/class reconciliation;
- runtime guards.

All serialized arrays use deterministic dtype/order.

## 12. P1A PASS gates

PASS requires all of:

1. all seven exact raw files pass frozen P0A identity verification;
2. exact P2C artifact identity passes;
3. exact P3 artifact identity passes;
4. exact selected A/120/16/32/PRICE identity passes;
5. frozen P3 dataset reconstruction/support reconciliation passes;
6. every selected T1 timestamp obtains exactly 26 finite EVENT_DEPTH features;
7. no P3 support row is dropped or added;
8. labels are bitwise identical to frozen reconstructed P3 labels;
9. exact four chronological folds reconcile;
10. every feature satisfies its mathematical domain:
   - OBI/pressures/flow imbalance within [-1,1] up to floating tolerance;
   - log features finite and nonnegative;
   - concentration within [0,1] up to tolerance;
11. all forward/storage guards remain false;
12. no model fit or predictive metric is run.

PASS status:

`EVENT_DEPTH_EXACT_P3_SUPPORT_MATERIALIZED`

Failure status:

`FAIL_EVENT_DEPTH_EXACT_P3_SUPPORT_NOT_PRESERVED`

Operationally incomplete before a valid artifact:

`INCONCLUSIVE_EVENT_DEPTH_MATERIALIZATION`

## 13. No prediction in P1A

Forbidden:
- LogisticRegression
- AUC
- AP
- BA
- macro F1
- Brier
- log loss
- temporal null
- thresholding
- feature selection
- PnL
- EXP024 filtering
- P4 composition

## 14. P1B authorization boundary

Only a frozen P1A PASS may authorize DEV031-P1B.

P1B will be separately preregistered before fitting.

Planned P1B comparison, if authorized:

- C0 = exact frozen P3 PRICE S1, 23 features;
- C1 = C0 + all 26 frozen EVENT_DEPTH features, 49 total;
- same T1 support;
- same four expanding folds;
- same low-capacity train-only StandardScaler + L2 LogisticRegression family;
- no threshold optimization;
- probability-first incremental metrics and temporal null;
- no opportunity gate or PnL.

P1A itself makes no predictive claim.
