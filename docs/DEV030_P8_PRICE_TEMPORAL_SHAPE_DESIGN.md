# DEV030-P8 PRICE Temporal Shape Design

Status: **DESIGN FROZEN BEFORE IMPLEMENTATION OR FITTING**

Date: 2026-09-02

Parent result:
`DEV030-P7 = FAIL_L1_OFI_NO_STABLE_INCREMENTAL_VALUE`

Research note:
`docs/DEV030_P8_PRICE_TEMPORAL_SHAPE_RESEARCH.md`

## 1. Scientific question

Does coarse causal temporal shape in the already-selected PRICE primitives add
stable T1 LONG_FIRST-vs-SHORT_FIRST information beyond the frozen 32-second
PRICE S1 whole-window summaries?

P8 changes representation only.

It does not change:
- target;
- window;
- primitive information family;
- model family.

## 2. Exact task and geometry

Exactly:
- BTCUSDT
- target A
- horizon = 120 seconds
- barrier = 16 bp
- window = 32 seconds
- task = DIRECTION_GIVEN_TOUCH
- SHORT_FIRST = 0
- LONG_FIRST = 1
- NONE excluded exactly as in P3

## 3. C0 baseline

C0 uses exactly the 23 frozen PRICE S1 features:
- spread_bps summaries;
- microprice_minus_mid_bps summaries;
- mid_log_return_250ms_bps summaries.

No change to their formulas or order.

## 4. C1 augmented temporal-shape representation

C1 contains all C0 features plus exact fixed-lag values of the same three PRICE
primitives at four predeclared causal landmarks:

- t - 32s
- t - 24s
- t - 16s
- t - 8s

Primitive order:
1. spread_bps
2. microprice_minus_mid_bps
3. mid_log_return_250ms_bps

Lag order within each primitive:
- lag_32s
- lag_24s
- lag_16s
- lag_8s

Exactly 12 added features.

Feature count:
- C0 = 23
- temporal-shape addition = 12
- C1 = 35

The current t value is NOT added because C0 already contains each primitive's
`__last` statistic.

No other lag is allowed.

## 5. Exact support

Primary C0 and C1 must use exactly the same PRICE T1 common-valid rows.

No support may be dropped merely because of C1 if the frozen 32-second PRICE S1
row is valid.

The implementation must prove that every requested lag snapshot is available
on every frozen PRICE S1-valid row. If not, fail closed instead of silently
shrinking support.

Primary OOF support is therefore expected to match P3 exactly:
- pooled = 573
- fold supports = 159, 64, 126, 224
- LONG = 309
- SHORT = 264

Any mismatch is a protocol failure.

## 6. Causal extraction

For a decision timestamp t, use only snapshots at:
- t-32s
- t-24s
- t-16s
- t-8s.

Each snapshot must be extracted by the existing frozen sequence-feature engine
or by byte-for-byte equivalent logic.

The derived 250ms return at a lag uses only that lag timestamp and its previous
250ms midpoint.

No future row relative to the lag may be used.

## 7. Frozen P3 provenance

Before primary P8 fitting:
- verify P2C/P3/P4/P5/P6/P7 artifact identities;
- reproduce exact P3 M1 prediction hashes on original support;
- verify exact 573-row pooled P3 support.

P3 reproduction remains provenance only.

Primary incremental comparison is matched C0 vs C1 under the same P8
probability-first model-selection protocol.

## 8. Outer folds

Exactly P3:
- F1 Jan-Mar -> Apr
- F2 Jan-Apr -> May
- F3 Jan-May -> Jun
- F4 Jan-Jun -> Jul

No random split.

## 9. Inner split

For each outer fold:
- inner validation = final outer-training day;
- inner fit = all earlier outer-training days.

No outer validation row may influence model selection.

## 10. Model family

Both C0 and C1 use exactly:

`StandardScaler(train-only) + LogisticRegression(L2)`

Parameters:
- solver = lbfgs
- l1_ratio = 0.0
- fit_intercept = True
- class_weight = None
- max_iter = 1000
- random_state = 20260825

Frozen C grid:
`[0.01, 0.1, 1.0, 10.0]`

No alternate model family.

## 11. Inner C selection

Separately for C0 and C1:

1. lowest binary log loss;
2. lowest Brier;
3. highest ROC AUC;
4. smaller C.

Serialize the full ledger.

## 12. Metrics

Per fold and pooled for C0/C1:
- binary log loss
- Brier
- ROC AUC

Threshold-0.5 diagnostics:
- balanced accuracy
- macro F1
- MCC
- class precision/recall/F1
- confusion matrix

No threshold optimization.

## 13. Incremental deltas

Compute:
- LL improvement = LL(C0) - LL(C1)
- Brier improvement = Brier(C0) - Brier(C1)
- AUC delta = AUC(C1) - AUC(C0)

For:
- pooled
- each fold
- every leave-one-fold-out pooled aggregate

## 14. Non-null precheck gates

Temporal null runs only if all pass:

1. pooled C1 log loss < C0;
2. pooled C1 Brier < C0;
3. pooled C1 AUC > C0;
4. pooled C1 AUC >= 0.56;
5. >=3/4 fold LL improvements positive;
6. >=3/4 fold AUC deltas positive;
7. >=3/4 C1 fold AUC > 0.50;
8. every LOO LL improvement > 0;
9. every LOO AUC delta > 0;
10. both classes receive nonzero probability in every fold;
11. exact-support invariant passes;
12. all dependency/provenance invariants pass.

## 15. Temporal null

Only after precheck PASS.

Hold C0/C1 validation probabilities fixed.

Within each validation day circularly shift labels using common eligible k
where:
`min(k, n_day-k) >= 10`.

Primary null statistic:
`LL(C0, shifted)-LL(C1, shifted)`

Pass requires:
- observed LL improvement > q95;
- one-sided empirical p <= .05.

AUC null is diagnostic only.

## 16. Terminal statuses

If precheck fails:
`FAIL_PRICE_TEMPORAL_SHAPE_NO_STABLE_INCREMENTAL_VALUE`

If precheck passes but null fails:
`FAIL_PRICE_TEMPORAL_SHAPE_TEMPORAL_NULL`

If all gates pass:
`ELIGIBLE_PRICE_TEMPORAL_SHAPE_INCREMENTAL_INFORMATION`

## 17. Forbidden rescue/search

Inside P8 do NOT:
- add any other lag;
- choose the best lag post hoc;
- change 32s window;
- add OFI/MLOFI/book/trade-flow features;
- add nonlinear/tree/deep model;
- class-weight/resample;
- calibrate;
- optimize threshold;
- compose T2/opportunity;
- run PnL/economics;
- open forward data.

Any such question requires a new DEV design.

## 18. Data scope

Authorized:
- consumed BTCUSDT Jan-Jul only.

Forbidden:
- Aug-30
- Sep-01+
- archive bucket
- abundant-love
- ETH/SOL
- news/options/on-chain

## 19. Implementation boundary

Implementation files only:
- `src/multimarket/dev030_p8_price_temporal_shape.py`
- `tests/test_dev030_p8_price_temporal_shape.py`

Frozen prior scientific source/test must remain unchanged.

No real Jan-Jul P8 fit until:
- focused P8 tests PASS;
- prior regressions PASS;
- source/test SHA256 frozen;
- worktree clean;
- GitHub boundary review confirms only P8/docs changes;
- explicit real-run authorization is recorded.

## 20. Interpretation boundary

A P8 pass means only:
> coarse fixed-lag temporal shape from the same PRICE primitives adds stable
> incremental conditional-direction information on consumed Jan-Jul data.

It does not imply:
- forward confirmation;
- profitability;
- action readiness;
- deployability.
