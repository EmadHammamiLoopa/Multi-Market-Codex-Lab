# DEV032-E1B Execution Freeze

Status: `EXECUTION_FROZEN_LOCAL_PREFLIGHT_REQUIRED`

Scientific execution commit:

`28945a54d4afb906131875d8c7b1150f5dd65247`

CI run:

`33635680162`

CI conclusion:

`SUCCESS`

The dedicated `dev032-e1b-screen` job and all other jobs in the workflow
completed successfully.

## Frozen scientific contract

- parent materialization: DEV032-E1A frozen PASS
- parent E1A SHA256:
  `76e1c97e8b9a899bc27f3193316cbfc85efba8b0a7aa037d4c46fcc6a8be4a50`
- BTCUSDT Jan-Jul 2026 development sandbox only
- exact support: 1374
- LONG: 684
- SHORT: 690
- B00 = PRICE23
- exactly 34 primary incremental candidates P02-P35
- P02 = exact frozen PRICE23 + EVENT_DEPTH26
- P03-P35 = PRICE23 + S03-S35
- same four chronological outer folds
- StandardScaler train-only
- L2 LogisticRegression / lbfgs / l1_ratio=0.0
- C grid = 0.01, 0.1, 1.0, 10.0
- chronological inner C selection preserving DEV031-P1B lineage
- pooled OOF ROC AUC primary
- pooled AUC delta versus B00 primary incremental statistic
- four fold deltas
- four leave-one-fold-out AUC deltas
- 1999 joint within-fold circular-shift null replicates
- null seed = 20260902
- single-step max-stat family-wise correction across all 34 primary candidates
- legacy common-shift audit diagnostic
- immutable strong-survivor gates
- complete leaderboard, including all failures
- at most three advancing mechanisms
- at most one initially per mechanism family
- process-level parallelism
- worker cap = 20
- one BLAS/OpenMP thread per worker

## Mandatory reproduction gates

Before the broad screen is accepted, the runner requires:

- exact DEV032-E1A artifact identity and status;
- exact seven E1A daily materialization identities;
- support/label/matrix hash validation;
- exact S02 = S00 concatenated with S01;
- frozen DEV031-P1B artifact identity and terminal FAIL status;
- frozen DEV030-P3 reproduction PASS;
- DEV031-P1B C0/C1 fold prediction reproduction PASS;
- P1B pooled AUC/log-loss/Brier reproduction PASS.

## Output

Canonical output directory:

`/home/emadh/Multi-Market/evidence/dev032_e1b_broad_predictive_screen_v1`

Canonical artifact:

`DEV032_E1B_BROAD_PREDICTIVE_SCREEN_RESULT.json`

The canonical output directory must not exist before execution.

After a valid canonical artifact is created:

`DEV032-E1B MUST NEVER BE RERUN`

Any change requires a new experiment/version.

## Prohibitions

During E1B, do not open or run:

- Aug-01
- Aug-30
- Sep-01+
- Railway
- market-raw-archive
- abundant-love
- downloads/acquisition
- E1A rematerialization
- PnL
- threshold optimization
- calibration rescue
- feature-subset search
- alternate model family
- nonlinear/deep model rescue

## Interpretation

Any successful candidate is only a:

`BTC JAN-JUL DEVELOPMENT SCREENING SURVIVOR`

It is not:

- a validated model;
- a trading strategy;
- an economic edge;
- a profitability result;
- a forward confirmation.

Independent historical replication remains mandatory before any Sep-01+
forward confirmation.

## Preflight rule

Do not run the canonical E1B command until a corrected local preflight confirms:

- exact HEAD = scientific execution commit above;
- clean working tree;
- canonical E1B output absent;
- required Python environment imports;
- dedicated E1B tests PASS;
- frozen source/test file SHA256 identities;
- post-test working tree remains clean.

Current state:

`DEV032_E1B_EXECUTION_FROZEN_LOCAL_PREFLIGHT_REQUIRED_NO_CANONICAL_RUN_YET`
