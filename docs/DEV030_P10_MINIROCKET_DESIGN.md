# DEV030-P10 — Frozen MiniRocket-Style Multivariate PRICE Design

Status: `DESIGN_FROZEN_IMPLEMENTATION_NOT_STARTED`

This design is frozen before any P10 analytical data load or model fit.

## Experiment identity

- Experiment ID: `DEV030-P10`
- Design version: `price-minirocket-multivariate-linear-v1`
- Task: `DIRECTION_GIVEN_TOUCH`
- Comparison: exact frozen C0 vs one MiniRocket-style augmented C1

## Target, support, folds

Target is unchanged:
- Target A
- horizon 120 s
- barrier 16 bp
- exact first-passage LONG_FIRST vs SHORT_FIRST

Exact support:
- pooled 573
- LONG 309
- SHORT 264
- folds [159, 64, 126, 224]
- fold LONG [86, 40, 60, 123]
- fold SHORT [73, 24, 66, 101]
- pooled support SHA256 `8b30ba4544530043ebadd323cc40a70a44861a3f00a018dbc1cc9d70fc1ff59d`
- pooled label SHA256 `8af5a70b6a3ff26d22be660809cc736a8cfc0d4a0d1c887a75ca66341cf97215`

Outer folds remain:
1. Jan-Mar / Apr
2. Jan-Apr / May
3. Jan-May / Jun
4. Jan-Jun / Jul

## C0 baseline

C0 is the exact 23-feature PRICE S1 probability-first baseline reproduced in P8/P9.

Before C1 scoring, P10 must reproduce C0 exactly:
- selected C;
- support/class counts;
- support SHA;
- label SHA;
- prediction SHA;
- fold metrics;
- pooled metrics.

Any mismatch => STOP before C1 scientific evaluation.

## Raw sequence

Window = 32 s.
Exact 1-second grid.
Lags 32,31,...,1 s, oldest to newest.

Channel order:
1. `spread_bps`
2. `microprice_minus_mid_bps`
3. `mid_log_return_250ms_bps`

Per-example shape: `[3,32]`.
Transform input dtype: `float32`.

No interpolation, ffill, bfill, smoothing, resampling, padding, or pre-transform normalization.

If exact sequence extraction fails on any frozen support row => STOP.

## MiniRocket-style transform

Reference source:
sktime commit `d26be800f423eb273d8a83269a2e9ec6dd524d77`

Pinned blobs:
- `4349de033310bbcbf51e105f899a9b83a296b7e7`
- `2f62d055107e4ae04cc6a50eea57dab0fc0310b5`
- BSD license `e321b92c174d19654c0bf83f6ee73f50b024f92c`

Implementation rule:
adapt only the minimal equal-length multivariate transform logic with BSD attribution. Do not install sktime at runtime. Do not copy GPL original source.

Frozen transform parameters:
- requested features = 10,000
- actual features = 9,996
- 84 fixed kernel patterns
- 119 features/kernel
- max dilations/kernel = 32
- expected length-32 dilations = [1,2,3]
- expected per-kernel allocation = [60,37,22]
- random_state = 0
- transform threads = 1
- input/output dtype = float32
- no pre-transform normalization

No alternative count, seed, dilation cap, channel set, or transform variant.

## Environment target

Dedicated P10 venv preferred; do not mutate P9 venv.

Frozen target:
- Python 3.14.4
- NumPy 2.5.2
- scikit-learn 1.9.0
- Numba 0.67.0
- llvmlite 0.49.x; exact patch frozen after install
- pytest 7.4.3

No sktime package in canonical P10 runtime.

## C1

C1 = exact C0 23 features + 9,996 MiniRocket-style features.
Total = 10,019 features.

Column order is deterministic: C0 first, MiniRocket second.

Fit `StandardScaler` on training data only over the complete C1 matrix.

No PCA, feature selection, clipping, calibration, dimensionality reduction, or screening.

## Downstream classifier

Exactly P9 probability-first L2 LogisticRegression:
- solver lbfgs
- C grid [0.01,0.1,1.0,10.0]
- class_weight None
- max_iter 1000
- fit_intercept True
- threshold 0.5 only for diagnostic class metrics
- train-only StandardScaler

Inner C selection:
1. minimum binary log loss
2. minimum Brier
3. maximum ROC AUC
4. smaller C tie-break

No new hyperparameter tuning.

## Nested transform rule

For each outer fold:

Inner:
- fit transform on inner-fit only;
- transform inner-fit/inner-validation;
- concatenate C0;
- train-only scaler;
- select C on inner validation.

Outer:
- refit transform on all outer-train only;
- transform train/untouched validation;
- concatenate C0;
- train-only scaler;
- fit selected C;
- predict validation once.

## Pre-fit determinism gates

All must pass before any analytical model fit:
- same-process parameter hash exact repeat;
- same-process feature hash exact repeat;
- fresh-process parameter hash exact repeat;
- fresh-process feature hash exact repeat;
- output count 9,996;
- finite outputs;
- output range [0,1];
- frozen synthetic parameters use channels {0,1,2};
- perturb-one-channel changes output;
- length <9 rejected;
- exactly one thread;
- exact dependency versions recorded.

Failure => STOP, no seed search.

## Scientific invariants

Before C1 scoring:
- verify frozen P2C-P9 artifacts;
- verify P9 status exactly `FAIL_PRICE_DENSE_SEQUENCE_NO_STABLE_INCREMENTAL_VALUE`;
- verify P9 artifact SHA256 `2f1913b3ac80df5cb0dd01dc7001c333983d22e6a8514346f9cee57a3333b9dc`;
- exact support/labels;
- exact C0 reproduction;
- all forward guards false;
- canonical P10 output absent.

## Promotion gates

Do not lower P9 bar. Precheck requires all:
- C1 pooled AUC >= 0.56;
- pooled AUC improves;
- pooled log loss improves;
- pooled Brier improves;
- >=3/4 folds improve AUC;
- >=3/4 folds improve log loss;
- >=3/4 C1 fold AUC >0.50;
- every LOO AUC delta >0;
- every LOO log-loss improvement >0;
- both classes noncollapsed each fold;
- exact support/invariants pass;
- pooled balanced accuracy does not regress;
- pooled macro-F1 does not regress.

Only if all prechecks pass: run the same frozen paired temporal null used in P9.

Final promotion additionally requires:
- observed log-loss improvement > null q95;
- empirical temporal-null p <=0.05.

Any gate failure => terminal P10 FAIL, no post-outcome tuning.

## Terminal statuses

- `ELIGIBLE_PRICE_MINIROCKET_INCREMENTAL_INFORMATION`
- `FAIL_PRICE_MINIROCKET_TEMPORAL_NULL`
- `FAIL_PRICE_MINIROCKET_NO_STABLE_INCREMENTAL_VALUE`

Implementation/pre-fit failures must not be misreported as scientific model failures.

## Prohibited

No:
- August/September;
- Railway storage;
- kernel/seed/channel/window/lag search;
- MiniRocket vs MultiRocket bake-off;
- OFI;
- CNN/TCN/LSTM/Transformer/TLOB;
- calibration;
- class weighting/resampling;
- threshold optimization;
- opportunity composition;
- PnL/economics;
- post-hoc subset/session rescue.

## Stop rule

If P10 fails, close the Jan-Jul PRICE-only sequence-representation family. No more PRICE architecture shopping on the consumed data.

If P10 passes, freeze/reproduce it before any economic composition or deeper confirmation.
