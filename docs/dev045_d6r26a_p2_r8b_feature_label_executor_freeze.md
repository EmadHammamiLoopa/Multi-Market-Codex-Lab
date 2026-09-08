# DEV045 D6R26A P2 R8B — Feature / label executor freeze

Parent R8A:

- HEAD: `abcfd786e5c8345b9857310f98e5e7e856d75815`
- dedicated CI: GREEN
- historical candidate simulation: NO
- P2 attempt consumed: NO

R8B freezes the pure causal feature mathematics and binds labels exactly to the already-frozen P1 fill/markout functions. It does not open Jan–Jul files, import `hftbacktest`, start candidate simulation, write the attempt marker, write canonical labels, fit models, or compute PnL.

## Window and timestamp semantics

All rolling windows are left-open/right-closed: `(t-W, t]` in local strategy time. Book windows use the last coalesced BBO/depth state with `local_ns <= t-W` as the anchor. Book observations must be strictly increasing in local time because all local market events sharing the same timestamp must be coalesced to the final post-market state before the candidate decision.

Every feature is materialized at the decision epoch after all `LOCAL_MARKET` events at that timestamp, so its stored observable-local timestamp is exactly `decision_local_ns`. Future book/flow observations may exist in an input container but are never included in a feature calculation.

Current feature support requires a valid uncrossed BBO, at least five bid and five ask levels at the decision state, and a causal book anchor at least 30 seconds before the decision.

## Frozen feature definitions

The exact 25-feature definition manifest has SHA256:

`cafe4cc9ff73e92f9d0a6b1c786a3a59769939afdd503fa3146bd262ea3dba92`

### F0 fair value

- `spread_ticks = best_ask_tick - best_bid_tick`.
- `mid = (best_bid + best_ask)/2`.
- BBO microprice uses opposite-side depth weights:
  `microprice = (bid_px*ask_qty + ask_px*bid_qty)/(bid_qty+ask_qty)`.
- `microprice_minus_mid_bps = 10000*(microprice-mid)/mid`.
- `vamp_bbo_minus_mid_bps` is intentionally identical to BBO microprice under the frozen standard BBO-VAMP definition. The resulting exact collinearity is disclosed, not hidden.
- L5 VAMP uses paired cross-side weights across the first five levels:
  `sum(bid_px_i*ask_qty_i + ask_px_i*bid_qty_i) / sum(bid_qty_i+ask_qty_i)`.

### F1 flow

- L1/L5 OBI: `(bid_qty-ask_qty)/(bid_qty+ask_qty)` using level 1 or summed levels 1–5.
- BBO OFI uses the standard Cont-style transition:
  - bid contribution: `I[pb1>=pb0]*qb1 - I[pb1<=pb0]*qb0`
  - ask contribution: `-I[pa1<=pa0]*qa1 + I[pa1>=pa0]*qa0`
  - positive values mean buy pressure.
- `bbo_ofi_1s` and `bbo_ofi_5s` are raw base-asset-quantity sums of those transitions over their causal windows.
- Trade imbalance is `(aggressive_buy_qty-aggressive_sell_qty)/(buy+sell)`, zero if no trades.
- Add imbalance is `(bid_add_qty-ask_add_qty)/(bid_add+ask_add)`, zero if no adds.
- Cancel imbalance is `(ask_cancel_qty-bid_cancel_qty)/(ask_cancel+bid_cancel)`, zero if no cancels, so positive means bullish liquidity withdrawal.
- Depth-event quantity increases map to ADD, decreases map to CANCEL; trade events are separate and are not silently folded into add/cancel flow.

### F2 toxicity

- `ofi_acceleration_1s_vs_5s = bbo_ofi_1s - bbo_ofi_5s/5`, in base-asset quantity per second.
- 250 ms depth changes are current best-depth quantity minus the best-depth quantity as of `t-250ms`, conditioned on candidate side and opposite side.
- `spread_change_1s = current_spread_ticks - spread_ticks_asof(t-1s)`.
- realized volatility over 1s/5s/30s is unannualized bps:
  `10000 * sqrt(sum(log(mid_j/mid_{j-1})^2))`, using the boundary anchor plus every coalesced BBO state in `(t-W,t]`.

### F3 execution

- side sign: `+1 BID`, `-1 ASK`.
- candidate distance is the frozen distance in ticks.
- displayed quantity is visible decision-book depth at the exact candidate price, zero if absent.
- estimated queue ahead equals that displayed quantity under the frozen risk-adverse join-behind-visible-queue estimate. This exact equality is disclosed.
- own/opposite best depth are the current level-1 quantities conditioned on candidate side.

## Label binding

R8B does not redefine labels. It calls P1 exactly for every frozen horizon:

- fill horizon origin: decision local time;
- markout horizon origin: exchange execution time;
- fill inclusion horizon for candidate markout: frozen 1 second;
- future midpoint: last BBO midpoint with exchange timestamp `<= target` only when source is observed through target;
- candidate multi-fill markout: executed-quantity-weighted mean;
- censoring remains censoring and is never mapped to no-fill.

## Closed surfaces

R8B keeps closed:

- historical file I/O;
- simulator import;
- candidate simulation;
- attempt marker write;
- canonical label write;
- model fitting;
- PnL/economic arena;
- August, September+, non-BTC, live trading.

Next after R8B GREEN: implement the raw historical event-to-book/flow adapter and real lane executor against the frozen R8A engine/writer + R8B feature/label contracts, still under a pre-execution CI surface before the one-shot Jan–Jul authorization.

`NO ECONOMIC STRATEGY EXECUTION / NO PNL / CANDIDATE LABEL SIMULATION ONLY`
