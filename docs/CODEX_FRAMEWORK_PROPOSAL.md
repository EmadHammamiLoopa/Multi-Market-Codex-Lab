# Codex Framework Proposal

Version: 1.0  
Status: architecture frozen for `CODEX-EXP-001`  
Evidence scope: sandbox only; no August data may be opened

## Objective

The system should choose the action with the highest conservative expected **net** economic value, subject to uncertainty, overlap, capacity, and risk constraints. Predictive accuracy is a diagnostic. `NO_TRADE` is the default and a first-class action.

```text
causal market state
        |
        v
signal engine: action-conditioned outcome distributions
        |
        v
execution engine: touch, fee, latency, slippage/fill assumptions
        |
        v
decision engine: calibrated net utility + abstention
        |
        v
risk/opportunity engine: overlap, concentration, inventory, capacity
        |
        v
NO_TRADE | TAKER_LONG | TAKER_SHORT | PASSIVE_BID | PASSIVE_ASK
```

The interfaces are action-based so a forecasting model cannot silently own execution assumptions.

## Core components

### Signal engine

Inputs are causal, locally observable features with an explicit timestamp and staleness. Each model outputs an `ActionForecast` rather than a direction alone:

- probability of positive net payoff for the proposed action;
- expected gross and net basis points when estimable;
- lower-tail or uncertainty estimate;
- horizon, feature time, and validity flag;
- calibration version and training-period identity.

The first implementation uses separate binary long/short sufficient-move classifiers. Later distributional models may estimate payoff bins or quantiles, but must retain this interface.

### Execution engine

The engine maps a signal timestamp to executable outcomes without future-aware decisions.

For taker actions:

- reaction latency: 250 ms primary;
- long entry at ask, exit at future bid;
- short entry at bid, exit at future ask;
- commission: 8 bp round trip primary, 10 and 12 bp stress;
- spread embedded in touch-to-touch returns;
- optional extra slippage reported separately, never hidden in the label.

For passive actions, a later engine must model order-entry/response latency, queue position, partial fill, cancellation, inventory, maker commission, and post-fill adverse selection. `touch = fill` is forbidden.

### Decision engine

The decision engine compares all available actions with `NO_TRADE = 0`. An action is eligible only if:

- its fold-local calibrated probability exceeds a frozen threshold;
- its expected net utility is positive under the primary assumptions;
- model, feature, book, and staleness checks are valid;
- uncertainty and risk gates pass.

For each side, expected net utility is reconstructed from its calibrated positive probability and fold-local positive/nonpositive payoff means. When long and short are both eligible, the higher expected utility wins; ties abstain. Thresholds are selected inside a chronological inner selection slice and then frozen for the outer day.

### Risk and opportunity engine

This layer enforces non-overlapping positions, one action per symbol, concentration limits, maximum exposure, and capacity checks. Research reports include opportunities/day, active-day fraction, hour concentration, tail loss, turnover, max drawdown, and PnL/maxDD. It cannot force a quota. The eventual aspiration of 20--40 good opportunities/day across markets is descriptive, never a promotion gate.

### Experiment and evidence layer

Every run records:

- experiment ID and parent hypothesis;
- code commit and dirty-tree state;
- immutable config and SHA-256;
- input file names, sizes, and SHA-256;
- exact train/calibration/selection/evaluation periods;
- package/runtime versions and hardware;
- status (`PASS`, `FAIL`, `INVALID`, or `NOT_RUN`);
- complete metrics and failure reason.

No output file is silently overwritten. A material hypothesis change receives a new ID.

## Candidate architecture 1: calibrated executable-net classifier

### Hypothesis

Phase L failed partly because it optimized future-mid squared error and only later imposed executable economics. A classifier trained on whether long or short touch-to-touch payoff exceeds frozen taker cost may rank the rare sufficient moves better. Calibration plus abstention may improve the high-confidence subset without manufacturing trades.

### Information advantage

No new raw information is claimed. The advantage is objective alignment: OFI/MLOFI, trade flow, spread, depth, and resiliency are asked to discriminate outcomes that are actually worth trading. This isolates whether the failure was target/loss mismatch rather than missing data.

### Evidence

Modern LOB research supports stationary order flow, while calibration/selective-prediction work supports probability-aware abstention. LOBFrame demonstrates why operational transaction metrics must accompany forecasts. The repository's own Phase L postmortem supplies the counterevidence: gross edge is small, so this experiment is expected to be difficult to pass.

### Data and execution

Use the existing BTCUSDT/ETHUSDT Phase L `FEATURES250.csv` files for 2026-01-01 through 2026-07-01 only. Use L0 as a comparator and L2 as the primary feature block. Taker/taker touch execution, 250 ms latency, 8/10/12 bp round-trip commission scenarios, 10 s and 30 s horizons, and non-overlapping decisions are frozen.

### Overfitting risk

High. The months are consumed sandbox data and the positive label is rare. Mitigations are a tiny model grid, time-separated calibration and selection halves, deterministic training stride, frozen thresholds, five outer development folds, full failed-result retention, and no August access. Even a pass is sandbox progress, not validation.

### Compute

Low to medium. Standardized logistic models fit on a deterministic 1-second training stride; inference remains at 250 ms. CPU and 32 GB RAM are sufficient. GPU use is unjustified.

### Why it may overcome prior failure

It directly tests the most plausible correctable flaw in Phase L: target and selection mismatch. If it fails, more capacity on the same single-venue information is unlikely to help enough.

## Candidate architecture 2: passive fill/adverse-selection policy

### Hypothesis

The measured microstructure edge may be real but too small for taker/taker execution. A passive entry, admitted only when fill probability is adequate and conditional adverse selection is low, may improve net economics.

### Information advantage

Queue depletion, OFI, recent aggressive flow, spread, replenishment, microprice, and short-horizon volatility may jointly indicate both fill chance and post-fill markout. The economic advantage comes from avoiding one taker crossing and possibly receiving a maker rate, not from predicting a larger price move.

### Data and execution

Prefer full event-level L2 plus trades with local timestamps; observed own-order outcomes or L3/MBO would be substantially better. Market-by-price replay requires a conservative queue-model sensitivity envelope. Primary evaluation must include RiskAverse queue assumptions, order entry/response latency, cancellations, partial fills, timeouts, taker fallback, inventory, and adverse markout.

### Overfitting risk

Very high because queue position is latent in MBP data. An optimistic probabilistic queue model can manufacture profit. The method is rejected if profitability disappears under RiskAverse/no-passive-credit cases or if one queue parameter determines the result.

### Compute

Medium to high. Event replay is I/O-heavy; GPU is not the bottleneck. hftbacktest is a useful implementation reference.

### Why it may overcome prior failure

It attacks the demonstrated cost bottleneck directly. It is ranked second because the necessary fill truth is weaker than the existing taker outcome truth.

## Candidate architecture 3: causal cross-venue, multi-horizon sequence model

### Hypothesis

The missing edge may be information that arrives first on another liquid venue or correlated contract. A causal model of Binance plus one or two leading BTC/ETH venues may identify price discovery before it reaches the execution venue.

### Information advantage

Lagged stationary OFI, signed trade flow, returns, spread, and staleness across venues can encode leadership and liquidity migration. Joint horizons can distinguish fleeting book pressure from moves likely to exceed cost.

### Data and execution

Requires synchronized multi-venue books/trades with exchange and local receipt timestamps, contract normalization, per-venue fee schedules, outage/staleness flags, and a causal as-of join. Start with sparse linear/logistic features. Only then compare a small MLP/TCN/LSTM. Execute and score on one frozen venue first.

### Overfitting risk

High. Clock errors, forward-filled stale quotes, venue selection, and many lag/horizon choices create false lead-lag. Controls include artificial delay tests, timestamp permutations, stale-feature ablations, venue-dropout tests, and family-level multiple-testing correction.

### Compute

High data engineering, medium model compute. The RTX 5090 is useful only for the later sequence-model comparison after the linear baseline establishes incremental information.

### Why it may overcome prior failure

Unlike another nonlinear Phase L model, it adds a genuinely new information source. It ranks third because the required historical dataset is not currently committed and should not be collected prospectively before historical progress is shown.

## Exact first experiment: CODEX-EXP-001

### Frozen question

On the consumed January--July Phase L sandbox, does a fold-local calibrated logistic classifier of positive executable net payoff improve stable outer-fold economics over a static-book comparator at realistic taker cost?

### Inputs

- symbols: BTCUSDT, ETHUSDT;
- dates: first day of each month, 2026-01-01 through 2026-07-01;
- primary features: Phase L L2 (L0 + OFI/MLOFI/trade flow + resiliency/interactions);
- comparator: Phase L L0 static book;
- no cross-market features;
- no August paths or dates.

### Labels

At feature time `t`, entry is the observable touch at `t + 250 ms`; exit is the touch after a frozen 10 s or 30 s holding horizon. Define:

```text
long_gross_bps  = 10,000 * log(exit_bid / entry_ask)
short_gross_bps = 10,000 * log(entry_bid / exit_ask)
long_positive   = long_gross_bps  - 8 > 0
short_positive  = short_gross_bps - 8 > 0
```

Rows crossing an invalid book state or day boundary are excluded. Training examples use a deterministic four-row (1 s) stride to reduce redundant overlapping labels and compute cost. Boundary-crossing examples are purged.

### Models and calibration

- standardized logistic regression, `class_weight=balanced`, deterministic solver;
- regularization `C in {0.1, 1.0}`;
- independent long and short models;
- the first half of the inner validation day calibrates base logits with Platt scaling;
- the second half selects the configuration and probability threshold;
- thresholds `{0.55, 0.65, 0.75, 0.85, 0.95}`;
- no outer-fold refit or threshold tuning.

If a calibration half contains only one class, the configuration is invalid. Calibration and selection halves are separated by an embargo of latency plus horizon.

### Walk-forward

For each outer evaluation day March through July:

1. base training uses complete earlier days except the immediately preceding day;
2. the preceding day is divided chronologically into calibration and selection halves;
3. configuration/threshold must pass inner selection at both 8 and 12 bp with at least 20 trades;
4. the frozen model/calibrator/configuration is scored once on the outer day;
5. if no configuration passes, the outer action is `NO_TRADE` and the fold is a recorded failure.

L0 and L2 tracks are selected independently. L2 is the candidate; L0 is the comparator.

### Outer metrics

For 8, 10, and 12 bp: trades, gross/net expectancy, total net PnL, PF, max drawdown, PnL/maxDD, active hours, positive active-hour fraction, tail losses, long/short mix, and concentration. For probability quality: Brier score, log loss, ECE, reliability bins, class prevalence, and coverage. Also report per-day results and latency sensitivity at 250/500/1000 ms as a diagnostic without retuning.

The first implementation freezes 250 ms as primary. Latency sensitivity beyond 250 ms may be added only as a read-only scoring ablation under the same model.

### Sandbox pass gate

All conditions are required for L2:

- a valid selected configuration in all five outer folds;
- at least 4/5 positive-expectancy folds at 8 bp;
- pooled expectancy at least +1.0 bp/trade and total PnL positive at 8 bp;
- PF at least 1.25 and PnL/maxDD at least 2.0 at 8 bp;
- pooled expectancy and total PnL positive at 12 bp;
- no fold worse than -2.0 bp/trade at 8 bp;
- at least 100 total trades and positive active-hour fraction at least 0.55;
- L2 pooled expectancy and total PnL both exceed L0;
- no single day contributes more than 50% of positive gross profit;
- calibration diagnostics are finite and emitted for every scored fold.

These are development gates, not a profitability claim. Gates will not be weakened after the result.

### Stop rule

If `CODEX-EXP-001` fails, retain the result and do not rescue it with a nonlinear model on the same labels in the same experiment. Diagnose failure by signal, calibration, coverage, cost, and stability. Any material alteration becomes `CODEX-EXP-002` or later. If it passes, stop tuning and preregister several genuinely new historical periods before acquiring or opening them.

## Hardware decision

No local LLM or GPU is needed for the first experiment. An LLM critique would be opinion rather than evidence, and logistic fitting is CPU-appropriate. GPU work becomes reasonable only for the third architecture after data/linear baselines pass. This keeps compute proportional to the hypothesis.
