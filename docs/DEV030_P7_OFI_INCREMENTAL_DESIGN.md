# DEV030-P7 Incremental L1 OFI Information Design

Status: **DESIGN FROZEN BEFORE IMPLEMENTATION OR FITTING**

Date: 2026-09-02

Parent state:
- P3 selected T1 survivor:
  A / 120s / 16bp / 32s / PRICE / S1
- P4 T2 TOUCH_VS_NONE:
  strong and deployability-relevant
- P5:
  FAIL_DIRECT_JOINT_THREECLASS_NO_INCREMENTAL_VALUE
- P6:
  FAIL_M2_DIRECTION_NO_STABLE_INCREMENTAL_VALUE

Research note:
`docs/DEV030_P7_OFI_INCREMENTAL_RESEARCH.md`

Design branch:
`research/dev030-p7-ofi-incremental-design`

## 1. Scientific question

Does a compact, predeclared multiscale L1 order-flow-imbalance family add
stable T1 LONG_FIRST-vs-SHORT_FIRST information beyond the frozen PRICE S1
representation on the already-selected target A?

P7 tests information content.

It does not test model capacity.

## 2. Exact task

Task:
`T1 = DIRECTION_GIVEN_TOUCH`

Class order:
- SHORT_FIRST = 0
- LONG_FIRST = 1

NONE rows are excluded exactly as in P3.

No relabeling is permitted.

## 3. Exact target and temporal geometry

Exactly:

- BTCUSDT
- target A
- horizon = 120 seconds
- barrier = 16 bp
- sequence window = 32 seconds

No target/horizon/barrier/window search.

## 4. Baseline representation C0

C0 is PRICE S1 only.

Exact underlying PRICE series:

1. spread_bps
2. microprice_minus_mid_bps
3. mid_log_return_250ms_bps

Existing frozen S1 summary engine only.

Feature count = 23.

## 5. Augmented representation C1

C1 contains:

- all 23 PRICE S1 features from C0
plus
- exactly 24 multiscale L1 OFI S1 summaries.

Frozen OFI series:

1. ofi_l1_250ms
2. ofi_l1_1s
3. ofi_l1_3s

For each OFI series use exactly:

- last
- mean
- std
- minimum
- maximum
- last_minus_first
- ols_slope
- sign_persistence

Total:
- PRICE = 23
- OFI = 24
- C1 = 47 features

No other FLOW, BOOK, MLOFI, trade-imbalance, or dynamics feature is allowed.

## 6. Source of the OFI values

P7 must use the already-frozen P2A/P2B feature pipeline.

The implementation may build the existing
`PRICE_BOOK_FLOW` candidate only as a source container because those frozen
OFI fields already exist there.

From that container, P7 must select only:
- PRICE S1 columns required by C0; and
- the 24 predeclared OFI S1 columns required by C1.

All other cumulative PRICE_BOOK_FLOW columns must be discarded before model
fitting.

The serialized artifact must record the exact selected column names/order.

## 7. Matched-support rule

Primary inference must use exact matched support.

FLOW validity can be narrower than PRICE validity.

Therefore:

- frozen P3 M1 is reproduced on original P3 support as a provenance check;
- primary C0 and C1 are both fit and scored only on the same OFI-valid T1 rows;
- C0 and C1 must have identical timestamps and labels in every fold;
- primary C1-vs-C0 comparison is forbidden if any timestamp/label/hash differs.

No missing-value imputation is allowed to restore dropped FLOW rows.

## 8. Exact outer folds

Use P3 folds unchanged:

| Fold | Train | Validation |
| --- | --- | --- |
| 1 | Jan-Mar | Apr |
| 2 | Jan-Apr | May |
| 3 | Jan-May | Jun |
| 4 | Jan-Jun | Jul |

No random split.

No shuffled K-fold.

## 9. Exact inner split

For each outer fold:

- inner validation = final outer-training day;
- inner fit = all earlier outer-training days.

No outer validation row may influence C selection.

## 10. Model family

Both C0 and C1 use:

`StandardScaler(train-only) + LogisticRegression(L2)`

Exact frozen family:

- solver = lbfgs
- l1_ratio = 0.0
- fit_intercept = True
- class_weight = None
- max_iter = 1000
- random_state = 20260825
- threshold diagnostic = 0.5

C grid:

`[0.01, 0.1, 1.0, 10.0]`

No alternate model family.

## 11. Inner C selection

Because P7 is probability-first after P6, select C separately for C0 and C1
using:

1. lowest binary log loss
2. lowest Brier score
3. highest ROC AUC
4. smaller C

The complete four-C ledger must be serialized for every representation/fold.

No BA-based C selection.

## 12. Primary metrics

For C0 and C1 on each outer fold and pooled:

Primary:
- binary log loss
- Brier score
- ROC AUC

Threshold-0.5 diagnostics:
- balanced accuracy
- macro F1
- MCC
- class precision/recall/F1
- confusion matrix

No threshold optimization.

## 13. Incremental comparisons

Primary paired deltas:

- log-loss improvement =
  LL(C0) - LL(C1)
- Brier improvement =
  Brier(C0) - Brier(C1)
- AUC delta =
  AUC(C1) - AUC(C0)

Compute:
- pooled
- each outer fold
- every leave-one-fold-out pooled aggregate

## 14. Non-null precheck gates

Temporal null runs only if all are true:

1. pooled C1 log loss < pooled C0 log loss;
2. pooled C1 Brier < pooled C0 Brier;
3. pooled C1 ROC AUC > pooled C0 ROC AUC;
4. pooled C1 ROC AUC >= 0.56;
5. at least 3/4 folds have positive log-loss improvement;
6. at least 3/4 folds have positive AUC delta;
7. at least 3/4 folds have C1 ROC AUC > 0.50;
8. every leave-one-fold-out log-loss improvement > 0;
9. every leave-one-fold-out AUC delta > 0;
10. both classes receive nonzero predicted probability in every fold;
11. matched support and frozen-dependency invariants all pass.

The 0.56 floor is kept from P6 to require a practically meaningful
direction-ranking improvement beyond the weak P3 signal.

## 15. Paired day-local temporal-label null

Run only after every non-null precheck gate passes.

Hold C0 and C1 probabilities fixed.

Within each validation day, circularly shift labels using shared eligible k.

Require:
`min(k, n_day-k) >= 10` in every validation fold.

Primary null statistic:

`delta_LL = LL(C0, labels) - LL(C1, labels)`

Secondary diagnostic:
`delta_AUC = AUC(C1, labels) - AUC(C0, labels)`

Pass requires:
- observed delta_LL > q95(null delta_LL)
- empirical one-sided p <= 0.05

AUC null is diagnostic only.

## 16. Frozen P3 provenance

Before C0/C1 primary comparison:

- reproduce the frozen P3 M1 prediction hashes on original P3 support;
- verify the frozen P3 artifact identity;
- verify P2C/P4/P5/P6 artifact identities;
- record the original P3 pooled metrics.

This provenance reproduction is not the primary P7 comparator because P7's
OFI-valid support may be smaller.

## 17. P7 terminal statuses

If non-null gates fail:

`FAIL_L1_OFI_NO_STABLE_INCREMENTAL_VALUE`

If non-null gates pass but paired temporal null fails:

`FAIL_L1_OFI_TEMPORAL_NULL`

If all gates pass:

`ELIGIBLE_L1_OFI_INCREMENTAL_INFORMATION`

## 18. No rescue search

A P7 failure may not trigger inside P7:

- choosing only the best OFI horizon;
- adding mlofi_l5/l10;
- adding trade imbalance;
- adding book depth;
- adding dynamics;
- changing the window;
- changing the barrier/horizon;
- class weighting/resampling;
- HGB/XGBoost/MLP/LSTM/Transformer;
- threshold optimization;
- PnL/economics;
- forward data.

Any such question requires a new DEV design.

## 19. Data scope

Authorized:
- consumed BTCUSDT Jan-Jul only.

Forbidden:
- Aug-30
- Sep-01+
- archive bucket
- abundant-love
- ETH/SOL
- external/news/options/on-chain additions

## 20. Implementation files

Only:

- `src/multimarket/dev030_p7_ofi_incremental.py`
- `tests/test_dev030_p7_ofi_incremental.py`

Frozen prior scientific source/test must remain unchanged.

## 21. Synthetic test requirements

At minimum verify:

1. exact A/120/16/32 identity;
2. exact 23 PRICE baseline names;
3. exact three OFI source features;
4. exact 24 OFI summary names;
5. exact 47 augmented feature count;
6. rejection of any extra FLOW column;
7. C0/C1 exact support matching;
8. chronological outer folds;
9. chronological inner splits;
10. train-only scaling;
11. exact C grid;
12. probability-first inner C selection;
13. log-loss/Brier/AUC arithmetic;
14. fold/pooled paired deltas;
15. leave-one-fold-out gates;
16. AUC >= 0.56 floor;
17. temporal-null common shifts;
18. every gate vetoes independently;
19. no threshold optimization;
20. no alternate model family;
21. no PnL/economics;
22. no forward-data interface;
23. deterministic hashes;
24. deterministic canonical JSON;
25. atomic write-once output;
26. tests do not analytically open real data.

## 22. Real-run boundary

Implementation and synthetic validation only until separately frozen.

A real Jan-Jul P7 fit requires a new explicit authorization after:
- focused P7 PASS;
- prior regressions PASS;
- source/test hashes frozen;
- worktree clean;
- GitHub boundary review confirms only P7/docs changes.

## 23. Interpretation boundary

A P7 pass means only:

> the predeclared multiscale L1 OFI family adds stable incremental
> conditional-direction information on consumed BTCUSDT Jan-Jul development
> data.

It does not imply:
- forward confirmation;
- deployability;
- profitability;
- action threshold readiness.

If P7 passes, later work may test composition with the already-successful P4
touch head under a separate frozen design.
