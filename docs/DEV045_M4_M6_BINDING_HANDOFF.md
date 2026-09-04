# DEV045 M4 -> M6 Binding Handoff

Date: 2026-09-04

Status:
SYNTHETIC BINDING IMPLEMENTED / LOCAL CONTRACTS GREEN /
AWAITING DEDICATED CI / NO HISTORICAL M6 OUTPUT

## Lineage

Branch:

`research/dev045-m6-m4-binding`

Frozen parent:

`5a3f7c3c117f73149efe20530b2d35394f4f02f1`

Parent meaning:

`Document DEV045 M6 pre-execution implementation handoff`

Frozen M4 replay adapter remains unchanged.

Frozen M6 economic arena core remains unchanged.

## New binding files

Source:

`src/multimarket/dev045_m4_m6_binding.py`

Tests:

`tests/test_dev045_m4_m6_binding.py`

Dedicated CI:

`.github/workflows/dev045-m6-m4-binding.yml`

## Binding contract

The binding is deliberately thin.

It converts frozen M4 replay execution evidence into frozen M6
`FillRecord` accounting inputs without changing M3 policy logic,
M4 queue/fill logic, M5 fees/inference, or M6 accounting.

### Passive maker execution

Passive GTC LIMIT responses are bound as `MAKER`.

The binding preserves:

- exact policy id
- authorized day
- exchange execution timestamp
- BUY/SELL side
- executed quantity
- executed price
- executed quote notional
- explicit NO_FILL events

Maker/taker role is never inferred from PnL or price behavior.

### Taker forced flatten

A final M4 `ReplayOrderView` alone is explicitly forbidden as the
historical accounting source for a forced MARKET flatten.

Reason:

hftbacktest PartialFillExchange can execute one MARKET request across
multiple price levels. Each internal fill is applied to simulator state,
while the final order view can contain only the most recent execution
quantity and price.

Therefore forced flatten accounting is bound from the simulator state
delta captured immediately before and immediately after the synchronous
waited MARKET request.

The binding conserves:

- aggregate executed quantity
- aggregate trading value / quote notional
- position delta
- cash/balance delta
- trade-count delta
- exact VWAP
- explicit `TAKER` liquidity role

This prevents under-accounting when a flatten walks multiple book levels.

## Frozen simulator semantics verified

Pinned upstream hftbacktest identity:

`a244a14250b42d97fc305569c93c4117cd5e1dff`

Version:

`2.4.4`

Required frozen patchset:

- issue #312 exact-final-fill cleanup
- issue #316 partial-fill local accounting

Pinned order constants:

- BUY = 1
- SELL = -1
- NEW = 1
- FILLED = 3
- CANCELED = 4
- PARTIALLY_FILLED = 5

The upstream PartialFillExchange implementation sets `exec_qty` to the
quantity of the individual fill, not cumulative order quantity.

The same implementation may execute MARKET orders through multiple depth
levels, which is why forced flatten uses state deltas rather than only
the final order view.

## Local synthetic validation

Environment:

- Python 3.14.4
- NumPy 2.5.2
- pytest 7.4.3

Binding suite:

`17 passed, 1 skipped`

The single local skip is the pinned hftbacktest constant-identity test,
because hftbacktest was not installed in the isolated local validation
environment.

The dedicated GitHub CI installs the exact frozen patched simulator and
therefore must execute that contract rather than skip it.

Frozen upstream contracts:

`21 passed`

This included:

- M6 economic arena
- M5 fee amendment
- M5 preregistration

Static compile:

PASS

`git diff --check`:

PASS

Frozen identities after validation:

- M3 policy unchanged
- M4 replay adapter unchanged
- M5 fee amendment unchanged
- M6 economic arena core unchanged

## Frozen economic boundary

Venue:

Binance Futures / USDⓈ-M

Symbol:

BTCUSDT

Primary fees:

- maker 0.0002
- taker 0.0005

Pre-result 1.5x adverse fee stress:

- maker 0.0003
- taker 0.00075

Historical M6 development days remain exactly:

- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

Policies remain exactly M01..M08.

## Current safety boundary

`M4_FROZEN_UNCHANGED = YES`

`M6_CORE_FROZEN_UNCHANGED = YES`

`M6_HISTORICAL_OUTPUT_GENERATED = NO`

`M6_CANONICAL_PNL_ARTIFACT_WRITTEN = NO`

`SEP01_PLUS_OPENED = NO`

`NON_BTC_OPENED = NO`

`LIVE_TRADING_AUTHORIZED = NO`

## Next action

Only after the dedicated M4->M6 binding CI is fully green:

1. freeze this binding identity;
2. construct the historical replay execution driver around this frozen
   binding;
3. validate driver contracts without opening unauthorized data;
4. perform the first and only preregistered Jan-Jul M6 historical arena
   execution.

The first historical output is evidence.

It must not trigger retuning, policy modification, fee modification,
eligibility modification, or rerunning the canonical arena.
