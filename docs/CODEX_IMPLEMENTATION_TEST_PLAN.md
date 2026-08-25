# Codex Implementation and Test Plan

Status: concrete plan for first milestone and `CODEX-EXP-001`

## 1. Baseline preservation

1. Reconstruct the exact `f193b199...` tree and retain its reachable Git history.
2. Configure the original repository as read-only `upstream`; the empty Codex Lab repository is `origin`.
3. Build an isolated workspace virtual environment from `pyproject.toml`.
4. Run all 49 baseline test modules unchanged and record pass/fail/skip counts plus dependency/platform failures.
5. Do not modify baseline behavior merely to silence an environment error.

Acceptance: baseline suite is either green or every failure is classified with the exact traceback and affected module.

## 2. Safety and experiment contracts

Implement a small shared module for:

- parsing and validating research dates;
- rejecting 2026-08-01 and 2026-08-04 through 2026-08-23 before path opening;
- rejecting dates outside the frozen CODEX-EXP-001 sandbox set;
- immutable experiment configuration and canonical SHA-256;
- fail-closed input manifests and unique result paths.

Tests:

- every sealed boundary and neighboring allowed date;
- path names containing a sealed ISO date;
- canonical config hash stability;
- missing-file status is `NOT_RUN`, not `FAIL` or a synthetic score.

## 3. Executable outcome layer

Reuse Phase L feature names and input validation, but place direct net-label logic in a separate module. For each row/horizon emit:

- valid mask;
- long and short gross touch-to-touch returns;
- long/short positive-at-primary-cost labels;
- entry and exit indices;
- embargo/non-overlap span.

Tests:

- hand-computed long and short touch returns;
- spread and commission signs;
- 250 ms entry latency;
- 10/30 s exit location on a 250 ms grid;
- invalid book and day-end rows excluded;
- no overlap includes latency plus horizon.

## 4. Calibration and decision layer

Implement deterministic base logistic and Platt calibration adapters. Keep `NO_TRADE`, long, and short choice independent of reporting.

Tests:

- calibration receives only the first inner-day half;
- selection receives only the second half after embargo;
- outer rows are never passed to any `fit` method;
- a one-class calibration slice invalidates the configuration;
- threshold equality, long/short tie, and non-finite probability abstain;
- greedy non-overlap is deterministic;
- reliability metrics handle empty bins and constant labels safely.

## 5. Walk-forward runner

Add a CLI runner with defaults matching the frozen ledger:

```powershell
python -m multimarket.codex_exp001 `
  --feature-dir evidence/v23/phase0dl_features250 `
  --output-dir evidence/codex
```

The runner must:

1. validate config and all requested dates before reading data;
2. hash every input;
3. create five March--July outer folds;
4. train on earlier complete days, calibrate/select on disjoint halves of the preceding day, and score the outer day once;
5. select L0 and L2 independently;
6. emit per-fold calibration, coverage, 8/10/12-bp economics, concentration, and pooled gates;
7. preserve a unique JSON artifact and append a ledger-ready Markdown row;
8. emit `NOT_RUN_MISSING_INPUT` with the complete missing-file list if features are absent;
9. never inspect or mention an August result file.

Tests use small synthetic `DayData` arrays and injectable model factories so leakage/split behavior can be asserted without a large dataset.

## 6. Verification sequence

Run in this order:

1. unchanged baseline suite;
2. new seal/config/outcome unit tests;
3. new split/calibration/decision unit tests;
4. entire repository suite;
5. CLI `--check-inputs` against the real default feature directory;
6. full CODEX-EXP-001 only when all 14 expected sandbox feature files exist and hashes are recorded;
7. review generated JSON for seal flags, split identities, non-finite metrics, and config/source hashes.

No August command is part of the plan.

## 7. Milestone commits

1. audit and modern-method review;
2. framework proposal, ledger, and test plan;
3. CODEX-EXP-001 implementation and unit tests;
4. baseline/full-suite verification and honest run status/result.

Push each meaningful milestone to `EmadHammamiLoopa/Multi-Market-Codex-Lab`. Never push to `upstream`.

## 8. Stop conditions

- Missing raw/features: emit `NOT_RUN`; do not substitute documentation numbers.
- Dependency/build failure: record environment failure, repair only the environment, rerun unchanged code.
- Leakage or seal assertion failure: mark `INVALID` and stop scoring.
- Valid sandbox failure: retain result and analyze; no same-ID tuning.
- Sandbox pass: freeze code/config and preregister multiple uninspected historical periods before acquisition/opening.
