# DEV031-P1B — Frozen Incremental Event/Depth Direction Design

Status: `DESIGN_FROZEN_BEFORE_IMPLEMENTATION_OR FITTING`

Experiment:
`DEV031-P1B`

Design version:
`event-depth-incremental-direction-v1`

## 1. Exact task

- symbol = BTCUSDT
- task = T1 DIRECTION_GIVEN_TOUCH
- class 0 = SHORT_FIRST
- class 1 = LONG_FIRST
- target = A
- horizon = 120 seconds
- executable barrier = 16 bp
- sequence window = 32 seconds

No target/window/barrier/task search.

## 2. Frozen input

P1B consumes only:

`/home/emadh/Multi-Market/evidence/dev031_p1a_event_depth_materialization_v1`

Manifest:
`DEV031_P1A_EVENT_DEPTH_MATERIALIZATION.json`

Required SHA256:
`a8a4f89262b9f01e76fc10a1b9c54ac28dd7faec3180a1a0fac19499eb9467d8`

Required P1A status:
`EVENT_DEPTH_EXACT_P3_SUPPORT_MATERIALIZED`

No raw L2 file is opened in P1B.

## 3. Exact support

Total frozen T1 support:
- 1,374 rows
- LONG = 684
- SHORT = 690

Primary outer-validation OOF support:
- Fold 1 Apr = 159 (86 / 73)
- Fold 2 May = 64 (40 / 24)
- Fold 3 Jun = 126 (60 / 66)
- Fold 4 Jul = 224 (123 / 101)
- pooled OOF = 573

P1B must reproduce exact support hashes and labels from P1A.

No row may be dropped or added.

## 4. Comparator C0

C0 contains exactly the 23 frozen P3 PRICE S1 features serialized by P1A.

Feature order must equal the P1A manifest order.

## 5. Augmented C1

C1 contains:
- all 23 C0 PRICE features;
- all 26 frozen EVENT_DEPTH features.

Total = 49 features.

No EVENT_DEPTH subset search.
No feature selection.
No PCA.
No interaction feature.
No missing-value imputation.
No alternate representation.

## 6. Frozen P3 provenance reproduction

Before primary C0/C1 inference:
- verify P3 artifact SHA256 =
  `f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`;
- verify P1A manifest records the same P3 dependency;
- reproduce exact frozen P3 selected-survivor OOF prediction hashes using the
  original P3 fitting rule and P1A PRICE23 matrix.

Expected P3 selected C by fold:
- F1 = 10.0
- F2 = 10.0
- F3 = 0.1
- F4 = 0.01

Expected frozen P3 OOF prediction hashes:
- F1 = `e03d233bff936b49a0452994497f32ca5ecbe52c1f490d855fe8d06dbfa9dcf4`
- F2 = `cd2cba0a6dcf3591ec9848b78e31aef796dad15d371bbecb8517aa2507340bdd`
- F3 = `19f9acf70b0065a307c0373952cad350339768607a156c9307e5192503bb1f31`
- F4 = `b05ee6e926d6a943e1fc89828eb3801af0863fa270bc2e5db5ed7cd93e9a4b66`

This is provenance only.

## 7. Primary C0/C1 fitting rule

Both C0 and C1 use the same family:

`StandardScaler(train-only) + LogisticRegression(L2)`

Parameters:
- solver = lbfgs
- l1_ratio = 0.0
- fit_intercept = True
- class_weight = None
- max_iter = 1000
- random_state = 20260825
- threshold diagnostic = 0.5

C grid:
`[0.01, 0.1, 1.0, 10.0]`

No other model family.

## 8. Exact outer folds

- Fold 1: Jan-Mar -> Apr
- Fold 2: Jan-Apr -> May
- Fold 3: Jan-May -> Jun
- Fold 4: Jan-Jun -> Jul

No random splitting.

## 9. Exact inner split

For each outer fold:
- inner validation = final outer-training day;
- inner fit = all earlier outer-training days.

No outer validation leakage.

## 10. Probability-first inner C selection

Select C separately for C0 and C1 by:
1. lowest binary log loss;
2. lowest Brier score;
3. highest ROC AUC;
4. smaller C.

Serialize all four candidates for every fold and representation.

No BA-based selection.

## 11. Primary metrics

Per fold and pooled:

Primary:
- binary log loss;
- Brier score;
- ROC AUC.

Threshold-0.5 diagnostics:
- balanced accuracy;
- macro F1;
- MCC;
- precision/recall/F1 by class;
- confusion matrix.

No threshold optimization.

## 12. Primary incremental deltas

For C1 versus C0:

- log-loss improvement = LL(C0) - LL(C1)
- Brier improvement = Brier(C0) - Brier(C1)
- AUC delta = AUC(C1) - AUC(C0)

Compute:
- every fold;
- pooled OOF;
- every leave-one-fold-out pooled aggregate.

## 13. Non-null precheck gates

Temporal null runs only if ALL are true:

1. pooled C1 log loss < pooled C0 log loss;
2. pooled C1 Brier < pooled C0 Brier;
3. pooled C1 AUC > pooled C0 AUC;
4. pooled C1 AUC >= 0.56;
5. >=3/4 folds have positive log-loss improvement;
6. >=3/4 folds have positive Brier improvement;
7. >=3/4 folds have positive AUC delta;
8. >=3/4 folds have C1 AUC > 0.50;
9. every leave-one-fold-out log-loss improvement > 0;
10. every leave-one-fold-out Brier improvement > 0;
11. every leave-one-fold-out AUC delta > 0;
12. both classes receive nonzero predicted probability in every fold;
13. all provenance/support/label/feature invariants pass.

The AUC floor 0.56 is frozen before fitting and matches the previous bounded
incremental-information standard.

## 14. Paired day-local temporal-label null

Run only after every precheck gate passes.

Hold C0 and C1 probabilities fixed.

Within each validation fold/day, circularly shift labels using the same shared k.

Eligible shifts:
`min(k, n_day-k) >= 10` for every validation day.

Expected shared set from frozen support:
k = 10..54, subject to implementation verification.

Primary null statistic:

`delta_LL = LL(C0, labels) - LL(C1, labels)`

Secondary diagnostics:
- delta Brier
- delta AUC

Pass requires:
- observed delta_LL > q95(null delta_LL);
- empirical one-sided p <= 0.05.

## 15. Terminal statuses

If non-null precheck fails:

`FAIL_EVENT_DEPTH_NO_STABLE_INCREMENTAL_DIRECTION_VALUE`

If precheck passes but temporal null fails:

`FAIL_EVENT_DEPTH_DIRECTION_TEMPORAL_NULL`

If all gates pass:

`ELIGIBLE_EVENT_DEPTH_INCREMENTAL_DIRECTION_INFORMATION`

## 16. Stop rule

If P1B fails, P1B may not:
- choose only the best event horizon;
- choose only one depth band;
- drop “bad” features;
- change 5/15/50 bp bands;
- change 1/4/16/32 s horizons;
- add more depth levels;
- add trades;
- add L1 OFI rescue;
- change target/window;
- class-weight/resample;
- threshold optimize;
- try HGB/XGBoost/MLP/LSTM/Transformer;
- use EXP024 rank as filter;
- compose P4 touch head;
- run PnL.

Any such question requires a new experiment ID.

## 17. Data/forward guards

Authorized:
- frozen P1A Jan-Jul materialized artifacts only.

Forbidden:
- raw L2 reopening;
- Aug-01;
- Aug-30;
- Sep-01+;
- Railway;
- archive bucket;
- abundant-love;
- ETH/SOL;
- PnL;
- opportunity filtering.

## 18. Canonical output

Directory:
`/home/emadh/Multi-Market/evidence/dev031_p1b_event_depth_incremental_v1`

Artifact:
`DEV031_P1B_EVENT_DEPTH_INCREMENTAL_RESULT.json`

Write once only.

## 19. Interpretation boundary

P1B PASS means only that the frozen event-time/deep-depth block adds stable
conditional-direction information on consumed Jan-Jul development data.

It does not prove:
- profitability;
- deployable policy;
- forward validity;
- opportunity ranking;
- touch probability.

Only after a P1B PASS may a later separately frozen design consider composition
with the preserved P4 touch head and/or EXP024 opportunity-ranking success.
