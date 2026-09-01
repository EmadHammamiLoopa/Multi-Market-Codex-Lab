# DEV030-P4 T2 Touch-Vs-None and Two-Head Composition Design

Status: **DESIGN FROZEN BEFORE T2 IMPLEMENTATION OR FITTING**

Parent scientific state:
- DEV030-P3 Campaign-1 implementation frozen at
  `c375ed43419ca00b93ff94f608d6957c57609ff8`
- DEV030-P3 real result artifact SHA256
  `f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`
- selected T1 survivor:
  `A / 120s / 16bp / 32s / PRICE / S1`
- selected T1 task:
  `DIRECTION_GIVEN_TOUCH`
- selected T1 pooled OOF BA:
  `0.5419424830832598`
- selected T1 pooled S1-minus-S0 BA delta:
  `+0.05505295675198585`

Design branch:
`research/dev030-p4-t2-composition-design`

This document freezes the next development question before any T2 model fit.

## 1. Scientific purpose

P3 established one development-stage T1 survivor on a primary economic target,
but T1 is oracle-conditioned: it predicts LONG_FIRST versus SHORT_FIRST only
on rows where a directional barrier is later touched.

P4 asks the missing deployability question:

> Can the same frozen causal 32-second PRICE representation predict whether
> target A will experience any directional first passage at all, and can that
> touch probability be composed with the frozen T1 direction head without
> weakening chronology, provenance, or claim boundaries?

P4 does **not** test profitability.

P4 does **not** optimize a trading threshold.

P4 does **not** open forward holdout data.

## 2. Frozen target and representation

There is exactly one T2 development configuration:

- symbol: BTCUSDT
- target: A
- horizon: 120 seconds
- barrier: 16 bp
- sequence window: 32 seconds
- feature block: PRICE
- representation: S1 engineered causal sequence summaries

No target, window, block, model family, or feature search is authorized in P4.

S0 matched snapshot is retained only as a baseline.

The frozen P3 T1 survivor remains immutable.

## 3. Authorized data scope

Authorized analytical data:

- already-consumed BTCUSDT development days only:
  - 2026-01-01
  - 2026-02-01
  - 2026-03-01
  - 2026-04-01
  - 2026-05-01
  - 2026-06-01
  - 2026-07-01

Forbidden:

- Aug-30
- Sep-01 or later
- archive bucket
- abundant-love
- ETH/SOL
- options
- DVOL
- funding
- open interest
- liquidations
- macro/news
- on-chain data
- EXP024 opportunity scores/ranks
- EXP029 eligibility/gates

No new data source is introduced.

## 4. Frozen source/result identities

Before any P4 model fit, verify:

- frozen P2B direction dataset source SHA256:
  `54e7315a12cac10413ac2017849466eb3d225282e3dcf48484615409680348c9`
- frozen P2A sequence feature source SHA256:
  `30952d31795d5fd88c9dfd9641a5332b662eeb32f30ec9ac283f8339d26ac11c`
- frozen first-passage source SHA256:
  `33dbbb53dfe10cfa859037fa2a89d05010f7950e3ec74e51422135ec585d0bc7`
- frozen P3 source SHA256:
  `9730f62cd6e2ee2a84cb402a890629f7335eb42b730f24f69ffca971281ba675`
- frozen P3 test SHA256:
  `a3d57a928d6a2dedc762111e1859fa9d290ee084412d7c613f7541398e46360b`
- frozen P2C artifact SHA256:
  `a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0`
- frozen P3 artifact SHA256:
  `f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`

Any mismatch is a hard pre-fit failure.

## 5. T2 label definition

T2 is exactly:

`TOUCH_VS_NONE`

On a target-A decision row:

- `TOUCH = 1` iff the frozen first-passage label is
  `LONG_FIRST` or `SHORT_FIRST`
- `NONE = 0` iff the frozen first-passage label is `NONE`
- rows with invalid target labels are excluded
- rows failing the frozen S1 common-support validity are excluded
- same-row ambiguous target rows remain invalid and excluded
- no label relabeling or tolerance change is allowed

T2 uses the same target geometry and causality semantics as the frozen T1
survivor.

## 6. T2 support

The T2 native evaluation support is:

`common representation support ∩ valid target rows`

Unlike T1, T2 includes valid `NONE` rows.

T2 must preserve:

- chronological timestamps
- per-day support counts
- per-day TOUCH/NONE counts
- fold train/validation support counts
- deterministic support hashes

T2 support must be constructed before fitting.

The implementation must also preserve the exact T1 subset identity inside T2
support so composition checks can prove that the frozen T1 head reproduces its
P3 behavior on directional-touch rows.

## 7. Chronological validation

Use exactly the existing four outer folds:

| Fold | Train days | Validate |
| --- | --- | --- |
| 1 | Jan-Mar consumed days | Apr consumed day |
| 2 | Jan-Apr consumed days | May consumed day |
| 3 | Jan-May consumed days | Jun consumed day |
| 4 | Jan-Jun consumed days | Jul consumed day |

No random split.

For each outer fold, use the final outer-training day as inner validation and
all earlier outer-training days as inner fit.

No outer validation label may enter preprocessing, C selection, feature
selection, or model fitting.

## 8. Frozen T2 baselines

### B0 — prevalence probability

For each outer fold:

`p_touch = training TOUCH prevalence`

applied as a constant probability to every validation row.

This is the principal calibration/ranking null baseline.

### B1 — matched S0 logistic model

Use the same frozen target, support, folds, and C grid, but with S0 snapshot
features.

This is the primary representation baseline.

### B2 — frozen S1 T2 logistic model

This is the candidate T2 model.

No other T2 model family is authorized.

## 9. T2 model family

Pipeline:

1. `StandardScaler`, fit on training rows only
2. `LogisticRegression`
   - solver = `lbfgs`
   - L2 semantics = `l1_ratio=0.0`
   - class_weight = `None`
   - max_iter = `1000`
   - fit_intercept = `True`
   - random_state = `20260825`

Frozen C grid:

`[0.01, 0.1, 1.0, 10.0]`

Select C on inner validation by:

1. highest Average Precision
2. highest ROC AUC
3. lowest Brier score
4. smaller C

This ordering is frozen because T2 is imbalanced and probability quality is
more important than a 0.5 classification threshold.

No class weighting or resampling is allowed.

## 10. T2 primary metrics

Report per fold and pooled OOF for B0, S0, and S1:

- support
- TOUCH count
- NONE count
- TOUCH prevalence
- Average Precision (AP)
- ROC AUC
- Brier score
- log loss

Also report threshold-0.5 diagnostics:

- balanced accuracy
- macro F1
- MCC
- confusion matrix `[NONE, TOUCH]`
- predicted TOUCH count
- predicted NONE count

Threshold-0.5 diagnostics do not determine the primary T2 gate.

## 11. Incremental T2 comparisons

The primary T2 representation comparison is S1 versus matched S0 on exact
support:

- `delta_AP = AP(S1) - AP(S0)`
- `delta_AUC = AUC(S1) - AUC(S0)`
- `delta_Brier = Brier(S0) - Brier(S1)`

Positive `delta_Brier` means S1 has lower/better Brier score.

Also report S1 lift over prevalence baseline:

- `AP_lift_ratio = AP(S1) / TOUCH_prevalence`
- `Brier_skill_vs_prevalence = 1 - Brier(S1)/Brier(B0)`

No pooled metric may hide fold-level instability.

## 12. T2 temporal null

Use the same day-local circular-shift principle as P3.

Keep S1 probabilities fixed.

Within each outer validation day, circularly shift binary TOUCH/NONE labels by
shared eligible k values satisfying:

`k > 0`

and

`min(k, n_day-k) >= 10`

Require at least 20 shared eligible shifts.

For every shift compute pooled:

- Average Precision
- ROC AUC

Primary null gate uses AP:

- observed pooled AP must be strictly greater than null q95
- empirical one-sided p <= 0.05

ROC AUC null is reported as a secondary falsification diagnostic.

The null cannot rescue a failed metric/stability precheck.

## 13. T2 engineering promotion gate

T2 is `ELIGIBLE_FOR_COMPOSITION` only if all are true:

1. pooled S1 ROC AUC >= 0.60
2. pooled S1 AP lift ratio over prevalence >= 1.50
3. pooled S1-minus-S0 AP delta > 0
4. pooled S1-minus-S0 ROC AUC delta > 0
5. pooled S1 Brier skill versus prevalence > 0
6. at least 3/4 outer folds have S1 ROC AUC > 0.50
7. at least 3/4 outer folds have S1 AP above that fold's TOUCH prevalence
8. leave-one-fold-out pooled S1-minus-S0 AP delta remains > 0 for all four omissions
9. observed pooled S1 AP > temporal-null AP q95
10. temporal-null empirical AP p <= 0.05

These are development engineering gates, not confirmatory statistical claims.

If T2 fails, do not optimize thresholds, change class weights, add models, or
open forward data.

## 14. Frozen T1 reconstruction requirement

Before composition, reconstruct the selected T1 head exactly fold by fold.

For each fold:

- use the same target A / 32s / PRICE / S1 representation
- use the same chronological training and validation calendars
- use the same scaler-fitting semantics
- use the exact P3 selected C recorded in the frozen artifact:
  - Fold 1 = 10.0
  - Fold 2 = 10.0
  - Fold 3 = 0.1
  - Fold 4 = 0.01

On each fold's T1 validation subset, regenerated T1 predictions/probabilities
must reproduce the frozen P3 prediction SHA256 exactly.

If any T1 prediction hash differs, composition is forbidden.

No T1 refit rule or C selection is allowed to change.

## 15. Two-head composition

Only if T2 passes Section 13.

For every valid T2 validation row:

- obtain `p_touch` from frozen T2 S1
- obtain `p_long_given_touch` from the frozen T1 S1 head scored on the same
  causal representation

Define:

`p_LONG = p_touch * p_long_given_touch`

`p_SHORT = p_touch * (1 - p_long_given_touch)`

`p_NONE = 1 - p_touch`

Require:

- each probability finite
- each probability in [0,1]
- row sum equal to 1 within numerical tolerance
- timestamp alignment exact
- no row from another support enters composition

This is a probability composition only.

## 16. Composition evaluation

Evaluate the composed three-class probabilities on valid target rows with
labels:

- SHORT_FIRST
- LONG_FIRST
- NONE

Primary composition metrics:

- multiclass log loss
- multiclass Brier score
- macro one-vs-rest ROC AUC where defined
- macro one-vs-rest Average Precision
- per-class AP
- per-class ROC AUC

Also report fixed argmax diagnostics:

- macro F1
- balanced accuracy
- confusion matrix in fixed order
  `[NONE, SHORT_FIRST, LONG_FIRST]`

Argmax is diagnostic only.

No abstention/action threshold is optimized.

## 17. Composition baselines

Compare against exactly:

### C0 — prevalence-only three-class baseline

Training-fold empirical class probabilities.

### C1 — T2-only nondirectional baseline

`p_NONE = 1-p_touch`

split touch probability according to training directional prevalence:

`p_LONG = p_touch * train_P(LONG | TOUCH)`

`p_SHORT = p_touch * train_P(SHORT | TOUCH)`

This measures whether the frozen T1 direction head adds value beyond T2 plus
a constant directional prior.

### C2 — frozen two-head composition

The candidate defined in Section 15.

No direct three-class learned model is authorized in this initial P4 campaign.

## 18. Composition success gate

Composition is labeled
`ELIGIBLE_FOR_LATER_POLICY_DESIGN`
only if:

1. T2 is `ELIGIBLE_FOR_COMPOSITION`
2. frozen T1 hash reproduction passes on all four folds
3. composed multiclass log loss is lower than C1 pooled
4. composed multiclass Brier score is lower than C1 pooled
5. composed macro one-vs-rest AP is higher than C1 pooled
6. at least 3/4 folds improve multiclass log loss versus C1
7. leave-one-fold-out pooled log-loss improvement versus C1 remains positive
8. no probability/provenance/alignment invariant fails

This still does not authorize a trading policy.

## 19. What P4 success would mean

A full P4 success means only:

- T2 contains stable touch information on the selected A configuration
- frozen T1 direction information adds value beyond a constant direction prior
  when composed with T2
- the system has a probabilistic deployable-state representation suitable for
  later policy design

It does not mean:

- profitable trading
- optimal threshold
- correct sizing
- forward-confirmed alpha
- production readiness

## 20. Failure interpretation

If T2 fails:

- record `FAIL_T2_TOUCH_NOT_STABLE`
- do not compose
- do not escalate capacity automatically
- do not reopen Campaign 1
- do not change the T1 survivor

If T2 passes but composition fails:

- record `FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE`
- preserve both T1 and T2 evidence separately
- do not optimize action thresholds

If both pass:

- record
  `ELIGIBLE_FOR_LATER_POLICY_DESIGN`
- freeze the exact two-head configuration before any later policy/economic
  stage

## 21. No threshold search in P4

P4 explicitly forbids:

- confidence threshold search
- abstention threshold search
- action threshold search
- top-k trading selection
- opportunity threshold
- fee-aware threshold
- threshold chosen from outer validation

The 0.5 threshold and argmax outputs are diagnostics only.

Threshold/policy design is a later separately frozen stage.

## 22. No economics in P4

Do not compute:

- PnL
- net expectancy
- fees
- slippage-adjusted edge
- Sharpe
- drawdown
- profit factor
- capital curve
- leverage
- position size
- stop/take-profit optimization

P4 is predictive/compositional only.

## 23. Implementation boundary

Planned implementation files only:

- `src/multimarket/dev030_p4_touch_composition.py`
- `tests/test_dev030_p4_touch_composition.py`

Frozen P3 source/test must not be modified.

Frozen P2C/P2B/P2A/first-passage source/test must not be modified.

## 24. Required synthetic tests before real T2 fitting

At minimum prove:

1. target/window/block identity is exactly A/120s/16bp/32s/PRICE
2. T2 mapping LONG_FIRST/SHORT_FIRST -> TOUCH and NONE -> NONE is exact
3. invalid and ambiguous target rows are excluded
4. common-support validity is exact
5. chronological outer folds are unchanged
6. chronological inner folds are unchanged
7. no outer validation enters scaler fit
8. exact C grid and AP/AUC/Brier tie order
9. no class weights or resampling
10. B0 prevalence probability is training-only
11. AP/AUC/Brier/log-loss arithmetic is correct
12. S0/S1 support is matched exactly
13. temporal null is day-local and deterministic
14. insufficient null shifts cannot pass
15. every T2 promotion gate independently vetoes advancement
16. frozen T1 C values are exact
17. regenerated T1 validation hashes must equal P3 hashes
18. composition probability arithmetic is exact
19. composition rows sum to one
20. three-class label order is exact
21. C0/C1/C2 baselines are exact
22. composition success gates independently veto advancement
23. no threshold optimization interface exists
24. no PnL/economic interface exists
25. no opportunity-gate interface exists
26. no forward-data interface exists
27. canonical JSON is deterministic
28. output is atomic/write-once
29. runtime provenance is fail-closed
30. implementation tests do not open real market data

## 25. Real-run authorization boundary

After implementation and synthetic tests are frozen, stop.

The real P4 Jan-Jul run requires separate explicit authorization.

No forward holdout may be opened merely because T2/composition passes.

## 26. Current decision

P4 is authorized for **implementation and synthetic testing only** after this
design freeze.

Real T2 fitting is not authorized by this document.

Campaign-2 M2 remains deferred.

The project priority is now:

`T2 touch learnability -> frozen T1 reproduction -> two-head composition`

before any policy threshold, economics, or forward confirmation.
