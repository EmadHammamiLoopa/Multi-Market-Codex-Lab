# CODEX-EXP-005-P1 Preregistration

Status: **PREREGISTERED BEFORE ANY EXP005-P1 MODEL OUTPUT**

Experiment ID: `CODEX-EXP-005-P1`

Parent data-readiness result: `CODEX-EXP-005-P0 = DATA_READY_SANDBOX`

Parent frozen audit artifact SHA-256: `b151aba2455ee237acf34da76d257b6f8d1a221166cffdbe967851315482ef52`

## Scientific question

Does causally available derivatives-native state add **within-regime timing information** for the frozen 10-minute >=24 bp executable-opportunity target beyond the existing R/regime baseline?

This experiment tests incremental information, not a new model class.

## Frozen market, symbols, dates, target, and horizon

- Market: Binance USD-M Futures.
- Symbols: BTCUSDT and ETHUSDT only.
- Dates: first day of each month January through July 2026 only.
- August remains sealed.
- Decision grid: every 60 seconds.
- Opportunity horizon: 600 seconds.
- Entry: decision time +250 ms, using the already-consumed Phase-L executable state.
- Opportunity target: oracle executable fixed-horizon gross opportunity >=24 bp, exactly as frozen in EXP004.

No new target, horizon, symbol, exchange, or cost assumption is allowed in P1.

## Input families

### Baseline R

Use the exact previously frozen EXP004-P1 R feature family and causal construction. No R feature may be added or removed after scoring.

### Derivatives block D

Use only the EXP005-P0-authorized state families:

#### Open interest

- current log open interest;
- 1-minute log change;
- 5-minute log change;
- 15-minute log change;
- 30-minute log change;
- 5-minute trailing z-score;
- 30-minute trailing z-score.

#### Premium / basis

Premium is defined causally as:

`10000 * (mark_price / index_price - 1)`

Features:

- current premium bp;
- 1-minute change;
- 5-minute change;
- 15-minute change;
- 30-minute change;
- 30-minute trailing z-score.

#### Funding

Use:

- current native `funding_rate`;
- change from the prior distinct native funding-rate state.

Do not use:

- `predicted_funding_rate`;
- raw mark price as a standalone predictive feature;
- raw index price as a standalone predictive feature;
- raw last price as a standalone predictive feature;
- liquidations;
- L2 features;
- another venue.

## Causal availability and staleness

All derivatives-state availability uses `local_timestamp` only.

For every current or lagged derivatives state used at decision time `t`:

- source local timestamp must be <= the lookup timestamp;
- no future native state may be used;
- maximum permitted staleness is 30 seconds.

The 30-second limit is frozen from P0 data-quality evidence before any P1 predictive scoring. P0 showed sub-second median update gaps, p99 generally around 2--3 seconds, and worst observed gaps below roughly 15 seconds.

If a required value at any lag cannot be reconstructed under the 30-second rule, that decision row is invalid for tracks using D.

## Trailing transforms

All z-scores and lag changes are past-only.

For a lag L at decision time t, the lagged value is the most recent native state available at or before `t-L`, subject to the same 30-second staleness limit.

No interpolation is allowed.

For a trailing z-score, the history window ends at the current decision time and may contain only causal reconstructed states. Mean and standard deviation are computed only from past decision-grid states within the frozen lookback. Zero-variance windows are invalid for that feature.

## Model

Use the same fixed model family as EXP004-P1:

- `StandardScaler`, fitted on training data only;
- `LogisticRegression`;
- L2 regularization;
- C = 1;
- solver = `lbfgs`;
- no class weighting;
- max_iter = 1000;
- random seed = 20260825.

No hyperparameter search, model selection, nonlinear rescue, calibration rescue, XGBoost, neural network, or threshold tuning is allowed in this experiment.

## Primary tracks

### R

Exact baseline R model, evaluated on the exact common support used by RD for each fold/symbol.

### RD

R plus the complete frozen derivatives block D.

The primary scientific comparison is **RD versus R on identical train and outer-test support**.

## Diagnostic tracks

Diagnostics do not promote or rescue the experiment.

Report:

- D-only;
- R + OI only;
- R + premium only;
- R + funding only;
- volatility-only baseline from EXP004 construction.

A strong diagnostic subtrack cannot rescue a failed primary RD result. Any later use of a successful subtrack requires a new experiment ID and new preregistration.

## Outer validation

Use the exact EXP004 chronological expanding outer folds:

- March 1: train January--February;
- April 1: train January--March;
- May 1: train January--April;
- June 1: train January--May;
- July 1: train January--June.

The target of each outer day must never enter its training period.

All scaling is train-only.

Report both:

- dense 1-minute outer-test metrics;
- deterministic non-overlap 10-minute metrics.

## Common-support invariant

Every comparison RD versus R must use identical rows in both training and outer test.

The common support is the subset where all frozen D features required by RD are causally valid under the 30-second staleness rule and where R is valid.

R may not receive extra rows merely because R itself does not require D.

## Primary metrics

Report for R and RD:

- prevalence;
- ROC AUC;
- average precision;
- average precision / prevalence;
- Brier score and Brier skill versus outer prevalence;
- log loss;
- top-decile precision and lift;
- top-quintile precision and lift;
- per-fold metrics;
- per-symbol pooled metrics;
- deterministic non-overlap 10-minute metrics.

Brier skill is descriptive in EXP005-P1 and is not an absolute promotion gate. No post-hoc calibration is permitted.

## Frozen primary promotion gates

`PREDICTABLE_INCREMENTAL_DERIVATIVES_SANDBOX` requires **all** of the following:

1. pooled ROC AUC(RD) - pooled ROC AUC(R) >= +0.01;
2. pooled average precision(RD) - pooled average precision(R) >= +0.01 absolute;
3. pooled top-decile precision(RD) >= pooled top-decile precision(R);
4. pooled log loss(RD) < pooled log loss(R);
5. at least 4 of 5 outer folds have AUC(RD) > AUC(R);
6. BTCUSDT pooled AUC(RD) > AUC(R);
7. ETHUSDT pooled AUC(RD) > AUC(R);
8. deterministic non-overlap pooled AUC(RD) - AUC(R) >= +0.01;
9. the derivatives timing falsification gate defined below passes;
10. all implementation/provenance/causality invariants pass.

There is no rescue by relaxing a failed threshold after outputs are opened.

## Derivatives timing falsification control

The principal falsification asks whether D contains timing information beyond coarse symbol/day regime state.

Construct a deterministic `RD_D_TIME_PERMUTED` track:

- preserve R exactly;
- preserve labels exactly;
- preserve the distribution of each full D feature vector within each symbol/day;
- deterministically permute complete D vectors across decision times within each symbol/day using seed 20260825;
- do not mix symbols;
- do not mix days;
- do not permute individual D columns independently;
- apply the permutation separately within training days before model fitting and within each outer-test day before scoring.

Frozen gate:

`pooled AUC(RD_REAL) - pooled AUC(RD_D_TIME_PERMUTED) >= +0.01`

The purpose is to test within-day timing information. The control preserves day-level derivatives distributions while destroying temporal alignment.

The falsification control cannot rescue a failed incremental primary gate.

## Positive control

Retain the forbidden future 10-minute executable-opportunity magnitude canary from EXP004 as a pipeline sensitivity control only.

The positive-control canary must improve pooled AUC materially over R; use the previously frozen +0.10 improvement requirement.

It cannot rescue the primary experiment.

## Feature-sign diagnostic

After fitting the real RD model, construct a diagnostic in which the signed D changes are inverted at scoring time:

- OI log changes;
- premium changes;
- funding-rate change.

Unsigned/current level variables and z-score magnitudes are not inverted merely to force a degradation.

The sign diagnostic is descriptive and cannot rescue a primary failure.

## Statuses

Possible final statuses:

- `PREDICTABLE_INCREMENTAL_DERIVATIVES_SANDBOX` — all frozen primary gates and invariants pass;
- `FAIL_DERIVATIVES_NO_INCREMENTAL_TIMING_INFORMATION` — the frozen primary promotion criteria fail;
- `INVALID` — provenance, sealed-data, causality, common-support, or implementation invariants are violated.

## Interpretation limits

A PASS would mean only that derivatives-native state adds incremental sandbox predictability for timing the frozen 10-minute opportunity event beyond R.

A PASS would **not** establish:

- long/short direction predictability;
- executable net profitability at 8/12 bp;
- strategy profitability;
- prospective validity;
- live-money readiness.

Only after a P1 PASS may a separate experiment preregister direction/value estimation and executable economics.

## No-rescue rule

After any P1 model output is opened, do not change under this experiment ID:

- target threshold;
- 10-minute horizon;
- 250 ms entry delay;
- symbols;
- venue;
- dates;
- staleness limit;
- derivatives feature set;
- model class;
- hyperparameters;
- promotion gates;
- time-permutation definition;
- August seal;
- costs;
- add liquidations, L2, external venues, or new data.

Any such change requires a new experiment ID.

## Required implementation tests before scoring

Before the first P1 model output, synthetic/unit tests must verify at minimum:

1. local timestamp is the only D availability clock;
2. a future derivatives record cannot enter a current lookup;
3. the 30-second staleness rule invalidates older state;
4. 1m/5m/15m/30m lag lookups are past-only;
5. z-score windows are past-only;
6. predicted funding rate is excluded;
7. no August file/path can be opened;
8. RD and R use exact common training support;
9. RD and R use exact common outer-test support;
10. time permutation preserves symbol/day and D rows but changes timing;
11. time permutation operates on complete D vectors, not independent columns;
12. outer folds are chronological and training-only scaling is preserved;
13. non-overlap metrics use the deterministic 10-minute schedule;
14. configuration and raw-input hashes are embedded in the result;
15. scoring refuses to overwrite an existing final or partial result.

After implementation and tests pass, freeze the exact pre-score commit and stop for review before scoring.
