# DEV045-D6R26A-P0 — Formal Generation-2 Conditional Maker Edge Design

## Parent conclusion

D6R25-R1 is frozen at `be9b827d2d4c4ccdeb4ecccf8979e771debd5dd2` with classification
`ZERO_FEE_GROSS_EDGE_NEGATIVE_POLICY_FAMILY_REJECT`.

This rejects only M01-M08 as instantiated. It does not reject market making generally.

## Generation-2 question

At a causal decision epoch, for a precise passive BTCUSDT quote:

1. what is the probability and fraction of execution within a finite horizon; and
2. conditional on execution, is the maker fill favorable or adversely selected?

D6R26A separates execution probability from execution quality. It contains no economic strategy and no PnL.

## Candidate universe

Every 1-second local strategy decision epoch creates counterfactual candidates on both sides at pre-registered passive distances `0, 1, 2, 4` ticks from the local best quote. Candidate size is exactly one lot, `0.001 BTC`.

Candidates are post-only GTX limit orders. No inside-spread improvement is allowed.

The canonical candidate simulator must use the existing validated D6R24 execution semantics:

- 250 ms entry latency and 250 ms response latency for the primary label surface;
- risk-adverse queue model;
- partial-fill exchange;
- BTCUSDT tick `0.1` and lot `0.001`.

A secondary 500/500 stress label surface is diagnostic only and cannot rescue primary qualification failure.

## Lane isolation

A single order per side/distance simulator lane would overlap at a 1-second decision cadence when the longest label horizon is 5 seconds. P2 therefore partitions every candidate configuration into five phase cohorts (seconds modulo five). This yields 40 independent lanes per day: `5 phases × 2 sides × 4 distances`.

A lane candidate expires at five seconds, and expiration/cancel terminality must be established before another candidate in that lane can be placed. This preserves every 1-second decision epoch without overlapping counterfactual orders inside one lane.

## Fill/censoring labels

For horizons 250 ms, 500 ms, 1 s, 2 s, and 5 s, labels are exactly:

- `FILLED_WITHIN_TAU`
- `NOT_FILLED_WITHIN_TAU`
- `CENSORED`

`CENSORED` is never converted into `NOT_FILLED_WITHIN_TAU`.

Post-only rejection at exchange arrival is an observed no-fill outcome because the candidate was causally attempted and rejected for violating maker-only semantics. If the placement outcome itself is unobservable before source end, it is censored.

Partial fills are first-class. Every candidate stores any-fill status, fill fraction by horizon, time-to-first-fill, and time-to-full-fill when a full fill occurs.

## Conditional markout

For every actual maker fill, the target at horizon `h` is:

`10000 * side_sign * (future_mid_h - fill_price) / fill_price`

where side sign is +1 for bid fills and -1 for ask fills.

The future reference is BBO mid observed causally after the fill's exchange execution time. Because fill price is used directly, spread capture is already embedded and must not be added again.

Multiple partial fills are aggregated by executed-quantity-weighted markout. If any fill included in a candidate-level horizon target lacks the full horizon of observable market data, that candidate markout horizon is censored.

Markout is execution quality / mark-to-mid, not flat-to-flat realized PnL.

## Local-only A0 feature families

A0 is strictly local to Binance BTCUSDT and uses only features observable no later than the decision-local timestamp.

- F0 fair value: spread, microprice displacement, BBO VAMP displacement, L5 VAMP displacement.
- F1 flow: L1/L5 imbalance, BBO OFI 1s/5s, trade imbalance 1s/5s, add imbalance 1s, cancel imbalance 1s.
- F2 toxicity: OFI acceleration, short-horizon same/opposite-side depth change, spread change, realized volatility 1s/5s/30s.
- F3 execution state: candidate side, candidate distance, displayed quantity at candidate price, decision-book queue-ahead estimate, best-depth quantities.

Realized queue state at exchange arrival is label-side diagnostic only and may never be used as a decision-time feature.

Inventory is excluded from D6R26A and deferred to D6R26B. Cross-venue features are excluded from A0 and require a later frozen incremental test above successful local-only A0.

## Model separation

Model A estimates finite-horizon fill probability using censor-aware labels. Initial model families are logistic regression and histogram gradient boosting.

Model B estimates conditional signed markout on observed fills. Initial model families are ridge regression and histogram gradient boosting.

No deep learning and no reinforcement learning are authorized in A0.

The core diagnostic score is:

`P(any_fill_within_1s | state, quote) * E(markout_1s_bps | fill_within_1s, state, quote)`

This is not realized PnL and is not a deployable quote rule.

## Development and untouched qualification

Jan-Mar are development-only. Candidate/model family selection uses leave-one-day-out within Jan-Mar.

Apr-Jul are a strict untouched out-of-time qualification surface. The selected model family and all gates must be frozen before Apr-Jul are opened in P3. No refit or threshold tuning is allowed on Apr-Jul.

## Qualification

The selected fill model must beat its base-rate log-loss aggregate and on at least 3 of 4 Apr-Jul days.

At the primary 1-second markout horizon:

- top predicted conditional-edge decile mean markout must exceed bottom decile aggregate;
- top decile mean must be positive aggregate;
- top-minus-bottom must be positive on at least 3 of 4 qualification days;
- top-minus-bottom must be positive for both bid and ask aggregate.

Censor/missing outcomes must remain explicit.

Other horizons are reported to describe half-life but cannot rescue a failed 1-second primary gate. A secondary model family cannot be substituted after qualification failure.

## Phase sequence

- P0: this design only. No historical source open, candidate simulation, model fit, or PnL.
- P1: candidate labeler implementation with synthetic fixtures only.
- P2: canonical Jan-Jul candidate-label materialization, no model fit and no PnL; freeze the label dataset.
- P3: Jan-Mar development selection followed by untouched Apr-Jul OOT qualification, no simulator and no PnL.
- D6R26B is allowed only after a D6R26A conditional-edge survivor and owns quote shaping, inventory skew, toxicity veto, and passive unwind.
- D6R26C is the first Generation-2 frozen economic replay.

## Prohibitions

No fee rescue, size tuning, leverage, live trading, August, September+, non-BTC markets, cross-venue A0, economic arena, or reinterpretation of D6R25-R1 as a rejection of market making generally.
