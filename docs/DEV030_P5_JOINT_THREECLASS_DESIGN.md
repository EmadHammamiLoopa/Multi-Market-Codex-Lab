# DEV030-P5 Direct Joint Three-Class Model Design

Status: **DESIGN FROZEN BEFORE IMPLEMENTATION OR FITTING**

Parent scientific state:
- P4 artifact SHA256:
  `8dbe23963def1e96da78a73d206e651aa40b0aeab8ba40419716529be33b5a16`
- P4 terminal status:
  `FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE`
- T2 TOUCH_VS_NONE:
  PASS and eligible for composition
- frozen P3 T1 hashes:
  reproduced exactly in P4
- selected representation:
  `A / 120s / 16bp / 32s / PRICE`

Design branch:
`research/dev030-p5-joint-threeclass-design`

## 1. Scientific question

P4 showed that the touch head is strong, while multiplying it by the frozen
conditional-direction head does not improve joint three-class probability
quality over the frozen C1 baseline.

P5 asks:

> Is the failure caused by the two-head factorization itself, such that a
> single low-complexity model trained directly on
> NONE / SHORT_FIRST / LONG_FIRST can learn a better joint probability
> distribution on the same frozen representation?

P5 does not test profitability.

P5 does not tune a trading threshold.

P5 does not open forward data.

## 2. Frozen configuration

Exactly one configuration is authorized:

- symbol: BTCUSDT
- target: A
- horizon: 120 seconds
- barrier: 16 bp
- sequence window: 32 seconds
- feature block: PRICE
- representation: S1 32-second causal PRICE summaries

No target/window/block search is allowed.

## 3. Labels

Joint target classes use exact frozen first-passage semantics:

- `NONE = 0`
- `SHORT_FIRST = 1`
- `LONG_FIRST = 2`

Rows are included iff:
- target is valid under the frozen first-passage contract
- representation common support is valid
- target future boundary is valid

Invalid/ambiguous target rows remain excluded.

No relabeling is allowed.

## 4. Data scope

Authorized:
- consumed BTCUSDT development days:
  Jan-01 through Jul-01, 2026 only

Forbidden:
- Aug-30
- Sep-01+
- archive bucket
- abundant-love
- ETH/SOL
- options/DVOL/funding/OI/liquidations
- macro/news
- on-chain
- opportunity-gate inputs
- PnL/economics

## 5. Frozen dependencies

Before first fit verify:

- P4 source SHA256:
  `bcab35f909fdb732a399e40d042689de5d254c5a6372b0abe18146c81c0c522f`
- P4 test SHA256:
  `7fde9b155e1d441252023b94225d3ec4f540a87847fb7ee3f6ae181579d5c265`
- P4 artifact SHA256:
  `8dbe23963def1e96da78a73d206e651aa40b0aeab8ba40419716529be33b5a16`
- P3 source SHA256:
  `9730f62cd6e2ee2a84cb402a890629f7335eb42b730f24f69ffca971281ba675`
- P3 artifact SHA256:
  `f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`
- P2C artifact SHA256:
  `a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0`

Any mismatch is a hard pre-fit failure.

## 6. Support identity

P5 must use exactly the same 5,748 pooled validation rows as P4 joint
composition evaluation.

Expected pooled class counts:
- NONE = 5,175
- SHORT_FIRST = 264
- LONG_FIRST = 309
- total = 5,748

Per-fold validation support must be exactly 1,437 rows in each of folds 1-4.

The implementation must hash the exact validation timestamps and labels and
record those hashes.

## 7. Chronological folds

Use the existing frozen outer folds:

| Fold | Train | Validate |
| --- | --- | --- |
| 1 | Jan-Mar | Apr |
| 2 | Jan-Apr | May |
| 3 | Jan-May | Jun |
| 4 | Jan-Jun | Jul |

Inner validation:
- last outer-training day

Inner fit:
- all earlier outer-training days

No random split.

No outer validation information may enter scaler fitting or C selection.

## 8. Frozen baselines

P5 compares the direct joint model against:

### C0
Training-fold three-class prevalence probabilities.

### C1
Frozen P4 baseline:
T2 touch probability + training-fold constant directional prior.

### C2
Frozen P4 failed two-head composition:
T2 touch probability × frozen T1 conditional direction probability.

The P5 implementation must reconstruct or load the exact frozen C1/C2 P4
predictions and verify metric identity with the P4 artifact before evaluating
the new model.

If frozen P4 baseline metrics cannot be reproduced exactly, P5 evaluation is
forbidden.

## 9. Candidate model J1

Single low-complexity joint model:

1. StandardScaler fit on training rows only
2. LogisticRegression
   - multi-class softmax semantics from scikit-learn
   - solver = `lbfgs`
   - L2 regularization
   - class_weight = `None`
   - max_iter = `1000`
   - fit_intercept = `True`
   - random_state = `20260825`

Frozen C grid:
`[0.01, 0.1, 1.0, 10.0]`

No other model family is authorized.

No class weighting.

No resampling.

No deep model.

## 10. Inner C selection

Select C on inner validation using this frozen order:

1. lowest multiclass log loss
2. lowest multiclass Brier score
3. highest macro one-vs-rest Average Precision
4. smaller C

This order prioritizes proper probability quality over classification
threshold metrics.

## 11. Metrics

Per fold and pooled report:

Primary:
- multiclass log loss
- multiclass Brier score
- macro one-vs-rest Average Precision
- macro one-vs-rest ROC AUC

Per class:
- AP for NONE
- AP for SHORT_FIRST
- AP for LONG_FIRST
- ROC AUC for each class

Diagnostics only:
- argmax balanced accuracy
- argmax macro F1
- confusion matrix in fixed order
  `[NONE, SHORT_FIRST, LONG_FIRST]`

Argmax diagnostics cannot determine promotion.

## 12. Primary comparison

The principal comparison is J1 vs C1.

Also report J1 vs C2 and J1 vs C0.

For J1 vs C1 compute:

- pooled log-loss improvement:
  `LL(C1) - LL(J1)`
- pooled Brier improvement:
  `Brier(C1) - Brier(J1)`
- pooled macro-AP delta:
  `MacroAP(J1) - MacroAP(C1)`
- fold-level log-loss improvements
- leave-one-fold-out pooled log-loss improvements

## 13. Directional-class safeguards

Because NONE dominates support, P5 must not pass merely by improving NONE.

Require directional discrimination to improve or at least not collapse.

Report:
- SHORT_FIRST AP delta vs C1
- LONG_FIRST AP delta vs C1
- mean directional AP delta:
  mean(SHORT delta, LONG delta)

Frozen safeguard:
- at least one of SHORT_FIRST or LONG_FIRST pooled AP must improve vs C1
- mean directional AP delta must be > 0

This prevents a NONE-only probability improvement from being called a success.

## 14. Temporal null

Only if all non-null precheck gates pass.

Use day-local circular shifts of the three-class validation labels.

Within each validation day:
- shift the full three-class label vector by shared k
- keep J1 probabilities fixed
- use eligible shared k satisfying
  `min(k, n_day-k) >= 10`

Require at least 20 eligible shifts.

For each shift, keep both frozen C1 probabilities and J1 probabilities fixed
and evaluate both against the same shifted three-class labels.

Primary null statistic:
`improvement_shift = LL(C1, shifted_labels) - LL(J1, shifted_labels)`

Observed statistic:
`improvement_observed = LL(C1, true_labels) - LL(J1, true_labels)`

Observed improvement must be strictly greater than the null q95.

Empirical one-sided p:
`(1 + count(null_improvement >= observed_improvement)) / (1 + n_null)`

Require p <= 0.05.

Secondary null diagnostic:
`macro_AP_delta_shift = MacroAP(J1, shifted_labels) - MacroAP(C1, shifted_labels)`

This paired-label construction is required because P5 tests incremental value
over C1 rather than absolute J1 predictiveness.

## 15. Frozen promotion gate

J1 is `ELIGIBLE_FOR_LATER_POLICY_DESIGN` only if all are true:

1. pooled J1 log loss < pooled C1 log loss
2. pooled J1 Brier < pooled C1 Brier
3. pooled J1 macro OVR AP > pooled C1 macro OVR AP
4. at least 3/4 folds improve log loss vs C1
5. every leave-one-fold-out pooled log-loss improvement vs C1 > 0
6. at least one directional-class AP improves vs C1
7. mean directional AP delta > 0
8. temporal-null observed log-loss improvement > null q95
9. empirical null p <= 0.05
10. all P4 baseline reproduction/provenance invariants pass

These are development engineering gates, not confirmatory claims.

## 16. Failure labels

If non-null precheck fails:
`FAIL_DIRECT_JOINT_THREECLASS_NO_INCREMENTAL_VALUE`

If temporal null fails:
`FAIL_DIRECT_JOINT_THREECLASS_TEMPORAL_NULL`

If all gates pass:
`ELIGIBLE_FOR_LATER_POLICY_DESIGN`

## 17. No rescue search

If J1 fails, P5 forbids:
- changing C grid
- class weighting
- threshold tuning
- target/window/block search
- adding PRICE_BOOK/FLOW
- direct threshold-based action policy
- opening forward data
- PnL
- M2/deep model in the same experiment

Any escalation must be separately designed.

## 18. Implementation boundary

Authorized implementation files only:

- `src/multimarket/dev030_p5_joint_threeclass.py`
- `tests/test_dev030_p5_joint_threeclass.py`

Frozen P4/P3/P2 scientific files must not be modified.

## 19. Synthetic tests required before real fitting

At minimum verify:

1. exact selected configuration identity
2. exact three-class mapping
3. invalid rows excluded
4. exact 5,748 expected pooled P4 support contract when reconciling real data
5. chronological outer folds
6. chronological inner split
7. scaler is training-only
8. exact C grid
9. exact C tie order
10. no class weights/resampling
11. multiclass log loss arithmetic
12. multiclass Brier arithmetic
13. macro OVR AP/AUC arithmetic
14. fixed class order
15. exact C0/C1/C2 baseline reproduction interface
16. J1-vs-C1 pooled deltas
17. fold log-loss gate
18. leave-one-fold-out gate
19. directional AP safeguard
20. three-class temporal null determinism
21. insufficient null shifts fail closed
22. every promotion gate independently vetoes
23. no threshold optimization interface
24. no PnL/economics interface
25. no opportunity-gate interface
26. no forward-data interface
27. deterministic canonical JSON
28. write-once atomic artifact
29. runtime provenance fail-closed
30. tests do not open real market data

## 20. Real-run boundary

After implementation and synthetic/regression tests are frozen, stop.

Real Jan-Jul P5 fitting requires separate explicit authorization.

Forward holdout remains closed regardless of P5 result.

## 21. Decision

P5 implementation and synthetic testing are authorized after this design
freeze.

Real P5 fitting is not yet authorized.

M2 remains deferred until this low-complexity factorization test is resolved.
