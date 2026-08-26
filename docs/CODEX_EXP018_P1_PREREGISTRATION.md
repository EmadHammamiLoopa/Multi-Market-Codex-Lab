# CODEX-EXP-018-P1 Preregistration

Status: **PREREGISTERED BEFORE ANY AUGUST TARGET, PREVALENCE, FEATURE DISTRIBUTION, MODEL OUTPUT, OR AUC IS INSPECTED**

Date: 2026-08-27

Experiment ID: `CODEX-EXP-018-P1`

Parent preserved commit:

`40ec11364dabb69bb2ed005df6e42034e0bbbec9`

Parent structural result:

`CODEX-EXP-017-P0 = AUG1_PHASE_L_FEATURES_GENERATED_AND_INTEGRITY_PASS`

EXP017 result artifact SHA-256:

`97c76a19a34971c7cef9eb01ad6c5b39d4e2c9885ed39a41054adef397ce4561`

Frozen Aug-01 FEATURES250 SHA-256:

`62c72f13f7176d9b4d9bdb69ad940cdcc56858698d64b4a061cecbb4a09ec5f5`

## Scientific question

Does the single causal trailing realized-volatility state variable `rv_30m_bps` independently rank occurrence of the already-frozen 10-minute executable opportunity target on the sealed BTCUSDT 2026-08-01 confirmation day?

This experiment tests **absolute volatility-regime predictability**, not whether VOL must outperform the broader R feature block.

R is retained only as a diagnostic benchmark.

## Why this hypothesis is separately justified

In the consumed sandbox, the frozen EXP004 volatility-only diagnostic was unexpectedly strong:

- pooled AUC = 0.66298
- AP/prevalence = 1.653x
- Brier skill = +0.02774
- top-decile lift = 2.014x

The broader R block improved only modestly over this baseline in EXP004.

Later BTC-only EXP011 and EXP015 diagnostics again showed strong VOL ranking on their common support.

Because those March-July outcomes are already known, re-running VOL on the same sandbox would not be a new test. EXP018 therefore uses the previously sealed 2026-08-01 BTCUSDT day as an independent confirmation holdout.

## Frozen symbol and calendar

Symbol:

`BTCUSDT`

Training calendar:

- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

Independent validation day:

`2026-08-01`

No ETH.

No 2026-08-04..2026-08-23 holdout access.

No later August date.

## Frozen input lineage

Training features use the already-consumed frozen Phase-L Jan-Jul `FEATURES250` files.

Validation uses exactly:

`BTCUSDT/2026-08-01_FEATURES250.csv`

from the local EXP017 derived directory.

Before parsing the validation file, EXP018 must verify:

1. EXP017 result artifact SHA-256 exactly:
   `97c76a19a34971c7cef9eb01ad6c5b39d4e2c9885ed39a41054adef397ce4561`
2. validation FEATURES250 SHA-256 exactly:
   `62c72f13f7176d9b4d9bdb69ad940cdcc56858698d64b4a061cecbb4a09ec5f5`

Any mismatch is `INVALID`.

## Frozen target

Exactly the EXP004/EXP011 opportunity-occurrence target:

- decision grid: every 60 seconds
- causal decision state at time t
- entry: t + 250 ms
- exit: entry + 600 seconds
- long gross bps:
  `10000 * log(bid_exit / ask_entry)`
- short gross bps:
  `10000 * log(bid_entry / ask_exit)`
- oracle magnitude:
  `max(long_gross_bps, short_gross_bps)`
- binary label:
  `oracle_gross_bps >= 24.0`

Direction remains hidden from model tracks.

No trading PnL is computed.

Rows without valid causal decision/entry/exit book state are excluded exactly as in the frozen EXP004 target implementation.

## Frozen causal feature

Primary legitimate model feature:

`rv_30m_bps`

Definition is the already-frozen EXP004 `_rv` construction:

- use 1-minute decision-grid midpoints
- 30-minute trailing window
- log returns between consecutive 1-minute mids
- realized volatility:
  `10000 * sqrt(sum(r_t^2))`
- all required book states must be valid
- no future row
- no forward fill

No other feature may enter the primary VOL model.

## Frozen R benchmark

For diagnostic comparison only, compute the exact frozen EXP004 `R_FEATURE_NAMES` block on the same valid-R support.

R is **not** a promotion gate for EXP018.

VOL does not need to outperform R to pass.

No post-result promotion of R is allowed from EXP018.

## Frozen training

Train only on BTCUSDT Jan-Jul consumed sandbox data.

For each training day, construct the same 1-minute target and R support using the frozen EXP004 implementation.

Concatenate all valid BTCUSDT Jan-Jul rows.

Primary model:

- feature count = 1
- feature = `rv_30m_bps`
- StandardScaler fit on training only
- LogisticRegression
- C = 1.0
- penalty = l2
- solver = lbfgs
- class_weight = none
- max_iter = 1000
- random_state = 20260825

No refit using August labels.

No tuning.

No calibration fit on August.

No threshold selection.

Diagnostic R benchmark uses the same frozen FixedLogistic model on the full R block.

## Frozen within-day timing placebo

To test whether the primary VOL signal contains timing information beyond day-level prevalence/regime composition:

- preserve each Jan-Jul training day's VOL feature rows exactly;
- independently permute that day's binary labels within that same day;
- deterministic seed derived from:
  `20260825|VOL_TIME_PLACEBO|BTCUSDT|YYYY-MM-DD`
- concatenate the permuted training days;
- fit the same one-feature FixedLogistic model;
- evaluate on the untouched Aug-01 labels.

August labels are never permuted.

The placebo is a falsification control only.

## Frozen positive control

Fit a forbidden canary model on Jan-Jul using:

- `rv_30m_bps`
- frozen oracle gross opportunity magnitude for that same training decision

Evaluate the canary on Aug-01 with the corresponding forbidden oracle magnitude.

This is a sensitivity control only and can never be promoted.

## Frozen support

Primary VOL, timing-placebo VOL, R benchmark, and canary are all evaluated on **the same Aug-01 valid-R support**.

This prevents support differences from driving metric comparisons.

The valid-R mask is determined before selecting the VOL column and follows the exact EXP004 R construction.

No options-flow support gate is used.

## Frozen metrics

On the full Aug-01 valid-R support compute:

- n
- prevalence
- ROC AUC
- average precision
- AP / prevalence
- Brier score
- Brier skill versus prevalence forecast
- log loss
- top-decile precision
- top-decile lift
- top-quintile precision
- top-quintile lift
- calibration intercept/slope as diagnostic

Also compute the same metrics on the deterministic non-overlapping 10-minute subset:

`minute_index % 10 == 0`

No other subset may be promoted.

## Frozen promotion gates

EXP018 PASS requires **all** of the following:

1. primary VOL full-support ROC AUC >= 0.60
2. primary VOL AP/prevalence >= 1.30
3. primary VOL Brier skill > 0
4. primary VOL top-decile lift >= 1.50
5. primary VOL non-overlap ROC AUC >= 0.57
6. primary VOL non-overlap top-decile lift >= 1.25
7. primary VOL AUC - timing-placebo VOL AUC >= 0.03
8. positive-control canary AUC - primary VOL AUC >= 0.10
9. Aug-01 valid-R support contains both target classes
10. all implementation/provenance/causality invariants pass

Thresholds 1-6 are inherited from the absolute evidence standard used in EXP004 where applicable.

The 0.03 timing-falsification margin and +0.10 canary sensitivity margin are inherited from EXP004's frozen diagnostic standards.

R-versus-VOL performance is reported but is not a gate.

## Status mapping

PASS only if all 10 gates pass:

`INDEPENDENT_VOLATILITY_REGIME_PREDICTABILITY_CONFIRMED`

Valid predictive failure:

`FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED`

Any provenance/hash/support/causality/implementation violation:

`INVALID`

## Frozen invariants

At minimum:

- parent EXP017 result artifact hash exact
- Aug FEATURES250 hash exact before parse
- exact symbol BTCUSDT
- exact validation date 2026-08-01
- training dates exactly Jan-Jul
- no Aug 04-23 access
- no network
- exact 60-second decision grid
- exact t+250ms entry
- exact +600s exit
- exact >=24 bp label
- exact `rv_30m_bps` primary feature
- valid-R common support identical across all tracks
- StandardScaler train-only
- no August fit/refit/tuning/calibration
- deterministic placebo permutation within each training day only
- August labels untouched
- direction not exposed to legitimate model inputs
- direction_scored = false
- pnl_scored = false

## Scientific guards

EXP018 necessarily opens Aug-01 analytically for the first time.

After output:

- sealed_aug1_analytically_opened = true
- target_scored = true
- model_fit = true
- auc_scored = true

Must remain false:

- older_august_holdout_opened
- direction_scored
- pnl_scored
- network_accessed

## No-rescue rule

Once EXP018 output exists, never rerun EXP018.

Do not:

- change the 30-minute volatility window
- add another volatility window
- add/remove R features
- change target threshold
- change horizon
- change decision grid
- change entry delay
- change model or regularization
- tune probability thresholds
- recalibrate on August
- change placebo construction
- relax any promotion gate
- remove part of Aug-01
- switch support masks
- open Aug 04-23 to rescue the result
- score direction or PnL under EXP018

Any materially different hypothesis requires a new Experiment ID.
