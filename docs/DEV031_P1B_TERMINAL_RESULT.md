# DEV031-P1B Terminal Result

Experiment:
`DEV031-P1B`

Official terminal status:

`FAIL_EVENT_DEPTH_NO_STABLE_INCREMENTAL_DIRECTION_VALUE`

Scientific execution commit:

`a6cf7a3c448cbb745de8a15ca6d2d33169628b2c`

Canonical artifact:

`/home/emadh/Multi-Market/evidence/dev031_p1b_event_depth_incremental_v1/DEV031_P1B_EVENT_DEPTH_INCREMENTAL_RESULT.json`

SHA256:

`4e55554151b8caba588ea2ffdf7c6b1454a5eabe74f833a44f3784a980ddb56b`

Bytes:
`14796`

## Result

C0 PRICE23 pooled:
- log loss = 0.7066614084
- Brier = 0.2553342217
- ROC AUC = 0.5364690595
- balanced accuracy = 0.5390188291
- macro F1 = 0.5002901694

C1 PRICE23 + EVENT_DEPTH26 pooled:
- log loss = 0.7344602724
- Brier = 0.2597066443
- ROC AUC = 0.5764930862
- balanced accuracy = 0.5749485143
- macro F1 = 0.5685096264

Primary deltas:
- log-loss improvement = -0.0277988640
- Brier improvement = -0.0043724226
- AUC delta = +0.0400240267

The preregistered probability-quality precheck failed, so the temporal null was
correctly not run.

Failed gates:
- pooled log loss better
- pooled Brier better
- at least 3/4 fold log-loss improvement
- at least 3/4 fold Brier improvement
- every leave-one-fold-out log-loss improvement positive
- every leave-one-fold-out Brier improvement positive

Ranking-related gates that passed:
- pooled AUC improved
- C1 pooled AUC >= 0.56
- AUC improved in 3/4 folds
- C1 AUC > 0.50 in 3/4 folds
- every leave-one-fold-out AUC delta positive

## Scientific interpretation

P1B is an official FAIL for stable incremental directional probability
information.

It contains a preserved partial success:
the frozen EVENT_DEPTH block improved directional ranking/discrimination in a
pattern that remained positive under every leave-one-fold-out AUC diagnostic.

This is hypothesis-generating only.

It does not authorize:
- changing P1B features;
- calibration rescue;
- threshold search;
- alternate models;
- PnL;
- EXP024 filtering;
- P4 composition;
- another Jan-Jul ranking test that pretends to be confirmatory.

A ranking-specific claim now requires a new experiment and fresh unseen data.

Permanent:
`DEV031-P1B MUST NEVER BE RERUN`.
