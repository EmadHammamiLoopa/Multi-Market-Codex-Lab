# CODEX-EXP-020-P0 Preregistration

Status: **PREREGISTERED DIAGNOSTIC-ONLY**

Date: 2026-08-27

Experiment ID: `CODEX-EXP-020-P0`

Parent preserved commit:

`164589a1e35806b0a5edbcfeceb613401501e297`

Frozen parent outcome:

`CODEX-EXP-019-P1 = FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED`

EXP019 artifact SHA-256:

`a6d55db8e938a0c9b80f3e39117c07fd85e0316d408b159f6bd421ffa7920def`

## Purpose

EXP020 is diagnostic-only.

It must not rescue, re-adjudicate, or relabel EXP019.

It asks two methodological questions raised by the frozen EXP019 result:

1. Why did the one-feature VOL model and the within-training-day label-permutation placebo produce identical Aug-01 ranking metrics?
2. Is the negative Aug-01 Brier skill consistent with severe base-rate / probability-calibration shift despite strong ranking?

## Data scope

Allowed analytical inputs:

- BTCUSDT Jan-Jul 2026 consumed Phase-L FEATURES250 files;
- the already-consumed, preserved EXP019 result artifact and its stored OOS prediction records.

Forbidden:

- reopening or reparsing the Aug-01 FEATURES250 file;
- any Aug-04..Aug-23 data;
- any other sealed August data;
- direction scoring;
- PnL scoring;
- network access.

## Frozen scientific state

EXP019 remains permanently:

`FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED`

No EXP020 output may change that status.

## Diagnostic A — one-feature monotonic placebo explanation

Using only the preserved EXP019 OOS prediction records:

- compare `p_VOL` and `p_VOL_TIME_PLACEBO`;
- compute Pearson correlation;
- compute Spearman rank correlation using deterministic average ranks;
- compare their sorted-index ordering;
- compare ROC AUC, AP, and top-decile ordering already present in EXP019.

Interpretation target:

If the two prediction vectors are strictly monotonic transformations of the same single feature ordering, identical rank metrics are expected even when probability calibration differs.

This is an explanatory diagnostic only.

## Diagnostic B — test-feature permutation falsification on consumed Jan-Jul

Use BTCUSDT consumed Jan-Jul only.

Use the same frozen target, support, feature, model, and expanding chronological design:

- feature = `rv_30m_bps`
- target = executable 10-minute oracle opportunity >= 24 bp
- decision step = 60 seconds
- entry delay = 250 ms
- model = frozen `FixedLogistic`
- training for each outer day = all earlier consumed BTC days
- outer days = 2026-03-01 through 2026-07-01

For each outer day:

1. fit the frozen VOL model on earlier days;
2. score the untouched outer-day VOL feature;
3. generate exactly 200 deterministic within-outer-day permutations of the **outer-day VOL feature values** while leaving labels fixed;
4. score each permuted vector with the already-fitted model;
5. compute real AUC and permutation AUC distribution.

Deterministic permutation seed:

`20260827|EXP020|VOL_TEST_FEATURE_PERM|YYYY-MM-DD|replicate`

Report per fold:

- real AUC;
- permutation mean AUC;
- permutation median AUC;
- permutation 95th percentile AUC;
- one-sided empirical p-value:
  `(1 + count(permuted_auc >= real_auc)) / (1 + 200)`.

Also pool the five outer folds by concatenating real predictions and, replicate-by-replicate, concatenating permuted predictions.

This is diagnostic evidence about whether causal VOL timing alignment carries information beyond the marginal VOL distribution.

No new promotion gate is defined.

## Diagnostic C — EXP019 calibration / base-rate shift

Use only the preserved EXP019 artifact.

Report:

- Jan-Jul training prevalence by day already stored in EXP019;
- pooled Jan-Jul training prevalence;
- Aug-01 prevalence from EXP019;
- mean `p_VOL` on Aug-01;
- mean `p_VOL_TIME_PLACEBO`;
- mean `p_R_BENCHMARK`;
- observed Brier score and Brier skill;
- prevalence-baseline Brier score;
- calibration intercept and slope already obtainable from stored labels/predictions using the frozen score function.

Also compute a **descriptive prior-shift correction** of VOL probabilities using the observed Aug prevalence:

`odds_corrected = odds_model * [pi_aug/(1-pi_aug)] / [pi_train/(1-pi_train)]`

where `pi_train` is pooled Jan-Jul training prevalence and `pi_aug` is the already-consumed Aug prevalence.

Report corrected Brier score, Brier skill, log loss, and AUC.

This correction is explicitly post-hoc and uses the observed Aug base rate. It is therefore diagnostic only and cannot validate or promote the model.

## Required provenance checks

Before analysis:

- EXP019 artifact SHA exactly matches the frozen digest;
- EXP019 status remains `FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED`;
- EXP019 OOS record SHA matches its recorded digest;
- Jan-Jul training feature hashes match frozen provenance;
- no Aug feature path is opened;
- no older August holdout is opened;
- no network access.

## Status mapping

Successful diagnostic execution:

`DIAGNOSTIC_COMPLETE_VOLATILITY_FALSIFICATION_AND_CALIBRATION`

Any implementation/provenance/causality violation:

`INVALID`

There is no scientific PASS status.

## No-rescue rule

EXP020 cannot:

- change EXP019's FAIL;
- define a new promotion gate after inspecting diagnostics;
- recalibrate and then call Aug-01 independently validated;
- use Aug-01 as a fresh holdout;
- open Aug-04..Aug-23;
- score direction;
- score PnL.

Any future predictive confirmation requires a new Experiment ID and a still-unopened holdout.
