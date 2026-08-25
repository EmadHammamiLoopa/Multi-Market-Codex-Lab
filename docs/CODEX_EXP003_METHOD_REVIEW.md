# CODEX-EXP-003 Method Review

Status: **PROCEED TO PRE-SCORE FREEZE WITH NARROW CAUSAL CLAIM**

## Research question

Do Binance Spot and Bybit linear-perpetual top-five book/trade features, observed at least 500 ms before a Binance USDS-M futures decision, add incremental out-of-sample information about executable 10 s or 30 s BTCUSDT/ETHUSDT moves beyond the existing Binance-futures-only L2 feature block?

This is a new information-source hypothesis. It does not reopen either closed experiment:

- `CODEX-EXP-001` remains a valid FAIL for the frozen single-venue taker formulation.
- `CODEX-EXP-002` remains a valid FAIL for the frozen conservative passive-entry formulation.

No EXP-001/002 label, threshold, cost, or result is changed. EXP-003 retains the target venue and economic hurdle while adding prospectively specified external inputs.

## External evidence review

The published literature makes venue leadership plausible but emphatically not guaranteed.

- Brandvold et al. document dynamic, time-varying price discovery across Bitcoin exchanges rather than a permanent leader ([Journal of International Financial Markets, Institutions and Money, 2015](https://doi.org/10.1016/j.intfin.2015.02.010)).
- Baur and Dimpfl find spot leading early regulated futures and attribute this partly to liquidity and trading-hour differences ([Journal of Futures Markets, 2019](https://doi.org/10.1002/fut.22004)).
- Alexander and Heck find unregulated crypto derivatives dominating regulated futures and US spot markets in a multivenue setting ([Journal of Financial Stability, 2020](https://doi.org/10.1016/j.jfs.2020.100776)).
- Frino et al. show that conclusions can reverse with sampling frequency, noise adjustment, contract choice, and window choice; at one-second sampling their futures market generally leads, with leadership varying by day and information event ([Journal of Futures Markets, 2025](https://doi.org/10.1002/fut.22560)).
- A 2025 high-frequency Bitcoin spot/futures study uses Hayashi–Yoshida lead-lag methods specifically because sparse asynchronous observations can distort conventional measures ([Journal of International Money and Finance, 2025](https://doi.org/10.1016/j.jimonfin.2025.103415)).
- Recent sub-second Binance evidence finds permanent-price information concentrated in 100 ms trading activity, supporting the need for explicit millisecond endpoints rather than coarse resampling ([Economics Letters, 2026](https://doi.org/10.1016/j.econlet.2026.113026)).
- More generally, Huth and Abergel show that regular sampling of assets updating at different speeds can create misleading high-frequency lead-lag conclusions ([Journal of Empirical Finance, 2014](https://doi.org/10.1016/j.jempfin.2014.01.003)), and recent work reports material price-discovery bias from asynchronous updates ([Emerging Markets Review, 2025](https://doi.org/10.1016/j.ememar.2025.101307)).

These studies justify testing cross-venue information, not expecting it to pass. They also motivate receipt-time as-of joins, explicit source age, common support, and an economic rather than purely statistical endpoint.

## Mechanism

The falsifiable mechanism is that a liquid related venue incorporates some order-flow or price information before the local Binance-futures L2 state fully reflects it. A 500 ms-old external return, imbalance, or volatility state could therefore change the ranking of economically large future moves after conditioning on current Binance-futures features.

The mechanism is not “cross-exchange correlation.” XALL must:

1. survive the same 8/12 bp executable economics as X0;
2. have enough nonoverlapping actions and calendar/hour stability;
3. beat X0 on both primary expectancy and total PnL on identical eligible rows; and
4. fail to look equally good under temporal/sign placebos.

Common news is not excluded. If an earlier external receipt is useful after conditioning on X0, it is incremental predictive information at the collector vantage whether the innovation originated in that venue or in common news. The study does not claim structural venue causation.

## Design choice: representation

Primary external data are uniformly `book_snapshot_5 + trades` for both sources, both symbols, and all dates. This is preferable to incremental L2 for the first cross-venue experiment because it freezes the same normalized top-five representation and avoids venue-specific reconstruction code. Tardis says the snapshots are reconstructed from real-time L2 whenever the tracked levels change and uses one normalized schema across exchanges.

The cost is that downloadable CSVs omit disconnect messages and expose only top five. Those limitations are addressed by conservative segment/staleness invalidation and a narrow claim; they are not repaired by switching sources or formats after inspection.

## Frozen feature set

Each external source contributes 17 features:

- mid log returns in bp over 250 ms, 1 s, and 3 s;
- relative spread in bp;
- top-one and top-five order-book imbalance;
- signed trade-quantity imbalance over 250 ms, 1 s, and 3 s;
- signed trade-count imbalance over the same windows;
- 3 s realized volatility in bp;
- source receipt age in ms; and
- source return minus the Binance-futures return over 250 ms, 1 s, and 3 s.

Raw amounts, raw depth, contract multipliers, basis levels, funding, liquidations, cross-asset features, and learned representations are excluded. Quantity ratios are within-source and dimensionless. All features are computed before modeling and carry source local timestamp, age, and validity.

## Tracks

- **X0:** existing Binance-futures L2 block only.
- **X1:** X0 + Binance Spot.
- **X2:** X0 + Bybit linear perpetual.
- **XALL:** X0 + both sources; the sole primary external-information track.

All tracks use the exact XALL common-support mask. This prevents an outage or stale source from changing the sample when comparing X0 with XALL. X1/X2 explain source contribution but cannot rescue XALL.

## Model and objective

The model remains deliberately low capacity:

- separate long and short balanced logistic classifiers;
- training-only standardization;
- `C ∈ {0.1, 1.0}`;
- Platt calibration on the purged first half of the immediately preceding day;
- horizons `{10 s, 30 s}`;
- probability thresholds `{0.55, 0.65, 0.75, 0.85, 0.95}`;
- probability plus calibrated positive-utility requirement;
- 250 ms target reaction before entry;
- bid/ask executable returns, not mid returns; and
- greedy nonoverlap over entry plus holding horizon.

Pooled totals sum net basis points for equal-notional actions across BTC and ETH. This prevents price level from becoming an implicit sizing rule; no dollar-capital claim is made.

There is no tree, neural model, interaction search, per-source hyperparameter, latency tuning, feature selection, or post-result threshold change.

EXP-003 makes one prospective selection change relative to EXP-001: a covered inner configuration may be promoted even when its inner economics are negative. This avoids censoring the X0 outer comparator and permits an actual incremental comparison. The minimum of 20 inner nonoverlapping actions remains mandatory, and outer gates remain strictly economic. This new rule applies only to EXP-003 and does not amend or rescue EXP-001.

## Walk-forward and leakage control

There are five calendar outer folds: March through July. For each symbol and track:

- base training uses all earlier days except the immediately preceding day;
- the preceding day is divided into purged calibration and inner-selection halves;
- training labels are subsampled at the frozen stride;
- the scaler and base logistic fit only base-training rows;
- Platt calibration and payoff means use only the calibration slice;
- model/horizon/C/threshold selection uses only the selection slice; and
- the outer day is touched once after selection.

Both BTCUSDT and ETHUSDT must produce X0 and XALL configurations in every calendar fold. Outer economics are pooled across symbols by calendar day to preserve the requested five-fold stability interpretation.

## Economic gates

XALL must satisfy all frozen gates simultaneously:

- XALL selected for both symbols in all five folds;
- X0 measured for both symbols in all five folds;
- at least four of five pooled calendar folds positive at 8 bp;
- pooled net expectancy at least 1.0 bp/trade at 8 bp;
- positive pooled total at 8 bp;
- profit factor at least 1.25;
- PnL/max-drawdown at least 2.0;
- positive expectancy and total at 12 bp;
- at least 100 nonoverlapping outer actions;
- at least 55% positive active hours;
- no positive calendar fold contributes more than 40% of total positive-fold profit;
- worst fold loss no worse than 50% of total positive-fold profit; and
- XALL strictly exceeds X0 in both 8 bp expectancy and total PnL.

No p-value, accuracy, AUC, calibration score, X1 result, X2 result, 250 ms delay, future canary, or favorable cost case can substitute for a failed economic gate.

## Alternatives rejected for this ID

- **More expressive model:** does not change the information mechanism and raises overfit risk.
- **OKX primary source:** different 2026 collector topology; new hypothesis.
- **Exchange-time synchronization:** exchange timestamps are not receipt times and can regress.
- **Source-specific latency correction estimated from January–July:** would tune alignment on consumed performance data.
- **Incremental L2 on one venue and snapshots on another:** representation confound.
- **Cross-venue basis/funding/liquidation features:** expands mechanisms and search space.
- **Passive execution:** already tested and closed under EXP-002.

## Review conclusion

The method is suitable for a frozen, hypothesis-generating sandbox experiment after the exact commit is published. Its strongest defensible conclusion is incremental information under a documented provider receipt-time policy. No external market file should be acquired until that commit and final pre-score review are complete.
