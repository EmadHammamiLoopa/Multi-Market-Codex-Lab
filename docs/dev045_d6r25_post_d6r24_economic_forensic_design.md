# DEV045-D6R25 — Post-D6R24 Economic Forensic Design

## Status

DESIGN ONLY. No D6R24 day artifact is opened or hashed during implementation or CI. No historical market source is opened. No replay, simulator, economic arena rerun, fee amendment, policy retuning, or live trading is authorized.

## Frozen parent

- D6R24 freeze HEAD: `06eff337e4a039cf47c8b10a41aa91e52df4c792`
- D6R24 execution HEAD: `b04a18f8eb5b4689abd15d7cdf6a6c889ee36212`
- Canonical result SHA256: `fafae1e2d98a6f5ad63188f69b61b5d42b53ca2e86a7032971378d7f82e31316`
- Canonical status: `CANONICAL_112_COMPLETE`
- Frozen classification: `ENGINEERING_CANONICAL_PASS_ECONOMIC_FALSIFICATION_FAIL_ALL_POLICIES`
- Engineering: 112/112, 112 audits, integrity PASS, terminal flat PASS.
- Economics: no survivors; every M01-M08 has negative primary and stress expectancy and zero positive days.

D6R24 is consumed and remains failed economically regardless of D6R25 findings.

## Question

Why is net expectancy negative? The forensic separates what the frozen replay outputs can identify exactly from what they cannot identify.

The first decision is intentionally coarse and falsifiable:

1. **Is gross pre-fee expectancy already non-positive?** If yes, zero fees cannot rescue that policy family; the problem is not fees.
2. **If gross expectancy is positive, is it overwhelmed by fee drag?** If yes, a new preregistered execution/economic design may be justified, but D6R24 is not reinterpreted.
3. **How much of fee drag comes from maker versus taker notional, and how does primary-to-stress degradation split between gross execution and fees?**

## Input surface

Only the seven immutable D6R24 day-result JSON artifacts identified by the D6R24 freeze metadata may be read in the later forensic execution. Each file must match its frozen byte size and SHA256 before its cycles are used.

Processing is one day at a time. The seven artifacts are never held in memory simultaneously.

The frozen day payload stores both raw fills and flat-to-flat cycles. D6R25 uses the already-accounted cycles for economic decomposition. It does not call `run_economic_arena` and does not reconstruct market state.

## Exact cycle fields used

- `policy_id`
- `day`
- `start_timestamp_ns`
- `end_timestamp_ns`
- `cash_pnl_before_fees`
- `fees`
- `net_pnl`
- `entry_notional`
- `net_bps`
- `maker_notional`
- `taker_notional`
- `fill_count`

## Frozen formulas

For every cycle:

- gross bps = `10000 * cash_pnl_before_fees / entry_notional`
- fee-drag bps = `10000 * fees / entry_notional`
- net bps = `10000 * net_pnl / entry_notional`
- parity: gross bps - fee-drag bps = net bps, within float tolerance.

Both cycle-mean and notional-weighted gross/fee/net bps are reported. The original D6R24 eligibility used cycle-mean net bps; D6R25 therefore keeps that quantity primary and reports weighted bps as a diagnostic, not a replacement criterion.

## Preregistered diagnostics

For each policy and scenario, plus day and four-hour descriptive slices where applicable:

- cycle count
- total gross cash PnL, total fees, total net PnL
- cycle-mean gross, fee-drag, and net bps
- notional-weighted gross, fee-drag, and net bps
- gross/fee/net accounting parity
- positive gross-cycle count/share and positive net-cycle count/share
- gross-bps and net-bps q05/q50/q95
- cycle-duration q05/q50/q95
- maker/taker notional totals and shares
- maker and taker fee components at the frozen scenario rates
- zero-fee expectancy (= gross expectancy)
- uniform fee-multiplier break-even diagnostic
- daily gross/fee/net decomposition
- four-hour block gross/fee/net decomposition
- primary-minus-stress gross, fee, and net expectancy deltas
- forced-flatten count as context only, with no PnL attribution

### Break-even fee interpretation

If cycle-mean gross expectancy is <= 0, the classification is:

`NO_NONNEGATIVE_FEE_MULTIPLIER_CAN_RESCUE_EXPECTANCY`

If gross expectancy is > 0 but net expectancy is < 0, the uniform fee multiplier needed for break-even is:

`gross_expectancy_bps / fee_drag_bps`

This is diagnostic only. It does not authorize changing the frozen Binance fee assumptions or retroactively promoting a D6R24 policy.

## Explicitly not identifiable from the frozen artifact

### Forced-flatten PnL or fee attribution

The replay payload stores `flatten_order_ids`, but the serialized `FillRecord` omits `order_id`. There is therefore no exact join from forced-flatten order IDs to individual fills. D6R25 may report forced-flatten counts but must emit `NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACT` for forced-flatten PnL/fee attribution.

### Adverse-selection markout

No post-fill midprice/reference-price markout series is saved in the D6R24 day artifact. Exact 1s/5s/30s adverse-selection markouts cannot be recovered without reopening market data, which this forensic does not authorize.

### Spread capture versus directional price movement

Flat-to-flat gross cash PnL is observable, but its decomposition into quoted-spread capture and subsequent reference-price movement is not stored. No invented decomposition is allowed.

### Queue-position counterfactual

Executed fills are observed; counterfactual queue position and unfilled opportunity value are not.

## Interpretation guardrails

- D6R24 remains an economic FAIL.
- No M01-M08 policy may be promoted from D6R25.
- No frozen fee is amended.
- No policy threshold, quote distance, inventory limit, latency, or support rule is retuned.
- Primary-vs-stress gross degradation is descriptive scenario sensitivity, not proof of causal latency attribution.
- Unsupported quantities are reported as not identifiable rather than approximated.

## Decision classes after the forensic

Exactly one high-level disposition is selected from the evidence:

1. `ZERO_FEE_GROSS_EDGE_NEGATIVE_POLICY_FAMILY_REJECT`
2. `POSITIVE_GROSS_EDGE_FEE_DOMINATED_REDESIGN_EXECUTION_ECONOMICS`
3. `MIXED_BY_POLICY_OR_REGIME_NEW_PREREGISTERED_FAMILY_REQUIRED`

The disposition informs a fresh successor design. It does not reopen D6R24.
