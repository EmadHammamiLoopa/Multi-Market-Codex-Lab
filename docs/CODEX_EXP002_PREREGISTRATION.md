# CODEX-EXP-002 Preregistration

Date frozen: 2026-08-25
Status: **FROZEN BEFORE ANY JAN–JUL PERFORMANCE OUTPUT**
Scope: consumed sandbox research; no profitability or validation claim

## 1. Hypothesis and falsification

Phase L and CODEX-EXP-001 suggest that single-venue short-horizon microstructure contains weak information that could not pay taker/taker costs. EXP002 tests a different mechanism:

> Can a low-capacity L2 filter improve passive-entry plus taker-exit economics over the identical unfiltered passive baseline under conservative queue, latency, fee, and capacity assumptions?

The hypothesis fails unless **every** frozen primary gate in section 15 passes. P0 profitability alone is insufficient. Probability-queue or faster/cheaper assumptions cannot rescue the primary result.

## 2. Data and seal

- original read-only root: `/home/emadh/Multi-Market`
- days: first UTC day of January, February, March, April, May, June, and July 2026
- symbols: BTCUSDT and ETHUSDT, Binance USD-M
- raw execution events: existing Tardis `trades`
- arrival book state: existing BOOK250 reconstructed from Tardis `incremental_book_L2`
- decision state: existing FEATURES250
- resets: existing snapshot indices

The exact 28 raw and 70 derived files passed the provenance gate documented in `CODEX_EXP002_DATA_AVAILABILITY.md`. No August data path is allowed. The implementation rejects every path containing `2026-08` and every day outside the seven-day whitelist.

## 3. Event ordering and causality

- sole observer/order clock: `local_timestamp`
- exchange timestamps never reorder events
- equal-local-time book groups remain atomic through the existing Phase L feature construction
- a trade with timestamp `<= order_arrival` cannot affect the simulated order
- all predictors come from the decision row; arrival, fill, and future states are forbidden as predictors
- no order, fill, exit, or markout label may cross UTC day end

## 4. Candidate universe and policies

For each symbol, candidates occur every 15 seconds beginning at 00:00:15 UTC. Side alternates deterministically by raw slot: buy, sell, buy, sell. Invalid L2 decision rows and candidates whose full slower-sensitivity span could cross midnight are excluded before label construction.

- **P0:** submits every remaining candidate.
- **P1:** sees the identical candidate stream and may submit only when its frozen predicted expected value is strictly above the inner-selected cutoff.
- **NO_TRADE:** submits nothing and has zero PnL.

P1 cannot choose a different side, time grid, order price, size, queue model, lifetime, latency, or exit than P0.

## 5. Order placement and size

- buy limit: decision-time best bid
- sell limit: decision-time best ask
- post-only intent
- fixed size: 0.001 BTC or 0.001 ETH
- no size search, leverage, compounding, Kelly, martingale, dynamic capital, or inventory scaling

At arrival, the order rests only when the valid same-side best still exactly equals the submitted limit. Otherwise the attempt is an arrival miss/reject and cannot fill.

## 6. Primary latency and cancellation

- order-entry latency: 250 ms
- order-response/cancel latency: 250 ms
- taker-exit response latency: 250 ms
- resting lifetime before timeout cancel request: 3 seconds from arrival
- first partial fill: immediately requests cancellation; executions during the 250 ms response remain included
- snapshot reset before fill completion: stop queue tracking and cancel; do not claim later fills

No faster latency is evaluated. A 500 ms entry/response/taker path is a slower-only diagnostic.

## 7. Primary RiskAverse queue

Initial queue ahead equals displayed L1 quantity at the exact limit price after entry latency. Only later raw trades at the exact price with the contra aggressor side advance the queue. Trade quantity consumes ahead quantity first, then the research order. Cancellations and arbitrary depth reductions contribute zero primary advancement.

Price touch, price cross, a future BOOK250 price, and an accelerated fill approximation never produce a primary fill.

For every attempt record arrival status, initial queue, exact-price qualifying trade quantity, queue advancement, filled quantity, first/full fill time, order age, timeout/cancellation status, and size/displayed-depth ratio.

## 8. Fill and economic labels

- fill label: any positive simulated execution quantity
- full/partial status: reported separately
- fill time: first positive execution timestamp
- economic exit: taker at executable bid after a buy or ask after a sell, at first causal book state at or after `fill_time + 10 s + response_latency`
- gross USD: signed filled quantity × price change
- fees: charged on entry and exit notionals
- partial quantity: retained and fully included in PnL; unfilled remainder is canceled

If a required within-day exit book state is unavailable, the run stops with an integrity error rather than dropping the realized outcome.

## 9. Markouts and adverse selection

For every fill, report signed mid-price markouts from the fill price at 1, 3, and 10 seconds after **fill time**. The adverse-fill indicator is a negative 1-second signed markout. These reporting horizons are not model/grid choices.

The conditional modeling target is 10-second gross passive-entry/taker-exit bps including taker response latency but before fees.

## 10. Features and models

One pooled, side-aligned vector is used:

1. `symbol_is_eth`
2. `spread_bps`
3. `side × microprice_minus_mid_bps`
4. `side × obi_l1`
5. `side × obi_l5`
6. own-side `log_qty_l1`
7. `side × ofi_l1_1s`
8. `side × trade_qty_imbalance_1s`

Training-only StandardScaler precedes both models.

- fill model: scikit-learn logistic regression, `C=1.0`, `lbfgs`, no class weights, seed 20260825
- conditional gross model: scikit-learn Ridge, `alpha=10.0`, fitted only to primary RiskAverse fills
- minimum model data: 500 candidate attempts, both fill classes, at least 50 fills, and at least 50 finite conditional targets

Failure of those requirements is a model failure and therefore experiment failure; no constant, neural, nonlinear, or alternate model replaces it.

## 11. Expected-value rule and tiny selection grid

For each candidate:

`EV_bps_per_order = P(fill) × (predicted_gross_if_filled_bps − 6 bps)`

The immediately preceding inner day selects one strict cutoff from `{0.00, 0.10, 0.25}` bps per submitted order by maximum total inner primary net USD. A cutoff is eligible only with at least 250 submitted inner candidates and 20 completed inner fills. Ties choose the lower cutoff. If none is eligible, the fold is a model failure and P1 submits no outer orders.

There is no feature, model-family, regularization, lifetime, horizon, cost, size, latency, or queue grid.

## 12. Fees

- primary maker entry: 2 bps, no rebate
- primary taker exit: 4 bps
- stress maker entry: 3 bps, no rebate
- stress taker exit: 5 bps

No zero-fee, VIP, assumed rebate, or personal-account case is run. Fee break-even is the observed gross expectancy per completed cycle.

## 13. Walk-forward

| Outer score | Model training | Inner cutoff selection |
|---|---|---|
| 2026-03-01 | Jan | Feb |
| 2026-04-01 | Jan–Feb | Mar |
| 2026-05-01 | Jan–Mar | Apr |
| 2026-06-01 | Jan–Apr | May |
| 2026-07-01 | Jan–May | Jun |

Both symbols and sides are pooled within each chronological slice. The model is not refitted on the inner day. The outer day is used once and cannot select any parameter.

## 14. Required reports

For P0 and P1, pooled and by outer fold where applicable:

- submitted/resting/filled/full/partial orders; fill, partial, arrival-miss, cancel, and timeout rates
- median/p90/p99 fill wait, initial queue, and size/displayed-depth ratio
- gross/net/stress expectancy, gross/net/stress total USD, PF, max drawdown, PnL/maxDD
- completions/day, positive-day fraction, positive active-hour fraction, day/hour concentration, p01/p05/worst loss
- 1/3/10 s fill-time markouts and 1 s adverse-fill rate
- maker/taker fees and break-even round-trip fee
- P0/P1 incremental expectancy, total PnL, fill rate, markouts, adverse fills, and trade count
- exact model coefficients/scalers, cutoff selection tables, input hashes, candidate-ledger hash, runtime, and frozen commit

## 15. Frozen primary PASS gates

Every gate is mandatory under RiskAverse queue, 250 ms latency, and primary/stress fees:

1. no model failures
2. at least 200 pooled P1 outer completed fills
3. at least 20 P1 completions in every one of five outer folds
4. P1 primary net expectancy > 0 bps
5. P1 primary total net USD > 0
6. P1 profit factor ≥ 1.20
7. P1 PnL/maxDD ≥ 1.0
8. at least four of five P1 outer folds have positive total net USD
9. P1 positive-day fraction ≥ 0.80
10. P1 positive active-hour fraction ≥ 0.50
11. P1 positive-PnL day concentration ≤ 0.40
12. P1 positive-PnL hour concentration ≤ 0.20
13. P1 stress net expectancy > 0 bps
14. P1 stress total net USD > 0
15. P1 net expectancy ≥ P0 net expectancy + 0.50 bps
16. P1 total net USD > P0 total net USD
17. P1 1 s adverse-fill rate ≤ P0 adverse-fill rate − 0.02
18. P1 fill rate ≥ 0.005 of submitted attempts
19. P1 median order/displayed-depth ratio ≤ 0.01
20. P1 p90 order/displayed-depth ratio ≤ 0.10
21. the primary result is the conservative RiskAverse result

NO_TRADE is zero. A result that clears some but not all gates is `FAIL`.

## 16. Diagnostic-only sensitivities

- **Q50 at 250 ms:** credits 50% of conservatively inferred same-price sampled nontrade depth reductions ahead, at sample end; execution still requires later exact-price trade volume.
- **RiskAverse at 500 ms:** repeats entry, cancel response, and taker response at 500 ms.

Neither diagnostic changes models, cutoff selection, or the PASS decision. Q50 and slower-latency performance may explain failure but cannot rescue it. Maker/maker, faster latency, rebate, touch fill, cross-venue inputs, and accelerated fills are not diagnostics in EXP002.

## 17. Freeze and no-rescue rule

The code, tests, method documents, provenance evidence, and this preregistration must be committed before the real Jan–Jul simulation starts. The run command must verify that `HEAD` equals the supplied frozen commit and that tracked files are unchanged.

After that commit, any material change to hypothesis, data, features, models, queue, candidate stream, order lifecycle, size, latency, fees, threshold grid, folds, metrics, or gates requires a new experiment ID. EXP002 will be preserved as PASS or FAIL without rescue, rerun, retuning, or reinterpretation.
