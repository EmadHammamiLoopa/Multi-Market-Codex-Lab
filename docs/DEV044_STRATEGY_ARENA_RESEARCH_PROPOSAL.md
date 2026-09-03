# DEV044 — Strategy Arena Research Proposal

Status: `RESEARCH_PROPOSAL_ONLY_NO_DATA_OPEN_NO_PNL`

Date: 2026-09-03

## 1. Project objective

This is a personal investment/profitability R&D project, not an academic
publication project.

The purpose of DEV044 is to stop treating "direction prediction" as a single
model-selection problem and instead compare a finite universe of complete
trading policies using executable net economic outcomes.

The core question is:

> Which fixed, causal short-horizon strategy families produce robust executable
> net profit after realistic spread, fees, latency, and risk constraints?

The primary objective is not classification accuracy. It is profitable,
repeatable, executable behavior.

## 2. Why DEV044 is genuinely different from DEV032 and DEV043

DEV032 already screened a broad universe of microstructure feature/model
representations. Repeating another 30-50 feature blocks would be wasteful.

DEV043 established an asymmetric result:

- event occurrence / TOUCH signal exists;
- conditional LONG/SHORT direction signal was not established by the frozen
  PRICE / PRESSURE / combined-HGB family.

DEV044 therefore evaluates complete strategy rules directly.

Each strategy must define:

- when a signal exists;
- LONG / SHORT / ABSTAIN logic;
- any regime condition;
- entry semantics;
- exit semantics;
- cooldown / flat-only behavior;
- cost model;
- risk limits.

The tournament is judged on executable PnL, not AUC or balanced accuracy.

## 3. Research principles for a personal-profit project

DEV044 is allowed to iterate on already-consumed development data.

It is NOT required to preserve academic one-shot protocol rules for every
development run.

However, because real capital is the eventual target, the following protections
remain economically necessary:

- strict causal feature construction;
- no look-ahead;
- realistic bid/ask execution;
- latency accounting;
- real fee accounting;
- explicit slippage stress;
- blocked / chronological validation;
- data-snooping controls when comparing many strategies;
- independent replication before capital deployment;
- no leverage during discovery.

The purpose of these controls is not publication quality. It is to reduce the
chance of deploying an overfit strategy.

## 4. Strategy Arena structure

Two execution divisions are proposed.

### Division T — directional / taker strategies

Primary research target:

`H1800_B32`

Primary execution shell:

- BTCUSDT
- 60-second decision cadence
- causal state only
- +250 ms executable entry
- LONG entry at ask
- SHORT entry at bid
- symmetric +/-32 bp barrier handling
- forced exit at 1800 s if neither barrier completes the trade
- +250 ms response latency for executable exit
- FLAT_ONLY
- fixed normalized notional
- no leverage
- no pyramiding
- no martingale
- no confidence sizing in Wave 1

The first tournament uses the same execution shell for all T strategies so the
ranking primarily reflects signal quality rather than exit optimization.

### Division M — passive / maker strategies

Maker strategies must NOT be evaluated with the existing simple taker
execution engine.

They require a queue-aware, latency-aware market-replay simulator.

Preferred implementation reference:

`hftbacktest`

Secondary implementation reference:

`NautilusTrader`

Maker results are ranked separately from taker results until the fill/queue
model has been validated.

## 5. Division T candidate universe

Exactly 16 core strategy mechanisms are proposed.

Each core is evaluated in two versions:

- `U` = ungated;
- `A` = opportunity-gated by the frozen Stage-A A0 TOUCH predictor.

Initial A-gate recommendation:

`A0 p_touch >= 0.50`

This creates 32 complete directional strategy candidates.

The gate value is provisional until the final DEV044-T design freeze. It should
not become a large threshold sweep.

### T01 — Multi-scale price momentum

Follow price direction only when short and medium trailing returns agree.

Candidate causal inputs:

- 8 s return
- 32 s return

LONG if both positive.
SHORT if both negative.
Otherwise ABSTAIN.

Rationale:
intraday cryptocurrency evidence supports both momentum and reversal; this rule
tests the continuation branch directly.

### T02 — Fast/slow EMA trend

Causal mid-price EMA crossover.

Representative structure:

- fast EMA around 4-8 s
- slow EMA around 32 s

LONG fast > slow.
SHORT fast < slow.

No optimization grid in the initial fixed candidate.

### T03 — Short-horizon breakout

Trade continuation after a causal local range break.

LONG when current executable/fair price breaks the prior rolling high.
SHORT on prior rolling low break.

A volatility floor prevents firing inside a nearly static book.

### T04 — Volatility-expansion momentum

Trade only when:

- recent signed price movement has a clear direction; and
- short-window realized volatility / range expands relative to a longer causal
  baseline.

Purpose:
separate trend continuation during active opportunity from ordinary noise.

### T05 — Short-term reversal / overreaction

Fade unusually large short-window price displacement relative to its trailing
causal distribution.

LONG after sufficiently negative standardized displacement.
SHORT after sufficiently positive standardized displacement.

This directly represents the cryptocurrency intraday reversal evidence.

### T06 — Microprice / VAMP fair-value follow

Use order-book-conditioned fair value.

LONG when generalized microprice / VAMP is materially above mid.
SHORT when materially below mid.

This is a direct microstructure directional rule, not a fitted classifier.

### T07 — Fair-value overshoot reversion

Compare observed executable/mid price against generalized microprice / VAMP.

If price moves materially beyond fair-value displacement while book pressure
does not confirm continuation, trade back toward fair value.

This is intentionally different from T06.

### T08 — L1 queue-imbalance direction

Use best bid / ask queue imbalance directly.

LONG when bid queue materially dominates ask.
SHORT for the opposite.

No model fit required.

### T09 — Multi-depth book imbalance / weighted depth

Use a fixed combination of:

- L1/L5/L10/L20/L50 depth imbalance;
- distance-weighted imbalance;
- weighted-depth fair price.

Trade only when near and deeper book pressure agree.

### T10 — OFI / MLOFI continuation

Use causal order-flow imbalance and multi-level order-flow imbalance.

LONG on sustained positive signed flow.
SHORT on sustained negative signed flow.

Use multiple causal horizons for persistence rather than a single snapshot.

### T11 — Aggressive trade-flow imbalance

Use buyer-initiated versus seller-initiated trade pressure separately from
resting-book imbalance.

LONG when aggressive buy flow dominates.
SHORT when aggressive sell flow dominates.

This is kept separate because executed trade flow may be more informative than
resting quote flow.

### T12 — Cancellation / depletion pressure

Use side-specific cancellation, deletion, replenishment and depletion events.

Example interpretation:

- ask depletion / ask cancellations can indicate upward pressure;
- bid depletion / bid cancellations can indicate downward pressure.

The strategy acts on persistent directional liquidity destruction rather than
static depth.

### T13 — Hawkes-lite exponential event-intensity direction

No full Hawkes fit in Wave 1.

Use fixed exponential-decay intensities of bid/ask add/remove event classes over
short and medium decay constants.

Trade when directional event excitation is persistent and asymmetric.

This captures event-time dynamics without a high-capacity model.

### T14 — Liquidity-shock continuation / recovery state

Detect a material best-level or near-book liquidity shock.

Continuation mode:
follow the side implied by persistent post-shock imbalance.

Recovery mode:
fade only when the book rapidly refills and price displacement loses flow
support.

The mode is determined causally from post-shock recovery state.

### T15 — Round-number pressure

Use distance to psychologically salient round BTC price levels together with
buy/sell pressure.

Recent cryptocurrency evidence reports abnormal buy pressure below round
numbers and sell pressure above them.

The strategy trades only when observed flow confirms the corresponding pressure.

### T16 — Regime-filtered consensus

Use a compact consensus rather than another fitted ML model.

Core directional votes:

1. price momentum;
2. order-book imbalance;
3. aggressive trade flow.

Trade only when at least two agree.

Optional regime veto:

- Hurst / persistence state;
- VPIN / toxicity state;
- extreme spread / liquidity state.

The regime layer may suppress trades but does not reverse the consensus.

## 6. Candidate count

Directional arena:

- 16 core mechanisms
- 2 gate states each
- total = 32 T candidates

Naming:

`T01U ... T16U`
`T01A ... T16A`

## 7. Division M candidate universe

Exactly eight initial maker mechanisms are proposed.

### M01 — symmetric pure market making

Fixed symmetric bid/ask quoting around mid with inventory cap.

Purpose:
baseline spread-capture control.

### M02 — order-book-imbalance skewed market making

Shift fair value and/or quote skew using standardized OBI.

Reference pattern:
hftbacktest "Market Making with Alpha - Order Book Imbalance".

### M03 — VAMP / microprice skewed market making

Use microprice / VAMP as short-horizon fair value, with inventory risk skew.

### M04 — GLFT / Avellaneda-Stoikov inventory market making

Reservation-price / inventory-risk market maker.

Use a bounded fixed configuration rather than a large parameter search.

### M05 — high-frequency grid market making

Queue-aware multi-level grid around the reservation price.

Reference:
hftbacktest GLFT / high-frequency grid examples.

### M06 — queue-position-aware market making

Use queue position and fill probability explicitly when deciding whether to
remain, cancel, or reprice.

This is materially different from naive passive-fill assumptions.

### M07 — toxicity-filtered market making

Pure or skewed market making that stops or widens quoting during high informed-
flow / toxicity states.

Candidate state:
VPIN + aggressive flow + spread regime.

### M08 — momentum-aligned adaptive market making

Market maker whose inventory target and quote skew align with short-horizon
momentum / order-flow alpha while retaining hard inventory limits.

This is a rule-based version of the performance-oriented adaptive market-making
idea; RL is deferred unless simpler control proves insufficient.

## 8. Why maker and taker must remain separate initially

The current repository can model causal executable taker entry/exit well.

It does not yet prove realistic maker fill probability.

For maker strategies, queue position and order latency materially affect fills,
adverse selection and realized PnL.

Therefore:

- do not award maker profits using optimistic "touch = fill" logic;
- use hftbacktest or an equivalently validated event-driven simulator;
- calibrate queue model conservatively;
- stress order latency;
- compare fill probability against post-fill adverse returns.

## 9. Development data plan

### Wave 1 — consumed Jan-Jul data

Use already-consumed BTCUSDT development data to:

- implement strategies;
- debug;
- eliminate obviously bad mechanisms;
- estimate turnover and activity;
- understand failure modes;
- tune only a very small number of structural constants if necessary.

Because this history has already been used extensively, Wave 1 is exploratory.

A Wave-1 winner is NOT capital-ready.

### Wave 2 — independent historical replication

Before using Sep-01+:

acquire or identify a separate older historical BTCUSDT L2/tick replication
pack not previously used for DEV044 selection.

Preferred target:

- at least 30 independent trading days;
- preferably 60-90 days;
- same Binance Futures instrument / comparable microstructure;
- L2 and trades if maker strategies are included.

Potential sources:

- existing archived project data if genuinely unused and older;
- Tardis or another historical L2 provider;
- compatible hftbacktest-format crypto history;
- exchange/public data where the required book semantics are available.

Sep-01+ should remain sealed during strategy discovery so it can later serve as
a true forward test.

## 10. Ranking metrics

Primary economic metrics:

- mean net executable bps / trade
- median net executable bps / trade
- total net bps
- profit factor
- positive-day fraction
- maximum drawdown
- worst day
- trade count
- trades/day
- exposure fraction
- turnover
- LONG/SHORT balance
- cost break-even bps

Robustness metrics:

- 250 / 500 / 1000 ms latency
- actual personal fee schedule
- fee stress
- +1 / +2 bp per-side extra slippage stress
- per-day stability
- leave-one-day-out performance
- regime stability
- block bootstrap confidence intervals

Do not select by raw return alone.

## 11. Tournament logic

### Round 1 — viability screen

A candidate remains alive only if:

- enough executed trades exist;
- gross executable expectancy > 0;
- primary net expectancy > 0;
- profit factor > 1;
- no execution-integrity failures;
- PnL is not concentrated in one single day.

This is intentionally lenient enough for discovery.

### Round 2 — robustness screen

Require stronger conditions such as:

- positive net expectancy after cost stress;
- positive median day;
- majority positive days;
- acceptable maximum drawdown;
- positive leave-one-day-out aggregate;
- latency degradation not catastrophic;
- no dependence on one isolated regime.

### Round 3 — multiple-strategy correction

Because 32+ strategies are compared, calculate anti-overfit diagnostics across
the full candidate universe.

Recommended:

- White Reality Check or Hansen SPA on strategy net return differentials;
- Deflated Sharpe Ratio;
- Probability of Backtest Overfitting / CSCV if sample size is adequate.

These are defensive tools for capital selection, not academic requirements.

### Round 4 — independent replication

Take only the top few distinct mechanisms to the independent historical pack.

Do not carry 32 strategies forward.

Recommended:

- maximum 4 finalists;
- preferably from different mechanism families.

### Round 5 — shadow / paper live

Run finalists live with no real orders or exchange sandbox/dry-run where
possible.

Compare:

- signal timing;
- expected fills;
- realized simulated fills;
- latency;
- cost drift;
- PnL drift.

### Round 6 — small-capital deployment

Only after historical replication + shadow-live stability.

Start unlevered and with a small fixed risk budget.

No automatic capital scaling until live behavior matches the validated
simulation closely.

## 12. Selection philosophy: do not blindly choose one winner

The final objective should be:

1. find profitable individual strategies;
2. identify correlation between their daily/trade PnL;
3. prefer a small portfolio of robust, weakly correlated survivors if available.

A slightly lower-return strategy can be more valuable than the top backtest if
it diversifies the main winner and has lower drawdown / regime dependence.

## 13. Implementation references

### hftbacktest

Primary reference for:

- L2/L3 market replay;
- feed/order latency;
- queue-position fill models;
- Binance Futures examples;
- OBI-skewed market making;
- GLFT/grid market making;
- queue-based market making.

Repository:
https://github.com/nkaz001/hftbacktest

Documentation:
https://hftbacktest.readthedocs.io/en/latest/

### NautilusTrader

Useful reference for:

- deterministic event-driven backtesting;
- order-book depth replay;
- live/backtest strategy parity;
- EMA trend example;
- mean reversion;
- order-book imbalance;
- grid market making;
- Hurst/VPIN directional strategy patterns.

Repository:
https://github.com/nautechsystems/nautilus_trader

### Hummingbot

Useful reference for:

- pure market making;
- inventory skew;
- multi-level quoting;
- strategy controllers;
- cross-exchange market making for a later multi-venue family.

Repository:
https://github.com/hummingbot/hummingbot

### Freqtrade

Not recommended as the primary L2/HFT execution simulator.

Useful specifically for development hygiene ideas such as:

- lookahead analysis;
- recursive-analysis;
- strategy-list batch backtests;
- dry-run / forward-test workflow.

Repository:
https://github.com/freqtrade/freqtrade

## 14. Literature / empirical anchors

Key mechanism references reviewed for DEV044:

1. Cont, Kukanov, Stoikov — order-flow imbalance and short-horizon price
   impact.
2. Gould & Bonart — queue imbalance as a one-tick-ahead predictor.
3. Stoikov — microprice as an order-book-conditioned future-price estimator.
4. Intraday cryptocurrency evidence showing both momentum and reversal.
5. 2026 Journal of Financial Markets evidence that order flow contains
   economically valuable crypto return information.
6. 2026 Bitcoin LOB / Hawkes forecasting evidence supporting event-time
   structure.
7. 2026 crypto microstructure work supporting VPIN/liquidity/toxicity and
   cross-market microstructure state.
8. 2026 cryptocurrency round-number evidence showing systematic buy/sell
   pressure around round prices.
9. Avellaneda-Stoikov and GLFT market-making frameworks.
10. White Reality Check, Hansen SPA, Deflated Sharpe Ratio and PBO/CSCV for
    controlling strategy-selection overfit.

## 15. Explicitly deferred ideas

Do not put these in Wave 1:

- large Transformer search;
- reinforcement-learning policy search;
- genetic algorithms / symbolic strategy mining;
- hundreds of indicator parameter combinations;
- leverage optimization;
- Kelly sizing;
- multi-asset / cross-exchange arbitrage;
- funding-rate arbitrage;
- options strategies;
- news/sentiment trading.

These may become later families after a simpler strategy demonstrates robust
economic value.

## 16. Recommended immediate next step

Do NOT run real PnL yet.

Next:

`DEV044-T0 STRATEGY CONTRACT + EXECUTION PARITY AUDIT`

T0 should freeze/verify:

- exact 16 core directional mechanisms;
- exact A0 gate definition;
- exact causal inputs available for each;
- common H1800/B32 execution shell;
- exact fee mapping;
- candidate naming;
- no lookahead;
- identical execution support;
- no Sep-01+ access.

Then implement the 32 T candidates with synthetic tests.

Only after T0 and CI should the first broad strategy tournament run on consumed
historical data.

## 17. Current state

`DEV044_STRATEGY_ARENA_RESEARCH_PROPOSAL_READY_T0_DESIGN_NEXT_NO_DATA_OPEN`
