# DEV037-P1-R1 Execution Freeze

Status: `EXECUTION_FROZEN_REAL_DATA_NO_RESULT_REPRODUCTION_PREFLIGHT_NEXT`

Date: 2026-09-02

Scientific implementation commit:

`25221269bee4681916af663b668cf1f4446a3294`

Dedicated CI confirmation:

- workflow run = `33687831459`
- workflow conclusion = SUCCESS
- job = `dev037-p1-r1`
- pytest = SUCCESS
- harness smoke = SUCCESS

Note:

Commit `f68af52539ac7af30f6c8e37e5b7822a0febce26` only updated the handoff after the
scientific implementation and CI wiring. It is intentionally excluded from the
scientific execution identity.

## Frozen parent

DEV037-P0-R2 canonical parent:

`/home/emadh/Multi-Market/evidence/dev037_p0_r2_operationally_pruned_controller_v1/DEV037_P0_R2_OPERATIONALLY_PRUNED_CONTROLLER_RESULT.json`

SHA256:

`494122f1aea64fb2a4c956d674330d9a400709656f0e116187d6fa2fefaa3336`

Bytes:

`27056`

Parent-selected controller:

`W120`

## Frozen policy family

Exactly:

- S0 TOUCH_ONLY_SELECTIVE
- S1 DIRECTION_CONFIDENCE_SELECTIVE
- S2 PRODUCT_JOINT_SELECTIVE
- S5 META_CORRECTNESS_FILTER

Challengers:

- S1
- S2
- S5

Comparator:

- S0

## Frozen operational rule

Only W120.

For each decision:

`threshold_t = q80(last up to 120 prior policy scores, method="higher")`

- current score excluded;
- warm-start from OOF training scores only;
- LONG/SHORT direction from frozen BTC45 sign;
- otherwise ABSTAIN.

## Frozen correctness endpoints

Primary:

`ACTION_PRECISION`

Primary challenger increment:

`DeltaPrecision = Precision(challenger) - Precision(S0)`

Required practical secondary:

`DeltaCorrectRate = CorrectActionsPerAllRows(challenger) - CorrectActionsPerAllRows(S0)`

True survivor requires all:

- operational reproduction PASS;
- pooled DeltaPrecision >= +0.02;
- pooled DeltaCorrectRate > 0;
- >=3/4 positive fold precision deltas;
- all four LOO precision deltas > 0;
- observed DeltaPrecision > three-challenger joint max-stat q95;
- FWER p <= 0.05.

## Frozen temporal null

Three challengers jointly:

- S1
- S2
- S5

Parameters:

- seed = 20260902
- replicates = 1999
- legal fold circular shifts = 30 .. n_fold-30
- q95 method = higher
- plus-one empirical p denominator = 2000

## Canonical output reserved

Directory:

`/home/emadh/Multi-Market/evidence/dev037_p1_r1_four_policy_w120_correctness_v1`

Artifact:

`DEV037_P1_R1_FOUR_POLICY_W120_CORRECTNESS_RESULT.json`

Canonical console log:

`/home/emadh/Multi-Market/evidence/dev037_p1_r1_canonical_console_v1.log`

From the moment the canonical start marker is printed:

`DEV037-P1-R1 MUST NEVER BE RERUN`

even if the attempt fails.

## Next permitted action

Real-data NO-RESULT reproduction preflight only.

The preflight may:

- verify parent artifact identity;
- reconstruct exact common support;
- rebuild OOF score streams;
- rebuild W120 actions for S0/S1/S2/S5;
- compare only operational counts and coverage to frozen R2;
- verify LONG/SHORT counts;
- verify all W120 operational feasibility;
- verify all required inputs finite;
- verify output/log absent;
- run focused tests and harness smoke.

The preflight must NOT:

- call action_metrics on validation labels;
- calculate action precision;
- count validation correct or false actions;
- compare challenger correctness to S0;
- run temporal null;
- classify survivors;
- run PnL;
- use fees/slippage;
- open forward data.

## Permanent upstream rules

`DEV037-P0-R2 MUST NEVER BE RERUN`

`DEV037-P0-R1 MUST NEVER BE RERUN`

`DEV036-C1 MUST NEVER BE RERUN`

`DEV035-G4B MUST NEVER BE RERUN`

`DEV034-G3B-R1 MUST NEVER BE RERUN`

`DEV034-G3A-R1 MUST NEVER BE RERUN`

Current state:

`DEV037_P1_R1_EXECUTION_FROZEN_REAL_DATA_NO_RESULT_REPRODUCTION_PREFLIGHT_NEXT`
