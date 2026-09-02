# DEV030-P10 Nested Runner Implementation Freeze

Status: `P10_RUNNER_IMPLEMENTATION_FROZEN`

## Scientific runner freeze commit

`94c74c98f2521c21db0b2a0680c9788ef40a00b1`

Only this commit is eligible as the scientific execution candidate for the
canonical DEV030-P10 Jan-Jul campaign after final local read-only preflight.
Later documentation-only descendants are not scientific execution commits.

## Frozen source/test identities

Transform source:
`src/multimarket/dev030_p10_minirocket_transform.py`

SHA256:
`56071d2cde4a189b5e1d6711aff16139c315618192e13d13d38374a9a91f384f`

Nested runner:
`src/multimarket/dev030_p10_minirocket.py`

SHA256:
`83eb7d142fac8906d51bb5f3343fd17840f6ccfe6108d2a20244e849b50b67a5`

Transform focused test:
`tests/p10_test_minirocket_transform.py`

SHA256:
`37323512adc9b5530fc8cb77cec0ec0585110696fa2fe949b5fd1db1e8554848`

Runner guard test:
`tests/p10_test_minirocket_runner.py`

SHA256:
`69522ee7afd61b69e52b1ca5db7bbe7f5cc6c7c82a53d03dc5eef59a1949f984`

Freeze-time pyproject:
SHA256
`e90e4fa9ca05d241043e72bbc7467df7564ff14446b0d797586b4684001a0403`

Freeze-time workflow:
SHA256
`56c428553428443dbeb0f68d2aa585bf57c4152e97bbc0e62a27743de25dd851`

## Local canonical environment

- Python 3.14.4
- NumPy 2.5.2
- scikit-learn 1.9.0
- pytest 7.4.3
- Numba 0.67.0
- llvmlite 0.49.0

Local focused transform + runner suite:
- 22 passed
- exit code 0

Local repository state:
- exact HEAD = `94c74c98f2521c21db0b2a0680c9788ef40a00b1`
- dirty count = 0

## Frozen prior result invariant

DEV030-P9 artifact:
`/home/emadh/Multi-Market/evidence/dev030_p9_price_dense_sequence_v1/DEV030_P9_PRICE_DENSE_SEQUENCE_RESULT.json`

SHA256:
`2f1913b3ac80df5cb0dd01dc7001c333983d22e6a8514346f9cee57a3333b9dc`

Local prefreeze check:
`P9_ARTIFACT_MATCH = True`

P10 canonical output directory:
`/home/emadh/Multi-Market/evidence/dev030_p10_price_minirocket_v1`

Local prefreeze state:
`P10_OUTPUT_EXISTS = False`

## GitHub CI evidence

Run:
`33580838772`

Results:
- Python 3.10 legacy: 789 tests, OK
- Python 3.12 legacy: 789 tests, OK
- Python 3.14 P10 transform + runner: 22 passed

## Frozen nested-fitting behavior

For every outer fold:
- MiniRocket is fitted on inner-fit only for C selection;
- inner-validation is transformed only with inner-fit parameters;
- a fresh MiniRocket fit is performed on full outer-train;
- outer-validation is transformed only with outer-train parameters;
- no validation data contributes to transform parameter fitting;
- downstream scaling remains train-only;
- C selection remains frozen probability-first;
- C0 must reproduce the frozen P8/P9 baseline exactly;
- P9 artifact status/SHA are required invariants;
- P9 promotion gates are retained;
- pooled BA and macro-F1 non-regression are additional gates;
- temporal null runs only after all prechecks pass.

## Scope at freeze

No canonical P10 Jan-Jul analytical campaign has been run.
No P10 scientific result exists.
No P10 canonical artifact exists.
No August/September data has been opened.
No Railway bucket/volume has been opened.

## Next permitted action

Perform one final read-only local preflight on this exact commit:
- source/test SHA identities;
- exact runtime versions;
- frozen P2C-P9 artifact identities/statuses;
- Jan-Jul manifest identities;
- P10 protocol constants;
- canonical output absence;
- exact clean HEAD.

Only if every gate passes may the canonical P10 one-shot be authorized.
