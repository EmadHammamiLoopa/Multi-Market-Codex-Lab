# DEV031-P1A Scientific Execution Freeze

Status: `DEV031_P1A_IMPLEMENTATION_FROZEN_CANONICAL_MATERIALIZATION_AUTHORIZED`

Scientific execution freeze commit:

`96881948a363c259b836c319ddf5ca5b04a66730`

Later documentation-only descendants must not be used as scientific execution commits.

## Frozen identities

- C++ extractor:
  `tools/dev031_p1a_event_depth.cpp`
  SHA256:
  `a7d9db4594caea6ec67255d80ce29fb8ce1370ea7f3aecac3056a47667a9c437`

- Python materializer:
  `src/multimarket/dev031_p1a_event_depth_materialize.py`
  SHA256:
  `8f29133a1b2663c5dc3f00ed42d11e84bbd9e979359dc5001b5c71ff7868b44b`

- synthetic test:
  `tests/test_dev031_p1a_event_depth_materialize.py`
  SHA256:
  `2bb1afe0a6241274bea861d5abe5dbb9cd8a8d81ddbb6da97d0c73e9048bc862`

- research preregistration SHA256:
  `54c222b1a1a0b60c72781d80848a4da1ad35b3482edbcc14a08910041a070721`

- frozen design SHA256:
  `f5c566ee58feb8aeb24bf1c82c6c6ddcf64b1a4c4ab0e0886b13c98b9c94c89e`

## Validation

Local focused P1A:
- 7 passed in 2.72s
- P1A_TEST_EXIT = 0
- protocol = PASS
- canonical output absent = PASS
- clean detached HEAD
- git diff check = 0

Post-P3 regression procedure:
- P3 = 49 passed, 1 known environment-state test deselected
- isolated synthetic-mode guard = `canonical_output_requires_real_mode` = PASS
- other frozen regressions = 189 passed
- P3 source SHA256 =
  `9730f62cd6e2ee2a84cb402a890629f7335eb42b730f24f69ffca971281ba675`
- P3 test SHA256 =
  `a3d57a928d6a2dedc762111e1859fa9d290ee084412d7c613f7541398e46360b`

GitHub CI:
- PR #4
- run `33586313560`
- dedicated P1A job = SUCCESS
- 7 passed
- P10/P0/P0A and Python 3.10/3.12 jobs = SUCCESS

## Scientific scope

P1A remains materialization-only:
- selected frozen P3 configuration A/120s/16bp/32s/PRICE
- exact frozen P3 T1 support and labels
- exact 23 P3 PRICE S1 features
- exactly 26 preregistered EVENT_DEPTH features
- no prediction, model fit, AUC, BA, Brier, log loss, thresholding, PnL,
  EXP024 filtering, or P4 composition
- no Aug-01/Aug-30/Sep-01+/Railway/archive/abundant-love access

## Canonical output

Directory:
`/home/emadh/Multi-Market/evidence/dev031_p1a_event_depth_materialization_v1`

Manifest:
`DEV031_P1A_EVENT_DEPTH_MATERIALIZATION.json`

One-shot rule:
Once a valid canonical P1A manifest exists, DEV031-P1A must never be rerun.

## Next action

Canonical P1A materialization is authorized exactly once from the scientific
execution freeze commit. After artifact creation, inspect read-only and preserve
the terminal status exactly.
