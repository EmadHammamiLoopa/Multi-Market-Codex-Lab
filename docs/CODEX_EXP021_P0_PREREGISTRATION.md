# CODEX-EXP-021-P0 Preregistration

Status: **PREREGISTERED CALIBRATION-DESIGN AUDIT**

Date: 2026-08-27

Experiment ID: `CODEX-EXP-021-P0`

Parent preserved commit:

`78bfeef1267afe858fbdfd310576111d4f352d08`

Parent diagnostic:

`CODEX-EXP-020-P0 = DIAGNOSTIC_COMPLETE_VOLATILITY_FALSIFICATION_AND_CALIBRATION`

EXP020 artifact SHA-256:

`cbbe2bd8a148b556cb0670b7a5adb4f49aef677e85ef77b8c4bea01a53e69249`

Frozen EXP019 status remains:

`FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED`

## Purpose

EXP021 is a sandbox-only calibration-design audit.

It does not retest EXP019 and cannot change EXP019's FAIL.

Its sole purpose is to determine whether a calibration rule can be selected **causally from historical consumed data only** before opening any still-sealed future holdout.

## Data scope

Analytical data allowed:

- BTCUSDT Phase-L FEATURES250 for Jan-Jul 2026 only.

Allowed parent artifacts:

- preserved EXP019 result;
- preserved EXP020 diagnostic result.

Forbidden:

- reparsing Aug-01 FEATURES250;
- opening Aug-04..Aug-23;
- any other sealed August data;
- ETH;
- direction;
- PnL;
- network access.

## Frozen base predictive model

The underlying ranking model is unchanged:

- symbol: BTCUSDT
- feature: `rv_30m_bps`
- target: frozen executable 10-minute opportunity >= 24 bp
- decision step: 60 s
- entry delay: 250 ms
- support: frozen valid-R support
- StandardScaler fit on base-model training data only
- LogisticRegression
- C = 1.0
- solver = lbfgs
- class_weight = none
- max_iter = 1000
- random_state inherited from frozen FixedLogistic

Calibration may alter probabilities only.

No candidate may use target-fold labels to fit itself.

## Frozen chronological audit folds

Calibration-design outer folds are exactly:

- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

For each outer fold D:

1. Fit the base VOL model on all consumed days strictly before D.
2. Predict D to obtain RAW probabilities.
3. Build calibration history only from completed OOF days strictly before D, beginning at 2026-03-01.
4. Each calibration-history day's probabilities must themselves come from a base VOL model trained only on days strictly before that calibration day.
5. Fit the candidate calibrator only on this historical OOF prediction/label history.
6. Apply it to RAW probabilities for D.

No target-fold label may enter model or calibrator fitting.

## Frozen OOF calibration-history construction

Earliest OOF calibration day:

`2026-03-01`

For each calibration day C:

- train base VOL model on all Jan-Jul sample days strictly earlier than C;
- predict C on valid-R support;
- store probability and label;
- these OOF records may be reused causally for later outer folds only.

For outer 2026-04-01:
- calibration history = Mar.

For outer 2026-05-01:
- calibration history = Mar-Apr.

For outer 2026-06-01:
- calibration history = Mar-May.

For outer 2026-07-01:
- calibration history = Mar-Jun.

## Frozen candidate set

Only three tracks exist:

### RAW

No calibration.

Diagnostic baseline only.

### ROLLING_OOF_INTERCEPT

Input:

`z = logit(p_raw)`

Fit only an additive intercept correction `delta` on historical OOF calibration records.

`delta` is the unique value satisfying:

`mean(sigmoid(z + delta)) = historical_OOF_prevalence`

Solve deterministically by bisection on [-30, 30] for exactly 100 iterations.

Apply:

`p_cal = sigmoid(logit(p_raw_target) + delta)`

This preserves ranking exactly.

### ROLLING_OOF_PLATT

On historical OOF calibration records fit:

`y ~ LogisticRegression(logit(p_raw))`

Frozen calibration model:

- one input column = clipped logit of OOF raw probability
- LogisticRegression
- C = 1e6
- solver = lbfgs
- class_weight = none
- max_iter = 1000
- random_state = 20260827
- no target-fold fit

Apply fitted intercept and slope to target RAW logits.

A fold with non-positive Platt slope makes the PLATT candidate structurally non-ready.

## Probability clipping

Before logit transforms:

`p = clip(p, 1e-6, 1 - 1e-6)`

No other clipping or probability floor.

## Frozen metrics

For RAW, INTERCEPT, and PLATT report per outer fold:

- n
- prevalence
- ROC AUC
- average precision
- Brier score
- Brier skill
- log loss
- calibration intercept
- calibration slope
- mean predicted probability

Also report candidate calibration parameters:

- INTERCEPT delta
- PLATT fitted intercept
- PLATT fitted slope
- calibration-history n
- calibration-history prevalence

## Frozen aggregate calibration metrics

Across the four outer folds compute:

### Aggregate Brier score

`sum((y-p)^2) / total_n`

### Fold-normalized Brier baseline

For each fold use that fold's observed prevalence as the constant-probability reference.

Aggregate baseline SSE:

`sum_over_folds sum((y - fold_prevalence)^2)`

Aggregate fold-normalized Brier skill:

`1 - candidate_total_SSE / aggregate_fold_baseline_SSE`

### Aggregate log loss

Total binary log loss over all four folds.

### Fold consistency counts

For each calibrated candidate:

- number of folds with Brier < RAW Brier;
- number of folds with log loss < RAW log loss;
- number of folds with AUC identical to RAW within absolute tolerance 1e-12.

## Frozen readiness rule

A calibrated candidate is `READY` only if all are true:

1. aggregate Brier score < RAW aggregate Brier score;
2. aggregate log loss < RAW aggregate log loss;
3. aggregate fold-normalized Brier skill > 0;
4. Brier improves over RAW in at least 3 of 4 folds;
5. log loss improves over RAW in at least 3 of 4 folds;
6. ranking is preserved in all 4 folds:
   `abs(candidate_auc - raw_auc) <= 1e-12`;
7. for PLATT only, fitted slope > 0 in all 4 folds;
8. all provenance/causality invariants pass.

No threshold may be relaxed after output.

## Frozen selection rule

If neither calibrated candidate is READY:

`NO_CALIBRATION_DESIGN_READY_SANDBOX`

If exactly one is READY, select it.

If both are READY:

1. select lower aggregate Brier score;
2. if exactly tied, select lower aggregate log loss;
3. if still exactly tied, select `ROLLING_OOF_INTERCEPT` for lower complexity.

Status:

`CALIBRATION_DESIGN_READY_SANDBOX`

The selected method is only a design candidate for a future independently preregistered experiment.

It is not validated by EXP021.

## Required invariants

- EXP020 artifact SHA exact;
- EXP020 status exact;
- EXP019 frozen FAIL remains unchanged;
- Jan-Jul feature hashes match frozen provenance;
- outer folds exactly Apr-Jul;
- OOF calibration days begin at Mar;
- every OOF prediction uses only strictly earlier base-model training days;
- every outer calibrator uses only OOF days strictly earlier than its target fold;
- no Aug feature parse;
- no Aug-04..Aug-23 access;
- no direction;
- no PnL;
- no network;
- EXP019 not re-adjudicated.

## Status mapping

Design candidate found:

`CALIBRATION_DESIGN_READY_SANDBOX`

No candidate satisfies frozen readiness:

`NO_CALIBRATION_DESIGN_READY_SANDBOX`

Implementation/provenance/causality violation:

`INVALID`

Neither non-INVALID status is a predictive PASS.

## No-rescue rule

EXP021 cannot:

- change EXP019's FAIL;
- use Aug-01 to choose a calibrator;
- fit any calibration parameter on Aug-01;
- open Aug-04..Aug-23;
- tune the candidate set after output;
- modify readiness rules after output;
- score direction;
- score PnL.

Any future independent validation requires a new Experiment ID and a still-unopened holdout.
