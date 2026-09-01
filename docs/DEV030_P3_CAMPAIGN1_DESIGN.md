# DEV030-P3 Campaign-1 Direction Modeling Design

Status: **DESIGN FROZEN BEFORE CAMPAIGN-1 MODEL FITTING**

Parent lineage:
- DEV030-P2C frozen implementation: `f428ed4aaf8319da61d3dc57d0f5949ca1c6837d`
- DEV030-P2C real materialization result recorded in handoff descendant:
  `76486920594f15ea9263da093090458195dc7d20`

Design branch:
`research/dev030-p3-campaign1-design`

Frozen real P2C artifact:
`/home/emadh/Multi-Market/evidence/dev030_p2c_direction_materialization_v1/DIRECTION_DATASET_MATERIALIZATION.json`

Frozen P2C artifact SHA256:
`a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0`

Frozen P2C artifact bytes:
`972852`

This document authorizes design and later implementation of the bounded DEV030
Campaign-1 modeling layer. It does not itself authorize a model fit. The real
Campaign-1 run is separately gated after the implementation and synthetic tests
are frozen.

## 1. Purpose

The primary question remains:

> Does causal sequence information available at decision time improve stable
> prediction of LONG_FIRST versus SHORT_FIRST, conditional on a later
> directional first-passage event, beyond a matched snapshot baseline?

This is T1: `DIRECTION_GIVEN_TOUCH`.

T1 is an oracle-touch diagnostic. It is not directly deployable because
membership in T1 depends on the future fact that a directional barrier is
eventually touched.

Campaign 1 is therefore a **predictive information test**, not a trading
strategy and not a PnL experiment.

## 2. Why P3 is now allowed

The preceding DEV030 stages established the prerequisites:

- P1: usable and nearly balanced directional labels exist.
- P2A: the sequence feature engine is causal and deterministic.
- P2B: T1 datasets, support masks, support hashes, and chronological folds are
  deterministic and frozen.
- P2C: the real consumed Jan-Jul data were materialized successfully with
  exactly 64 candidate representations, preserved support hashes, and no
  forward-data opening.

P3 may therefore test predictability without changing target, sequence,
support, or fold semantics.

## 3. Frozen data scope

Authorized analytical data for Campaign 1:

- BTCUSDT only.
- The seven already-consumed development days:
  - 2026-01-01
  - 2026-02-01
  - 2026-03-01
  - 2026-04-01
  - 2026-05-01
  - 2026-06-01
  - 2026-07-01

Forbidden:

- Aug-30.
- Sep-01 or later.
- archive-bucket data.
- abundant-love data.
- ETH/SOL.
- external/news/macro/options/DVOL/OI/funding/liquidation/on-chain data.
- any data not in the frozen P2B input manifest.

The P2C materialization artifact is the authoritative support/provenance
contract for P3.

## 4. Frozen source identities

The implementation must verify before fitting:

- `src/multimarket/dev030_direction_dataset.py`
  SHA256
  `54e7315a12cac10413ac2017849466eb3d225282e3dcf48484615409680348c9`

- `src/multimarket/dev030_sequence_features.py`
  SHA256
  `30952d31795d5fd88c9dfd9641a5332b662eeb32f30ec9ac283f8339d26ac11c`

- `src/multimarket/dev030_first_passage.py`
  SHA256
  `33dbbb53dfe10cfa859037fa2a89d05010f7950e3ec74e51422135ec585d0bc7`

- P2C canonical artifact SHA256
  `a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0`

A mismatch is a hard pre-fit failure.

## 5. Pre-fit reconstruction and reconciliation

P3 must not trust a newly reconstructed in-memory dataset merely because the
loader completed.

Before any estimator is fit:

1. verify the frozen P2C artifact bytes;
2. verify the frozen scientific source identities;
3. verify the seven Jan-Jul input file hashes through the frozen P2B loader;
4. reconstruct the 64 candidate datasets with the frozen P2B builder;
5. recompute all candidate/day/fold support identities;
6. reconcile them against the frozen P2C artifact.

At minimum, require exact equality for:

- candidate count = 64;
- candidate order;
- target/window/block identities;
- per-day decision counts;
- per-day T1 counts and class counts;
- native S0 support hashes;
- native S1 support hashes;
- common-support hashes;
- T1-common-support hashes;
- fold train/validation T1 counts;
- fold train/validation class counts;
- all fold support hashes.

No model fit may occur before reconciliation succeeds.

## 6. Candidate universe

Campaign 1 contains exactly 64 candidates:

```text
4 targets × 4 windows × 4 feature blocks = 64
```

Target order:

1. A = 120 s / 16 bp — primary economic
2. B = 300 s / 24 bp — primary economic
3. C = 300 s / 12 bp — learnability control
4. D = 60 s / 8 bp — short/cost control

Window order:

```text
8, 16, 32, 60 seconds
```

Block order:

```text
PRICE
PRICE_BOOK
PRICE_BOOK_FLOW
PRICE_BOOK_FLOW_DYNAMICS
```

Every candidate compares:

- S0 = matched causal snapshot;
- S1 = engineered causal sequence summaries.

All S1-vs-S0 comparisons use exact candidate-specific common support.

No candidate may be added after results are observed.

## 7. Chronological outer folds

Use exactly the frozen P2B folds:

| Fold | Train days | Validation day |
| --- | --- | --- |
| 1 | Jan, Feb, Mar consumed days | Apr consumed day |
| 2 | Jan, Feb, Mar, Apr consumed days | May consumed day |
| 3 | Jan-May consumed days | Jun consumed day |
| 4 | Jan-Jun consumed days | Jul consumed day |

These are consumed **days**, not full calendar months.

There is:

- no random row shuffle;
- no random train/test split;
- no k-fold mixing of future and past observations.

The expanding temporal structure is consistent with the standard time-series
validation principle that training data precede evaluation data.

## 8. Inner hyperparameter selection

For each outer fold independently:

- the final consumed training day becomes the inner-validation day;
- all earlier outer-training days become the inner-fit set.

Exact inner split:

| Outer fold | Inner fit | Inner validation |
| --- | --- | --- |
| 1 | Jan-Feb | Mar |
| 2 | Jan-Mar | Apr |
| 3 | Jan-Apr | May |
| 4 | Jan-May | Jun |

The outer validation day must never influence:

- scaling;
- C selection;
- feature selection;
- threshold selection;
- preprocessing;
- candidate eligibility.

If either inner-fit or inner-validation T1 support lacks both classes, the
candidate/fold fails closed. There is no random fallback split.

## 9. M0 controls

The following deterministic controls are reported, not tuned:

1. training-majority prediction; training tie -> SHORT;
2. `microprice_minus_mid_bps >= 0` -> LONG else SHORT;
3. `obi_l1 >= 0` -> LONG else SHORT;
4. when FLOW is present:
   `ofi_l1_1s >= 0` -> LONG else SHORT.

M0 does not select candidates and cannot satisfy the Campaign-1 promotion gate
by itself.

## 10. M1 model family

Campaign 1 uses one learned family only:

`StandardScaler -> L2-regularized LogisticRegression`

Frozen logical configuration:

```text
solver = lbfgs
class_weight = None
max_iter = 1000
fit_intercept = True
decision threshold = 0.5
C grid = [0.01, 0.1, 1.0, 10.0]
```

The current development environment uses scikit-learn 1.9.0.

For scikit-learn 1.9.0, the implementation should express L2 semantics with
`l1_ratio=0.0` rather than relying on the deprecated `penalty="l2"`
argument. This is a compatibility modernization only; it does not authorize a
different penalty family.

Before real fitting, synthetic tests must prove the intended L2 configuration
and exact frozen C grid.

No class weights and no sample weights are used because the T1 classes are
already close to balanced and the campaign is intended to test raw directional
information rather than reweighting.

## 11. Train-only preprocessing

For each representation and fold:

1. fit `StandardScaler` on the relevant training rows only;
2. transform inner validation using that training-fitted scaler;
3. select C using inner validation;
4. refit a fresh scaler on the complete outer training rows;
5. refit a fresh logistic model using selected C;
6. transform and score the untouched outer validation rows.

No scaler statistic from outer validation may enter training.

Zero-variance training features are permitted only through the standard
`StandardScaler` behavior; no validation-derived variance filter is allowed.

All model inputs must be finite before fitting. No imputation is authorized.

## 12. C selection

For every S0 and S1 outer-fold model independently, evaluate exactly:

```text
C = 0.01
C = 0.1
C = 1.0
C = 10.0
```

Select by lexicographic order:

1. highest inner balanced accuracy;
2. highest inner macro F1;
3. smaller C.

Do not use outer-validation metrics to choose C.

Selected C must be recorded for every fold and representation.

## 13. Primary metrics

For S0 and S1 separately, report per outer fold and pooled OOF:

- support count;
- LONG count;
- SHORT count;
- predicted LONG count;
- predicted SHORT count;
- balanced accuracy;
- macro F1;
- Matthews correlation coefficient;
- LONG precision;
- LONG recall;
- LONG F1;
- SHORT precision;
- SHORT recall;
- SHORT F1;
- confusion matrix in fixed order `[SHORT, LONG]`.

Also record ROC AUC from M1 probabilities as a **secondary diagnostic only**.
ROC AUC does not enter the promotion gate.

The primary incremental comparisons are:

```text
delta_BA = BA(S1) - BA(S0)
delta_macro_F1 = macro_F1(S1) - macro_F1(S0)
```

Both pooled and per-fold deltas are required.

## 14. Trial ledger

The authoritative result must contain an append-only logical ledger with all
64 candidates in frozen order.

Each entry records:

- candidate identity;
- support hashes;
- feature counts;
- fold support;
- M0 results;
- S0 M1 results;
- S1 M1 results;
- selected C values;
- pooled metrics;
- S1-minus-S0 deltas;
- temporal-null result if run;
- falsification diagnostics if run;
- every promotion-gate boolean;
- final failure reason or survivor status.

No candidate may be removed after its outcome is known.

## 15. Deterministic prediction hashes

For every fitted S0/S1 outer fold, record a deterministic SHA256 over the
chronological tuple stream:

```text
decision_timestamp_us
true_label
predicted_label
p_long as IEEE-754 float64 big-endian bytes
```

The hash domain must include:

```text
DEV030-P3-OOF-PREDICTION-V1
target
window
block
representation
fold_id
```

This provides compact reproducibility evidence without publishing a large
prediction matrix.

## 16. Temporal-label null

The primary falsification remains the frozen within-day circular-shift null.

For each candidate:

- use only outer-validation T1 rows;
- keep the fitted S1 probabilities and predictions fixed;
- group labels by UTC validation day;
- circularly shift labels within each day only;
- never wrap labels across days or folds.

A shared displacement `k` is eligible only when for every participating
validation-day group:

```text
k > 0
min(k, n_day - k) >= 10
```

Require at least 20 shared eligible shifts.

For each eligible `k`:

- apply the same k to each participating fold/day group;
- concatenate folds chronologically;
- compute pooled balanced accuracy.

Compute:

```text
null_q95 = quantile(null_BA, 0.95, method="higher")

empirical_p =
  (1 + count(null_BA >= observed_BA))
  / (1 + number_of_null_BA_values)
```

Promotion requires:

- observed S1 pooled BA strictly > null_q95;
- empirical p <= 0.05.

This p-value is a bounded development diagnostic, not a family-wise
confirmatory p-value across the 64-candidate search.

## 17. Falsification staging

To avoid unnecessary computation without weakening the gate:

### Stage F0 — metric precheck

Run for all 64 candidates:

- M0;
- M1 S0;
- M1 S1;
- all four outer folds;
- pooled metrics;
- S1-vs-S0 deltas.

### Stage F1 — temporal null

Run the temporal-label null only for candidates that satisfy every promotion
condition except the null condition itself.

A candidate that fails the metric/stability precheck records:

`TEMPORAL_NULL_NOT_RUN_PRECHECK_FAILED`

This is not a pass; it is a computational short-circuit for an already-failed
candidate.

### Stage F2 — explanatory temporal diagnostics

Only candidates that pass F1 receive:

- sequence-order reversal;
- deterministic within-sequence time permutation;
- incremental feature-block alignment permutation where applicable.

These diagnostics are explanatory and cannot rescue a temporal-null failure.

## 18. Sequence-order reversal diagnostic

For a candidate reaching F2:

- reverse each validation raw sequence in time;
- recompute S1 summaries;
- keep the trained model fixed;
- rescore without refitting.

Record the change in BA and macro F1.

Because some summaries are order-invariant while endpoint/trend summaries are
not, this test probes whether the learned signal depends on sequence direction.

## 19. Within-sequence time permutation diagnostic

For each F2 candidate, create one deterministic position permutation per
target/window/fold from SHA256 seed material:

```text
20260825 | target | window | fold | time_permutation
```

Apply the same position permutation to every validation sequence in that
fold, recompute S1 summaries, and score with the unchanged model.

No labels enter permutation construction.

## 20. Incremental feature-block alignment diagnostic

For F2 candidates beyond the PRICE block:

- preserve earlier block columns;
- move the newly added block as a unit across validation samples;
- do not refit.

Use:

```text
k = max(10, floor(n_fold / 3))
```

reduced only if needed to keep `k < n_fold`.

This tests whether an apparent incremental block gain depends on correct
chronological feature/label alignment.

## 21. Promotion gate

A candidate is `ELIGIBLE_FOR_NEXT_DEVELOPMENT_STAGE` only if:

1. target is A or B;
2. pooled S1 balanced accuracy >= 0.54;
3. median outer-fold S1 balanced accuracy > 0.50;
4. at least 3 of 4 outer folds have S1 BA > 0.50;
5. pooled S1-minus-S0 BA delta >= +0.02;
6. S1-minus-S0 BA delta is positive in at least 3 of 4 folds;
7. every fold predicts at least one LONG and one SHORT;
8. pooled predicted-minority fraction >= 0.10;
9. observed pooled S1 BA > temporal-null q95;
10. temporal-null empirical p <= 0.05;
11. leave-one-fold-out pooled S1-minus-S0 BA delta is strictly positive after
    omitting each fold in turn.

No gate may be weakened after results are observed.

C and D may be reported as learnability controls but can never be promoted by
Campaign 1.

## 22. Leave-one-fold-out stability

For each candidate, recompute the pooled S1-minus-S0 BA delta four times,
dropping one outer fold at a time.

All four reduced pooled deltas must be strictly positive for promotion.

This prevents a single validation day from carrying the entire incremental
sequence effect.

## 23. Deterministic survivor selection

Campaign 1 may produce more than one eligible A/B candidate.

Exactly one candidate may be selected for the next development stage using
this frozen lexicographic ranking:

1. larger minimum outer-fold S1 BA;
2. larger median outer-fold S1 BA;
3. larger pooled S1-minus-S0 BA delta;
4. larger pooled S1 BA;
5. larger pooled S1 macro F1;
6. shorter sequence window;
7. simpler feature block using frozen block order;
8. frozen target order A before B.

This ranking is applied only among candidates that already pass every gate.

The selected candidate is labeled:

`SELECTED_FOR_NEXT_DEVELOPMENT_STAGE`

It is not labeled confirmed, deployable, profitable, or production-ready.

All non-selected passing candidates remain in the ledger as
`ELIGIBLE_NOT_SELECTED`.

## 24. Complete Campaign-1 interpretation

Possible campaign outcomes:

### Outcome A — primary survivor exists

At least one A/B candidate passes all gates.

Then:
- select exactly one by Section 23;
- freeze it;
- allow a separately designed Campaign 2/nonlinearity or T2 composition stage;
- do not open forward holdout yet unless a later design explicitly chooses to
  freeze the final development configuration first.

### Outcome B — only C/D passes

Interpretation:
- direction may be learnable on an easier or cost-challenged target;
- primary economic direction remains unsolved;
- do not advance to deployable composition.

### Outcome C — no candidate passes

Interpretation:
- initial engineered sequence summaries did not establish stable incremental
  direction information;
- stop this initial direction campaign;
- do not automatically escalate to boosting, MLP, CNN, TCN, Transformer, or
  attention in search of a survivor.

## 25. No economic inference in P3

Campaign 1 must not compute or optimize:

- PnL;
- net expectancy;
- fees;
- slippage-adjusted returns;
- take-profit;
- stop-loss;
- leverage;
- position sizing;
- drawdown;
- Sharpe;
- profit factor;
- capital curves;
- execution thresholds;
- confidence thresholds.

The known target barriers and historical cost references may be reported only
as frozen target metadata.

## 26. No opportunity-gate composition yet

EXP024 established useful opportunity ranking, but Campaign 1 must not use:

- EXP024 scores;
- opportunity ranks;
- opportunity thresholds;
- EXP029 gates;
- volatility eligibility states

as model inputs or sample filters.

The direction layer must first establish its own incremental information.

## 27. Output contract

Planned canonical output directory:

`/home/emadh/Multi-Market/evidence/dev030_p3_campaign1_v1`

Primary artifact:

`DEV030_P3_CAMPAIGN1_RESULT.json`

The primary artifact must contain:

- status;
- experiment/design version;
- execution commit;
- Python/numpy/scikit-learn versions;
- frozen source identities;
- P2C artifact identity;
- seven-file input manifest;
- runtime provenance;
- exact candidate order;
- exact folds and inner folds;
- complete 64-candidate trial ledger;
- metrics;
- selected C values;
- prediction hashes;
- null results;
- diagnostics;
- gate booleans;
- survivor-selection result;
- explicit prohibited-activity flags.

Canonical JSON rules:

- UTF-8;
- sorted keys;
- stable separators;
- finite numbers only;
- no NaN/Infinity;
- explicit numpy normalization;
- deterministic ordering;
- write once;
- atomic replace;
- no overwrite.

## 28. Runtime provenance

The real Campaign-1 result must explicitly record:

```text
jan_jul_analytically_opened = true
aug30_analytically_opened = false
sep01_or_later_analytically_opened = false
archive_bucket_opened = false
abundant_love_opened = false

model_fit_run = true
campaign_1_run = true
pnl_backtest_run = false
```

A contradictory provenance state fails closed.

## 29. Implementation files

Authorized next implementation files only:

- `src/multimarket/dev030_p3_direction.py`
- `tests/test_dev030_p3_direction.py`

Do not modify:

- frozen first-passage source/tests;
- frozen sequence-feature source/tests;
- frozen direction-dataset source/tests;
- frozen P2C materialization source/tests.

## 30. Required synthetic tests before any real fit

The P3 test suite must prove at minimum:

1. frozen source/artifact SHA mismatches fail before model fitting;
2. 64-candidate identity/order is exact;
3. reconstructed support mismatch fails before fitting;
4. outer fold identities are exact consumed-day folds;
5. inner fold identities are exact and chronological;
6. outer validation never enters scaler fit;
7. outer validation never selects C;
8. exact C grid and tie-breaking;
9. L2 logistic configuration is exact;
10. threshold is exactly 0.5;
11. confusion-matrix order is `[SHORT, LONG]`;
12. BA, macro F1, MCC, class metrics are correct;
13. ROC AUC is diagnostic only;
14. S0/S1 comparisons use identical common support;
15. prediction hash is deterministic and order-sensitive;
16. candidate ledger contains all 64 candidates;
17. no failed candidate disappears;
18. day-local null never wraps across days;
19. eligible shift set is exact;
20. null q95 and empirical-p arithmetic are exact;
21. insufficient null shifts cannot pass;
22. F1/F2 staging cannot accidentally promote a precheck failure;
23. each promotion gate independently vetoes promotion;
24. C/D can never be promoted;
25. leave-one-fold-out stability is exact;
26. survivor ranking is deterministic;
27. no economic metric/interface is present;
28. no forward-data interface is present;
29. no opportunity-gate input is present;
30. canonical result serialization is deterministic and atomic.

All tests must be synthetic. They must not open Jan-Jul, Aug-30, Sep-01+,
archive, or abundant-love.

## 31. Real-run authorization boundary

After the P3 source and synthetic tests are frozen and all P2A/P2B/P2C
regressions pass, stop.

The real Campaign-1 model fit requires a separate explicit execution
authorization.

That real run may reopen only the already-consumed Jan-Jul development days.

It must not open Aug-30 or Sep-01+.

## 32. External implementation references reviewed

The design remains aligned with the official scikit-learn guidance used by the
current environment:

- `TimeSeriesSplit` documentation emphasizes time-ordered evaluation in
  which training data precede test data and later training sets expand.
- `StandardScaler` computes and stores scaling statistics from the data passed
  to `fit`, reinforcing the requirement that only training rows enter scaler
  fitting.
- `LogisticRegression` documents L2 regularization, `lbfgs`, and the inverse
  regularization parameter `C`; in scikit-learn 1.9 the old explicit
  `penalty` argument is deprecated, motivating the frozen `l1_ratio=0.0`
  compatibility form.

These references support implementation mechanics. They do not establish
predictive validity or profitability for BTCUSDT.

## 33. Quality principle

Token/computation saving is allowed only when it does not weaken the
experiment.

Examples permitted:
- skip expensive temporal-null diagnostics for a candidate that already fails
  a required precheck gate;
- cache mathematically identical deterministic intermediate transforms if
  output identities are proved equal.

Examples forbidden:
- fewer folds;
- fewer required metrics;
- weaker support reconciliation;
- opening forward data early;
- dropping failed candidates from the ledger;
- relaxing gates;
- replacing chronological selection with random splitting.

The project optimizes for evidence quality first, efficiency second.
