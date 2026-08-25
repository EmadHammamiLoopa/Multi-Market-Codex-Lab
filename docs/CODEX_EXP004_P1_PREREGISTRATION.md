# CODEX-EXP-004-P1 Preregistration

Status: **PREREGISTERED BEFORE ANY P1 MODEL OUTPUT**

Date: 2026-08-25

Experiment ID: `CODEX-EXP-004-P1`

## Question

`CODEX-EXP-004-P0` established that 10 minutes is the shortest preregistered fixed horizon with sufficiently distributed executable economic headroom. P1 asks one narrower question:

> Can causally available information at decision time rank the probability that a >=24 bp executable fixed-horizon opportunity will occur over the next 10 minutes?

P1 does **not** predict trade direction and does not claim trading profitability.

## Frozen target

At each eligible decision time `t`:

- reaction/entry = `t + 250 ms`;
- exit = entry + 600 s;
- `long_gross_bps = 10000*log(bid_exit/ask_entry)`;
- `short_gross_bps = 10000*log(bid_entry/ask_exit)`;
- `oracle_gross_bps = max(long_gross_bps, short_gross_bps)`;
- primary binary label = `1[oracle_gross_bps >= 24]`.

The oracle is used only to define whether an economically meaningful opportunity occurred. Direction is not exposed to the model and is not scored as a trade.

## Data

- BTCUSDT and ETHUSDT Binance USD-M Futures.
- Existing immutable Phase-L `FEATURES250` files only.
- First UTC day of January through July 2026 only.
- Exact file hashes must match the previously frozen EXP001 provenance.
- No new downloads.
- No Binance Spot/Bybit external features.
- No OI, funding, basis, liquidation, options, macro, on-chain, or news data.
- August remains sealed.

## Decision grid

- Decisions every 60 seconds from UTC midnight.
- Labels whose entry/exit would cross a UTC day boundary are invalid.
- Feature construction may use only observations at or before the decision timestamp.
- Every rolling feature must have a complete causal lookback and must not forward-fill through invalid book state.

## Frozen feature tracks

### Track R — regime state, primary

Derived only from the target market's historical state at or before `t`:

1. log mid returns over 1m, 3m, 5m, 10m, 30m;
2. absolute returns over the same lookbacks;
3. realized volatility from 1-minute returns over 5m, 15m, 30m;
4. current spread bps;
5. trailing 1m and 5m mean spread bps;
6. 5m, 15m, 30m mid-price range in bps;
7. current normalized position inside the 5m, 15m, 30m trailing mid range.

### Track RL2 — regime plus L2 support, secondary prespecified track

All Track-R features plus:

1. current microprice-minus-mid bps;
2. current OBI L1/L5/L10;
3. current OFI L1 1s and 3s;
4. current MLOFI L5 1s and 3s;
5. current trade quantity imbalance 1s and 3s;
6. current trade count imbalance 1s and 3s;
7. current bid/ask depth L5 log quantities;
8. trailing 1-minute mean and standard deviation of OBI L5;
9. trailing 1-minute mean and standard deviation of OFI L1 1s;
10. trailing 1-minute mean and standard deviation of trade quantity imbalance 1s.

No feature may be added after scoring starts.

## Models

For each symbol and track separately:

- `StandardScaler`, fit on training data only;
- `LogisticRegression`;
- `C = 1.0` fixed;
- L2 penalty;
- solver `lbfgs`;
- `class_weight = None`;
- `max_iter = 1000`;
- deterministic random seed where applicable: `20260825`.

There is no hyperparameter grid and no post-hoc model selection.

## Chronological outer folds

Five frozen outer folds:

1. outer March 1; train January 1 and February 1;
2. outer April 1; train January 1 through March 1;
3. outer May 1; train January 1 through April 1;
4. outer June 1; train January 1 through May 1;
5. outer July 1; train January 1 through June 1.

Training labels that cross a training-day boundary are removed. No outer-day observation participates in scaling or fitting.

Because source days are separated by approximately one month, cross-day label overlap does not occur. Within each day the dense 1-minute observations may have overlapping 10-minute labels; inference metrics must therefore also be reported on a deterministic `nonoverlap_10m` subset consisting of decisions exactly 10 minutes apart from UTC midnight.

## Baselines

Every model is compared against:

1. unconditional outer prevalence;
2. a volatility-only scalar baseline using trailing 30-minute realized volatility, fit as the same fixed logistic model.

The primary scientific comparison is whether Track R contains stable incremental information beyond prevalence and the volatility-only baseline. RL2 is a prespecified incremental-information diagnostic and may establish that microstructure adds information, but it cannot retroactively change P0 or any previous experiment.

## Metrics

Report separately for BTC, ETH, each outer fold, and pooled out-of-sample predictions:

- prevalence;
- ROC AUC;
- average precision / PR AUC;
- Brier score;
- Brier skill score versus prevalence forecast;
- log loss;
- top-decile precision;
- top-decile lift versus prevalence;
- top-quintile precision and lift;
- calibration intercept/slope as diagnostics only;
- all the same rank metrics on `nonoverlap_10m` where sample size permits.

No trading PnL is computed in P1 because direction is intentionally absent.

## Frozen primary PASS gates for Track R

Track R is `PREDICTABLE_SANDBOX` only if **all** of the following hold on pooled outer predictions and fold stability:

1. pooled ROC AUC >= 0.60;
2. pooled average precision >= 1.30 x pooled prevalence;
3. pooled Brier skill score > 0 versus the prevalence forecast;
4. pooled top-decile lift >= 1.50 x prevalence;
5. at least 4 of 5 outer calendar folds have ROC AUC > 0.55;
6. at least 4 of 5 outer calendar folds have top-decile lift > 1.0;
7. both BTC and ETH pooled ROC AUC >= 0.57;
8. both BTC and ETH pooled top-decile lift >= 1.25;
9. `nonoverlap_10m` pooled ROC AUC >= 0.57;
10. `nonoverlap_10m` pooled top-decile lift >= 1.25.

If any primary gate fails, Track R fails.

## RL2 incremental gate

RL2 is considered incrementally informative only if it independently satisfies all Track-R absolute PASS gates **and**:

- pooled ROC AUC exceeds Track R by at least 0.01;
- pooled average precision exceeds Track R by at least 0.01 absolute;
- pooled top-decile precision is not lower than Track R.

If R passes and RL2 does not beat it, the simpler R track remains preferred.

If R fails but RL2 independently passes all absolute gates and all incremental gates, P1 may be labeled `PREDICTABLE_SANDBOX_RL2_ONLY`; this is allowed because RL2 was preregistered before scoring. It still does not authorize direction or live validation.

## Falsification controls

Before final interpretation, run prespecified diagnostics on the same outer folds:

1. **time permutation placebo:** permute training labels within symbol/day using seed 20260825; real Track-R pooled ROC AUC must exceed placebo by >=0.03;
2. **future positive-control canary:** add the forbidden future 10-minute absolute executable opportunity magnitude as a single feature; pooled ROC AUC must improve by >=0.10 over real Track R. This is sensitivity evidence only and never trading evidence;
3. **feature sign diagnostic:** invert all signed momentum/flow features after fitting; it must not improve every primary discrimination metric simultaneously.

Diagnostics cannot rescue a failed primary run.

## Interpretation

Possible final statuses:

- `PREDICTABLE_SANDBOX_R` — Track R passes all frozen gates;
- `PREDICTABLE_SANDBOX_RL2_ONLY` — R fails but preregistered RL2 passes all absolute and incremental gates;
- `FAIL_OPPORTUNITY_NOT_PREDICTABLE` — neither eligible track passes;
- `INVALID` — leakage, provenance, seal, schema, or execution invariants fail.

A predictive PASS means only that opportunity occurrence is rankable on consumed sandbox data. It is not a profitable strategy.

## Stop/no-rescue rule

If P1 fails, do not rescue this experiment ID with:

- a different 10-minute threshold;
- a different horizon;
- XGBoost/LightGBM/Random Forest/deep learning;
- probability-threshold search;
- direction labels;
- new markets;
- new external data;
- OI/funding/basis/liquidations;
- lower transaction-cost assumptions;
- opening August.

Any genuinely new information source becomes a separately preregistered experiment.

## Next step only after P1 PASS

Only after a P1 predictive PASS may the project preregister a directional/value stage for the selected opportunities. The direction stage must be judged on executable net economics at 8 bp primary and 12 bp stress and must remain separate from the P1 opportunity-detection claim.
