# DEV033-G2B-R1 — Loader Recovery Freeze

Status: `R1_RECOVERY_DESIGN_FROZEN_NO_REAL_FIT`

Parent scientific design:

`docs/DEV033_G2B_LAYERED_SCREEN_DESIGN.md`

Parent failed canonical attempt:

`DEV033-G2B`

Official parent terminal status:

`DEV033_G2B_INVALID_LOADER_API_NO_PREDICTIVE_RESULT`

## Cause

The parent loader called a nonexistent function:

`dd.build_candidate_day_dataset(...)`

The frozen dataset API and the already-validated DEV030-P6 reproduction path
use:

`dd.build_candidate_day(...)`

## R1 allowed changes

R1 changes only execution plumbing:

1. use:
   `dd.build_candidate_day(day, target=p6.SELECTED_TARGET, window_seconds=p6.SELECTED_WINDOW_SECONDS, block=p6.SELECTED_BLOCK)`
2. use distinct experiment ID:
   `DEV033-G2B-R1`
3. use distinct canonical output:
   `/home/emadh/Multi-Market/evidence/dev033_g2b_r1_layered_temporal_screen_v1`
4. use distinct artifact filename:
   `DEV033_G2B_R1_LAYERED_TEMPORAL_SCREEN_RESULT.json`
5. add CI coverage for the corrected loader call.

## Scientific invariants unchanged

Unchanged:

- frozen P3 base
- frozen G2A artifact
- 24 candidate universe
- feature matrices
- four outer folds
- chronological inner C-selection
- StandardScaler protocol
- LogisticRegression lineage
- threshold 0.5
- balanced-accuracy primary endpoint
- four-fold stability diagnostics
- LOO diagnostics
- 1999 temporal shifts
- seed 20260902
- all 24 candidate-specific null vectors
- joint 24-way max-stat FWER
- survivor/inconclusive/rejected gates
- max three advancements
- max one per family
- no weak slot filling
- all forward/economic guards.

## Recovery validity

The original G2B attempt failed before any predictive fit or metric, so R1 does
not reuse or overwrite a scientific result.

The original G2B ID remains permanently non-rerunnable.

Current state:

`DEV033_G2B_R1_RECOVERY_FROZEN_IMPLEMENTATION_NEXT_NO_REAL_FIT`
