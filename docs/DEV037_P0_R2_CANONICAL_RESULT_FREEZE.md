# DEV037-P0-R2 Canonical Result Freeze

Status: `CANONICAL_SUCCESS_CONTROLLER_SELECTED_W120`

Date: 2026-09-02

Scientific execution commit:

`e5c13df91ceeebb58e5e3c95eadedb0efe5af282`

Canonical artifact:

`/home/emadh/Multi-Market/evidence/dev037_p0_r2_operationally_pruned_controller_v1/DEV037_P0_R2_OPERATIONALLY_PRUNED_CONTROLLER_RESULT.json`

Artifact SHA256:

`494122f1aea64fb2a4c956d674330d9a400709656f0e116187d6fa2fefaa3336`

Artifact bytes:

`27056`

Canonical contract:

- 19 PASS
- 0 FAIL
- process exit = 0
- read-only verification = PASS
- staging residue = none
- git tree clean

Permanent rule:

`DEV037-P0-R2 MUST NEVER BE RERUN`

## Terminal result

`DEV037_P0_R2_CONTROLLER_SELECTED`

Selected controller:

`W120`

Controller ranking:

1. W120
2. W360
3. W720

## Retained policy family

Exactly:

- S0 TOUCH_ONLY_SELECTIVE
- S1 DIRECTION_CONFIDENCE_SELECTIVE
- S2 PRODUCT_JOINT_SELECTIVE
- S5 META_CORRECTNESS_FILTER

Removed before any correctness evaluation:

- S3 BALANCED_MIN_PERCENTILE
- S4 GEOMETRIC_BALANCED_PERCENTILE

## Global feasibility

All controller windows were operationally feasible across all retained
policy-fold pairs:

- W120 = 16/16
- W360 = 16/16
- W720 = 16/16

Therefore ranking proceeded under the frozen operational criteria.

## Aggregate controller ranking statistics

### W120

- mean absolute coverage error = `0.014649964463397303`
- worst absolute coverage error = `0.02942430703624735`
- mean rolling60 absolute error = `0.08182724406528191`
- rolling60 outside count = `5846`

### W360

- mean absolute coverage error = `0.03667377398720683`
- worst absolute coverage error = `0.06638237384506043`
- mean rolling60 absolute error = `0.11987280539070228`
- rolling60 outside count = `9848`

### W720

- mean absolute coverage error = `0.051066098081023456`
- worst absolute coverage error = `0.09410092395167023`
- mean rolling60 absolute error = `0.13847134643916914`
- rolling60 outside count = `11668`

W120 won every frozen ranking criterion before the final smaller-window
tie-break became relevant.

## W120 validation-fold coverage

Fold 1 / Apr:

- S0 = `0.17057569296375266`
- S1 = `0.20113717128642503`
- S2 = `0.18336886993603413`
- S5 = `0.17199715707178392`

Fold 2 / May:

- S0 = `0.17484008528784648`
- S1 = `0.19829424307036247`
- S2 = `0.17981520966595593`
- S5 = `0.17626154939587776`

Fold 3 / Jun:

- S0 = `0.2082444918265814`
- S1 = `0.19545131485429992`
- S2 = `0.19545131485429992`
- S5 = `0.20540156361051884`

Fold 4 / Jul:

- S0 = `0.2281449893390192`
- S1 = `0.20398009950248755`
- S2 = `0.2125088841506752`
- S5 = `0.22103766879886283`

All W120 policy-fold pairs satisfy the frozen [0.10,0.30] coverage guard and
emit both LONG and SHORT actions.

## Forbidden-activity verification

All remained false:

- validation correctness inspected = false
- action precision calculated = false
- correct action count calculated = false
- false action count calculated = false
- temporal null run = false
- survivor classification run = false
- PnL run = false
- fees run = false
- slippage run = false
- forward data opened = false

Therefore W120 selection is independent of policy correctness and profitability.

## Scientific/practical consequence

W120 is the frozen online coverage controller for the next DEV037 policy
correctness screen.

The prior six-policy DEV037-P1 design is superseded and must not run.

The next correctness screen must evaluate exactly S0/S1/S2/S5 under W120 on
identical folds and rows, with a jointly controlled temporal null.

No PnL or forward holdout is authorized yet.

Current state:

`DEV037_P0_R2_W120_SELECTED_FOUR_POLICY_CORRECTNESS_SCREEN_DESIGN_NEXT`
