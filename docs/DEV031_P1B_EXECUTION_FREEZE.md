# DEV031-P1B Scientific Execution Freeze

Status: `DEV031_P1B_IMPLEMENTATION_FROZEN_CANONICAL_FIT_AUTHORIZED`

Scientific execution freeze commit:

`a6cf7a3c448cbb745de8a15ca6d2d33169628b2c`

Later documentation-only descendants must not be used as execution commits.

## Frozen identities

- source:
  `src/multimarket/dev031_p1b_event_depth_incremental.py`
  SHA256:
  `46e2753744fc02385cd70162fab5ae19a094eac768fd0b708fc077ecebb2c578`

- test:
  `tests/test_dev031_p1b_event_depth_incremental.py`
  SHA256:
  `ad3b1def838f3fab7797b782a5ef91d3a7a862020e51f90ffcc1dcb30ddb1a68`

- research SHA256:
  `e327c18c536c88ad5ab77b0f98beeec9ee105554dd521f5a211868068ef40893`

- design SHA256:
  `d40f7852f6b13edc329535ef437c22e6fad1e549eaa7a41ee400de8c769299e6`

## Final local freeze validation

- focused P1B = 8 passed in 3.28s
- P1B_TEST_EXIT = 0
- protocol = PASS
- P1A real-input precheck = PASS
- total T1 = 1,374
- LONG = 684
- SHORT = 690
- every C0 matrix = rows x 23
- every C1 matrix = rows x 49
- frozen P3 reproduction = PASS
- all four P3 OOF prediction hashes reproduced exactly
- canonical P1B output absent = PASS
- FINAL_HEAD = scientific execution freeze commit
- DIRTY_COUNT = 0
- git diff check = 0

The transient untracked `.build/` directory was deleted before freeze. It was
a generated local build cache only and was never part of the scientific tree.

## CI

PR #5
workflow run:
`33621896878`

Results:
- dev031-p1b-incremental = SUCCESS
- focused P1B = 8 passed
- dev031-p1a-materialization = SUCCESS
- dev031-p0-audit = SUCCESS
- dev031-p0a-audit = SUCCESS
- p10-transform = SUCCESS
- Python 3.10 unit tests = SUCCESS
- Python 3.12 unit tests = SUCCESS

## Frozen scientific comparison

C0:
- exact frozen P3 PRICE23

C1:
- exact C0 PRICE23
- plus all frozen EVENT_DEPTH26
- total = 49 features

Both use:
- exact same P1A T1 support and labels
- exact same four chronological folds
- train-only StandardScaler
- L2 LogisticRegression
- C grid [0.01, 0.1, 1.0, 10.0]
- probability-first chronological inner selection
- no threshold optimization
- temporal null only after strict precheck

## Preserved successes

- EXP024-P1 opportunity ranking success remains valid and preserved.
  It is not used as a P1B filter, feature, threshold, or rescue.
- DEV030-P3 remains the frozen directional anchor.
- DEV030-P4 touch-head success remains preserved for a later separately frozen
  composition stage.

## Forbidden

- raw L2 reopening
- Aug-01 / Aug-30 / Sep-01+
- Railway/archive/abundant-love
- feature subset search
- alternate model family
- EXP024 filtering
- P4 composition
- PnL
- threshold optimization

## Canonical output

Directory:
`/home/emadh/Multi-Market/evidence/dev031_p1b_event_depth_incremental_v1`

Artifact:
`DEV031_P1B_EVENT_DEPTH_INCREMENTAL_RESULT.json`

One-shot rule:
Once a valid canonical result artifact exists, DEV031-P1B must never be rerun.
