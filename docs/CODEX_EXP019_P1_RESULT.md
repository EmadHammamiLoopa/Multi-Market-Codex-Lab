# CODEX-EXP-019-P1 Frozen Result

Status: **FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED**

Date: 2026-08-27

Frozen pre-output HEAD:

`bcf6f20f5b633b2aec4ac83983fdd50e8d95ddb0`

Result artifact:

`evidence/codex/exp019_p1_corrected_volatility_aug1/INDEPENDENT_VOLATILITY_AUG1_CORRECTED.json`

Result artifact SHA-256:

`a6d55db8e938a0c9b80f3e39117c07fd85e0316d408b159f6bd421ffa7920def`

Configuration SHA-256:

`ff1036eb24cf0afdc8654ad33d66a3a3177afb2b1406735c57232f0905fa526a`

OOS prediction-record SHA-256:

`3be80f4e869fe1138f9e395fb382d6b854cbcffe20ff70608a47c4bf286c3b23`

## Official adjudication

`CODEX-EXP-019-P1 = FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED`

This is a **valid predictive FAIL**, not INVALID.

No implementation, provenance, authorization, support, causality, direction, PnL, or network invariant failed.

## Aug-01 support

- valid-R decisions: **1,399**
- positives: **15**
- negatives: **1,384**
- prevalence: **0.010721944245889922**
- deterministic non-overlap decisions: **139**

The Aug-01 event prevalence was therefore approximately **1.07%**, much lower than most consumed Jan-Jul training days.

## Primary VOL result

Primary feature:

`rv_30m_bps`

Full support:

- n: **1,399**
- prevalence: **0.010721944245889922**
- ROC AUC: **0.9685934489402698**
- average precision: **0.3204202299670842**
- AP / prevalence: **29.88452678159672x**
- Brier score: **0.012884520692056659**
- Brier skill: **-0.21472046160953706**
- log loss: **0.09096185811853556**
- top-decile precision: **0.10**
- top-decile lift: **9.326666666666666x**
- top-quintile precision: **0.05357142857142857**
- top-quintile lift: **4.996428571428571x**

Deterministic non-overlap 10-minute subset:

- n: **139**
- prevalence: **0.007194244604316547**
- ROC AUC: **1.0**
- average precision: **1.0**
- AP / prevalence: **139.0x**
- Brier skill: **-0.36839832132419326**
- top-decile lift: **9.928571428571427x**

The non-overlap subset contains only one positive event, so its perfect rank metrics are descriptive but statistically fragile.

## Timing-placebo result

Full-support VOL_TIME_PLACEBO:

- ROC AUC: **0.9685934489402698**
- average precision: **0.3204202299670842**
- Brier skill: **-0.9469207513002456**
- top-decile lift: **9.326666666666666x**

Therefore:

`VOL_auc_minus_timing_placebo_auc = 0.0`

The preregistered timing-falsification gate required at least `+0.03`, so it failed.

## R diagnostic benchmark

Full support:

- ROC AUC: **0.9706647398843931**
- average precision: **0.37153926857106856**
- Brier skill: **-0.14583550887632635**
- top-decile lift: **9.326666666666666x**

Diagnostic deltas:

- `R_auc_minus_VOL_auc = 0.002071290944123283`
- `R_ap_minus_VOL_ap = 0.05111903860398437`

R was diagnostic only and was not a promotion gate.

## Positive-control canary

CANARY_VOL full support:

- ROC AUC: **1.0**
- average precision: **1.0**
- Brier skill: **0.9094223458318592**

Therefore:

`CANARY_auc_minus_VOL_auc = 0.031406551059730226`

The preregistered canary sensitivity gate required at least `+0.10`, so it failed.

This is a ceiling-effect failure under the frozen gate because legitimate VOL AUC was already approximately 0.969.

## Frozen promotion gates

Passed:

- VOL AUC >= 0.60
- VOL AP/prevalence >= 1.30
- VOL top-decile lift >= 1.50
- VOL non-overlap AUC >= 0.57
- VOL non-overlap top-decile lift >= 1.25
- Aug support contains both classes
- all implementation/provenance/causality invariants

Failed:

1. `vol_brier_skill_positive`
2. `vol_auc_minus_timing_placebo_at_least_0_03`
3. `canary_auc_minus_vol_at_least_0_10`

Because EXP019 required all 10 gates, the official result is FAIL.

## Invariants and authorization

All invariants passed.

Key provenance:

- EXP018 invalid artifact SHA exact
- EXP018 state proves Aug remained analytically unopened before EXP019
- EXP017 structural parent SHA exact
- global research-seal source unchanged
- exact authorized Aug path verified
- Aug FEATURES250 SHA exact
- common support exact
- no Aug fit/refit
- older Aug holdout unopened
- direction not scored
- PnL not scored
- network not accessed

Frozen Aug FEATURES250 SHA:

`62c72f13f7176d9b4d9bdb69ad940cdcc56858698d64b4a061cecbb4a09ec5f5`

## Scientific interpretation

The independent Aug-01 validation provides unusually strong **rank-discrimination evidence** for the frozen trailing-volatility state: AUC approximately 0.969, AP approximately 0.320 against approximately 1.07% prevalence, and top-decile lift approximately 9.33x.

However, EXP019 does **not** satisfy the frozen evidence standard for calling the volatility-regime timing hypothesis independently confirmed.

Three issues prevent promotion:

1. probability calibration/generalization failed the positive Brier-skill requirement;
2. the frozen within-training-day label-permutation placebo produced identical Aug ranking, so the experiment did not establish incremental event timing beyond preserved regime/day structure under this falsification;
3. the frozen +0.10 canary AUC margin was unreachable given the legitimate model's near-ceiling AUC and therefore failed as preregistered.

The result must not be rescued by changing gates, recalibrating on Aug-01, changing the placebo, changing the model, or selecting a subset after observing the outcome.

## Scientific state after EXP019

Aug-01 is now analytically consumed.

Must remain:

- older Aug-04..Aug-23 holdout unopened
- direction_scored = false
- pnl_scored = false

Any new hypothesis requires a new Experiment ID and must not use Aug-01 as an independent holdout again.
