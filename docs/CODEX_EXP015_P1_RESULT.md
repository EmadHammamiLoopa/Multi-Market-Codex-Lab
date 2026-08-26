# CODEX-EXP-015-P1 Frozen Result

Status: **FAIL_SEGMENTED_BTC_OPTIONS_FLOW_NO_INCREMENTAL_TIMING_INFORMATION**

Date: 2026-08-26

Frozen implementation HEAD before output:

`10824ff7ae6740d8a914719bb47e27410563afc6`

Configuration SHA-256:

`948dc8d382b520e101e27a7dd002807e30412eca7dee447e35cd45eee23166e4`

OOS prediction-records SHA-256:

`048f3156cddd5d36ad07a9e3a0c9d08aec66a8ace96615b45fdeaa0ed919acaa`

Result artifact:

`evidence/codex/exp015_p1_segmented_options_flow/SEGMENTED_BTC_OPTIONS_FLOW_TIMING.json`

Result artifact SHA-256:

`7a34a413979c098a7a8173b916b5faa2eaf4c2e277dc2ae6cbe12e9acbc5d10d`

## Official result

`CODEX-EXP-015-P1 = FAIL_SEGMENTED_BTC_OPTIONS_FLOW_NO_INCREMENTAL_TIMING_INFORMATION`

This is a valid frozen failure, not an invalid run.

All implementation, provenance, support, expiry, causality, chronological-fold, and common-support invariants passed.

Sealed August was not opened. Direction and PnL were not scored.

## Frozen representation

- BTCUSDT target only
- March-July 2026 consumed sandbox
- outer folds April-July
- 4 flow windows: 1, 5, 15, 30 minutes
- 6 moneyness × maturity segments
- 4 metrics per segment
- 96 segmented option-flow features
- corrected Deribit expiry = 08:00 UTC
- ATM boundary = ±0.025 log-moneyness
- maturity boundaries = 7 and 30 days
- structural zeros allowed for empty individual segments
- aggregate 1-minute flow required for support
- same frozen target, R baseline, FixedLogistic model, folds, controls, and gates as EXP011

## Common support

Pooled outer-test common support:

`n = 5062`

Prevalence:

`0.1495456341`

Fold outer counts:

- 2026-04-01: 1314
- 2026-05-01: 1237
- 2026-06-01: 1258
- 2026-07-01: 1253

## Pooled metrics

R baseline:

- AUC: `0.6029494751`
- AP: `0.2306502445`
- Brier: `0.1247370531`
- log loss: `0.4139161035`
- top-decile precision: `0.2662721893`

Segmented F only:

- AUC: `0.5343309138`
- AP: `0.1612919180`
- Brier: `0.1572997027`
- log loss: `0.5517413089`
- top-decile precision: `0.1360946746`

R + segmented F:

- AUC: `0.5402059293`
- AP: `0.1651946467`
- Brier: `0.1572237757`
- log loss: `0.5487020452`
- top-decile precision: `0.1637080868`

VOL diagnostic:

- AUC: `0.6335013356`
- AP: `0.2539192503`

R + time-permuted segmented F:

- AUC: `0.5714666213`
- AP: `0.1831262759`

CANARY_R:

- AUC: `0.9999420047`
- AP: `0.9996676876`

## Frozen primary deltas

- RF AUC - R AUC: `-0.0627435457`
- RF AP - R AP: `-0.0654555978`
- RF top-decile precision - R: `-0.1025641026`
- R Brier - RF Brier: `-0.0324867225` (RF worse)
- R log loss - RF log loss: `-0.1347859417` (RF worse)
- RF AUC - time-permuted RF AUC: `-0.0312606919`
- CANARY_R AUC - R AUC: `+0.3969925297`

The negative timing-falsification delta means the time-permuted segmented flow performed better than the correctly timed segmented flow.

## Fold behavior

RF vs R AUC delta:

- Apr: `-0.0405743921`
- May: `-0.0587063563`
- Jun: `+0.0589681173`
- Jul: `-0.0263716069`

RF beat R in only 1 of 4 outer folds.

## Non-overlap protection

On pooled non-overlapping 10-minute decisions:

- R AUC: `0.5389429996`
- F AUC: `0.5178900157`
- RF AUC: `0.5235465408`
- RF_F_TIME_PERMUTED AUC: `0.5402483516`

Segmented RF is worse than R and also worse than the time-permuted control.

## Gate adjudication

Passed 2 of 12 frozen gates:

- implementation/provenance/causality invariants: PASS
- positive-control canary delta >= 0.10: PASS

Failed 10 of 12:

- >=3/4 fold RF AUC wins
- timing falsification delta >= 0.01
- non-overlap incremental AUC >= 0.01
- non-overlap RF AUC >= 0.57
- pooled incremental AUC >= 0.01
- pooled incremental AP >= 0.01
- lower Brier
- lower log loss
- pooled RF AUC >= 0.60
- top-decile precision not lower

## Scientific interpretation

The preregistered moneyness × maturity segmented BTC options-flow representation does not add stable incremental 10-minute opportunity-timing information beyond R on the consumed March-July sandbox.

The result is stronger than a near-miss: the legitimate segmented-flow model materially degrades pooled discrimination, calibration, ranking quality, and non-overlap performance, while a time-permuted version performs better than the correctly timed version.

This rejects the specific 96-feature segmented BTC option-trade-flow block tested in EXP015.

It does not justify post-hoc feature pruning, alternate segment boundaries, window changes, regularization tuning, month removal, direction scoring, PnL scoring, or opening August under EXP015.

The VOL diagnostic remains stronger than R in this sandbox, but it is diagnostic only and cannot rescue EXP015. Any volatility-centered predictive hypothesis requires a new Experiment ID and preregistration before scoring.
