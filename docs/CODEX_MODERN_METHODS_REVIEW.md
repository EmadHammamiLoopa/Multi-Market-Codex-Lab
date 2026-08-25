# Modern Methods Review: Cost-Aware Multi-Market Microstructure

Review date: 2026-08-25  
Scope: primary research and implementation references published or materially revised in 2022--2026  
Decision context: historical research only; no live orders; August sealed periods remain untouched

## Bottom line

Recent research does not justify dropping a large Transformer into this project. Three findings are more relevant:

1. stationary order-flow representations generally transfer better than raw book states;
2. a simple MLP or LSTM is often difficult to beat once labels and evaluation are controlled;
3. forecasting metrics can remain impressive while executable profitability disappears.

For this repository, the information bottleneck and the cost bottleneck are more urgent than model capacity. The strongest first experiment is a simple, calibrated, cost-aligned taker policy on the existing Phase L features. Passive execution and multi-venue inputs are worthwhile follow-ups, but both require materially better execution/data assumptions.

## Evidence map

| Method or source | Claimed information advantage | Costs represented? | Data required | L3 / queue truth? | Convincing OOS evidence? | Main risk for this project | Compute / engineering |
|---|---|---|---|---|---|---|---|
| Deep order-flow imbalance | Stationary multi-level OFI instead of raw book levels; multi-horizon signal | Not a complete deployment-cost proof | Synchronized LOB updates and trades | No for the predictive feature | Strong statistical evidence across the study data; economic transfer still venue-specific | Repeating Phase L information with a new network | Low--medium |
| Alpha term-structure LSTM / seq2seq | Forecast the horizon profile jointly | Generally forecasting-oriented | Dense LOB sequences | No | Comparative evidence, but not a guarantee after current crypto costs | Model selection on a weak target | Medium |
| TLOB and modern LOB Transformers | Dual temporal/book attention; efficient long context | No complete executable proof in this repo's setting | Large normalized LOB tensor corpus | No | Broad benchmark comparison; authors also document temporal deterioration | Complexity, calibration drift, dataset shift | High |
| LOBFrame | Reproducible preprocessing, forecasting, and complete-transaction evaluation | Yes, through an operational trading metric/backtest layer | LOBSTER-style event data | Usually richer event data than Binance MBP | Explicitly exposes the forecasting-to-trading gap | Substantial adapter work; equity assumptions do not transfer directly | Medium--high |
| Calibrated selective prediction | Reliable probability/coverage trade-off and abstention | Only when labels/utilities include costs | Any supervised features plus a chronological calibration set | No | Methodologically appropriate; performance is application-specific | Tiny positive class and calibration drift | Low |
| hftbacktest queue/latency models | Replay maker decisions under configurable fill and latency assumptions | Fees, touch, latency, inventory can be modeled | MBP or MBO feed plus trades and latency assumptions | MBO preferred; MBP needs inferred queue | Sensitivity tool, not observed fill truth | False maker alpha from optimistic queue position/no impact | Medium |
| State-dependent fill models | Predict fill probability conditional on book/event state | Only if adverse selection and fees are also included | Order-level events and observed order outcomes | Usually yes or a close proxy | Good mechanism evidence; transfer requires own venue data | Phase L MBP cannot identify exact queue position | High data burden |
| Cross-exchange / cross-asset price discovery | Lead-lag and venue fragmentation may add information not in one book | Mixed; often not full HFT cost model | Time-aligned multi-venue trades/books, receipt times, staleness | No for taker; yes-ish for maker queue per venue | Evidence that venues/crypto assets share information, not proof of this policy | Timestamp alignment, fee fragmentation, API gaps | High engineering |
| Agent-based / neural LOB simulation | Counterfactual order placement and stress testing | Configurable | Calibrated event data | Often approximated | Useful for sensitivity, weak as primary profitability evidence | Simulator-realism gap and self-confirming alpha | Very high |

## 1. Order-flow representations

The [Deep Order Flow Imbalance paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3900141) argues that stationary order-flow inputs outperform raw LOB representations and that predictability is concentrated at short horizons. The [multi-level and cross-sectional OFI study](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4568641) reports incremental explanatory power from deeper levels and a smaller cross-sectional benefit. These are high-quality reasons to preserve Phase L's OFI/MLOFI design, not evidence that it clears Binance costs. Phase L already tested the core mechanism and found gross opportunities mostly below two or three basis points.

Decision: preserve stationary OFI, signed trade flow, spread, depth, resiliency, and staleness. Do not add more book levels or cross-sectional inputs until a cost-aligned target shows incremental net value.

## 2. Sequence models: simple baselines first

The [alpha term-structure study](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4770476) finds that comparatively simple LSTM baselines can be hard to beat when the task is controlled. [TLOB](https://arxiv.org/abs/2502.15757) proposes a specialized Transformer and, importantly, reports declining predictability and label-dependent deterioration over time. A broader [2024 benchmark of 15 models](https://link.springer.com/article/10.1007/s10462-024-10715-4) likewise reports a material drop on newer data.

Decision: a multi-horizon MLP/LSTM is a legitimate third experiment if simple cost-aligned models survive. It must be compared against linear/logistic and shallow-MLP baselines on identical folds. A Transformer has no priority until sample size, net labels, and drift controls justify its capacity.

## 3. Forecast accuracy is not trading value

The [LOBFrame paper](https://arxiv.org/abs/2403.09267) and its [open implementation](https://github.com/FinancialComputingUCL/LOBFrame) explicitly bridge forecasting and complete-transaction evaluation. This is directly relevant to the repository's history: positive R2 and directional cells did not survive executable scoring. LOBFrame is a useful reference architecture, but its LOBSTER/equity data assumptions and research license constraints mean it should be adapted conceptually rather than copied wholesale.

Decision: every candidate must output action-level net expectancy, opportunity count, profit factor, drawdown, turnover, coverage, and fold dispersion. Accuracy, AUC, R2, and calibration are diagnostics only.

## 4. Cost-aligned probabilistic decisions

Probability calibration is valuable only if it is chronological and the event being calibrated matches the decision. General calibration metrics are reviewed in the [JMLR calibration survey](https://www.jmlr.org/papers/v23/22-0658.html); [selective prediction under shift](https://proceedings.neurips.cc/paper_files/paper/2023/hash/4791edcba96fbd82a8962b0f790b52c9-Abstract-Conference.html) shows why coverage and abstention must be analyzed under changing distributions. More recent work on [time-series calibration under distribution shift](https://proceedings.mlr.press/v337/huang26b.html) reinforces that a held-out calibration period cannot be assumed permanent.

The first experiment therefore estimates, separately for long and short, the probability that the realized touch-to-touch payoff remains positive after frozen commission and safety margin. Calibration uses only a fold-local chronological calibration slice. The model may abstain. A reliability diagram and selective net-expectancy curve are mandatory, and no threshold may be chosen on an outer fold.

Decision: implement this now with logistic regression as the preregistered primary model. A shallow nonlinear model is a later ablation, not a rescue within the same result.

## 5. Fees and executable prices

Binance exposes authenticated USD-M futures commission rates through [`GET /fapi/v1/commissionRate`](https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/User-Commission-Rate); its documented example uses maker `0.0002` and taker `0.0004`. That example corresponds to 2 bp maker or 4 bp taker per side, before spread, slippage, latency, and adverse selection. An actual experiment must hash the authenticated response (with secrets removed) or explicitly label the public example as an assumption.

For a taker backtest, entry and exit are priced at future executable touches after frozen latency, not at the mid. The spread is therefore embedded. The primary additional commission assumption is 8 bp round trip, with 10 and 12 bp stress. These values are not tuned against results.

Decision: preserve the Phase L 8/12 bp economic discipline, add a 10 bp middle stress, and separate gross, spread, commission, and optional slippage in all reports.

## 6. Passive execution, queue models, and adverse selection

The [hftbacktest fill-model documentation](https://hft.readthedocs.io/en/latest/order_fill.html) correctly warns that market-data replay assumes the simulated order does not change the market. For market-by-price data it offers conservative RiskAverse and probabilistic queue models; its [latency model documentation](https://hft.readthedocs.io/en/latest/latency_models.html) separates feed, order-entry, and response latency. These are appropriate sensitivity tools, not ground-truth historical fills.

Recent work models [state-dependent fill probabilities](https://arxiv.org/abs/2403.02572), [time-varying fill probability with deep survival models](https://arxiv.org/abs/2306.05479), and [adverse-selection-aware fill simulation](https://arxiv.org/abs/2409.12721). Those methods need order outcomes or richer order-level data than Phase L's market-by-price history provides. Inferring queue position from displayed depth alone can turn non-fills into fictional profits.

Decision: the second experiment may test passive entries, but it must report a three-way sensitivity envelope: no passive credit, RiskAverse queue, and a preregistered probabilistic queue model. It needs maker fill ratio, time-to-fill, cancellation, post-fill markout, inventory, and taker fallback costs. It cannot be the first result because its key latent variable is unobserved in the current data.

## 7. Multi-market and multi-venue information

Evidence from [Coinbase limit orders and cross-exchange information](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4150979) supports the existence of fragmented price discovery. Research on [cross-cryptocurrency return predictability](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3974583) supports broader lead-lag structure, though at different horizons and without proving this HFT use case.

The missing information in Phase L may be venue leadership rather than model nonlinearity. A serious cross-venue design needs exchange event time and local receipt time, explicit per-venue staleness, comparable contract specifications, per-venue fees, and strict causal joins. Last-value forward fills without an age feature are disallowed. BTC and ETH features should be aligned by what was locally observable, not by rounded exchange timestamps.

Decision: pursue multi-venue BTC/ETH order flow after the cost-aligned single-venue experiment. Start with sparse lagged OFI/return features and permutation tests before any sequence network.

## 8. Simulation and the reality gap

A [2024 LOB simulation review](https://arxiv.org/abs/2402.17359) catalogs increasingly realistic learned and agent-based simulators. A newer [study of the simulation-to-reality gap](https://arxiv.org/abs/2603.24137) argues that profitability is highly sensitive to execution assumptions. Simulators are useful for stress tests and mechanism exploration, but a strategy discovered only inside a fitted simulator is not independent evidence.

Decision: use simulation only for queue/latency sensitivity and capacity stress. Historical replay remains the primary evidence source.

## Recommended research order

1. **CODEX-EXP-001:** calibrated executable-net taker classification on Phase L features; simple logistic model; explicit abstention.
2. **CODEX-EXP-002:** conservative passive adverse-selection filter with queue-model sensitivity, only if suitable historical raw events are available.
3. **CODEX-EXP-003:** causal cross-venue/cross-asset OFI baseline, followed by a small MLP/LSTM only when it adds stable outer-fold value.
4. Transformer or learned simulator work only after the earlier stages demonstrate an information advantage that survives costs.

## Falsification standard

A modern method is useful here only if, on identical chronological splits, it adds stable net expectancy at the frozen primary cost, retains nontrivial opportunities, has a confidence interval not dominated by one day, and does not depend on an optimistic latency or queue assumption. If it only improves AUC, R2, or gross returns, it is a research diagnostic rather than a strategy improvement.
