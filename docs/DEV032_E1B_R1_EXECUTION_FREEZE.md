# DEV032-E1B-R1 Execution Freeze

Status: `R1_EXECUTION_FROZEN_LOCAL_PREFLIGHT_REQUIRED`

Recovery execution commit:

`6cf6757aeaed07e899973353585d9b031230f4b6`

CI run:

`33637116778`

CI conclusion:

`SUCCESS`

Dedicated job:

`dev032-e1b-r1-harness = SUCCESS`

## Scientific invariance

DEV032-E1B-R1 changes only the execution harness.

The frozen parent scientific implementation remains unchanged from:

`28945a54d4afb906131875d8c7b1150f5dd65247`

The following remain unchanged:

- BTCUSDT Jan-Jul 2026 development sandbox;
- exact 1374 support / 684 LONG / 690 SHORT;
- B00 = PRICE23;
- exactly 34 primary candidates P02-P35;
- same four chronological outer folds;
- StandardScaler train-only;
- LogisticRegression / lbfgs / l1_ratio=0.0;
- C grid = 0.01 / 0.1 / 1.0 / 10.0;
- pooled OOF ROC AUC primary;
- pooled AUC delta versus B00 primary incremental statistic;
- fold and leave-one-fold-out stability;
- null seed = 20260902;
- null replicates = 1999;
- single-step max-stat FWER over all 34 primary candidates;
- legacy common-shift diagnostic;
- complete leaderboard;
- immutable survivor gates;
- at most three advancing mechanisms;
- at most one initially per mechanism family;
- worker cap = 20;
- one BLAS/OpenMP thread per worker;
- all forward/PnL/optimization prohibitions.

## Harness recovery

New executable module:

`src/multimarket/dev032_e1b_r1_harness.py`

Required invocation style:

`python -m multimarket.dev032_e1b_r1_harness ...`

The module is guarded by:

`if __name__ == "__main__":`

Synthetic CI verifies process-pool startup under Python 3.14 using a real
importable module and explicit `forkserver` context.

## R1 canonical output

New recovery output directory:

`/home/emadh/Multi-Market/evidence/dev032_e1b_r1_broad_predictive_screen_v1`

The original failed-at-harness parent output path must remain absent.

After a valid R1 canonical artifact is written:

`DEV032-E1B-R1 MUST NEVER BE RERUN`

## Preflight rule

Before any R1 real-data execution:

- exact HEAD must equal the recovery execution commit;
- working tree must be clean;
- original E1B output must remain absent;
- R1 output must be absent;
- Python executable must be the known market-p10 environment;
- R1 process-pool smoke must PASS locally;
- E1B core/runner tests and R1 harness tests must PASS;
- frozen file hashes must match;
- post-test tree must remain clean.

Current state:

`DEV032_E1B_R1_EXECUTION_FROZEN_LOCAL_PREFLIGHT_REQUIRED_NO_REAL_RUN_YET`
