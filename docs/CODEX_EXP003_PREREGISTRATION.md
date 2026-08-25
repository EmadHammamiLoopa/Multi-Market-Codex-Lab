# CODEX-EXP-003 Preregistration

Status: **FROZEN BEFORE EXTERNAL MARKET-DATA ACQUISITION**

Date: 2026-08-25

Experiment ID: `CODEX-EXP-003`

Configuration SHA-256: `8e18432c593ea21fed73df57f60877bba388c346b846425b06f0e06e177b0171`

The exact executable freeze is the published 40-character Git `HEAD` reported in the pre-score handoff. It is intentionally not embedded in this tracked file because a commit cannot contain its own hash. Both acquisition and scoring require that full hash and refuse a mismatched or tracked-dirty worktree.

## Scientific state inherited from prior experiments

`CODEX-EXP-001` and `CODEX-EXP-002` are permanently closed scientifically valid failures. Nothing here rescues, retunes, reruns, or relabels them. Their results motivate a new source-of-information hypothesis while keeping Binance-futures execution and the cost hurdle unchanged.

No external January–July market file had been downloaded, previewed, ranged, hashed, or opened when this preregistration was written. No August market file may ever be opened under this research sequence.

## Hypothesis

For BTCUSDT and ETHUSDT, Binance Spot and Bybit linear-perpetual information received by the Tardis collector at least 500 ms before a Binance USDS-M futures decision adds enough incremental out-of-sample information beyond Binance-futures-only L2 to identify economically large executable moves after 8–12 bp round-trip costs.

Null: XALL fails any standalone gate or fails to beat X0 in both primary expectancy and total PnL.

Alternative: XALL passes every primary and diagnostic-suite gate and strictly beats measured X0 on identical decision support.

A PASS is sandbox, hypothesis-generating evidence only. It is not independent validation, a profitability claim, structural venue causation, or proof of a co-located deployable latency edge.

## Frozen data

- target/execution input: existing causal Binance USDS-M futures `FEATURES250` for `BTCUSDT` and `ETHUSDT`;
- external X1: Tardis `binance` exact `BTCUSDT`/`ETHUSDT`, `book_snapshot_5` and `trades`;
- external X2: Tardis `bybit` exact `BTCUSDT`/`ETHUSDT` linear perpetuals, same two data types;
- days: first UTC calendar day of January through July 2026 only;
- no OKX, other venue, other symbol, other date, other depth, native message, or replacement representation.

All external files are daily gzip CSVs split by `local_timestamp`. The frozen post-review request set has 56 files. Acquisition is forbidden until the pre-score commit has been published and reviewed.

## Timestamp contract

Primary decision cutoff is `c=t−500ms`, where `t` is the Binance-futures 250 ms decision timestamp. Eligibility and all source windows use only `local_timestamp`.

- primary delay: 500 ms;
- optimistic diagnostic: 250 ms, non-rescuing;
- extra-delay stress: 1,000 ms, non-rescuing;
- maximum current book age at decision: 2,000 ms;
- receipt gap over 2,000 ms: new continuity segment;
- equal book receipt timestamps: one atomic group, final file-order full state;
- exchange timestamp: audit only, never ordering, joining, anchoring, eligibility, or tie-breaking;
- every external feature row records source local timestamp, source age, validity, and source audit.

All 250 ms/1 s/3 s source returns and trade windows end at `c`. All anchors must remain inside one valid segment. No feature crosses a gap, invalid book, or UTC day boundary. No indefinite forward fill is permitted.

The causal claim is limited to recorded arrival ordering at the Tardis collector vantage; see `CODEX_EXP003_TIMESTAMP_AUDIT.md`.

## Frozen external features

Per source, in exact order:

1. mid return 250 ms, bp;
2. mid return 1 s, bp;
3. mid return 3 s, bp;
4. relative spread, bp;
5. OBI top one;
6. OBI top five;
7. signed trade-quantity imbalance 250 ms;
8. signed trade-quantity imbalance 1 s;
9. signed trade-quantity imbalance 3 s;
10. signed trade-count imbalance 250 ms;
11. signed trade-count imbalance 1 s;
12. signed trade-count imbalance 3 s;
13. realized volatility 3 s, bp;
14. source age, ms;
15. source return 250 ms minus Binance-futures return 250 ms;
16. source return 1 s minus Binance-futures return 1 s; and
17. source return 3 s minus Binance-futures return 3 s.

Quantities enter only dimensionless within-source ratios. No raw size, raw depth, funding, liquidation, basis, clock-latency correction, learned feature, or post-acquisition feature is allowed.

## Tracks and support

- `X0 =` Binance-futures L2 block.
- `X1 = X0 +` Binance Spot features.
- `X2 = X0 +` Bybit features.
- `XALL = X0 + X1-source + X2-source` and is the sole primary external track.

Every track uses the exact common support `base_L2_valid AND spot_valid AND bybit_valid`. X0 and XALL therefore score the same eligible rows. X1 and X2 are diagnostic source decompositions and cannot rescue XALL.

## Labels and execution

At a valid decision row `t`:

- entry is at `t+250ms`;
- long enters target ask and exits target bid;
- short enters target bid and exits target ask;
- horizons are 10 s and 30 s after entry;
- label is whether executable gross return minus 8 bp is strictly positive;
- separate balanced logistic models predict long and short labels;
- proposed action must meet the selected probability threshold and positive calibrated utility;
- if both sides qualify, greater calibrated utility wins; and
- greedy nonoverlap forbids a new action until reaction plus the selected holding horizon has elapsed.

No midpoint execution, passive execution, maker credit, partial fill, sizing, inventory optimization, or slippage rescue is part of this ID. The 8 bp primary and 12 bp stress envelopes are the frozen all-in friction assumptions.

Totals are cumulative net basis points across equal-notional actions, pooled across BTC and ETH. No price-dependent coin quantity or capital-sizing rule is fitted. “Total PnL” in the gates means this cumulative equal-notional bp total, not a dollar backtest.

## Model grid

- family: balanced `LogisticRegression`, `lbfgs`, fixed seed `20260825`;
- training-only NumPy standardizer;
- `C ∈ {0.1, 1.0}`;
- separate long/short models;
- Platt logistic calibration on base-model logits;
- horizons `{10, 30}` seconds;
- probability thresholds `{0.55, 0.65, 0.75, 0.85, 0.95}`;
- 20 combinations per track/fold;
- training-row stride 4; and
- at least 20 nonoverlapping inner-selection actions for configuration eligibility.

The best covered inner candidate is selected lexicographically by 8 bp expectancy, total, profit factor, shorter horizon, higher threshold, then smaller C. Inner economics may be negative so X0 remains measurable. This is a prospective EXP-003 comparison rule and does not revise EXP-001.

## Walk-forward

Five pooled calendar outer folds:

| Outer | Base training | Calibration/selection |
|---|---|---|
| 2026-03-01 | Jan 1 | Feb 1 |
| 2026-04-01 | Jan–Feb | Mar 1 |
| 2026-05-01 | Jan–Mar | Apr 1 |
| 2026-06-01 | Jan–Apr | May 1 |
| 2026-07-01 | Jan–May | Jun 1 |

The preceding day is split at its midpoint. Calibration labels ending at or after the midpoint are purged. The second half is inner selection. Base model/scaler never see calibration, selection, or outer rows; Platt calibration never sees selection or outer rows; configuration choice never sees outer rows. BTC and ETH models are fit separately, then their outer actions are pooled by calendar fold.

## Primary pass gates

All must be true:

1. XALL selects for both symbols in all five folds;
2. X0 selects for both symbols in all five folds;
3. at least four of five pooled calendar folds have positive 8 bp total;
4. pooled XALL 8 bp net expectancy is at least 1.0 bp/action;
5. pooled XALL 8 bp total is positive;
6. XALL profit factor is at least 1.25;
7. XALL total/max-drawdown is at least 2.0;
8. XALL 12 bp expectancy and total are both positive;
9. XALL has at least 100 nonoverlapping outer actions;
10. at least 55% of active UTC hours are positive;
11. no positive calendar fold contributes more than 40% of total positive-fold profit;
12. the worst calendar-fold loss is no worse than 50% of total positive-fold profit;
13. XALL 8 bp expectancy strictly exceeds X0; and
14. XALL 8 bp total strictly exceeds X0.

If X0 is not measured on every fold, incrementality is undefined and the experiment FAILS. Zero actions are not measured zero expectancy.

## Mandatory diagnostic suite

The primary verdict is not a final PASS until all diagnostic artifacts are produced by the frozen commit.

- 250 ms source delay: optimistic, report only, cannot rescue.
- 1,000 ms source delay: extra-delay stress, report only, cannot rescue.
- timestamp permutation: frozen within-day seed; counterfactual primary gates must not pass.
- sign placebo: fit/select on unmodified causal train/inner data, then reverse signed external features on XALL outer rows only; counterfactual primary gates must not pass.
- 60 s time placebo: lag external features without day wrap; counterfactual primary gates must not pass.
- source dropout: X1 and X2 results reported; neither can rescue.
- future-leak positive control: source access through `t+250ms` plus an explicitly named future 10 s target-return canary. Its best long/short mean outer ROC-AUC improvement over primary must be at least 0.02. The canary is excluded from primary artifacts and gates.

Final PASS requires both the primary gates and the diagnostic-suite gates. A placebo passing primary gates or an insensitive future canary invalidates final PASS. Diagnostic economics can never substitute for primary economics.

## Required tests before freeze

1. as-of join never selects a future local timestamp;
2. exact 500 ms delay;
3. stale source invalidation;
4. exchange timestamps cannot override local ordering;
5. label/calibration day purge;
6. no forward fill through an outage/gap;
7. quantity normalization is causal;
8. standardization is training-only;
9. sealed-date rejection before open;
10. no outer-day leakage;
11. 1,000 ms delay is stricter;
12. future access requires explicit canary mode;
13. timestamp/sign/time transforms leave X0 untouched; and
14. identical common support across tracks.

Only synthetic data may be used before the freeze.

## No-rescue and stop rules

After publication, no gate, delay, staleness rule, feature, source, date, representation, cost, model, hyperparameter, label, support mask, or diagnostic interpretation may change under this ID. Failed/missing data are not replaced. A primary FAIL is permanent. A technical invalidation may be repaired only under a new experiment ID and a new untouched dataset, never by rereading the consumed outer sample.

The required action after publishing the exact pre-score commit is **STOP FOR REVIEW**. No external market-data downloader or scoring command may run in the same pre-score phase.
