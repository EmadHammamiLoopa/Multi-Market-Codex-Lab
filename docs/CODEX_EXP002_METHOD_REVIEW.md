# CODEX-EXP-002 Method Review

Date: 2026-08-25
Decision: **proceed to a frozen, low-capacity sandbox experiment**

## What can and cannot be identified

Tardis documents `localTimestamp` as the message arrival time, trade `side` as the liquidity-taker/aggressor side, and incremental-book `amount` as the new level amount rather than a delta. It also documents that equal local timestamps form an atomic message and that a snapshot resets the local book. These facts support causal arrival-time replay and exact same-price aggressor-trade accounting. [Tardis data types](https://docs.tardis.dev/tardis-machine/data-types), [Tardis data FAQ](https://docs.tardis.dev/faq/data)

Market-by-price data does not identify the exact order identities ahead of a hypothetical order. The hftbacktest queue documentation therefore treats queue position as modeled. Its RiskAverseQueueModel advances only from trades at the order price and does not assign favorable unknown cancellations ahead. Probability models allocate depth decreases according to assumptions. [hftbacktest queue models](https://hftbacktest.readthedocs.io/en/v1.8.4/reference/queue_models.html)

The accelerated hftbacktest tutorial explicitly removes queue-position and market-depth replay for speed. Such an approximation is unsuitable as the promotion engine here because queue uncertainty is the experiment’s main risk. [hftbacktest accelerated backtesting](https://hftbacktest.readthedocs.io/en/latest/tutorials/Accelerated%20Backtesting.html)

Consequently, EXP002 can identify outcomes under a deliberately conservative MBP queue model. It cannot claim to reproduce the user’s historical private queue rank or actual fills.

## Event clock and decision state

All ordering uses Tardis local arrival timestamps. Exchange timestamps never reorder events. Equal-local-time data is atomic: the existing 250 ms features expose only complete atomic groups through the grid time. An order arriving at time `a` cannot consume a trade with local timestamp `<= a`.

FEATURES250 supplies decision-time predictors only. The fill engine does not derive a fill from a future book touch, FEATURES250 label, mid-price path, or price crossing. It uses exact-price raw trade events after arrival.

## Candidate stream and inventory control

Each symbol receives one candidate every 15 seconds, beginning 15 seconds after UTC day start. Side alternates exogenously buy/sell by slot. P0 and P1 receive the identical stream; P1 may only discard candidates. This avoids a hidden side-selection advantage.

The maximum slower-sensitivity execution span is less than 15 seconds: 500 ms arrival + 3 s lifetime + 500 ms cancellation response + 10 s exit horizon + 500 ms taker response. Candidates whose complete span could cross UTC midnight are purged before labels are created. Thus same-symbol positions cannot overlap, and no label crosses a day boundary.

## Primary queue and order lifecycle

At decision time a post-only limit is sent at the current best bid for a buy or best ask for a sell. It arrives 250 ms later. It is allowed to rest only if the book is valid and the same-side best price at arrival exactly equals the submitted limit. Arrival price changes are recorded as misses, not filled orders.

The initial primary queue is the displayed L1 quantity at the exact arrival price. Later cancellations and displayed-depth reductions receive zero primary credit. Only later raw trades with the opposite aggressor side at the exact limit price consume the queue. Trade quantity consumes the ahead quantity first; only residual trade quantity executes the research order.

An unfilled order requests cancellation 3 seconds after arrival; cancellation takes the same 250 ms response latency. A first partial fill triggers an immediate cancellation request; additional exact-price executions during the response latency are retained, the remaining size is canceled, and all executed quantity is included in economics. A snapshot reset makes the modeled rank unobservable and stops crediting subsequent fills.

This is intentionally harsher than MBO truth could be. It cannot create a fill merely because the market touched or crossed the quote.

## Diagnostic queue sensitivity

Q50 is not a promotion model. At each later 250 ms sample where the order price remains the visible best, it computes:

`inferred_nontrade_reduction = max(0, prior_depth - current_depth - exact_price_trade_qty)`

It credits 50% of that inferred reduction ahead of the order, at the end of the sample interval. It credits nothing while the price is off-touch. Execution still requires a later exact-price aggressor trade. This is a coarse probability/cancellation allocation sensitivity, not an assertion about true order identities. A Q50 success cannot rescue a RiskAverse primary failure.

## Latency choice

250 ms is frozen because it matches the existing causal feature clock and avoids inventing sub-grid observer state. It is not claimed to be the user’s measured network latency. A slower 500 ms entry/response path is reported. No faster latency is evaluated, so latency cannot become a rescue parameter.

## Fill and markout separation

The fill label is `any executed quantity > 0` within the queue lifecycle. Fill prediction is a logistic regression on decision-time state.

The conditional model is fitted only on simulated fills. Its target is the gross passive-entry/taker-exit basis-point return: exit at the executable bid for a buy or ask for a sell 10 seconds after the first fill, plus response latency. The model is Ridge regression. It never receives fill-time or post-submission state as an input.

Reported 1/3/10 s markouts start at the first simulated fill time and use the first causal BOOK250 state at or after each horizon. They do not start at the signal.

P1 expected value per submitted order is:

`predicted_fill_probability × (predicted_conditional_gross_bps − maker_fee_bps − taker_fee_bps)`

No-fill outcomes have zero execution PnL. The architecture keeps fill, adverse selection, and fee assumptions visible even though the sign of expected value is driven largely by the conditional estimate.

## Feature and capacity review

One side-aligned eight-variable vector is used for both low-capacity models:

1. ETH symbol indicator
2. spread bps
3. side-aligned microprice-minus-mid bps
4. side-aligned OBI L1
5. side-aligned OBI L5
6. log displayed own-side L1 quantity
7. side-aligned OFI L1 over 1 s
8. side-aligned trade-quantity imbalance over 1 s

The vector uses existing Phase L semantics. It contains no model-derived feature, future state, arrival-time state, fill outcome, or new data. Logistic `C=1` and Ridge `alpha=10` are fixed. The only selected value is one of three expected-value cutoffs on the immediately preceding inner day.

## Fees

Binance exposes a signed user-specific commission-rate endpoint rather than one universally applicable personal rate. Its official example shows positive maker and taker commission rates (2 bps and 4 bps), not a universal maker rebate. [Binance USD-M user commission rate](https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/User-Commission-Rate)

No personal signed endpoint was called. The frozen primary envelope is therefore 2 bps maker entry plus 4 bps taker exit. Stress is 3 + 5 bps. Zero fee, VIP, and rebate cases are absent. Break-even total fee is reported as observed gross expectancy.

## Order size and capacity

Size is fixed at 0.001 base units for both BTCUSDT and ETHUSDT. It is never optimized, compounded, levered, or dynamically scaled. Every resting order records size divided by displayed L1 quantity. Median ≤1% and p90 ≤10% are promotion gates; failure means the “small relative to depth” premise did not hold.

## Walk-forward and falsification

Five outer folds score March through July. For each fold, all days earlier than the immediately preceding day train the models; the immediately preceding day selects one expected-value cutoff; the next day is scored once. The inner day is not added to the model fit, and the outer day affects neither model nor cutoff.

The experiment is intentionally difficult to pass: coverage, primary and stress economics, stability, concentration, P1-over-P0 expectancy and total PnL, adverse-fill improvement, order-depth ratios, and conservative-queue survival are all mandatory. Diagnostics cannot rescue failure.
