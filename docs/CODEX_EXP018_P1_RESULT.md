# CODEX-EXP-018-P1 Frozen Result

Status: **INVALID**

Date: 2026-08-27

Frozen pre-output HEAD:

`c2dbaed8113d7f015b3dc9f7691d85ee4fd12705`

Result artifact:

`evidence/codex/exp018_p1_independent_volatility_aug1/INDEPENDENT_VOLATILITY_AUG1.json`

Result artifact SHA-256:

`4d48612201f5597b5e6b9a0ed423f0fd131bdc31473d11238c96149749748f44`

## Official result

`CODEX-EXP-018-P1 = INVALID`

Failure type:

`ResearchSealError`

Failure message:

`sealed research day: 2026-08-01`

## Scientific state at failure

The one-shot reached the frozen EXP018 execution marker and therefore EXP018 must never be rerun.

However, the failure occurred before analytical opening of the Aug-01 feature file.

Recorded guards:

- sealed_aug1_analytically_opened = false
- target_scored = false
- model_fit = true
- auc_scored = false
- older_august_holdout_opened = false
- direction_scored = false
- pnl_scored = false
- network_accessed = false

Thus the Jan-Jul training models were fit, but no Aug-01 target, prevalence, model prediction metric, AUC/AP, direction, or PnL was produced.

No predictive conclusion can be drawn from EXP018.

## Root cause

EXP018 imported `sha256_file` from:

`src/multimarket/codex_research.py`

That helper performs:

`assert_unsealed_path(target)`

before opening a file.

The generic research seal in `codex_research.py` contains:

`2026-08-01`

inside `SEALED_DAYS`.

Therefore the EXP018 validation path:

`.../BTCUSDT/2026-08-01_FEATURES250.csv`

was rejected by the legacy generic seal during the in-run SHA-256 verification step.

The exception was raised before the intended authorized analytical `_load_day()` call.

This is an implementation/protocol incompatibility: EXP018 had separately preregistered authorization to open exactly the frozen Aug-01 artifact, but reused a legacy helper whose purpose is to reject all sealed dates.

## Evidence that Aug-01 predictive data remained unopened

The frozen result reports:

- `sealed_aug1_analytically_opened = false`
- `target_scored = false`
- `auc_scored = false`

The only Aug-01 accesses before failure were the already-authorized opaque byte-hash operations used to verify the frozen EXP017 artifact.

No Aug-01 CSV parse or predictive scoring occurred.

## Adjudication

This is not a predictive FAIL.

It is not evidence against the volatility-regime hypothesis.

It is a frozen `INVALID` caused by a seal-aware hashing helper being incompatible with the newly authorized sealed-day validation protocol.

EXP018 may not be repaired or rerun.

A correction requires a new Experiment ID.

The correction must preserve every scientific choice from EXP018 unchanged and change only the sealed-artifact access mechanism so that exactly the preregistered Aug-01 file may be hash-verified and then analytically opened.

The corrected experiment must continue to forbid all other sealed August dates, including 2026-08-04 through 2026-08-23.
