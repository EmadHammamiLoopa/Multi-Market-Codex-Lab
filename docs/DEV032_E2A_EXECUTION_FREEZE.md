# DEV032-E2A Execution Freeze

Status: `EXECUTION_FROZEN_LOCAL_PREFLIGHT_REQUIRED_NO_CANONICAL_RUN_YET`

Scientific execution commit:

`72f47d3020e0eb2e9c484514c663a93534eb0755`

CI run:

`33640787470`

CI conclusion:

`SUCCESS`

Dedicated job:

`dev032-e2a-materialization = SUCCESS`

## Scientific scope

DEV032-E2A is representation/materialization only.

It must not:

- fit LogisticRegression;
- fit PCA globally;
- fit SVD globally;
- compute AUC/logloss/Brier;
- run temporal nulls;
- run PnL;
- open Sep-01+;
- open Railway/archive/abundant-love;
- change support or labels.

## Frozen design lineage

Wave-2 design:
`docs/DEV032_E2_WAVE2_ADAPTIVE_REFINEMENT_DESIGN.md`

Formula specification:
`docs/DEV032_E2A_FORMULAS.md`

Exactly 10 adaptive refinement representations.
Exactly 130 raw materialized columns.
Exact support target:

- rows = 1374
- LONG = 684
- SHORT = 690

Parent support/provenance anchor:

`DEV032-E1A`

SHA256:

`76e1c97e8b9a899bc27f3193316cbfc85efba8b0a7aa037d4c46fcc6a8be4a50`

## Frozen implementation files

- `src/multimarket/dev032_e2a_feature_core.py`
- `src/multimarket/dev032_e2a_materialize.py`
- `src/multimarket/dev032_e2a_runner.py`
- `tools/dev032_e2a_raw_features.cpp`
- `tests/test_dev032_e2a.py`
- `.github/workflows/test.yml`

The original DEV032-E1A extractor remains untouched.

## Preserved implementation-test failure

The first E2A CI run:

`33640577120`

failed only in the E2A synthetic test because the synthetic fixture deleted one
of exactly 50 levels, intentionally triggering the extractor's insufficient
depth fail-closed behavior at a later support timestamp.

No real data was accessed by CI.

The fixture was corrected to a partial depletion that preserves 50 levels.

Corrected CI:

`33640787470 = SUCCESS`

This test failure remains part of the audit trail and is not a scientific
result.

## Canonical output contract

Canonical directory:

`/home/emadh/Multi-Market/evidence/dev032_e2a_wave2_materialization_v1`

Canonical artifact:

`DEV032_E2A_WAVE2_MATERIALIZATION.json`

Before canonical execution, the output directory must not exist.

After one valid canonical artifact is written:

`DEV032-E2A MUST NEVER BE RERUN`

## Next permitted action

Local preflight only:

- exact execution HEAD;
- clean working tree;
- canonical output absent;
- known Python environment;
- g++/zlib available;
- dedicated E2A tests PASS;
- frozen implementation SHA256 recorded;
- no real materialization yet.

Current state:

`DEV032_E2A_EXECUTION_FROZEN_LOCAL_PREFLIGHT_REQUIRED_NO_CANONICAL_RUN_YET`
