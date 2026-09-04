# DEV045 M6 Historical Feed Contract Handoff

Date: 2026-09-04

Status:

HISTORICAL FEED CONTRACT IMPLEMENTED /
SYNTHETIC CONTRACTS GREEN /
FROZEN REGRESSIONS GREEN /
NO HISTORICAL DATA OPENED /
NO HISTORICAL REPLAY EXECUTED

## Lineage

Branch:

`research/dev045-m6-historical-replay-driver`

Frozen parent:

`bc3340c9c085eb62a272b6672842f960692f51bb`

Parent meaning:

Frozen DEV045 M4 -> M6 replay binding.

## New implementation

Source:

`src/multimarket/dev045_m6_tardis_feed.py`

Tests:

`tests/test_dev045_m6_tardis_feed.py`

CI:

`.github/workflows/dev045-m6-historical-feed.yml`

## Historical source contract

Venue source:

Tardis downloadable Binance Futures feed.

Frozen symbol:

`BTCUSDT`

Authorized development days only:

- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

Expected local Phase0DL raw layout:

`data/v23_phase0dl_l2_raw/trades/BTCUSDT/<day>.csv.gz`

and

`data/v23_phase0dl_l2_raw/incremental_book_L2/BTCUSDT/<day>.csv.gz`

August 1 remains sealed.

No September-or-later data is authorized.

No non-BTC data is authorized.

## Converter identity

The driver does not reimplement Tardis event conversion.

It reuses the official Tardis converter from the exact pinned
hftbacktest 2.4.4 source commit:

`a244a14250b42d97fc305569c93c4117cd5e1dff`

The frozen M1 safety patch remains:

- issue #312 exact-final-fill cleanup
- issue #316 partial-fill local accounting

The Tardis converter itself is not modified by this patch.

## Important queue-ordering invariant

The official converter requires:

1. trades input first;
2. incremental_book_L2 input second.

Reason:

a trade-related depth update can already reflect the traded quantity.
Processing the depth update before its associated trade can reduce queue
position twice.

The historical feed contract freezes trades-before-depth ordering.

## Raw fail-closed preflight

Before conversion the module rejects:

- unauthorized day
- nonlocal/network raw root
- missing file
- wrong gzip CSV suffix
- wrong Tardis header
- wrong exchange
- wrong symbol
- invalid timestamps
- negative raw feed latency
- out-of-day local timestamps
- reversed local ordering
- nonfinite price or amount
- nonpositive trade quantity
- unknown trade aggressor side
- invalid L2 side
- negative L2 amount
- invalid snapshot marker
- missing SOD snapshot
- depth rows before SOD snapshot
- file ending inside an unfinished snapshot batch

Negative feed latency is rejected before the upstream converter can
correct it automatically because frozen M4 requires nonnegative raw feed
latency.

## Memory safety

The upstream converter defaults to a very large event buffer.

The new preflight counts raw rows and snapshot batches first and creates
a bounded conversion buffer sized from the validated daily files.

This prevents unnecessary 100-million-row default allocation during the
historical execution.

## Post-conversion contract

Converted data must:

- be nonempty
- satisfy frozen M4 `validate_events`
- remain inside the authorized UTC day by local timestamp
- contain trade events
- contain depth snapshot events

No converted output file is written by the feed contract.

## Synthetic validation

Feed tests:

`6 passed`

They cover:

- exact BTC development scope
- bounded buffer sizing
- official converter integration
- frozen M4 event validation
- negative-latency rejection
- unknown trade-side rejection
- SOD snapshot requirement

The full frozen DEV045 regression set was also rerun in the same patched
simulator environment before this handoff was written.

## Execution boundary

The module explicitly freezes:

`HISTORICAL_REPLAY_EXECUTION_ENABLED = False`

`HISTORICAL_PNL_OUTPUT_ENABLED = False`

`NETWORK_ACQUISITION_ENABLED = False`

Therefore this phase does not:

- open Jan-Jul historical files
- run M01-M08
- run hftbacktest historical replay
- call M6 economic arena
- calculate strategy PnL
- write the canonical M6 result
- open Aug-01
- open Sep-01+
- open non-BTC
- access Railway
- access bucket/volume
- authorize live trading

## Next action

Only after dedicated historical-feed CI is fully green:

1. freeze this feed-contract commit;
2. implement the historical replay orchestration contract;
3. synthetically prove policy -> M4 -> binding -> M6 fill/audit wiring;
4. freeze that orchestration;
5. reread M5/M6 preregistration and frozen handoffs;
6. only then perform the first one-shot Jan-Jul M6 historical arena.

The first historical M6 output is evidence and must not be used for
retuning or rerunning the canonical arena.
