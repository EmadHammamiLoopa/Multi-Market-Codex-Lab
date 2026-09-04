# DEV045 D5 Full-Stream Integrity Contract

## Status

PRE-REGISTERED / FROZEN BEFORE FULL RAW STREAM SCAN.

This document defines the acceptance rules for the first complete
content scan of the fourteen raw BTCUSDT streams frozen by D4.

No full raw-file content scan has been executed while authoring or
freezing this contract.

## Parent identity

Parent commit:

`47d45f011c15f9d37089bf2627228a524a63e1cf`

Frozen D4 manifest:

`evidence/dev045_d4_raw_provenance.tsv`

Frozen D4 manifest SHA-256:

`7fa6cf76ee8c6da98c5758756c887f0fb7b4d2e5eaf6b0e9f87551dce9981c12`

## Exact scope

The D5 full-stream integrity scan may read only the fourteen streams
already frozen by D4:

- exchange: `binance-futures`
- symbol: `BTCUSDT`
- kinds:
  - `trades`
  - `incremental_book_L2`
- days:
  - `2026-01-01`
  - `2026-02-01`
  - `2026-03-01`
  - `2026-04-01`
  - `2026-05-01`
  - `2026-06-01`
  - `2026-07-01`

No August 1 data, September-or-later data, non-BTC data, or network
market-data acquisition is permitted.

## File/provenance gates

Each frozen stream must:

1. exist as a regular file;
2. not be a symlink;
3. retain the D4-frozen byte size;
4. retain the D4-frozen SHA-256;
5. be readable through gzip EOF without decompression/truncation error;
6. contain at least one data row;
7. retain its exact expected header;
8. contain exactly eight fields per data row.

Any violation is D5B FAIL.

## Exact headers

Trades:

`exchange,symbol,timestamp,local_timestamp,id,side,price,amount`

Incremental L2:

`exchange,symbol,timestamp,local_timestamp,is_snapshot,side,price,amount`

## Global row identity

Every row must have:

- exchange exactly `binance-futures`;
- symbol exactly `BTCUSDT`;
- exchange timestamp corresponding in UTC to the stream's frozen D4 day.

Allowed side values:

- trades: `buy`, `sell`
- incremental L2: `bid`, `ask`

Unexpected side values are a failure.

The contract requires allowed-domain membership; it does not require
every allowed side value to appear in every individual file.

## Numeric rules

Both timestamps must parse as positive integers.

Price and amount must parse as finite numeric values.

Price:

- trades: `price > 0`
- incremental L2: `price > 0`

Amount:

- trades: `amount > 0`
- incremental L2: `amount >= 0`

### Depth zero quantity

A zero amount in `incremental_book_L2` is explicitly valid.

It represents level deletion/removal semantics and MUST NOT be treated
as corrupted market data.

D5A observed 114 depth zero-amount rows across the 14 initial
256-row samples.

The number `114` is descriptive only.

It is:

- NOT an acceptance threshold;
- NOT an expected full-stream count;
- NOT a target;
- NOT a reason to alter D5B after the full scan.

Trades remain strictly `amount > 0`.

## Timestamp/ordering rules

For every row:

`local_timestamp >= timestamp`

This is the exchange-to-local observation relationship.

Separately, the physical row sequence inside each file must satisfy:

`local_timestamp[i] >= local_timestamp[i-1]`

Equality is allowed.

This local-time ordering rule exists because replay must receive
events in nondecreasing local observation time.

### Exchange timestamp ordering is NOT a D5 gate

D5 does NOT require exchange timestamps themselves to be monotonically
nondecreasing.

An exchange event timestamp may therefore be less than a preceding
row's exchange timestamp without automatically failing D5, provided
the local observation ordering and all other gates remain valid.

This distinction is frozen before the full scan.

## Incremental L2 snapshot rules

`is_snapshot`, case-normalized, must belong to:

- `true`
- `false`

Each incremental L2 file must contain at least one row with
`is_snapshot=true`.

Depth rows with `amount=0` remain allowed even when encountered in
snapshot material.

## Explicit non-gates

The following are NOT D5 integrity acceptance gates:

- trade-ID uniqueness;
- whole-row uniqueness;
- monotonic exchange timestamp ordering;
- profitability;
- expectancy;
- profit factor;
- fill quality;
- policy ranking;
- strategy performance.

They may not be silently added to D5 after seeing full-stream output.

## D5B execution boundary

D5B is the canonical full-stream integrity scan under this frozen
contract.

D5B may:

- verify D4 provenance;
- decompress and inspect every row of the exact 14 frozen streams;
- compute structural/integrity counts and diagnostics;
- write a D5 integrity evidence artifact.

D5B may NOT:

- run the Tardis converter;
- run hftbacktest;
- execute M01-M08;
- compute historical PnL;
- execute the economic arena;
- write canonical PnL;
- open August 1;
- open September-or-later data;
- open non-BTC market data;
- acquire market data from the network;
- touch Railway;
- authorize live trading.

## Failure discipline

The first canonical D5B result is evidence.

If a failure reflects a genuine data-integrity violation, the failure
is frozen.

If a failure is proven to come from implementation or from an
incorrectly encoded frozen contract rule, it must be corrected through
an explicit narrowly scoped lineage step. It must not be silently
rerun with relaxed conditions.

## Relationship to later stages

Passing D5 proves only that the frozen raw streams satisfy the
pre-registered structural/content integrity contract.

It does NOT establish strategy profitability.

Converter validation, historical-driver validation, the evidence map,
and the historical economic one-shot remain later stages.
