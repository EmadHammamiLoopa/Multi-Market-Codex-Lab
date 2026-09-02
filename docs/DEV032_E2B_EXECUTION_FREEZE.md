# DEV032-E2B Execution Freeze

Status: `EXECUTION_FROZEN_LOCAL_PREFLIGHT_REQUIRED_NO_CANONICAL_RUN_YET`

Scientific execution commit:

`0b9e680e1403222ae5a426ef95457a6e722e2ed3`

CI run:

`33643183961`

CI conclusion:

`SUCCESS`

All 12 workflow jobs completed successfully, including:

- `dev032-e2b-screen = SUCCESS`
- `dev032-e2a-materialization = SUCCESS`
- `dev032-e1b-screen = SUCCESS`
- `dev032-e1b-r1-harness = SUCCESS`
- all retained regression jobs = SUCCESS

## Frozen E2B scope

E2B tests exactly ten preregistered adaptive refinements against frozen parent
mechanisms on the already-consumed BTCUSDT Jan-Jul 2026 development sandbox.

No canonical E2B run has occurred yet.

## Frozen parent identities

E2A:

`/home/emadh/Multi-Market/evidence/dev032_e2a_wave2_materialization_v1/DEV032_E2A_WAVE2_MATERIALIZATION.json`

SHA256:

`3c26614f576af4e52b2d52f237e2e939cd79a988238022076ddcdbf57d06b89c`

bytes:

`15261`

E1B-R1:

`/home/emadh/Multi-Market/evidence/dev032_e1b_r1_broad_predictive_screen_v1/DEV032_E1B_BROAD_PREDICTIVE_SCREEN_RESULT.json`

SHA256:

`af223d3f97b85ae1c929f81b3ec71e892477b9b26e719638acb05ae153578b95`

bytes:

`287823`

## Reproduction gate

Before any refinement result can be interpreted, E2B must reproduce:

- B00
- P07
- P09
- P13
- P17
- P21
- P32
- P35

against frozen E1B-R1 by:

- four exact prediction hashes each;
- four exact selected C values each;
- pooled AUC/logloss/Brier within absolute tolerance 1e-15.

Any mismatch invalidates E2B before refinement interpretation.

## E2B refinement universe

Exactly:

- E2R01
- E2R02
- E2R03
- E2R04
- E2R05
- E2R06
- E2R07
- E2R08
- E2R09
- E2R10

PCA/SVD transforms are train-only and fixed at five components.

## Joint null

- 1999 replicates
- seed 20260902
- same within-fold circular shift tuple for every parent/refinement pair
- parent-relative delta statistic
- single-step max-stat FWER across all 10 refinements

## Process safety

Canonical execution must use:

`python -m multimarket.dev032_e2b_harness`

Never use stdin/heredoc with ProcessPoolExecutor.

Interactive wrapper rules:

- never use bare `exit`;
- never leave `set -e`, `set -u`, or `pipefail` enabled in the parent shell;
- strict shell logic, if needed, must stay inside a child shell;
- preserve a dedicated console log;
- after any canonical attempt, never rerun blindly.

## Canonical output

Directory:

`/home/emadh/Multi-Market/evidence/dev032_e2b_adaptive_refinement_screen_v1`

Artifact:

`DEV032_E2B_ADAPTIVE_REFINEMENT_SCREEN_RESULT.json`

After the first canonical execution attempt begins:

`DEV032-E2B MUST NEVER BE RERUN`

## Next permitted action

Local preflight only.

Current state:

`DEV032_E2B_EXECUTION_FROZEN_LOCAL_PREFLIGHT_REQUIRED_NO_CANONICAL_RUN_YET`
