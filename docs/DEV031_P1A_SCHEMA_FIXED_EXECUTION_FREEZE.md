# DEV031-P1A Schema-Fixed Scientific Execution Freeze

Status: `DEV031_P1A_SCHEMA_FIXED_IMPLEMENTATION_FROZEN_CANONICAL_MATERIALIZATION_AUTHORIZED`

Scientific execution freeze commit:

`dbcde61b378bdc9f2533ac21af72632651a52df2`

The earlier execution candidate
`96881948a363c259b836c319ddf5ca5b04a66730`
is permanently superseded for execution because its first canonical attempt
stopped at a frozen-P3 provenance schema mismatch before any raw P1A read.

That attempt remains recorded as:
`ABORTED_PROVENANCE_SCHEMA_NO_RAW_NO_ARTIFACT`

## Frozen identities

- C++ extractor SHA256 =
  `a7d9db4594caea6ec67255d80ce29fb8ce1370ea7f3aecac3056a47667a9c437`
- Python materializer SHA256 =
  `4978de8c9258ecfa768ce69ad0b7c9769c796f6e5d68f284a3740a30365bc124`
- P1A test SHA256 =
  `dbb1feca4f1eb4012fb77ae90e9d98ab1ea04b5d5b256f07435dbc7e16bc0dc8`
- research SHA256 =
  `54c222b1a1a0b60c72781d80848a4da1ad35b3482edbcc14a08910041a070721`
- design SHA256 =
  `f5c566ee58feb8aeb24bf1c82c6c6ddcf64b1a4c4ab0e0886b13c98b9c94c89e`

## Local schema-fixed freeze validation

- focused P1A = 8 passed in 1.36s
- P1A_TEST_EXIT = 0
- real frozen P0A status = `DATA_READY_EVENT_DEPTH_RAW_L2`
- real frozen P2C status = `DIRECTION_DATASET_SUPPORT_MANIFEST_MATERIALIZED`
- real frozen P3 selected candidate matched nested schema exactly
- selected P3 trial found exactly once
- P1A_REAL_PROVENANCE_SCHEMA = PASS
- canonical P1A output absent = PASS
- FINAL_HEAD = scientific execution freeze commit
- DIRTY_COUNT = 0
- git diff check = 0

## CI

Schema-fixed focused P1A:
- run `33620587030`
- dedicated job = SUCCESS
- 8 passed

Companion regressions:
- Python 3.10 = SUCCESS
- Python 3.12 = SUCCESS
- DEV031-P0 = SUCCESS
- DEV031-P0A = SUCCESS
- P10 transform = SUCCESS

## Scientific scope unchanged

No scientific design changed from the frozen P1A design:
- A / 120s / 16bp / 32s / PRICE
- exact frozen P3 T1 support/labels
- 23 frozen P3 PRICE S1 features
- 26 preregistered EVENT_DEPTH features
- no predictive metric/model/PnL
- no EXP024 filter/feature
- no P4 composition
- no Aug-01/Aug-30/Sep-01+/Railway/archive/abundant-love

## One-shot rule

Canonical P1A materialization may execute once from
`dbcde61b378bdc9f2533ac21af72632651a52df2`.

Once a valid canonical P1A manifest exists, DEV031-P1A must never be rerun.
