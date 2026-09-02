# DEV033-G2B-R1 Execution Freeze

Status: `EXECUTION_FROZEN_LOCAL_PREFLIGHT_REQUIRED_NO_CANONICAL_R1_RUN_YET`

Scientific recovery execution commit:

`9817a620279fd8a4a8ba0717c0e400f7ef2a1cf1`

Successful CI run:

`33651348435 = SUCCESS`

All 14 jobs passed, including:

- dev033-g2b-screen = SUCCESS
- dev033-g2a-materialization = SUCCESS
- dev032-e2b-screen = SUCCESS
- dev032-e1b-screen = SUCCESS
- dev032-e1b-r1-harness = SUCCESS
- retained DEV031/DEV032 regressions = SUCCESS
- unit-tests Python 3.10 = SUCCESS
- unit-tests Python 3.12 = SUCCESS

Parent DEV033-G2B remains permanently frozen as:

`DEV033_G2B_INVALID_LOADER_API_NO_PREDICTIVE_RESULT`

and must never be rerun.

## R1 recovery scope

R1 changes only execution plumbing:

1. corrected loader API:
   `dd.build_candidate_day(...)`
2. distinct experiment identity:
   `DEV033-G2B-R1`
3. distinct canonical output directory:
   `/home/emadh/Multi-Market/evidence/dev033_g2b_r1_layered_temporal_screen_v1`
4. distinct artifact filename:
   `DEV033_G2B_R1_LAYERED_TEMPORAL_SCREEN_RESULT.json`
5. CI coverage explicitly exercises the corrected loader API.

The scientific design is unchanged from frozen G2B:

- same frozen DEV030-P3 base
- same frozen DEV033-G2A parent
- same 24 candidate universe
- same candidate matrices
- same four outer folds
- same chronological inner C selection
- same StandardScaler protocol
- same LogisticRegression lineage
- same threshold 0.5
- same balanced-accuracy incremental endpoint
- same four-fold and LOO stability diagnostics
- same 1999 temporal-shift replicates
- same seed 20260902
- same 24 candidate-specific null vectors
- same joint max-stat FWER
- same survivor/inconclusive/rejected gates
- same advancement limits
- same forward/economic guards

## Canonical R1 output

Directory:

`/home/emadh/Multi-Market/evidence/dev033_g2b_r1_layered_temporal_screen_v1`

Artifact:

`DEV033_G2B_R1_LAYERED_TEMPORAL_SCREEN_RESULT.json`

After the first canonical R1 screen begins:

`DEV033-G2B-R1 MUST NEVER BE RERUN`

## Process safety

Mandatory:

- importable module harness
- no bare exit
- no parent-shell strict flags
- dedicated R1 console log
- one BLAS/OpenMP thread per process
- max 12 workers
- read-only diagnosis after any canonical attempt
- no forward holdout/PnL/Railway/archive/acquisition

## Next permitted action

Local R1 preflight only.

Current state:

`DEV033_G2B_R1_EXECUTION_FROZEN_LOCAL_PREFLIGHT_REQUIRED`
