# DEV045-M0 — Maker Feasibility / Queue-Aware Replay Design

Status:

`NO_PNL_FEASIBILITY_DESIGN_FROZEN`

Date: 2026-09-03

## 1. Why DEV045 exists

DEV044-T closed with:

`DEV044_T1_NO_ECONOMIC_SURVIVOR`

under the frozen H1800/B32 taker shell.

The dominant economic problem was insufficient executable edge after crossing
costs. Several A0-gated variants reduced losses materially but did not become
profitable.

DEV045 therefore tests a materially different execution family:

`PASSIVE / MAKER`

DEV045 is not a rescue of DEV044. It is a separate hypothesis.

## 2. DEV045-M0 purpose

M0 must answer only:

> Can the currently available historical data support a sufficiently
> conservative queue-aware maker replay to justify opening maker PnL?

M0 computes NO maker strategy PnL.

## 3. Available historical data

Current historical source:

- Tardis Binance Futures
- BTCUSDT
- `incremental_book_L2`
- `trades`

The existing Phase0DL lineage reconstructs Market-By-Price L2 state causally
from exchange timestamp order.

This is sufficient to know displayed quantity by price level.

It is NOT Market-By-Order.

Therefore exact queue rank / individual resting-order priority is not directly
observable.

## 4. Consequence of MBP data

Maker backtesting must not assume:

- touch = fill
- size decrease = our queue position advances fully
- cancellation always occurs ahead of us
- exact FIFO position is known
- full fill on every trade through our price

Queue position must be modeled conservatively.

## 5. Required simulator semantics

Primary reference implementation:

`hftbacktest`

M0 must prove compatibility with:

- Market-By-Price replay
- queue position model
- configurable order latency
- partial-fill-aware or explicitly conservative exchange model
- maker/taker fee model
- exact price/size event replay

No custom optimistic fill simulator is permitted for first maker economics.

## 6. Frozen queue-model family

At least two queue assumptions must be supported before PnL:

### Q0 — Risk-averse queue

Cancellations / modifications do not advance our order.

Queue position advances only via trade execution at our price.

This is the conservative primary feasibility model.

### Q1 — Probabilistic queue

A fixed hftbacktest probability queue model may be used as a diagnostic.

The exact function must be frozen before maker PnL.

Q1 may not promote a strategy that fails Q0 primary economics in the first
maker arena unless a later prospective calibration proves Q1 matches real
fills materially better.

## 7. Partial fills

M0 must verify that the selected exchange simulation records partial fills or
else explicitly uses a no-partial-fill model as a conservative bound.

If partial fills are enabled:

- fill quantity must be constrained by observed trade quantity at our price;
- replay cannot consume liquidity that was not observed;
- remaining order quantity stays working or is canceled according to policy.

## 8. Latency

Maker order lifecycle requires separate latency states:

- submit latency
- cancel latency
- replace latency

No zero-latency maker simulation.

M0 must support at least:

- 100 ms diagnostic
- 250 ms primary
- 500 ms stress

These are execution feasibility settings only.

No strategy PnL is opened in M0.

## 9. Initial snapshot / book continuity

Replay must start from a valid snapshot or equivalent complete reconstructed
book state.

Any exchange/event gap must invalidate the interval until a valid reinit.

No interpolation.

No silent book repair.

## 10. Order-size feasibility

Maker order quantity must be small enough that the replay assumption of no
market impact is plausible.

M0 must compute only capacity diagnostics such as:

- order size / displayed L1 quantity
- order size / displayed quantity at quote price
- fraction of timestamps where requested size exceeds conservative displayed
  capacity

No PnL.

## 11. Fee semantics

M0 must not hard-code an optimistic rebate.

Before maker PnL, the arena must freeze:

- verified maker fee/rebate assumption
- taker fee for forced inventory liquidation
- whether fees are value-based or quantity-based

At minimum first economic arena must include:

- neutral maker fee/rebate scenario
- verified personal/account-relevant scenario when available
- adverse fee stress

Fee scenarios cannot differ by strategy.

## 12. Adverse-selection diagnostics required before PnL

For hypothetical passive fills under Q0/Q1, M0 or the next pre-PnL stage must
support measuring post-fill executable markout at fixed horizons:

- 1s
- 5s
- 30s

Purpose:

detect whether apparent spread capture is systematically offset by adverse
selection.

These markouts are diagnostics, not strategy PnL.

## 13. Required raw-data audit

Before simulator use, M0 must read only metadata/schema and verify:

- raw L2 files exist for authorized BTC development days
- raw trade files exist
- exact headers are stable across days
- snapshots are present
- exchange timestamps are monotone/nondecreasing as required by source
- local timestamps exist for latency diagnostics
- side / price / amount fields are finite/valid
- trade side / price / amount fields are valid
- no Sep-01+ file is opened
- no non-BTC file is opened

## 14. Feasibility outcomes

Exactly one of:

### PASS_QUEUE_AWARE_MBP_FEASIBLE

Requirements:

- MBP + trade replay compatible with selected simulator
- Q0 conservative queue model operational
- one Q1 diagnostic model operational
- partial-fill semantics understood/frozen
- latency lifecycle supported
- fee hooks supported
- adverse-selection markout support demonstrated
- exact snapshot/book continuity verified

### CONDITIONAL_MBP_QUEUE_MODEL_ONLY

Use when:

- replay works,
- but exact queue position is unobservable because source is MBP.

This is acceptable for historical discovery only if Q0 is primary and later
prospective live fill calibration is mandatory.

### FAIL_MAKER_DATA_INSUFFICIENT

Use when:

- required snapshot/event continuity is missing,
- trades cannot be aligned to book events,
- queue model cannot be implemented defensibly,
- or latency/partial fills cannot be represented.

A FAIL closes historical maker work unless a different data source is acquired.

## 15. No-PnL rule

M0 must not compute:

- maker PnL
- spread capture
- strategy PF
- strategy drawdown
- maker leaderboard
- winner/ranking

## 16. Forward guards

- Sep-01+ sealed
- all non-BTC sealed
- no maker strategy tuning
- no order-spacing grid
- no inventory-risk grid
- no queue-model cherry-picking from PnL
- no touch=fill approximation

## 17. Next if M0 passes

`DEV045-M1 MAKER REPLAY PARITY + SYNTHETIC FILL TESTS`

Only after M1 is green may a finite maker strategy family be frozen.

## Current state

`DEV045_M0_NO_PNL_FEASIBILITY_AUDIT_NEXT`
