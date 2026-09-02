# DEV032-E1B-R1 — Process-Safe Harness Recovery

Status: `RECOVERY_DESIGN_FROZEN_IMPLEMENTATION_ONLY`

Parent scientific execution commit:

`28945a54d4afb906131875d8c7b1150f5dd65247`

## Reason for recovery

The original DEV032-E1B canonical attempt terminated with exit code 1 and
produced no canonical output directory, no artifact, no staging directory, and
no leaderboard.

Read-only diagnosis confirmed all frozen E1A/P1B/P3 identities and the E1B
loader contract.

The original command invoked the process-pool runner from a stdin/heredoc Python
main module. Under Python 3.14 on POSIX, ProcessPoolExecutor uses a start method
away from fork by default and requires an importable/safely guarded main module.

Therefore the original attempt is classified:

`DEV032_E1B_INVALID_EXECUTION_HARNESS_NO_RESULT`

It must never be rerun.

## Scientific protocol invariance

DEV032-E1B-R1 changes execution harness only.

The following remain byte-for-byte / semantically unchanged from the frozen
parent runner and design:

- BTCUSDT Jan-Jul 2026 development sandbox;
- exact 1374 / 684 LONG / 690 SHORT support;
- B00 = PRICE23;
- exactly 34 primary candidates P02-P35;
- P02 = frozen S02;
- P03-P35 = PRICE23 + S03-S35;
- same four chronological outer folds;
- StandardScaler train-only;
- L2 LogisticRegression / lbfgs / l1_ratio=0.0;
- C grid 0.01, 0.1, 1.0, 10.0;
- chronological inner C selection;
- pooled OOF ROC AUC primary;
- pooled AUC delta versus B00 primary incremental statistic;
- fold and LOO stability checks;
- null seed 20260902;
- 1999 joint within-fold circular-shift replicates;
- single-step max-stat FWER across all 34 primary candidates;
- legacy common-shift audit;
- complete leaderboard;
- immutable survivor gates;
- at most three advancing mechanisms;
- at most one initially per mechanism family;
- process-level parallelism;
- worker cap 20;
- one BLAS/OpenMP thread per worker;
- all forward/PnL/optimization prohibitions.

## Allowed code change

Only a process-safe real-file executable harness may be added.

The harness must:

1. be executed from a real Python file/module, not stdin/heredoc;
2. protect execution with `if __name__ == "__main__":`;
3. use the Python 3.14 POSIX `forkserver` context explicitly when available;
4. call the unchanged frozen `run_e1b()` implementation;
5. print artifact path/hash/bytes and survivor lists;
6. provide a synthetic process-pool smoke mode that touches no real evidence.

The frozen parent scientific modules must not be altered in R1.

## Recovery output

Use a new canonical directory:

`/home/emadh/Multi-Market/evidence/dev032_e1b_r1_broad_predictive_screen_v1`

The recovery harness must call the parent runner with a non-parent output path
under an explicit recovery mode. Because the parent runner's canonical guard is
hard-coded to the original E1B directory, R1 requires a thin recovery wrapper
that temporarily supplies a recovery-specific output contract without changing
scientific calculations.

No original DEV032-E1B path may be created or reused.

After one valid R1 canonical artifact is written:

`DEV032-E1B-R1 MUST NEVER BE RERUN`

## Next permitted action

- implement process-safe R1 harness;
- add synthetic process-pool smoke test;
- run CI;
- freeze recovery execution commit;
- corrected local preflight;
- only then authorize one R1 canonical recovery execution.

Current state:

`DEV032_E1B_R1_RECOVERY_DESIGN_FROZEN_IMPLEMENTATION_ONLY`
