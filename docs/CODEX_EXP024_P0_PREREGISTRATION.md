# CODEX-EXP-024-P0 Preregistration

Status: **PREREGISTERED BEFORE FRESH PROSPECTIVE COLLECTION**

Date frozen: 2026-08-29

Experiment ID: `CODEX-EXP-024-P0`

Parent preserved readiness commit:

`3a343cef8520a5eb7f966e9ee31826a1ff85b930`

This phase is data acquisition and integrity only. It creates a genuinely
fresh BTCUSDT bookTicker holdout for a separately preregistered future
prospective experiment. It makes no predictive claim.

## Frozen lineage

- EXP022-P1 invalid preserved commit:
  `91ae1465a20354082e9005eff1742ac3b2b73651`;
- EXP023-P0 preregistration commit:
  `ee34a50950f7ad78b608611743f4ac0a2f480f63`;
- EXP023-P0 corrected implementation commit:
  `306446a4a215680076ad96b32781499ba4abe6b1`;
- EXP023-P0 preserved readiness commit:
  `3a343cef8520a5eb7f966e9ee31826a1ff85b930`;
- EXP023-P0 readiness artifact:
  `evidence/codex/exp023_p0_implementation_correction/IMPLEMENTATION_CORRECTION_READINESS.json`;
- required readiness artifact SHA-256:
  `4eaf158b2517cf6c0be2efc2e7026a73a6b9986977d2c78499bb5785f142c1af`;
- required readiness status:
  `IMPLEMENTATION_CORRECTION_READY_FOR_FRESH_PROSPECTIVE_VALIDATION`.

The consumed 2026-08-28 prospective raw file and finalized grid are not
EXP024-P0 inputs. They must not be opened, read, hashed, copied, parsed,
inspected, summarized, or analyzed.

## Purpose and non-claim scope

EXP024-P0 has one purpose: prospectively acquire and causally finalize one
complete future UTC day of the same minimum Binance USD-M Futures BTCUSDT
bookTicker information set validated by EXP022-P0.

EXP024-P0 does not:

- construct or score a target;
- fit or score a model;
- calculate ROC AUC, average precision, lift, calibration, or any other
  predictive metric;
- score direction, PnL, or leverage;
- inspect an older August holdout;
- use historical backfill or reconstruct missed data;
- change the later scientific feature, target, model, support, null, or
  ranking gates.

## Frozen prospective day and launch condition

Symbol:

`BTCUSDT`

Venue:

`Binance USD-M Futures`

Frozen collection day:

`2026-08-30 UTC`

Day bounds:

- start: `2026-08-30T00:00:00Z` inclusive;
- end: `2026-08-31T00:00:00Z` exclusive.

The collector may run only if its frozen implementation is launched and armed
before `2026-08-30T00:00:00Z`. The collector must record a durable
`collector_armed` transport record with a local wall-clock timestamp strictly
before UTC midnight.

If the launch-time check occurs at or after UTC midnight, collection must
refuse before opening a raw output. A late launch must never be called a full
day, must not be backfilled, and must not silently switch to another date.

If the 2026-08-30 deadline cannot be met, this frozen collection must not run.
A new explicitly frozen future day is required.

## Frozen source and raw protocol

Primary stream:

`btcusdt@bookTicker`

Endpoint family:

`wss://fstream.binance.com`

Only the public Binance USD-M Futures WebSocket source is permitted. No
authentication, trading endpoint, REST historical API, alternate stream,
backfill API, or additional data source is allowed.

Every accepted quote preserves the same EXP022 fields:

- local receive wall-clock nanoseconds and UTC rendering;
- local monotonic receive nanoseconds;
- connection epoch;
- exchange event time `E`, when present;
- exchange transaction time `T`, when present;
- update id `u`;
- symbol `s`;
- best bid price and quantity `b`, `B`;
- best ask price and quantity `a`, `A`.

Transport records preserve collector arming, connection attempts, connection
open/close, transport errors, collection end, epoch, and local clocks.

Raw records are independent, append-free, lossless gzip JSONL. The frozen raw
path for a `/data` deployment root is:

`/data/bookticker/BTCUSDT/2026-08-30.jsonl.gz`

The output must be created exclusively. An existing file, including an empty
file or partial prior attempt, must cause refusal. An interrupted raw file is
preserved as failure evidence and is never resumed or merged.

## Frozen raw acceptance semantics

The EXP022 acceptance rules remain exact. Reject a quote update if:

- its symbol is not BTCUSDT under the frozen parser;
- best bid or ask is non-finite or non-positive;
- best ask is less than or equal to best bid;
- either quantity is non-finite or negative;
- local receive wall-clock time is earlier than the previous accepted quote;
- local monotonic receive time is earlier than the previous accepted quote.

Rejected records remain in raw diagnostics and are never used as grid state.
No quote outside the frozen UTC day may be accepted.

## Frozen causal finalization

The causal clock is local receive time. A quote received at local time `r` may
affect only grid timestamps `t >= r`. Exchange timestamps never backdate a
quote.

After the day ends, finalize sequentially with the memory-safe EXP022
streaming semantics into exactly 345,600 rows:

`00:00:00.000, 00:00:00.250, ..., 23:59:59.750 UTC`

The exact CSV columns and order remain:

1. `local_timestamp_us`
2. `best_bid`
3. `best_ask`
4. `mid`
5. `book_valid`
6. `quote_age_ms`
7. `connection_epoch`
8. `source_update_id`
9. `exchange_event_time_ms`
10. `exchange_transaction_time_ms`

At every grid time, use the latest accepted quote whose local receive time is
at or before the grid time. There is no interpolation, future fill, prior-day
fill, backfill, or reconstruction.

A grid quote is valid only if:

1. an accepted quote exists at or before the grid time;
2. bid is finite and positive;
3. ask is finite and strictly greater than bid;
4. quantities are finite and non-negative;
5. symbol is BTCUSDT;
6. accepted wall and monotonic clocks did not reverse;
7. the quote belongs to the active connection epoch;
8. quote age is no more than 2,000 ms.

A connection attempt, close, transport error, or collection end invalidates
the prior quote state. `connection_opened` activates the new epoch. A new epoch
requires a fresh accepted quote before any row becomes valid.

## Full-day and failure policy

A complete prospective observation attempt requires all of:

- exactly one valid `collector_armed` record strictly before day start;
- exact frozen collector metadata and a full 40-character implementation
  commit recorded in that record;
- at least one connection attempt;
- exactly one `collection_end` record at or after day end;
- no accepted quote outside the frozen day;
- the unchanged minimum valid-grid coverage of 99.0%;
- every frozen EXP022 integrity gate.

The 99.0% validity gate is retained exactly; it is neither loosened nor used to
excuse a late start or missing end marker.

If the process is interrupted and no valid end marker exists, or if collection
starts late, finalization must preserve a failed integrity result. Do not
restart, resume, backfill, repair, merge, or silently switch dates. A new
future day requires a new explicit freeze.

## Frozen integrity gates

`PROSPECTIVE_BOOKTICKER_DATA_READY`

is permitted only if all of these inherited conditions pass:

- raw file exists and is non-empty;
- grid has exactly 345,600 rows;
- grid spacing is exactly 250,000 microseconds;
- first timestamp is exactly UTC midnight;
- last timestamp is exactly 23:59:59.750 UTC;
- valid coverage is at least 0.99;
- no invalid or crossed price was accepted;
- no negative quantity was accepted;
- no accepted wall-clock reversal occurred;
- no accepted monotonic-clock reversal occurred;
- no wrong-symbol quote was accepted;
- no future quote was used;
- raw and grid SHA-256 values are recorded;
- raw and grid byte sizes are recorded;
- transport, reconnect, acceptance, rejection, and coverage diagnostics are
  reported;
- the full-day arming, metadata, day-scope, and collection-end conditions
  above pass;
- every no-analysis guard has its frozen false value.

If acquisition completes but any integrity gate fails:

`FAIL_PROSPECTIVE_BOOKTICKER_DATA_INTEGRITY`

If provenance, execution, one-shot, or protocol logic is violated:

`INVALID`

These statuses are data integrity results only. None is predictive.

## No-analysis guards

Throughout EXP024-P0 all of these remain false:

- `older_august_holdout_opened`;
- `historical_aug1_feature_reparsed`;
- `target_scored`;
- `model_fit`;
- `auc_scored`;
- `direction_scored`;
- `pnl_scored`;
- `leverage_scored`.

Network access is permitted only for the later frozen prospective WebSocket
acquisition. It is not permitted during preregistration, implementation, or
synthetic testing.

## Output and one-shot rule

Expected finalized grid path for a `/data` evidence root:

`/data/evidence/codex/exp024_prospective_bookticker/BTCUSDT/2026-08-30_BOOKTICKER250.csv`

Expected audit artifact name:

`PROSPECTIVE_BOOKTICKER_AUDIT.json`

The audit records raw/grid paths, bytes, SHA-256 values, raw diagnostics, grid
diagnostics, exact integrity gates, implementation commit, preregistration
SHA-256, lineage readiness SHA-256, and all no-analysis guards.

Existing grid, audit, or `.part` outputs must never be overwritten. The audit
is created through an exclusive `.part` file and an atomic move.

## Relationship to a future P1

P0 readiness does not authorize target construction, model fitting, scoring,
ranking metrics, direction, PnL, or leverage. A separate future P1 protocol
must be preregistered and frozen before the fresh grid is opened analytically.

At preregistration creation time, no 2026-08-30 network collection was
started, no 2026-08-28 market-data file was accessed, no older August holdout
was opened, and no target, model, AUC, AP, lift, direction, PnL, or leverage
quantity was calculated.
