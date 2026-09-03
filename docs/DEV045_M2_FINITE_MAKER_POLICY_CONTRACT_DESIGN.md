# DEV045-M2 — Finite Maker Policy Contract Design

Status:

`DESIGN_FROZEN_NO_PNL`

Date: 2026-09-03

## 1. Objective

Freeze a small, economically motivated family of maker policies before any
maker strategy PnL is observed.

DEV045 exists because DEV044-T found no taker survivor under the frozen 10bp
round-trip envelope, while several mechanisms retained positive gross
executable edge. M2 attacks the dominant observed bottleneck — crossing cost —
without changing the already-frozen directional evidence.

M2 computes NO strategy PnL and selects NO winner.

## 2. Frozen parent

DEV045-M1:

`DEV045_M1_GREEN_FROZEN`

Scientific execution identity:

`589074c37a099b2414527dbc85a01de615493742`

M1 MUST NOT be modified or rerun for economic rescue.

## 3. Research anchors

The policy family is restricted to mechanisms supported by established
market-microstructure evidence:

- Avellaneda & Stoikov (2008), inventory-aware reservation-price market making,
  DOI 10.1080/14697680701381228.
- Guéant, Lehalle & Fernandez-Tapia (2013), explicit inventory constraints and
  optimal quoting, DOI 10.1007/s11579-012-0087-0.
- Gould & Bonart (2016), queue imbalance predicts near-term price direction,
  DOI 10.1142/S2382626616500064.
- Moallemi & Yuan, queue-position valuation: queue priority has material
  economic value and should not be discarded by unnecessary repricing,
  SSRN 2996221.
- Felder (2023), prediction-aware limit-order placement can reduce adverse
  selection while preserving spread capture, SSRN 4320775.
- Albers, Cucuringu, Howison & Shestopaloff (2024), live Binance/Bybit evidence
  that latency and book changes create systematically worse execution than
  naive backtests, SSRN 4677989.

High-capacity RL policy search is deliberately deferred.

## 4. Common execution shell

All eight policies use exactly the same execution shell.

Market:

`BTCUSDT Binance Futures`

Historical source:

`Tardis incremental_book_L2 + trades`

Primary queue assumption:

`RISK_ADVERSE`

Diagnostic queue assumption:

`LOG_PROB`

Q1 may never promote a policy that fails Q0.

### Decision cadence

`1 second`

Causal state only.

### Live orders

At most:

- one working bid;
- one working ask.

No pyramiding of same-side maker orders.

### Base passive quote

Wave-1 quotes join the displayed best price.

No inside-spread improvement.

No crossing.

If a policy requests a shift that would cross, clamp to the nearest passive
price.

### Order size

Per side:

`min(0.001 BTC, 1% of displayed quantity at the intended quote price)`

If this is below exchange minimum executable quantity, do not quote.

No size optimization in the first arena.

### Inventory

Hard cap:

`[-0.003 BTC, +0.003 BTC]`

At the long cap, new bid quoting is disabled.

At the short cap, new ask quoting is disabled.

A nonzero inventory that remains unresolved for 60 seconds is flattened using
the frozen taker execution path, with actual taker fee and latency.

At end of authorized replay interval:

- cancel all working maker orders;
- flatten remaining inventory executably;
- no mark-to-mid terminal profit.

### Quote maintenance

At each 1-second decision:

- if the working quote equals the policy target and the side remains enabled,
  keep the order and preserve queue position;
- otherwise cancel first;
- replace only after cancellation reaches the exchange;
- no cancel/replace overlap.

Primary order lifecycle latency:

`250ms entry / 250ms response`

Stress:

`500ms / 500ms`

Diagnostic:

`100ms / 100ms`

### Simulator

Any fill/accounting path must use the M1 safety-patched exact hftbacktest 2.4.4
source identity.

Unpatched PyPI 2.4.4 is forbidden for PnL.

## 5. Exact finite policy family

Exactly eight policies.

No ninth policy may be added after first economic output.

### M01 — SYM_JOIN

Purpose: pure spread-capture control.

- quote both sides at best bid/ask;
- no alpha skew;
- only hard inventory cap/timeout controls.

This is the null maker benchmark.

### M02 — INVENTORY_RESERVATION

Purpose: test classical inventory-risk control.

Start from M01.

Let one inventory unit = 0.001 BTC.

Reservation shift:

- long 1 unit -> shift both target quotes down 1 tick;
- long 2+ units -> shift down 2 ticks;
- short 1 unit -> shift both targets up 1 tick;
- short 2+ units -> shift up 2 ticks.

Maximum inventory shift:

`2 ticks`

No fitted risk-aversion parameter.

### M03 — L1_OBI_SKEW

Purpose: test bounded queue-imbalance fair-value skew.

Define:

`OBI = (bid_qty - ask_qty) / (bid_qty + ask_qty)`

using current L1 displayed quantities.

Start from M02 inventory reservation.

Additional reference shift:

- |OBI| < 0.25 -> 0 ticks;
- 0.25 <= |OBI| < 0.50 -> 1 tick in the sign of OBI;
- |OBI| >= 0.50 -> 2 ticks in the sign of OBI.

Total combined shift is capped to +/-2 ticks.

No OBI threshold sweep.

### M04 — MICROPRICE_SKEW

Purpose: use order-book-conditioned fair value.

Microprice:

`(ask * bid_qty + bid * ask_qty) / (bid_qty + ask_qty)`

Reference displacement:

`round((microprice - mid) / tick_size)`

clipped to:

`[-2,+2] ticks`

Combine with M02 inventory reservation and cap the final shift to +/-2 ticks.

No fitted microprice model.

### M05 — TOXICITY_VETO

Purpose: reduce fills during strongly adverse aggressive flow.

Start from M04.

Trailing causal aggressive-trade imbalance over 1 second:

`TFI = (buy_qty - sell_qty) / (buy_qty + sell_qty)`

Rules:

- TFI >= +0.60 -> retreat ask target by 1 additional tick;
- TFI <= -0.60 -> retreat bid target by 1 additional tick;
- |TFI| >= 0.80 -> disable the adverse side entirely for that decision.

All targets remain passive.

No threshold sweep.

### M06 — T10A_OFI_MAKER_ADAPTER

Purpose: reuse the strongest nontrivial DEV044 information rather than invent a
new predictor.

Use the exact frozen T10 OFI direction plus the exact frozen A0 gate:

`A0 p_touch >= 0.50`

No refit and no threshold change.

When the frozen signal is LONG:

- bid stays at its normal passive target;
- ask retreats 1 tick.

When SHORT:

- ask stays at its normal passive target;
- bid retreats 1 tick.

When A0 is closed or T10 has no direction:

- no directional skew;
- fall back to M02 inventory reservation.

This tests whether previously observed positive gross OFI edge can become
economically useful when crossing cost is removed.

### M07 — T05A_REVERSAL_MAKER_ADAPTER

Purpose: reuse the frozen short-term reversal mechanism that also showed
positive gross executable edge in DEV044.

Use exact frozen T05 direction and exact A0 gate:

`A0 p_touch >= 0.50`

No refit and no threshold change.

Apply the same one-tick adverse-side retreat convention as M06.

When gate/direction is absent, fall back to M02.

### M08 — QUEUE_PRESERVE_HYSTERESIS

Purpose: test the economic value of queue priority.

Start from M02.

A working quote is NOT canceled merely because the newly computed target moves
by one tick.

Reprice only when:

- target differs from working price by at least 2 ticks; or
- inventory cap disables the side; or
- the quote would become marketable/crossed; or
- book validity is lost.

This deliberately trades responsiveness for queue-position preservation.

## 6. Why the family is limited to eight

The first maker arena must identify mechanisms, not search hundreds of
parameters.

The family spans:

1. pure symmetric maker baseline;
2. inventory control;
3. static book imbalance;
4. microprice fair value;
5. aggressive-flow adverse-selection veto;
6. prior OFI alpha adapted to maker execution;
7. prior reversal alpha adapted to maker execution;
8. queue-priority preservation.

This is broad enough to test the key economic hypotheses while keeping
multiple-comparison risk manageable.

## 7. Fee rule

No canonical maker economic run is authorized until the user's actual
Binance Futures maker/taker fee tier is verified.

Required scenarios once fees are frozen:

1. actual personal/account fee schedule — PRIMARY;
2. neutral maker fee/rebate = 0 — diagnostic only;
3. adverse fee stress — fixed before PnL.

No optimistic rebate assumption.

No policy-specific fee.

## 8. Economic evaluation contract for later arena

The later economic arena must run all eight policies.

Primary eligibility requires, under Q0 Risk-Adverse:

- positive net executable expectancy under actual fees;
- PF > 1;
- at least 4 of 7 development days positive;
- no execution-integrity failure;
- no single day contributes >50% of total positive PnL;
- positive aggregate under 500/500ms latency stress;
- terminal inventory always flattened executably.

Q1 LogProb is diagnostic only.

A policy cannot be promoted solely because Q1 is profitable.

Family-level anti-overfit control must use aligned time blocks across all eight
policies. The exact bootstrap/max-stat implementation and block length must be
frozen before first maker PnL.

## 9. Mandatory diagnostics

Per policy report:

- submitted maker orders;
- maker fills;
- partial-fill count;
- fill ratio;
- average queue wait;
- cancel count;
- cancel-to-fill ratio;
- average inventory;
- maximum absolute inventory;
- forced-taker liquidation count;
- maker gross spread capture;
- 1s / 5s / 30s post-fill markout;
- maker fees/rebates;
- taker liquidation costs;
- net bps;
- PF;
- max drawdown;
- positive days;
- worst day;
- Q0/Q1 fill divergence;
- 250ms vs 500ms degradation.

A strategy with positive spread capture but negative post-fill markout is not
treated as healthy maker alpha.

## 10. Forbidden

M2 and the first maker arena must not:

- optimize quote distance;
- optimize order size;
- optimize inventory cap;
- optimize inventory timeout;
- sweep OBI thresholds;
- sweep TFI thresholds;
- change A0 threshold;
- refit T05/T10;
- choose Q1 because it makes more money;
- add RL;
- add a ninth policy;
- open Sep-01+;
- open non-BTC;
- use touch=fill;
- use unpatched hftbacktest accounting;
- mark terminal inventory to mid.

## 11. Next stage

After this design is frozen:

`DEV045-M3 MAKER POLICY IMPLEMENTATION + SYNTHETIC CONTRACT TESTS`

M3 must implement all eight deterministic policies and prove policy-state,
inventory, cancel/replace, and forced-flatten semantics on synthetic replay.

Still no canonical maker PnL in M3.

## Current state

`DEV045_M2_FINITE_POLICY_DESIGN_FROZEN_M3_IMPLEMENTATION_NEXT_NO_PNL`
