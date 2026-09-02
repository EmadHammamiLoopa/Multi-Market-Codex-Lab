# DEV030-P10 — MiniRocket-Style Multivariate PRICE Representation Audit

Status: `AUDIT_PASS_DESIGN_FREEZE_READY`

Research/design only. No Jan–Jul analytical data was loaded, no model was fitted, no P10 artifact was written, and no August/September/Railway storage was opened.

## Research question

Does one frozen deterministic MiniRocket-style transform of the same three-channel 32-second causal PRICE sequence add stable direction-given-touch information beyond the frozen 23-feature PRICE summary baseline?

P10 is a representation test, not an architecture search and not an economic test.

## Prior evidence preserved

- EXP024-P1 remains the strong opportunity-ranking success.
- DEV030-P3 remains the frozen direction baseline success.
- DEV030-P4 touch-vs-none remains a component success although composition failed.
- DEV030-P8 failed sparse PRICE temporal-shape increment.
- DEV030-P9 terminal result is `FAIL_PRICE_DENSE_SEQUENCE_NO_STABLE_INCREMENTAL_VALUE`.
- P9 artifact SHA256 is `2f1913b3ac80df5cb0dd01dc7001c333983d22e6a8514346f9cee57a3333b9dc`.
- P9 must never be rerun.

## Primary source audit

### Original MiniRocket

Repository: https://github.com/angus924/minirocket

Observed/pinned main commit:
`0b1c245d9c9dbc50886f28bc7b32d5d45b5663d6`

Scientific source:
Dempster, Schmidt, Webb, MiniRocket, KDD 2021 / arXiv:2012.08791.

Findings:
- MiniRocket is an almost-deterministic convolutional transform followed by a linear classifier.
- The original repository contains a basic multivariate implementation.
- The multivariate implementation uses random instance/channel choices unless randomness is controlled.
- Input is expected as `np.float32`.
- Pre-transform normalization is not required by the method.
- The original repository is GPL-3.0.

Because Multi-Market-Codex-Lab is a public GitHub repository, P10 must not copy/vendor the GPL implementation into this repository merely for convenience. It remains an algorithmic reference only.

### sktime MiniRocketMultivariate

Repository: https://github.com/sktime/sktime

Pinned source-review commit:
`d26be800f423eb273d8a83269a2e9ec6dd524d77`

Pinned blobs:
- wrapper `_minirocket_multivariate.py`: `4349de033310bbcbf51e105f899a9b83a296b7e7`
- Numba core `_minirocket_multi_numba.py`: `2f62d055107e4ae04cc6a50eea57dab0fc0310b5`
- BSD-3-Clause license: `e321b92c174d19654c0bf83f6ee73f50b024f92c`

Findings:
- equal-length multivariate input is `[n_instances, n_dimensions, n_timepoints]`;
- minimum series length is 9;
- explicit integer `random_state` is supported;
- seeded randomness controls channel combinations and bias-fitting sample selection;
- `n_jobs=1` is supported;
- requested 10,000 features round down to 9,996 (multiple of 84);
- output is PPV-style `float32` features;
- source is BSD-3-Clause.

## Environment compatibility

Frozen P9 environment:
- Python 3.14.4
- NumPy 2.5.2
- scikit-learn 1.9.0
- pytest 7.4.3

Numba 0.67.0 supports Python >=3.10,<3.15 and NumPy <2.6, including NumPy 2.5.2. Its compatible llvmlite line is 0.49.x.

The current sktime package supports Python 3.14 but constrains scikit-learn to <1.8.0, conflicting with frozen scikit-learn 1.9.0.

Decision:
- do not install sktime into the canonical project environment;
- do not downgrade scikit-learn;
- use a minimal local MiniRocket-style transform adapted from the pinned BSD sktime source with attribution;
- runtime transform dependency is NumPy + Numba only.

## Sequence geometry feasibility

Frozen input:
- 3 channels;
- 32 timepoints;
- oldest to newest;
- `spread_bps`;
- `microprice_minus_mid_bps`;
- `mid_log_return_250ms_bps`.

32 >= minimum length 9, so no padding is required.

Frozen requested MiniRocket capacity:
- requested features = 10,000;
- fixed kernel patterns = 84;
- features per kernel = floor(10000/84) = 119;
- actual output features = 9,996;
- max dilations per kernel = 32.

For length 32 the deterministic dilation calculation produces:
- unique dilations = [1, 2, 3];
- features per dilation per kernel = [60, 37, 22].

No kernel-count or dilation sweep is allowed.

## Determinism requirements

Frozen:
- random_state = 0;
- input dtype = float32;
- one transform thread;
- fixed channel order;
- fixed time order;
- no seed sweep;
- no seed averaging.

Before any analytical fit, synthetic implementation tests must prove:
1. same-process parameter hashes are identical on repeated fit;
2. same-process transformed-feature hashes are identical;
3. fresh-process parameter hashes are identical;
4. fresh-process transformed-feature hashes are identical;
5. output feature count is exactly 9,996;
6. outputs are finite and in [0,1];
7. all three channels are represented in fitted channel parameters on the frozen fixture;
8. perturbing one channel changes the transform;
9. length <9 is rejected;
10. no interpolation/ffill/bfill/padding is performed.

Any determinism failure => STOP before analytical model fit. No seed search.

## Leakage requirement

MiniRocket parameters are fitted from X. Therefore chronological validation X must not influence transform fitting.

For inner C selection:
- fit transform on inner-fit days only;
- transform inner-fit and inner-validation;
- choose C on inner validation only.

For outer evaluation:
- refit transform on all outer-train days only;
- transform outer-train and untouched outer-validation;
- score validation once.

No fitted transform parameters may cross a validation boundary.

## Statistical caution

P10 creates 9,996 transform features from only 573 pooled examples. This is accepted only as a final bounded representation test because:
- feature count is frozen before outcomes;
- downstream model remains L2-regularized and linear;
- no feature selection/PCA/tuning is allowed;
- chronological nested evaluation remains intact;
- promotion requires probability-quality, fold stability, LOO stability, and temporal-null significance, not pooled AUC alone.

## Audit conclusion

`PASS_FOR_DESIGN_FREEZE`

P10 is technically feasible if:
- BSD-derived isolated transform is used;
- Numba 0.67.0 is frozen;
- exact llvmlite patch is recorded after environment creation;
- deterministic pre-fit tests pass;
- P9 gates are not lowered;
- no data is opened until implementation freeze.

## Prohibited before implementation freeze

- no Jan–Jul analytical load;
- no P10 model fit;
- no P10 artifact;
- no August/September data;
- no Railway bucket/volume access;
- no kernel/seed/channel/window/lag sweep;
- no OFI retry;
- no calibration;
- no threshold/PnL/economic test;
- no CNN/TCN/LSTM/Transformer/TLOB.
