# DEV037-P0 Policy Feasibility Result

Status: `FAIL_ABSOLUTE_OOF_THRESHOLD_TRANSFER_NOT_OPERATIONALLY_STABLE`

Date: 2026-09-02

## Result summary

DEV037-P0 completed as a real-data feasibility diagnostic only.

No validation correctness was inspected.

Observed:

- checks pass = 43
- checks fail = 5
- focused tests = 9 passed
- harness smoke = PASS
- git tree remained clean
- canonical DEV037-P1 output remained absent

The frozen six-policy family was not operationally feasible under the original
absolute OOF q80 threshold-transfer rule.

## Root cause

The issue is score-distribution transfer, not validation-label performance.

Thresholds derived as absolute q80 values from historical OOF training scores
did not preserve approximately 20% action coverage on later validation days.

Examples:

Fold 1 / Apr:

- S0 coverage = 0.0021321962
- S1 coverage = 0.2530206112
- S2 coverage = 0.0078180526
- S3 coverage = 0.0021321962
- S4 coverage = 0.0021321962
- S5 coverage = 0.0028429282

Fold 2 / May:

- S0 = 0.0021321962
- S1 = 0.2082444918
- S2 = 0.0085287846
- S3 = 0.0049751244
- S4 = 0.0092395167
- S5 = 0.0049751244

Fold 3 / Jun:

- S0 = 0.0071073205
- S1 = 0.0120824449
- S2 = 0.0127931770
- S3 = 0.0291400142
- S4 = 0.0149253731
- S5 = 0.0085287846

Fold 4 / Jul:

- S0 = 0.0433546553
- S1 = 0.2075337598
- S2 = 0.1364605544
- S3 = 0.2615493959
- S4 = 0.2345415778
- S5 = 0.0660980810

This strongly indicates policy-score scale/calibration drift across time.

## What this result does NOT say

P0 did not calculate:

- validation action precision;
- validation correct action count;
- validation false-action count;
- challenger-vs-S0 correctness deltas;
- temporal null;
- survivor status;
- PnL;
- fees;
- slippage;
- forward data.

Therefore no policy has been scientifically rejected on predictive/action
quality.

## Scientific consequence

Do not run DEV037-P1 under the original absolute threshold-transfer design.

Do not change q80 to q70/q60 after observing these coverages.

Instead create a separately frozen policy-threshold transport mechanism that is
deployable and label-free.

Current state:

`DEV037_P0_FAIL_ABSOLUTE_THRESHOLD_TRANSFER_ADAPTIVE_UNLABELED_COVERAGE_CONTROL_DESIGN_NEXT`
