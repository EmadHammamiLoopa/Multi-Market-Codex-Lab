# DEV037-P0-R1 — Adaptive Label-Free Coverage Controller Screen

Status: `DESIGN_FROZEN_BEFORE_ANY_R1_REAL_DATA_RUN`

Date: 2026-09-02

## 1. Why R1 exists

DEV037-P0 failed operationally because absolute OOF q80 thresholds did not
transfer stably across later validation days.

This was diagnosed without inspecting validation correctness.

Observed coverage drift was severe for most policies, indicating score-scale
and calibration drift rather than a demonstrated failure of the policies
themselves.

Therefore R1 changes only threshold transport.

It does not change:

- touch model;
- BTC45 direction model;
- six policy score definitions;
- action direction rule;
- support;
- labels;
- target coverage;
- future P1 correctness endpoint.

## 2. Objective

Select one deployable, label-free online threshold controller that tracks the
frozen target action coverage:

`20%`

using only historical policy scores available before each decision.

The selected controller will then be frozen for the later DEV037-P1
correctness screen.

R1 is operational only.

No validation correctness may be inspected.

## 3. Frozen candidate controllers

Exactly three controllers are screened:

### W120

Rolling reference window:

`120 prior scores`

Approximately 2 hours at the one-minute decision cadence.

### W360

Rolling reference window:

`360 prior scores`

Approximately 6 hours.

### W720

Rolling reference window:

`720 prior scores`

Approximately 12 hours.

No other window may be added after the R1 run.

## 4. Sequential threshold rule

For each policy score stream separately:

At decision index t:

1. construct a reference buffer containing only scores observed before t;
2. the buffer capacity is the candidate window W;
3. before enough current-day scores exist, warm-start the buffer with the most
   recent OOF training scores available before the validation day;
4. retain only the most recent W reference scores;
5. compute:

`threshold_t = quantile(reference_buffer, 0.80, method="higher")`

6. ACT iff:

`score_t >= threshold_t`

7. after the decision is made, append score_t to the reference buffer.

The current score must never enter its own threshold calculation.

No label is used.

## 5. Policies

The controller screen is applied to exactly the same six frozen DEV037 policy
scores:

- S0 TOUCH_ONLY_SELECTIVE
- S1 DIRECTION_CONFIDENCE_SELECTIVE
- S2 PRODUCT_JOINT_SELECTIVE
- S3 BALANCED_MIN_PERCENTILE
- S4 GEOMETRIC_BALANCED_PERCENTILE
- S5 META_CORRECTNESS_FILTER

S5 remains trained from expanding OOF training predictions only.

The controller screen changes only how the final act/abstain threshold is
transported online.

## 6. Real-data scope

Historical Jan-Jul DEV036-C1 common support only.

Outer validation days:

- Apr
- May
- Jun
- Jul

No Aug-30 reuse.
No Sep-01+.
No Railway/archive/abundant-love.
No forward holdout.

## 7. R1 permitted outputs

For each controller W and policy S, serialize only operational quantities:

- action count;
- abstain count;
- coverage;
- LONG count;
- SHORT count;
- per-hour or 60-row rolling coverage series;
- threshold series summary:
  - min
  - median
  - max
  - first
  - last;
- coverage deviation from target:
  `abs(coverage - 0.20)`
- mean absolute 60-row rolling coverage error;
- maximum absolute 60-row rolling coverage error;
- number of rolling windows with coverage outside [0.10, 0.30];
- number of action-state switches;
- warm-start reference count.

No correctness-conditioned metric is permitted.

## 8. Feasibility guard per policy/controller/fold

A policy/controller pair is operationally feasible on a fold if:

- coverage >= 0.10;
- coverage <= 0.30;
- LONG count > 0;
- SHORT count > 0;
- action count > 0;
- abstain count > 0.

## 9. Controller-level feasibility

A controller is globally feasible only if:

- all six policies pass the fold feasibility guard on all four validation
  folds;
- no non-finite thresholds;
- no chronology violation;
- no self-inclusion in threshold reference;
- warm-start reference is non-empty for every policy/fold.

## 10. Controller ranking

Among globally feasible controllers, select exactly one using only operational
coverage quality.

Ranking order:

1. smallest mean absolute pooled coverage deviation from 0.20 across all
   24 policy-fold combinations;
2. smallest worst absolute pooled coverage deviation across those 24
   combinations;
3. smallest mean absolute 60-row rolling coverage error;
4. fewest 60-row windows outside [0.10, 0.30];
5. smaller window size.

This ranking never uses labels or correctness.

## 11. Terminal outcomes

If one or more controllers are globally feasible:

`DEV037_P0_R1_ADAPTIVE_CONTROLLER_SELECTED`

Advance deterministic rank 1 only.

If none are globally feasible:

`DEV037_P0_R1_NO_CONTROLLER_OPERATIONALLY_FEASIBLE`

No correctness screen may run.

## 12. Scientific/practical interpretation

R1 tests whether a live, score-only controller can keep action frequency near
the desired operating point despite score-distribution drift.

It does not test profitability.

It does not test whether one policy is better than another.

It does not test action correctness.

## 13. External rationale

Selective prediction literature evaluates risk jointly with coverage and
typically uses a selector threshold on a confidence score. Under distribution
shift, fixed thresholds can become unstable, motivating adaptive calibration or
risk-control mechanisms.

For this project, R1 uses a simpler deployment-oriented version:

- no labels online;
- no conformal guarantee claim;
- no external implementation;
- only rolling empirical quantile control over already frozen policy scores.

## 14. Permanent no-rerun rules

`DEV036-C1 MUST NEVER BE RERUN`

`DEV035-G4B MUST NEVER BE RERUN`

`DEV034-G3B-R1 MUST NEVER BE RERUN`

`DEV034-G3A-R1 MUST NEVER BE RERUN`

DEV037-P1 has not run.

## 15. Current state

`DEV037_P0_R1_ADAPTIVE_CONTROLLER_DESIGN_FROZEN_IMPLEMENTATION_NEXT_NO_CORRECTNESS_SCORING`
