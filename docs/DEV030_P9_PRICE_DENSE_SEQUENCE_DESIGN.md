# DEV030-P9 — PRICE Dense Sequence Linear v1

## Frozen status
Experiment ID: `DEV030-P9`
Design version: `price-dense-sequence-linear-v1`
Research question: Does one frozen dense causal PRICE sequence add stable direction-given-touch information beyond the successful P3 PRICE summary baseline?

This design is frozen before implementation and before any real Jan-Jul fit.

## Target and task
- Target: DEV030-P3 Target A
- Horizon: 120 seconds
- Barrier: 16 bp
- Entry latency / first-passage semantics: unchanged from frozen DEV030
- Task: DIRECTION_GIVEN_TOUCH
- Classes: LONG_FIRST vs SHORT_FIRST only
- Decision support, labels, ordering, and folds: must exactly reproduce P3/P8

## Window and dense representation
Window: 32 seconds.

Incremental channels only:
1. `spread_bps`
2. `microprice_minus_mid_bps`
3. `mid_log_return_250ms_bps`

Sampling:
- exactly one deterministic value per second;
- lags are exactly 32s, 31s, ..., 1s;
- oldest to newest within each channel;
- exact causal timestamps only;
- no interpolation;
- no forward fill;
- no backward fill;
- no value repair.

The incremental representation therefore contains:
- 32 values/channel
- 3 channels
- 96 incremental values total

If exact sequence extraction is impossible on the unchanged P3/P8 support using the canonical materialized source, implementation must fail closed before fitting. Support shrink is forbidden.

## Baseline and augmented model
C0:
- exact P8 probability-first baseline;
- exact 23 PRICE S1 summary features;
- exact frozen regularized logistic procedure and C grid.

C1:
- C0 plus the flattened 96-value dense PRICE sequence;
- total feature count = 119.

No additional engineered summaries are introduced.

## Model protocol
- Same L2 LogisticRegression family as P3/P8.
- Same frozen C grid: [0.01, 0.1, 1.0, 10.0].
- Train-only StandardScaler.
- Inner selection only on outer-training data.
- Probability-first selection order remains identical in spirit to P8: log loss, then Brier, then AUC, then smaller C.
- Threshold remains 0.5 for thresholded diagnostics.
- No class weighting/resampling.
- No calibration.

## Chronological folds
Must remain exactly:
1. January-March train -> April validation
2. January-April train -> May validation
3. January-May train -> June validation
4. January-June train -> July validation

## Frozen support invariants
Expected exact P3/P8 direction support:
- pooled support = 573
- pooled LONG_FIRST = 309
- pooled SHORT_FIRST = 264
- fold support = 159, 64, 126, 224
- fold LONG = 86, 40, 60, 123
- fold SHORT = 73, 24, 66, 101

Any support, label, fold, chronological ordering, class-count, or support-hash mismatch is a hard failure.

## Reproduction requirements
Before evaluating C1, implementation must:
- reproduce exact P3 M1 prediction hashes;
- reproduce exact P8 C0 selected Cs, predictions, hashes, and metrics;
- reproduce fold memberships, labels, class counts, support hashes, and label hashes;
- verify both predicted classes are represented;
- reject constant-probability/single-class collapse;
- record per-fold prediction/support/label hashes;
- record runtime provenance and prohibited-activity assertions.

## Promotion gate
The P8 bar is not lowered.

C1 must:
- pooled AUC >= 0.56;
- improve pooled AUC over C0;
- improve pooled log loss over C0;
- improve pooled Brier over C0;
- improve AUC and log loss in at least 3 of 4 folds;
- have every leave-one-fold-out AUC delta > 0;
- have every leave-one-fold-out log-loss improvement > 0;
- not regress balanced accuracy or macro-F1 versus C0.

Only if all prechecks pass may the frozen paired temporal-null procedure run. Final promotion also requires the frozen temporal-null significance gate.

Any required gate failure is terminal for P9. No tuning after viewing outcomes.

## Explicit prohibitions
Inside P9 there is:
- one window only;
- one sampling rate only;
- one channel set only;
- one representation only;
- one model family only;
- no lag sweep;
- no window sweep;
- no channel sweep;
- no model shopping;
- no calibration;
- no threshold selection;
- no PnL/economic optimization;
- no OFI;
- no opportunity/touch composition;
- no August/September holdout consumption.

## Storage and operational prohibition
P9 design, implementation, and synthetic/regression testing must not touch Railway buckets or volumes, including `market-raw-archive` and all project volumes.

## Implementation gate
A fresh implementation branch must be created from this design branch. Source/tests may then be implemented and tested. Real Jan-Jul execution remains separately prohibited until focused tests, frozen regressions, hashes, clean-tree checks, and a separate implementation freeze are completed.
