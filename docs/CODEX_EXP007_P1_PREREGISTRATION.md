# CODEX-EXP-007-P1 Preregistration

Status: **PREREGISTERED BEFORE ANY EXP007-P1 PREDICTIVE OUTPUT**

Date: 2026-08-26

Experiment ID: `CODEX-EXP-007-P1`

Parent data-readiness result:

`CODEX-EXP-007-P0 = DATA_READY_MAINTENANCE_AWARE_DVOL_SANDBOX`

Parent frozen result commit:

`4124ef0ed1ec186098a486f2c6c48a1581fe3406`

Parent P0 result SHA-256:

`0ce28490fff42d93d528675c0e1135e7e442f04727a6fb9997d441d115bde6ec`

Frozen EXP006 DVOL acquisition-manifest SHA-256:

`4d217438803ea82ead8899a9ab3ed45aa9942675748107191c79430a0250118d`

## Scientific question

> Does causally available own-currency Deribit
> options-implied volatility state add incremental
> information about the timing of the frozen 10-minute
> >=24 bp executable-opportunity target beyond the existing
> regime baseline R?

EXP007-P1 tests incremental information.

It does not test a new model family.

It does not predict trade direction.

It does not establish trading profitability.

## Prior evidence

EXP004 established substantial 10-minute opportunity
headroom but found that the existing R/regime representation
did not satisfy all frozen opportunity-predictability gates.

EXP005 tested Binance perpetual-derivatives information
including open interest, funding, and premium/basis.
Those features did not provide stable incremental
within-regime timing information.

EXP006/EXP007-P0 established that frozen BTC and ETH
Deribit DVOL data can causally support a bounded
30-minute feature family despite scheduled-maintenance gaps
that occur outside required cross-midnight causal support.

EXP007 changes the information family to options-implied
volatility.

It does not rescue EXP004, EXP005, or EXP006.

## Frozen symbols

Only:

- BTCUSDT target market paired with BTC DVOL;
- ETHUSDT target market paired with ETH DVOL.

BTC DVOL may not be used for ETHUSDT.

ETH DVOL may not be used for BTCUSDT.

No cross-asset DVOL feature is allowed.

## Frozen target and horizon

Use exactly the EXP004/EXP005 executable-opportunity target.

At each eligible decision time `t`:

- reaction/entry = `t + 250 ms`;
- exit = entry + 600 seconds;
- long gross bps =
  `10000 * log(bid_exit / ask_entry)`;
- short gross bps =
  `10000 * log(bid_entry / ask_exit)`;
- oracle gross bps =
  `max(long_gross_bps, short_gross_bps)`;
- binary target =
  `1[oracle_gross_bps >= 24]`.

Direction is hidden from the predictive tracks.

The oracle is used only to define whether an economically
meaningful fixed-horizon opportunity occurred.

No target threshold or horizon may be changed after
scoring begins.

## Frozen supervised dates

Only the first UTC day of:

- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

January and February 1 are not used.

August remains sealed.

## Decision grid

Decisions occur every 60 seconds from UTC midnight.

A decision is eligible only if:

1. the existing target-market R features are causally valid;
2. all frozen DVOL features are causally valid;
3. the executable 10-minute label remains inside the
   same UTC supervised day;
4. no future observation enters any feature.

## Frozen DVOL availability rule

For a decision at time `t`, the newest usable DVOL candle
has timestamp:

`<= t - 60 seconds`.

The candle timestamped at `t` is never usable at `t`.

No incomplete current-minute DVOL candle is used.

No interpolation, forward-fill, backward-fill, synthetic
candle, or another data source may repair missing DVOL.

## DVOL notation

For a decision at `t`, define:

- `C_k` = DVOL close of the candle timestamped
  `t - k minutes`;
- `O_k` = open of that candle;
- `H_k` = high of that candle;
- `L_k` = low of that candle.

Therefore:

- `C_1` is the latest usable completed DVOL candle;
- `C_31` is the oldest close required by the frozen
  30-minute transforms.

All prices must be finite and strictly positive.

Define one-minute DVOL log change:

`r_k = log(C_k / C_(k+1))`.

## Frozen DVOL feature block V

Exactly ten features are allowed.

### Level

1. `log(C_1)`

### Changes

2. `log(C_1 / C_2)` — 1-minute change;
3. `log(C_1 / C_6)` — 5-minute change;
4. `log(C_1 / C_16)` — 15-minute change;
5. `log(C_1 / C_31)` — 30-minute change.

### Latest completed-candle state

6. `log(H_1 / L_1)` — latest completed-minute DVOL range;
7. `log(C_1 / O_1)` — latest completed-minute DVOL
   open-to-close change.

### Trailing DVOL variation

For N in {5, 15, 30}, define:

`RV_N = sqrt(mean(r_k^2 for k = 1..N))`

using only completed candles.

8. `RV_5`;
9. `RV_15`;
10. `RV_30`.

No additional DVOL feature may be added after predictive
scoring starts.

No z-score, percentile, rolling rank, longer lookback,
option skew, option volume, option open interest,
term structure, strike data, risk reversal, or butterfly
measure is allowed under this experiment ID.

## Maximum DVOL history

The maximum frozen DVOL lookback is 30 minutes.

Feature construction may require only timestamps from:

`t - 31 minutes`

through:

`t - 1 minute`.

A longer lookback requires a new experiment ID.

## Baseline R

Track R uses the exact EXP004-P1 regime feature family and
causal definitions.

The family contains only target-market information known at
or before the decision time:

1. log mid returns over 1m, 3m, 5m, 10m, 30m;
2. absolute returns over 1m, 3m, 5m, 10m, 30m;
3. realized volatility from 1-minute returns over
   5m, 15m, 30m;
4. current spread bps;
5. trailing 1m and 5m mean spread bps;
6. 5m, 15m, 30m mid-price range in bps;
7. current normalized position inside the
   5m, 15m, 30m trailing mid range.

R may not be modified under EXP007-P1.

## Predictive tracks

### R

Exact baseline R.

### RV — primary

Exact R plus the complete frozen ten-feature V block.

The primary scientific comparison is:

`RV versus R`

on identical train and outer-test rows.

### V — diagnostic only

The ten DVOL features without R.

V cannot rescue a failed RV primary result.

### VOL — diagnostic only

The existing EXP004 volatility-only scalar baseline.

VOL cannot rescue EXP007.

## Common-support invariant

Every R-versus-RV comparison must use exactly the same
training and outer-test rows.

Common support is the subset where:

- R is valid;
- all ten V features are valid;
- the frozen opportunity label is valid.

R may not receive additional rows merely because it does
not require DVOL.

The V-only diagnostic must also use that same common
support.

## Frozen model

For each symbol and track separately:

- `StandardScaler`, fit on training data only;
- `LogisticRegression`;
- L2 penalty;
- `C = 1.0`;
- solver `lbfgs`;
- `class_weight = None`;
- `max_iter = 1000`;
- deterministic seed where applicable:
  `20260825`.

There is:

- no hyperparameter grid;
- no model selection;
- no XGBoost;
- no LightGBM;
- no Random Forest;
- no neural network;
- no LSTM;
- no Transformer;
- no calibration rescue;
- no threshold optimization.

## Frozen chronological outer folds

Four expanding outer folds:

1. outer 2026-04-01;
   train 2026-03-01;

2. outer 2026-05-01;
   train 2026-03-01 through 2026-04-01;

3. outer 2026-06-01;
   train 2026-03-01 through 2026-05-01;

4. outer 2026-07-01;
   train 2026-03-01 through 2026-06-01.

No outer-day observation may participate in fitting,
scaling, or feature normalization.

Training labels whose executable horizon crosses the
training-day boundary are removed.

## Dense and non-overlap evaluation

Primary outer prediction uses the frozen one-minute
decision grid.

Because adjacent decisions have overlapping 10-minute
future horizons, all discrimination metrics must also be
reported on deterministic:

`nonoverlap_10m`

consisting of decisions exactly ten minutes apart from
UTC midnight.

The non-overlap subset is diagnostic/protection against
overlapping-label inflation and also contains a frozen
incremental AUC gate below.

## Primary metrics

Report for R, RV, V, VOL, the falsification track, and
positive control where applicable:

- sample count;
- prevalence;
- ROC AUC;
- average precision;
- average precision / prevalence;
- Brier score;
- Brier skill score versus outer prevalence;
- log loss;
- top-decile precision;
- top-decile lift;
- top-quintile precision;
- top-quintile lift.

Report separately:

- each outer fold;
- BTC pooled outer predictions;
- ETH pooled outer predictions;
- pooled BTC+ETH outer predictions;
- deterministic nonoverlap_10m predictions.

Brier skill remains descriptive and is not independently
a promotion gate.

## Frozen primary promotion gates

`PREDICTABLE_INCREMENTAL_DVOL_SANDBOX`

requires every gate below to pass.

### Incremental discrimination

1. pooled:
   `AUC(RV) - AUC(R) >= +0.01`;

2. pooled:
   `AP(RV) - AP(R) >= +0.01` absolute;

3. pooled:
   `top_decile_precision(RV) >= top_decile_precision(R)`.

### Probability quality

4. pooled:
   `log_loss(RV) < log_loss(R)`;

5. pooled:
   `Brier(RV) < Brier(R)`.

### Calendar stability

6. at least 3 of 4 outer folds have:
   `AUC(RV) > AUC(R)`.

### Symbol stability

7. BTC pooled:
   `AUC(RV) > AUC(R)`;

8. ETH pooled:
   `AUC(RV) > AUC(R)`.

### Absolute sanity floors

9. pooled:
   `AUC(RV) >= 0.60`;

10. BTC pooled:
    `AUC(RV) >= 0.57`;

11. ETH pooled:
    `AUC(RV) >= 0.57`.

### Non-overlap

12. nonoverlap_10m pooled:
    `AUC(RV) - AUC(R) >= +0.01`;

13. nonoverlap_10m pooled:
    `AUC(RV) >= 0.57`.

### Falsification and integrity

14. the DVOL timing falsification gate below passes;

15. the positive-control sensitivity gate below passes;

16. all implementation, frozen-artifact, causality,
    common-support, fold, and August-seal invariants pass.

Failure of any primary gate means EXP007-P1 does not
establish incremental DVOL timing information.

No gate may be relaxed after outputs are opened.

## DVOL timing falsification

Construct:

`RV_V_TIME_PERMUTED`

as follows:

- preserve R exactly;
- preserve labels exactly;
- preserve common support exactly;
- preserve the complete ten-feature V vector as one unit;
- within each symbol/day, deterministically permute complete
  V vectors across decision times;
- do not permute individual V columns independently;
- do not mix symbols;
- do not mix days;
- perform separate deterministic permutations for each
  training day and each outer-test day;
- use seed `20260825`;
- fit the same frozen scaler/logistic pipeline.

This preserves each symbol/day's DVOL feature distribution
while destroying within-day temporal alignment.

Frozen timing gate:

`AUC(RV_REAL) - AUC(RV_V_TIME_PERMUTED) >= +0.01`

on pooled outer predictions.

If real DVOL fails to beat the time-permuted DVOL track by
at least 0.01 AUC, EXP007 cannot claim incremental
within-day timing information even if other metrics look
favorable.

The falsification track cannot rescue a failed primary
incremental gate.

## Positive control

Retain the forbidden future 10-minute executable-opportunity
magnitude canary used in prior experiments.

The canary is a pipeline-sensitivity control only.

It is never a legitimate predictor.

Frozen sensitivity requirement:

`AUC(CANARY_R) - AUC(R) >= +0.10`

on pooled outer predictions.

A positive-control PASS cannot rescue any failed primary
EXP007 gate.

A failed positive control invalidates interpretation of the
experiment implementation.

## Required implementation invariants

Before accepting any result:

1. exact EXP007-P0 result SHA must match;
2. exact frozen EXP006 DVOL raw hashes must match;
3. only the frozen supervised dates are used;
4. August is not opened;
5. latest DVOL candle used at time t is timestamped
   no later than t-60 seconds;
6. no DVOL lookback exceeds 30 minutes;
7. no missing DVOL is filled or interpolated;
8. R and RV training support are identical;
9. R and RV outer-test support are identical;
10. scaling is fit on training rows only;
11. chronological folds exactly match preregistration;
12. no outer label enters training;
13. direction is not scored;
14. trading PnL is not scored.

An invariant failure produces:

`INVALID`

rather than scientific PASS or FAIL.

## Possible final statuses

### PASS

`PREDICTABLE_INCREMENTAL_DVOL_SANDBOX`

All frozen primary gates and invariants pass.

Meaning:

the tested options-implied volatility representation
contains reproducible incremental information about
10-minute opportunity timing beyond R on the consumed
March-July sandbox.

This is not direction or profitability evidence.

### FAIL

`FAIL_DVOL_NO_INCREMENTAL_TIMING_INFORMATION`

At least one frozen primary gate fails while all scientific
and implementation invariants remain valid.

A valid failure remains a failure.

### INVALID

Leakage, seal violation, artifact mismatch, support mismatch,
fold error, causality error, or material implementation
failure invalidates the run.

## Diagnostic interpretation rule

V-only, VOL, individual DVOL feature behavior, per-symbol
cells, or isolated outer folds are diagnostic only.

They cannot rescue a failed primary RV result.

A favorable post-hoc subgroup or individual DVOL feature
requires a new experiment ID and new preregistration.

## Stop / no-rescue rule

If EXP007-P1 fails, do not rescue it by:

- changing the 24 bp threshold;
- changing the 10-minute horizon;
- removing a bad month;
- selecting only BTC or only ETH;
- changing C;
- changing logistic regularization;
- adding polynomial interactions;
- using XGBoost;
- using Random Forest;
- using LSTM;
- using Transformer models;
- changing the maximum DVOL lookback;
- adding options-chain features;
- adding skew or term structure;
- using threshold optimization;
- changing transaction-cost assumptions;
- scoring direction;
- opening August.

Any materially different hypothesis requires a new
experiment ID.

## Next step after PASS only

A PASS authorizes only a separately preregistered next
scientific stage.

It does not itself authorize live trading.

Direction and executable net economics must remain separate
from the present opportunity-timing claim.

August remains sealed unless and until a future protocol
explicitly preregisters its one-time independent validation.
