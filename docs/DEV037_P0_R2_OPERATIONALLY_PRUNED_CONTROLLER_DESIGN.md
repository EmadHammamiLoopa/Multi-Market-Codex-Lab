# DEV037-P0-R2 — Operationally Pruned Adaptive Controller Screen

Status: `DESIGN_FROZEN_BEFORE_ANY_R2_REAL_DATA_RUN`

Date: 2026-09-02

## 1. Rationale

DEV037-P0-R1 was a canonical coverage-only screen.

It inspected no validation correctness and no PnL.

R1 failed global feasibility because the bounded percentile-combination
policies S3 and S4 became operationally unstable under distribution shift,
especially on Fold 1 / Apr.

Observed Fold-1 coverage for S3/S4:

- W120: approximately 87%
- W360: approximately 78%
- W720: approximately 57%

The mechanism is percentile saturation and large score ties at the upper bound.

Rather than add tie-specific complexity to rescue those policies, R2 removes
S3 and S4 from the policy family on operational grounds only.

No correctness information is used in this pruning decision.

## 2. Frozen retained policy family

Exactly four policies remain:

- S0 TOUCH_ONLY_SELECTIVE
- S1 DIRECTION_CONFIDENCE_SELECTIVE
- S2 PRODUCT_JOINT_SELECTIVE
- S5 META_CORRECTNESS_FILTER

Removed permanently from DEV037 policy competition:

- S3 BALANCED_MIN_PERCENTILE
- S4 GEOMETRIC_BALANCED_PERCENTILE

They may not be reintroduced in DEV037.

## 3. Why these four remain

The retained family still spans materially distinct mechanisms:

- S0: opportunity/touch strength;
- S1: direction confidence;
- S2: joint touch × direction confidence;
- S5: supervised meta correctness filter.

This is sufficient diversity for a practical joint policy screen without
retaining mechanically unstable percentile-combination scores.

## 4. Controller candidates

Exactly the same label-free rolling controllers:

- W120
- W360
- W720

No new window is added.

## 5. Threshold rule

At each decision t, for each policy independently:

`threshold_t = q80(prior_scores_only, method="higher")`

Rules:

- target coverage = 0.20;
- current score excluded from its own reference;
- rolling reference contains prior scores only;
- warm-start uses prior OOF training scores only;
- no labels online.

## 6. Real-data scope

Exact DEV036-C1 common support and the same four validation folds:

- Apr
- May
- Jun
- Jul

No support change.
No new predictive features.
No model-lineage change.

## 7. Allowed R2 outputs

Coverage-only operational quantities:

- action count;
- abstain count;
- coverage;
- LONG count;
- SHORT count;
- coverage absolute error vs 0.20;
- rolling60 coverage error;
- rolling60 windows outside [0.10,0.30];
- threshold summary;
- action-state switches;
- warm-start count.

No correctness-conditioned metric is permitted.

## 8. Pair feasibility

Each policy/controller/fold pair must satisfy:

- coverage in [0.10,0.30];
- LONG > 0;
- SHORT > 0;
- actions > 0;
- abstentions > 0;
- finite threshold stream.

## 9. Controller global feasibility

A controller is globally feasible only if all four retained policies pass the
pair feasibility guard on all four validation folds.

Total required feasible pairs per controller:

`4 policies × 4 folds = 16`

## 10. Controller ranking

Among globally feasible controllers:

1. smallest mean absolute coverage deviation from 0.20 over all 16 pairs;
2. smallest worst absolute coverage deviation;
3. smallest mean rolling60 absolute coverage error;
4. fewest rolling60 windows outside [0.10,0.30];
5. smaller window.

Advance exactly one controller.

## 11. Terminal outcomes

If at least one controller is globally feasible:

`DEV037_P0_R2_CONTROLLER_SELECTED`

If none is globally feasible:

`DEV037_P0_R2_NO_CONTROLLER_OPERATIONALLY_FEASIBLE`

## 12. Consequence for DEV037-P1

If R2 selects a controller:

DEV037-P1 must be redesigned/frozen to evaluate exactly the four retained
policies S0/S1/S2/S5 under that single selected controller.

The prior six-policy P1 design is superseded and must not be run.

If R2 finds no controller:

stop the current selective-policy family before correctness/PnL.

## 13. Strict prohibitions

R2 must not inspect:

- action precision;
- correct action count;
- false action count;
- challenger-vs-S0 correctness delta;
- temporal null;
- policy survivor status;
- PnL;
- fees;
- slippage;
- leverage;
- position sizing;
- forward data.

## 14. Permanent no-rerun rules

`DEV037-P0-R1 MUST NEVER BE RERUN`

`DEV036-C1 MUST NEVER BE RERUN`

`DEV035-G4B MUST NEVER BE RERUN`

`DEV034-G3B-R1 MUST NEVER BE RERUN`

`DEV034-G3A-R1 MUST NEVER BE RERUN`

## 15. Current state

`DEV037_P0_R2_OPERATIONALLY_PRUNED_CONTROLLER_DESIGN_FROZEN_IMPLEMENTATION_NEXT_NO_CORRECTNESS`
