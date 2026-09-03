# Multi-Market Codex Lab — Architecture Decision Record

Date: 2026-09-03
Status: `ARCHITECTURE_DECISION_FROZEN`
Scope: software architecture only

## Decision

The application architecture is frozen as:

```text
MARKET / STRATEGY LAYER
        ↓
MULTI-MARKET ALLOCATOR
        ↓
CENTRAL RISK ENGINE
        ↓
UNIFIED EXECUTION INTERFACE
        ↓
┌───────────────────────────────────┐
│ Crypto Adapter                    │
│   Binance / Kraken                │
│                                   │
│ Traditional Adapter               │
│   Saxo / IBKR                     │
│                                   │
│ FX/CFD Adapter if needed later    │
│   Vantage / MT5                   │
└───────────────────────────────────┘
```

Permanent rule:

`ONE_AGENT + ONE_RISK_LAYER + ONE_INTERNAL_EXECUTION_INTERFACE + VENUE_SPECIFIC_ADAPTERS`

The application is not coupled directly to Binance, Kraken, Saxo, IBKR,
Vantage, MT5, or any future broker/exchange.

## Core interface

The unified interface exposes common semantic operations such as:

```text
get_instruments()
get_market_data()
get_order_book()
get_positions()
get_balance()
get_fees()
get_margin_state()
place_order()
cancel_order()
replace_order()
emergency_flatten()
health_check()
```

The central strategy/agent layer must not contain venue-specific API request
formats or credentials.

## Critical rule: unified interface is NOT lowest-common-denominator execution

A unified interface must not erase venue-specific execution capabilities.

Every adapter exposes an explicit capability descriptor. Example capability
surface:

```text
supports_post_only
supports_reduce_only
supports_native_stop
supports_native_take_profit
supports_market_order
supports_limit_order
supports_partial_fill
supports_queue_model
supports_level1
supports_level2
supports_level3
supports_margin
supports_leverage
supports_shorting
supports_futures
supports_options
supports_fx
supports_equities
supports_crypto_spot
supports_crypto_derivatives
supports_cancel_all
supports_dead_man_switch
supports_testnet
supports_paper_trading
supports_streaming_market_data
```

Capabilities are descriptive contracts, not assumptions.

## Capability negotiation

Before routing an executable strategy decision, the execution layer must compare
strategy requirements with adapter capabilities.

Example:

```text
strategy_requires = {
    post_only,
    level2,
    partial_fill,
    maker_taker_fee_model
}

venue_capabilities = adapter.capabilities()

if strategy_requires ⊄ venue_capabilities:
    REJECT_ROUTE
```

Permanent rule:

`UNSUPPORTED_REQUIRED_CAPABILITY => FAIL_CLOSED / NO_ORDER`

The system must never silently substitute a weaker execution behavior merely to
make an order routable.

Examples of forbidden silent degradation:

- maker/post-only strategy converted to an ordinary limit order when post-only
  behavior is required;
- L2/queue-dependent strategy routed to a venue without the required market
  depth semantics;
- reduce-only safety requirement dropped because the broker does not expose it;
- native stop requirement emulated without an explicitly tested synthetic-stop
  execution module;
- futures strategy redirected to a CFD and treated as economically identical;
- exchange maker/taker accounting reused for a spread/commission CFD broker.

## Execution engines remain asset/venue-family specific

The target system contains separate execution-validation families:

```text
CRYPTO_EXECUTION_ENGINE
FX_METALS_EXECUTION_ENGINE
EQUITIES_EXECUTION_ENGINE
```

They share the unified interface above them, but they do not share an assumed
fill model.

### Crypto exchange engine

Examples: Binance / Kraken.

Relevant mechanics can include:

- exchange LOB;
- maker/taker classification;
- post-only semantics;
- queue uncertainty;
- passive fills;
- partial fills;
- exchange latency;
- maker/taker fees;
- futures margin/liquidation rules.

### FX / metals / CFD engine

Examples: Vantage / MT5 or another broker.

Relevant mechanics can include:

- quoted spread;
- broker commission;
- slippage;
- swap/rollover;
- sessions;
- broker routing;
- stop execution behavior.

No crypto queue model is inherited automatically.

### Equities / listed-markets engine

Examples: Saxo / IBKR.

Relevant mechanics can include:

- trading calendars;
- auctions;
- exchange routing;
- tick tables;
- native order-type support;
- borrow/short restrictions;
- market-specific fees.

Each family requires its own validation lineage before live capital.

## Multi-market allocator

The allocator sits above execution engines and compares opportunities only after
venue-specific executable economics have been normalized into a common risk
representation.

It may decide:

```text
BTC       -> crypto adapter
XAUUSD    -> FX/metals adapter
EURUSD    -> FX adapter
NVDA      -> equities adapter
NO EDGE   -> ABSTAIN
```

No trade is required merely because one market is open.

## Central risk engine

Risk authority is centralized and venue-independent.

At minimum it must eventually govern:

- total portfolio exposure;
- per-asset exposure;
- per-asset-class exposure;
- per-venue exposure;
- leverage caps;
- correlated-position limits;
- daily loss limits;
- drawdown limits;
- stale-data detection;
- venue/API health;
- order-rate limits;
- duplicate-order prevention;
- cancel-all / emergency flatten;
- global trading disable switch.

Adapters may impose stricter venue rules but may never weaken central limits.

## Test-to-live rule

Each adapter follows its own evidence path:

```text
OFFLINE REPLAY
      ↓
TESTNET / DEMO / PAPER
      ↓
LIVE SHADOW MONITORING
      ↓
MINIMUM-SIZE CONTROLLED LIVE
      ↓
SEPARATELY AUTHORIZED SCALE-UP
```

Test and live credentials are separate.

Live trading credentials must not include withdrawal capability as part of the
trading-agent design.

## Relationship to DEV045

This ADR does NOT modify DEV045.

DEV045 remains:

`CRYPTO MAKER EXECUTION RESEARCH — BINANCE FUTURES BTCUSDT`

Its data source, queue assumptions, patched simulator, M01-M08 policy family,
latencies, accounting contract, M5 multiplicity control, and fee gate remain
unchanged.

Frozen scientific identity remains:

`DEV045-M5 = cbffd48a9eea77a7ace843f9c830ac96bd39a071`

Current fee-freeze work remains separate from this architecture decision.

No scientific freeze, fee gate, result, or PnL status from M0-M5 is changed by
this ADR.

If a future Kraken or other crypto venue is added, it requires an explicit
venue-replication/migration validation lineage. It cannot inherit Binance fill
or queue results by assumption.

## Future implementation order

1. Complete current DEV045 venue-specific crypto lineage.
2. Introduce the unified interface around proven execution semantics.
3. Implement explicit adapter capability descriptors.
4. Implement capability negotiation and fail-closed routing.
5. Add FX/metals execution lineage and adapter.
6. Add equities/listed-market execution lineage and adapter.
7. Add multi-market allocator.
8. Add portfolio-wide central risk controls and cross-venue kill switch.
9. Authorize coordinated multi-market live execution only after separate gates.

## Frozen architecture principles

`ONE_APPLICATION_DOES_NOT_REQUIRE_ONE_EXTERNAL_BROKER`

`UNIFIED_INTERFACE_DOES_NOT_MEAN_UNIFIED_FILL_MODEL`

`UNIFIED_INTERFACE_DOES_NOT_MEAN_LOWEST_COMMON_DENOMINATOR`

`CAPABILITY_NEGOTIATION_PRECEDES_ORDER_ROUTING`

`UNSUPPORTED_REQUIRED_CAPABILITY_FAILS_CLOSED`

`VENUE_SPECIFIC_SCIENTIFIC_EVIDENCE_IS_NOT_TRANSFERABLE_BY_ASSUMPTION`
