# DEV045 D6 Converter Validation Contract

## Status

PRE-REGISTERED / FROZEN BEFORE REAL-DATA CONVERTER EXECUTION.

D5B has already established that all fourteen frozen raw streams pass
the full-stream integrity contract with zero violations.

D6 now validates only the Tardis -> hftbacktest conversion boundary.

It does not test strategy profitability.

## Frozen parent

Parent commit:

`d8d9935579b703d10107435d9d14c3be0be49654`

Frozen D5B artifact:

`evidence/dev045_d5b_full_stream_integrity.json`

SHA-256:

`51af9bbf48d36de43ee7ce8337f6ef772cd74c555c1bc2f85db485d3d463d96a`

Required D5B state:

- status = PASS
- total violations = 0

## Frozen converter lineage

hftbacktest:

- version: `2.4.4`
- upstream commit:
  `a244a14250b42d97fc305569c93c4117cd5e1dff`

Upstream Tardis converter path:

`py-hftbacktest/hftbacktest/data/utils/tardis.py`

Frozen upstream converter Git blob:

`1ca038895d30f320561d6b28ffa13c1d788ea6bf`

The DEV045 M1 patch may modify only the frozen simulator safety targets.

The upstream Tardis converter must remain byte-identical after applying
the M1 patch.

## Existing project feed binding

D6 uses the already-frozen implementation:

`src/multimarket/dev045_m6_tardis_feed.py`

Git blob:

`8bf7d620ce54cfa0ef759e9f8a866cea39570bc8`

It must not be rewritten after observing real converted output.

The converter call semantics remain:

1. trades file first;
2. incremental_book_L2 file second;
3. `snapshot_mode="process"`;
4. `base_latency=0`;
5. `output_filename=None`.

The output is in memory only during converter validation.

## Canary day

The first real-data converter canary is:

`2026-01-01 BTCUSDT`

This day is selected only because D5B established that it has the
smallest total raw-row count among the seven frozen development days.

This is a resource-safety selection.

No PnL or economic result is used to select the canary.

## Why D6 is split

The pinned upstream converter preallocates an event array.

The frozen hftbacktest event dtype has eight aligned 8-byte fields:

- ev
- exch_ts
- local_ts
- px
- qty
- order_id
- ival
- fval

Therefore:

`event_dtype.itemsize = 64 bytes`

The converter also loads raw CSV content using Polars and creates
temporary structured arrays.

For this reason real conversion is not authorized until a separate
resource-feasibility preflight has been frozen.

## D6B: preflight and memory feasibility

D6B may open only the two frozen January 1 raw files:

- trades/BTCUSDT/2026-01-01.csv.gz
- incremental_book_L2/BTCUSDT/2026-01-01.csv.gz

D6B may run the existing `preflight_day()` function.

It may calculate:

- trade rows;
- depth rows;
- snapshot rows;
- snapshot batches;
- maximum snapshot-side rows;
- converter buffer size;
- snapshot buffer size;
- mandatory event preallocation bytes;
- currently available machine memory.

D6B MUST NOT call the Tardis converter.

The frozen engineering safety gate is:

`available memory >= 4 × mandatory event preallocation`

The factor four is a resource-safety margin for the event buffer,
Polars frames, input structured arrays, sorting, and conversion
temporaries.

It is not a statistical or economic acceptance criterion.

## D6C: real converter canary

D6C is authorized only after D6B has a frozen PASS.

D6C may convert only January 1 BTCUSDT.

It must use the exact frozen converter and project binding.

No converted `.npz` file is written.

The result must:

- be nonempty;
- satisfy the frozen M4 event validation;
- contain at least one trade event;
- contain at least one depth snapshot event;
- satisfy local timestamp >= exchange timestamp;
- remain within January 1 by local timestamp;
- have the exact frozen event dtype fields;
- have event dtype itemsize = 64 bytes.

With `snapshot_mode="process"`, output row count must satisfy:

lower bound:

`trades_rows + depth_rows`

upper bound:

`trades_rows + depth_rows + 2 * snapshot_batches`

The first D6C result is evidence whether PASS or FAIL.

## Explicit prohibitions

D6 does NOT authorize:

- M01-M08 execution;
- historical policy replay;
- PnL;
- economic evaluation;
- canonical PnL writing;
- August 1 data;
- September-or-later data;
- non-BTC data;
- network market-data acquisition;
- Railway;
- live trading.
