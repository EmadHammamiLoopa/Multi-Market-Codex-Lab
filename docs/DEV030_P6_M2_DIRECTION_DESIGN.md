# DEV030-P6 Bounded M2 Direction Capacity Design

Status: **DESIGN FROZEN BEFORE IMPLEMENTATION OR FITTING**

Date: 2026-09-02

Parent scientific state:
- P3 selected T1 survivor:
  A / 120s / 16bp / 32s / PRICE / S1
- P3 artifact SHA256:
  `f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`
- P4 artifact SHA256:
  `8dbe23963def1e96da78a73d206e651aa40b0aeab8ba40419716529be33b5a16`
- P5 artifact SHA256:
  `d9a89a1be1dc3733cd510666f9a2d717e853a8c414c2c3c943d28ebafa741c00`

Research review:
`docs/DEV030_P6_M2_DIRECTION_RESEARCH.md`

Design branch:
`research/dev030-p6-m2-direction-design`

## 1. Scientific question

P4 established strong TOUCH_VS_NONE prediction.

P4 two-head composition and P5 direct linear three-class modeling both failed
to improve joint probability quality.

P6 therefore asks one narrow question:

> On the exact frozen P3 T1 direction-given-touch task and exact frozen
> 32-second PRICE S1 representation, does a tightly bounded nonlinear model
> add stable out-of-sample directional probability information beyond the
> frozen regularized logistic M1 head?

P6 is a **capacity diagnostic**.

It is not:
- a new representation search;
- a new target search;
- a trading policy;
- a PnL experiment;
- a forward confirmation.

## 2. Why the selected M2 family is bounded histogram gradient boosting

External research before this design found:

- medium/small tabular problems often remain favorable to tree ensembles over
  generic deep neural architectures;
- high-frequency microstructure research supports the possibility of
  nonlinear information in stationary engineered inputs;
- DEV030 has only 1,374 total T1 touch rows and 573 chronological OOF rows;
- the selected S1 PRICE representation has only 23 engineered features.

Therefore P6 uses exactly one nonlinear family:
`sklearn.ensemble.HistGradientBoostingClassifier`.

No MLP, CNN, LSTM, TCN, Transformer, TabPFN, XGBoost, LightGBM, CatBoost,
random forest, SVM, or model-family comparison is permitted inside P6.

Research references and rationale are frozen separately in
`DEV030_P6_M2_DIRECTION_RESEARCH.md`.

## 3. Exact task and labels

Task:
`T1 = DIRECTION_GIVEN_TOUCH`.

Binary class order:
- `SHORT_FIRST = 0`
- `LONG_FIRST = 1`

Only valid touch rows from the frozen first-passage target are included.

NONE rows are excluded exactly as in P3 T1.

No relabeling is allowed.

## 4. Exact frozen configuration

Exactly one configuration:

- symbol: BTCUSDT
- target: A
- horizon: 120 seconds
- executable barrier: 16 bp
- sequence window: 32 seconds
- feature block: PRICE
- representation: S1 causal sequence summaries
- feature count: exactly 23

No target/window/block/feature-subset search is allowed.

## 5. Exact PRICE S1 features

The representation is produced only by the frozen P2A feature engine.

Underlying PRICE series:
1. `spread_bps`
2. `microprice_minus_mid_bps`
3. `mid_log_return_250ms_bps`

Frozen summary statistics:
- last
- mean
- std
- minimum
- maximum
- last_minus_first
- ols_slope

Additionally for naturally signed series:
- sign_persistence

Therefore:
- spread = 7 summaries
- microprice-minus-mid = 8 summaries
- mid return = 8 summaries
- total = 23 features

The exact feature names/order must match the frozen
`sequence_summary_feature_names("PRICE")` contract.

No new interaction term or engineered feature may be added.

## 6. Data scope

Authorized:
- already-consumed BTCUSDT Jan-Jul 2026 development days only.

Forbidden:
- Aug-30;
- Sep-01 or later;
- archive bucket;
- abundant-love hot buffer;
- ETH/SOL;
- external macro/news;
- options/DVOL/funding/OI/liquidation/on-chain data.

Forward holdout remains closed regardless of P6 result.

## 7. Frozen source/artifact dependencies

Before any real estimator fit, verify:

P3:
- source SHA256 =
  `9730f62cd6e2ee2a84cb402a890629f7335eb42b730f24f69ffca971281ba675`
- test SHA256 =
  `a3d57a928d6a2dedc762111e1859fa9d290ee084412d7c613f7541398e46360b`
- artifact SHA256 =
  `f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`

P4:
- source SHA256 =
  `bcab35f909fdb732a399e40d042689de5d254c5a6372b0abe18146c81c0c522f`
- test SHA256 =
  `7fde9b155e1d441252023b94225d3ec4f540a87847fb7ee3f6ae181579d5c265`
- artifact SHA256 =
  `8dbe23963def1e96da78a73d206e651aa40b0aeab8ba40419716529be33b5a16`

P5 artifact:
- SHA256 =
  `d9a89a1be1dc3733cd510666f9a2d717e853a8c414c2c3c943d28ebafa741c00`

P2C artifact:
- SHA256 =
  `a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0`

Any mismatch is a hard pre-fit failure.

## 8. Exact support contract

P6 must reproduce the exact frozen P3 selected-survivor T1 validation support.

Pooled OOF support:
- total = 573
- LONG_FIRST = 309
- SHORT_FIRST = 264

Outer validation support:
- Fold 1 = 159: LONG 86 / SHORT 73
- Fold 2 = 64: LONG 40 / SHORT 24
- Fold 3 = 126: LONG 60 / SHORT 66
- Fold 4 = 224: LONG 123 / SHORT 101

P6 must record:
- exact validation timestamps;
- exact labels;
- support SHA256;
- label SHA256;
- M1 probability SHA256;
- M2 probability SHA256.

Any support or label mismatch forbids comparison.

## 9. Chronological outer folds

Use the exact P3 folds:

| Fold | Outer train | Outer validation |
| --- | --- | --- |
| 1 | Jan-Mar | Apr |
| 2 | Jan-Apr | May |
| 3 | Jan-May | Jun |
| 4 | Jan-Jun | Jul |

No random split.

No shuffled cross-validation.

No row-level random K-fold.

## 10. Chronological inner selection

For each outer fold:

- inner validation = last outer-training day;
- inner fit = all earlier outer-training days.

Examples:
- outer Fold 1: inner fit Jan-Feb, inner validate Mar;
- outer Fold 2: inner fit Jan-Mar, inner validate Apr;
- etc.

No outer validation data may enter M2 capacity selection.

## 11. Explicit future-label overlap assertion

P6 must verify before fitting that no training label information interval
overlaps the outer validation label interval.

Use the frozen P2A/P2B information interval semantics, including:
- 32-second representation lookback;
- 250 ms latency;
- 120-second future target horizon.

The existing day-boundary rejection should make the outer calendar folds safe,
but P6 must record an explicit PASS rather than assume it.

A detected overlap is a hard failure.

## 12. Frozen M1 baseline reconstruction

The comparator is not a freshly tuned logistic model.

It is the exact frozen P3 selected-survivor M1.

Selected P3 C by outer fold:
- Fold 1 = 10.0
- Fold 2 = 10.0
- Fold 3 = 0.1
- Fold 4 = 0.01

Expected frozen P3 OOF prediction hashes:
- Fold 1 =
  `e03d233bff936b49a0452994497f32ca5ecbe52c1f490d855fe8d06dbfa9dcf4`
- Fold 2 =
  `cd2cba0a6dcf3591ec9848b78e31aef796dad15d371bbecb8517aa2507340bdd`
- Fold 3 =
  `19f9acf70b0065a307c0373952cad350339768607a156c9307e5192503bb1f31`
- Fold 4 =
  `b05ee6e926d6a943e1fc89828eb3801af0863fa270bc2e5db5ed7cd93e9a4b66`

All four must reproduce exactly before M2 comparison.

P3 pooled M1 diagnostics to reproduce:
- balanced accuracy = 0.5419424831
- macro F1 = 0.5113006397
- MCC = 0.0920119182
- ROC AUC = 0.5367264882

P6 additionally computes frozen M1 binary:
- log loss;
- Brier score;
on the same 573 OOF rows.

## 13. M2 model family

Exactly:
`HistGradientBoostingClassifier`.

Fixed parameters for every capacity:

- loss = `log_loss`
- learning_rate = `0.05`
- min_samples_leaf = `20`
- l2_regularization = `1.0`
- max_features = `1.0`
- max_bins = `255`
- categorical_features = `None`
- early_stopping = `False`
- class_weight = `None`
- random_state = `20260825`

No StandardScaler is used for M2.

No class/sample weights.

No resampling.

No calibration layer.

No warm start across candidates/folds.

## 14. Frozen four-capacity M2 grid

Only:

| Capacity ID | max_leaf_nodes | max_iter |
| --- | ---: | ---: |
| H1 | 3 | 50 |
| H2 | 3 | 100 |
| H3 | 7 | 50 |
| H4 | 7 | 100 |

No other hyperparameter value may be tried.

This grid is a bounded capacity test, not an open optimization search.

## 15. Inner capacity selection

Evaluate H1-H4 on the chronological inner validation day.

Selection order:

1. lowest binary log loss;
2. lowest Brier score;
3. highest ROC AUC;
4. fewer `max_leaf_nodes`;
5. fewer `max_iter`.

The complete H1-H4 inner ledger must be serialized for every outer fold.

No balanced-accuracy-based capacity selection is allowed.

## 16. Probability metrics

For M1 and M2 on every outer fold and pooled OOF:

Primary:
- binary log loss;
- Brier score;
- ROC AUC.

Diagnostics only at threshold 0.5:
- balanced accuracy;
- macro F1;
- MCC;
- SHORT precision/recall/F1;
- LONG precision/recall/F1;
- confusion matrix.

No threshold optimization is permitted.

## 17. Paired M2-vs-M1 comparisons

Primary paired deltas:

- log-loss improvement =
  `LL(M1) - LL(M2)`
- Brier improvement =
  `Brier(M1) - Brier(M2)`
- AUC delta =
  `AUC(M2) - AUC(M1)`

Compute:
- pooled;
- each of four outer folds;
- every leave-one-fold-out pooled aggregate.

## 18. Non-null precheck gates

The temporal null is run only if **all** are true:

1. pooled M2 log loss < pooled M1 log loss;
2. pooled M2 Brier < pooled M1 Brier;
3. pooled M2 ROC AUC > pooled M1 ROC AUC;
4. pooled M2 ROC AUC >= 0.56;
5. at least 3/4 folds have positive M2-vs-M1 log-loss improvement;
6. at least 3/4 folds have M2 ROC AUC > 0.50;
7. at least 3/4 folds have M2 ROC AUC >= M1 ROC AUC;
8. every leave-one-fold-out pooled log-loss improvement > 0;
9. every leave-one-fold-out pooled AUC delta > 0;
10. both classes receive nonzero predicted probability in every fold;
11. all support/dependency/M1-reproduction/interval-overlap invariants pass.

Why 0.56 AUC:
P3 M1 pooled AUC is 0.5367. A model-capacity escalation must produce more than
a numerically tiny ranking change to justify the additional flexibility.
The 0.56 floor is frozen before fitting.

## 19. Paired day-local temporal-label null

Run only after all non-null precheck gates pass.

For each validation fold/day:
- hold M1 probabilities fixed;
- hold M2 probabilities fixed;
- circularly shift the binary T1 labels by the same shared k.

Eligible k:
- require `min(k, n_day-k) >= 10` in every outer validation day.

Given the frozen validation support, the expected common eligible shifts remain
k = 10..54, subject to implementation verification.

For each shift calculate pooled:

`delta_LL_shift = LL(M1, shifted_labels) - LL(M2, shifted_labels)`

Secondary:
`delta_AUC_shift = AUC(M2, shifted_labels) - AUC(M1, shifted_labels)`

Primary observed statistic:

`delta_LL_observed = LL(M1, true_labels) - LL(M2, true_labels)`

Require:
- observed delta_LL > null delta_LL q95;
- empirical one-sided p <= 0.05.

Empirical p:
`(1 + count(null >= observed)) / (1 + n_null)`

AUC null is diagnostic only.

## 20. Final promotion gate

M2 is:
`ELIGIBLE_FOR_DIRECTION_CAPACITY_UPGRADE`

only if:

- every non-null precheck gate passes;
- paired temporal null passes;
- no forbidden activity occurred.

Otherwise:

If non-null gates fail:
`FAIL_M2_DIRECTION_NO_STABLE_INCREMENTAL_VALUE`

If non-null gates pass but paired null fails:
`FAIL_M2_DIRECTION_TEMPORAL_NULL`

## 21. No rescue search

If P6 fails, this experiment may not:

- enlarge H1-H4;
- lower min_samples_leaf;
- remove L2 regularization;
- add class weights;
- resample;
- tune probability threshold;
- add PRICE_BOOK;
- add FLOW;
- add DYNAMICS;
- change the target;
- change the horizon;
- change the barrier;
- change the 32-second window;
- calibrate probabilities;
- switch to MLP/CNN/LSTM/Transformer;
- run PnL;
- open forward data.

Any new information/feature experiment must receive a new DEV ID/design.

## 22. Diagnostics allowed after model evaluation

Allowed, diagnostic only:
- selected capacity by fold;
- train/inner-validation model ledger;
- feature usage/importances if available without refit;
- validation probability distributions;
- fold class counts;
- threshold-0.5 metrics;
- M2-vs-M1 deltas;
- temporal-null distribution if authorized by the precheck.

Diagnostics cannot rescue a failed gate.

## 23. Implementation boundary

Authorized implementation files:

- `src/multimarket/dev030_p6_m2_direction.py`
- `tests/test_dev030_p6_m2_direction.py`

Frozen P3/P4/P5/P2 scientific source/test must not be modified.

## 24. Synthetic tests required before any real fitting

At minimum:

1. exact selected configuration identity;
2. exact 23-feature PRICE S1 order;
3. exact T1 label mapping;
4. NONE exclusion;
5. exact real support constants 573 / 309 / 264;
6. exact fold support constants 159/64/126/224;
7. chronological outer folds;
8. chronological inner splits;
9. explicit interval-overlap fail-closed check;
10. frozen M1 C values;
11. frozen M1 prediction-hash contract;
12. exact H1-H4 grid;
13. exact fixed HGB parameters;
14. early_stopping=False;
15. no scaler in M2;
16. no class weights/resampling;
17. exact inner capacity tie order;
18. binary log-loss arithmetic;
19. Brier arithmetic;
20. ROC-AUC arithmetic;
21. paired pooled deltas;
22. fold delta gates;
23. leave-one-fold-out gates;
24. AUC >= 0.56 floor;
25. paired temporal-null arithmetic;
26. common-shift rule;
27. insufficient null shifts fail closed;
28. every promotion gate independently vetoes;
29. no threshold-optimization interface;
30. no PnL/economics interface;
31. no opportunity-gate interface;
32. no forward-data interface;
33. no alternate model-family interface;
34. deterministic probability hashes;
35. deterministic canonical JSON;
36. atomic write-once output;
37. canonical dependency overrides forbidden;
38. tests do not open real market data.

## 25. Real-run boundary

Implementation/testing phase is synthetic only.

After:
- P6 focused tests pass;
- P5/P4/P3/P2 regressions pass;
- frozen dependency hashes remain exact;
- worktree is clean;
- GitHub boundary review confirms only P6/docs changes;

then freeze P6 implementation.

Real Jan-Jul P6 fitting requires a separate explicit authorization and
canonical one-shot run.

## 26. Interpretation boundary

Even a P6 pass means only:

> bounded nonlinear capacity adds stable incremental conditional-direction
> information on already-consumed BTCUSDT Jan-Jul development data.

It does NOT mean:
- forward confirmation;
- deployability;
- profit;
- positive net expectancy;
- a trading threshold;
- capital readiness.

If P6 passes, the upgraded direction probabilities may later be retested in a
separately frozen composition/policy stage.

If P6 fails, the project should stop escalating capacity on the frozen PRICE
representation and reconsider information/features rather than run deeper
models.
