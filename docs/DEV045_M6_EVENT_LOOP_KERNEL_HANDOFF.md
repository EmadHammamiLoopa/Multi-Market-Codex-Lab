# DEV045-D2 Actual Event-Loop Kernel Handoff

Date: 2026-09-04

## Status

ACTUAL PATCHED-SIMULATOR EVENT-LOOP KERNEL READY FOR FREEZE

Scope:

SYNTHETIC / IN-MEMORY ONLY

No historical raw files opened.
No historical replay executed.
No historical PnL computed.
No economic arena executed.
No canonical result written.

## Parent

DEV045-D1:

`d7650e26f2ff9069206fcea27542cb98b19111f6`

Dedicated D1 CI:

`33893854676`

Conclusion:

`SUCCESS`

## D2 local verification

Final local gate:

- D2 tests: 13 passed
- D1 regression: 32 passed
- M4 + M4/M6 binding regression: 24 passed
- compile: PASS
- frozen blob identities: PASS
- refined prohibited-surface audit: PASS

## First D2 failure and correction

The first real-kernel run failed because D2 referenced:

`hftbacktest.PARTIALLY_FILLED`

The pinned Python package exports order-status constants from:

`hftbacktest.order`

The kernel was corrected to import:

- NONE
- NEW
- EXPIRED
- FILLED
- CANCELED
- PARTIALLY_FILLED

from `hftbacktest.order`.

No policy behavior changed.

After that namespace-only correction:

`13/13 D2 tests PASS`

## Static-safety false positive

The first static grep used the broad token:

`requests`

This incorrectly matched ordinary local counters:

- `cancel_requests`
- `submit_requests`

It did NOT indicate network access.

The static audit was refined to detect actual imports/calls such as:

- import requests
- requests.get/post/...
- import httpx
- boto3 client/resource
- open(...)
- Path(...)
- convert_day(...)
- run_economic_arena(...)
- railway

The refined audit passed.

No source code was modified to resolve that static-gate false positive.

## D1.5 same-timestamp diagnostic

A synthetic diagnostic tested two half-lot aggressive trades at the same
timestamp against one frozen M3 one-lot passive order.

Observed:

- final ReplayOrderView exec_qty = 0.001
- simulator state volume delta = 0.001
- simulator position delta = 0.001
- simulator num_trades delta = 1

The diagnostic assertion expecting `num_trades_delta == 2` was incorrect.

This did not reveal maker-accounting loss.

Frozen M3 guarantees:

- LOT_SIZE = 0.001
- BASE_ORDER_QTY = 0.001
- every executable passive quote is exactly one lot

Therefore no new maker state-delta accounting amendment was introduced.

Frozen passive M4->M6 ReplayOrderView binding remains authoritative.

Forced MARKET flatten remains different and continues to bind from simulator
state deltas because one MARKET request may cross multiple price levels.

## What D2 proves on the real patched simulator

D2 exercises:

- patched hftbacktest 2.4.4
- RiskAdverse queue model
- PartialFillExchange
- frozen primary and stress latency
- asynchronous order submission
- asynchronous cancellation
- no request overlap
- exact local one-second policy scheduler
- dynamic simulator L1
- causal 1-second aggressive-trade window
- maker fill binding
- local inventory-knowledge clock
- exact 60-second timeout
- quote cancellation before flatten
- executable MARKET flatten
- M4->M6 taker state-delta binding
- terminal flat inventory

## Clock domains preserved

Policy / feature clock:

`LOCAL_STRATEGY_TIME`

Inventory timeout clock:

`LOCAL_POSITION_KNOWLEDGE_TIME`

Economic M6 FillRecord timestamp:

`EXCHANGE_EXECUTION_TIME`

These remain deliberately distinct.

## D2 policy scope

D2 proves the common execution kernel using:

- M01
- M02

D2 deliberately rejects:

- M03
- M04
- M05
- M06
- M07
- M08

at this layer.

This is intentional.

Policy-specific integration belongs to D3.

## D3 next gate

After dedicated D2 CI is green, build policy-specific synthetic integration.

D3 must prove all eight frozen policies without historical data.

Required:

### M03

Dynamic L1 OBI from simulator depth.

### M04

Dynamic microprice skew from simulator depth.

### M05

Causal aggressive buy/sell 1-second flow window.

No future trade use.

### M06 / M07

M5A + M5B semantics:

Jan-Mar:

- base-only / M02-equivalent

Apr-Jul exact local minute:

- exact A0 + causal legacy state -> APPLY_ADAPTER
- missing either -> FALLBACK_TO_M02

Apr-Jul intermediate seconds:

- NO_ALPHA_UPDATE
- no A0 query
- no probability carry

### M08

Frozen queue-preserve hysteresis.

### All policies

- asynchronous order lifecycle
- no cancel/submit overlap
- maker binding exactly once
- local inventory age
- exact timeout
- executable terminal flatten
- terminal zero inventory

## Still forbidden after D2

Until D3 is frozen:

- no Jan-Jul raw historical file opening;
- no Tardis historical conversion;
- no historical policy replay;
- no M6 economic arena;
- no historical PnL;
- no canonical result.

After D3, immutable provenance for the intended 14 raw files is the next
historical-data gate.

Only after provenance and final preregistration/handoff reread may the first
one-shot M6 historical replay be authorized.

The first historical result is evidence and cannot authorize retuning.

## Post-freeze generic unit-test compatibility correction

Freeze commit:

`6344326a083747bc04548652fa5136de7a046068`

The repository-wide `test.yml` Python 3.12 job failed during unittest
discovery before executing any D2 test.

Exact failure:

`ModuleNotFoundError: No module named 'hftbacktest'`

Reason:

the generic repository test matrix installs the normal project dependencies
but intentionally does not build/install the patched hftbacktest simulator.

D2 had imported `hftbacktest.order` at module-import time solely to obtain
order-status constants.

Correction:

- remove the top-level hftbacktest dependency from D2;
- reuse already-frozen M4->M6 status constants for NEW/FILLED/CANCELED/
  PARTIALLY_FILLED;
- retain pinned upstream NONE=0 and EXPIRED=2;
- dedicated D2 patched-simulator CI independently verifies all six values
  against the exact upstream/patched hftbacktest 2.4.4 installation.

No D2 strategy, lifecycle, timing, fill, queue, fee, or economic behavior
changes.

Historical execution remains closed.
