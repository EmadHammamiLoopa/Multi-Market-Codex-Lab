# DEV037-P0-R2 Execution Freeze

Status: `EXECUTION_FROZEN_SINGLE_COVERAGE_ONLY_CANONICAL_R2_NEXT`

Date: 2026-09-02

Scientific implementation commit:

`e5c13df91ceeebb58e5e3c95eadedb0efe5af282`

Dedicated CI:

- workflow run = `33686650238`
- workflow conclusion = SUCCESS
- job = `dev037-p0-r2`
- pytest = SUCCESS
- harness smoke = SUCCESS

## Frozen retained policy family

Exactly:

- S0 TOUCH_ONLY_SELECTIVE
- S1 DIRECTION_CONFIDENCE_SELECTIVE
- S2 PRODUCT_JOINT_SELECTIVE
- S5 META_CORRECTNESS_FILTER

Removed from DEV037 before any correctness evaluation:

- S3 BALANCED_MIN_PERCENTILE
- S4 GEOMETRIC_BALANCED_PERCENTILE

## Frozen controller candidates

Exactly:

- W120
- W360
- W720

No new window is permitted.

## Frozen threshold rule

For each policy score stream and decision t:

`threshold_t = q80(prior_scores_only, method="higher")`

Rules:

- target coverage = 0.20;
- current score excluded from its own threshold;
- rolling reference uses only prior scores;
- warm-start uses prior OOF training scores only;
- no label is used.

## Frozen feasibility rule

A policy/controller/fold pair must satisfy:

- coverage in [0.10,0.30];
- LONG > 0;
- SHORT > 0;
- action count > 0;
- abstain count > 0;
- finite threshold stream.

A controller is globally feasible only if all:

`4 policies × 4 folds = 16 pairs`

pass.

## Frozen ranking

Among globally feasible controllers:

1. smallest mean absolute coverage deviation from 0.20;
2. smallest worst absolute coverage deviation;
3. smallest mean rolling60 absolute coverage error;
4. fewest rolling60 windows outside [0.10,0.30];
5. smaller window.

Advance exactly one controller.

## Canonical output reserved

Directory:

`/home/emadh/Multi-Market/evidence/dev037_p0_r2_operationally_pruned_controller_v1`

Artifact:

`DEV037_P0_R2_OPERATIONALLY_PRUNED_CONTROLLER_RESULT.json`

From the canonical R2 start marker:

`DEV037-P0-R2 MUST NEVER BE RERUN`

even if the attempt fails.

## Strict prohibitions

R2 must not inspect or calculate:

- validation action precision;
- correct action count;
- false action count;
- challenger-vs-S0 correctness delta;
- temporal null;
- policy survivor status;
- PnL;
- fees;
- slippage;
- position sizing;
- leverage;
- forward data.

## Permanent upstream rules

`DEV037-P0-R1 MUST NEVER BE RERUN`

`DEV036-C1 MUST NEVER BE RERUN`

`DEV035-G4B MUST NEVER BE RERUN`

`DEV034-G3B-R1 MUST NEVER BE RERUN`

`DEV034-G3A-R1 MUST NEVER BE RERUN`

Current state:

`DEV037_P0_R2_EXECUTION_FROZEN_SINGLE_COVERAGE_ONLY_CANONICAL_RUN_NEXT`
