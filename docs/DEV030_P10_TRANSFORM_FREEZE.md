# DEV030-P10 Transform Implementation Freeze

Status: `P10_TRANSFORM_IMPLEMENTATION_FROZEN`

## Scientific transform freeze commit

`e46f36337a9f0cb5c6ba17136fec3e0c60f0edf7`

This commit contains the frozen deterministic MiniRocket-style transform source,
the focused synthetic test suite, the isolated P10 dependency extra, and the
initial CI wiring. Later commits that only reorganize CI/test discovery or update
documentation are not scientific transform commits.

## Frozen local identities

Transform source:
`src/multimarket/dev030_p10_minirocket_transform.py`

SHA256:
`56071d2cde4a189b5e1d6711aff16139c315618192e13d13d38374a9a91f384f`

Focused synthetic test content SHA256:
`37323512adc9b5530fc8cb77cec0ec0585110696fa2fe949b5fd1db1e8554848`

At the scientific freeze commit the test path was:
`tests/test_dev030_p10_minirocket_transform.py`

The same test content was later moved to:
`tests/p10_test_minirocket_transform.py`
solely so legacy `unittest discover` would not import a Numba-dependent pytest
module in legacy environments. The test semantics/content were unchanged.

Freeze-time project file identities:
- `pyproject.toml` SHA256:
  `e90e4fa9ca05d241043e72bbc7467df7564ff14446b0d797586b4684001a0403`
- initial P10 CI workflow SHA256 at scientific freeze:
  `75a92b8972274a386133e8385d7c76ec4da87b3a46050fb7d04136b0dc98bd0c`

## Canonical transform environment

Local canonical environment:
- Python 3.14.4
- NumPy 2.5.2
- scikit-learn 1.9.0
- pytest 7.4.3
- Numba 0.67.0
- llvmlite 0.49.0

Local focused transform tests:
- 11 passed
- exit code 0
- exact HEAD = scientific transform freeze commit
- dirty count = 0

## Final CI evidence

Final CI-only head:
`73f3c401ee6df4ac2fea768f4e36b74b1924ec1d`

GitHub Actions run:
`33580590326`

Results:
- legacy unit-tests Python 3.10 = SUCCESS
- legacy unit-tests Python 3.12 = SUCCESS
- P10 transform canonical Python 3.14 = SUCCESS

The Python 3.14 P10 job pins:
- NumPy 2.5.2
- scikit-learn 1.9.0
- pytest 7.4.3
- Numba 0.67.0
- llvmlite 0.49.0

Two earlier CI failures were infrastructure/test-discovery issues only:
1. Python 3.10 resolver selected NumPy 2.2.6, correctly rejected by the exact
   P10 runtime gate.
2. legacy unittest discovery imported the Numba-dependent P10 pytest file without
   the P10 dependency extra.

Neither failure changed or challenged the scientific transform implementation.

## Frozen transform specification

- input shape = [n_instances, 3, 32]
- dtype = float32
- channels = spread_bps, microprice_minus_mid_bps,
  mid_log_return_250ms_bps
- requested features = 10,000
- actual features = 9,996
- kernel patterns = 84
- features/kernel = 119
- dilations = [1,2,3]
- per-kernel allocation = [60,37,22]
- random_state = 0
- one transform thread
- no interpolation/padding/ffill/bfill
- explicit deterministic pre-materialized sampling plan
- domain-separated parameter and feature SHA256

## Scope

No Jan-Jul P10 analytical data was loaded to establish this freeze.
No P10 classifier was fitted.
No P10 canonical artifact exists.
No August/September data or Railway storage was opened.

## Next permitted action

Write and test the nested analytical P10 runner against synthetic/injected data.
Do not execute the canonical Jan-Jul P10 campaign until the complete runner is
separately frozen and local preflight passes.
