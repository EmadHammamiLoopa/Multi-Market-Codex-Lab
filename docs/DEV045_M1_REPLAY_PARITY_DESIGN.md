# DEV045-M1 — Maker Replay Parity and Synthetic Fill Design

Status:

`PRE_STRATEGY_PNL_DESIGN_FROZEN`

Date: 2026-09-03

## 1. Purpose

M1 proves that the pinned historical maker simulator behaves as intended on
controlled event streams before any real maker strategy family is designed or
scored.

M1 is not a profitability experiment.

M1 computes no maker strategy PnL, no strategy PF, no strategy drawdown, no
ranking and no winner.

## 2. Frozen parent

DEV045-M0 canonical status:

`DEV045_M0_CONDITIONAL_MBP_QUEUE_MODEL_ONLY`

Canonical artifact:

`/home/emadh/Multi-Market/evidence/dev045_m0_maker_feasibility_v1/DEV045_M0_MAKER_FEASIBILITY_RESULT.json`

Identity:

- bytes = `15490`
- SHA256 =
  `9a950ba7f4421cc06815f58ce559d3365081f7c8d6ce360225f65154a70138f3`

M0 MUST NEVER BE RERUN.

## 3. Simulator

Pinned:

`hftbacktest==2.4.4`

Primary queue model:

`risk_adverse_queue_model`

Diagnostic queue model:

`log_prob_queue_model`

Primary exchange fill model for parity testing:

`partial_fill_exchange`

Conservative bound diagnostic:

`no_partial_fill_exchange`

## 4. Tardis conversion contract

Use the official:

`hftbacktest.data.utils.tardis.convert`

Input order is frozen as:

1. trades file
2. incremental_book_L2 file

This ordering is mandatory because the converter documentation warns that
processing depth before the associated trade can reduce queue position twice.

Snapshot mode:

`process`

No snapshot ignore mode is authorized in M1.

Converted event dtype must be exactly the hftbacktest event dtype with fields:

- ev
- exch_ts
- local_ts
- px
- qty
- order_id
- ival
- fval

M1 must call the official event-order validator.

Feed latency requirement:

`local_ts >= exch_ts`

No negative latency correction is allowed in M1 synthetic tests; fixtures must
be natively valid.

## 5. Synthetic event families

Every synthetic fixture has explicit expected queue/fill behavior.

### F0 — snapshot initialization

A full bid/ask snapshot initializes an uncrossed MBP book.

Required:

- best bid/ask correct
- displayed quantity correct
- no order fill before our order exists

### F1 — touch is not fill

Place a passive buy at best bid behind displayed quantity.

Then change unrelated levels and/or quote the same price without a sell trade
that consumes the queue ahead.

Under Q0 Risk-Adverse:

`NO FILL`

This is the primary anti-optimism sentinel.

### F2 — cancellation does not advance Q0 queue

Place passive order behind displayed quantity.

Reduce displayed quantity at our price by cancellation/modification only.

Under Q0:

our queue position does not advance from this decrease.

Required:

`NO FILL solely from cancellation`

### F3 — trade advances Q0 queue

Place passive buy at best bid.

Feed sell trades at exactly our price.

Queue is advanced only by observed sell trade quantity.

Order must remain unfilled until cumulative executable trade quantity is
sufficient to consume the queue ahead according to the simulator.

### F4 — partial fill

After queue ahead is consumed, a sell trade at our buy price has quantity less
than our remaining order quantity.

Under PartialFillExchange:

required order status / executed quantity must show partial execution.

Remaining quantity must stay working.

### F5 — full fill after partial

A later same-price sell trade consumes remaining quantity.

Required:

- final FILLED state
- executed quantity = submitted quantity
- maker execution

### F6 — no-partial-fill bound

Replay the same F4 fixture under NoPartialFillExchange.

Behavior must differ exactly according to documented no-partial-fill semantics.

This is a diagnostic bound, not a selectable queue/fill model.

### F7 — order-entry latency

Freeze:

- diagnostic = 100ms
- primary = 250ms
- stress = 500ms

An order submitted locally at t must not participate in exchange queue/fill
events before t + entry latency.

### F8 — cancel latency

A cancel request does not remove the working exchange order instantaneously.

Events occurring before cancel reaches the exchange remain able to fill it.

This test is mandatory because optimistic instant cancel would understate maker
adverse selection.

### F9 — probabilistic queue diagnostic

Replay fixed cancellation/depletion fixtures under Q1 LogProb.

Required:

- deterministic output for the same event stream / configuration
- behavior may advance queue on size decreases
- Q1 never becomes primary because it produces more fills

No PnL-based model choice.

## 6. Post-fill markout plumbing

M1 may compute only mechanical markout plumbing on synthetic fills.

Required horizons:

- +1s
- +5s
- +30s

For a maker buy fill:

`markout_h = executable_mid_or_frozen_reference_h - fill_price`

For a maker sell fill use the sign-reversed convention.

M1 tests only sign/time alignment and timestamp causality.

M1 does not aggregate these into maker strategy profitability.

## 7. Maker/taker classification

Synthetic passive fills must be classified as maker fills.

Any order that crosses immediately is outside the passive M1 primary fixtures.

Fee-hook plumbing must accept:

- maker fee/rebate
- taker fee

but M1 uses neutral fees for fill-semantic tests.

## 8. Determinism

For every synthetic fixture:

- repeated replay must produce identical fill state
- identical timestamps
- identical executed quantities
- identical order status
- identical markout plumbing

No random queue model is permitted.

## 9. Real-data converter smoke

After synthetic parity is green, M1 may perform one NO-PNL conversion smoke
using a bounded prefix of one already-authorized BTC development day.

Purpose only:

- converter accepts actual Tardis files
- event order validates
- snapshot events exist
- trade events exist
- no negative feed latency
- initial book can be constructed

Do not submit a strategy order in this real-data smoke.

Do not compute maker PnL.

Do not open Aug or Sep.

## 10. Promotion gate

M1 passes only if ALL are green:

1. official Tardis converter parity
2. event-order validation
3. snapshot initialization
4. F1 touch!=fill sentinel
5. Q0 cancellation does not advance queue
6. Q0 observed trades advance queue
7. partial-fill semantics
8. no-partial-fill bound understood
9. 250ms entry latency
10. cancel latency
11. Q1 deterministic diagnostic
12. maker/taker classification
13. neutral fee hooks
14. 1s/5s/30s markout plumbing
15. real-data converter smoke

Any failure blocks maker strategy PnL.

## 11. Forbidden

M1 must not:

- design maker alpha thresholds
- optimize quote offsets
- optimize order size
- optimize cancel horizon
- optimize inventory skew
- compare strategy returns
- compute PF
- compute drawdown
- rank maker policies
- use touch=fill
- choose Q1 because it looks more profitable
- open Aug
- open Sep-01+
- open non-BTC

## 12. Next only after M1 PASS

`DEV045-M2 FINITE MAKER POLICY CONTRACT DESIGN`

M2 must freeze a small finite policy family before first maker strategy
economics.

## Current state

`DEV045_M1_REPLAY_PARITY_DESIGN_FROZEN_IMPLEMENTATION_NEXT_NO_STRATEGY_PNL`
