# DEV045 D6R8A — Feb–Jul Resource Scaling Contract

Status: CONTRACT ONLY / NO NEW RAW DAY OPEN / NO CONVERSION

Parent:

`c301e691ae89675f6e244a7b987d3cb0b4488381`

D6R7B is frozen PASS and its repository CI is green.

## Why this gate exists

The bounded converter successfully produced the canonical Jan 1 artifact,
but the real full-day run peaked at **9,946,800,128 bytes RSS** while the
pre-run `MemAvailable` was **10,097,618,944 bytes**.

That is about **98.506%** of the observed available-memory budget. The old
10-minute slice rule therefore materially underpredicted the real full-day
peak and must not be reused to authorize larger days.

D6R5C and D6R7B used about 4.22 GB and 4.31 GB respectively, but those were
read-only memmap / hftbacktest ingestion paths. They are not converter
capacity measurements.

## Frozen D5B reference row counts

D6R8A uses the previously frozen D5B full-stream-integrity counts only as
reference metadata; it does not reopen raw data:

| Month | Reference raw rows | Ratio vs D5B Jan |
| --- | ---: | ---: |
| 2026-01 | 63,666,274 | 1.0000× |
| 2026-02 | 172,721,707 | 2.7129× |
| 2026-03 | 145,757,298 | 2.2894× |
| 2026-04 | 129,067,640 | 2.0273× |
| 2026-05 | 104,234,425 | 1.6372× |
| 2026-06 | 165,502,465 | 2.5995× |
| 2026-07 | 172,067,693 | 2.7027× |

D5B's Jan reference count is 63,666,274, while the later D6R4 conversion
contract used 63,666,276 expected base events. The two-row difference is
preserved explicitly and is **not reconciled** in D6R8A. All ratios in this
gate use the D5B reference counts consistently.

## Risk-only linear projections

For danger assessment only, multiplying Jan's observed converter peak RSS
by the D5B row-count ratio gives:

| Month | Naive projected RSS | GiB |
| --- | ---: | ---: |
| 2026-02 | 26,984,904,085 | 25.1317 |
| 2026-03 | 22,772,162,078 | 21.2082 |
| 2026-04 | 20,164,679,625 | 18.7798 |
| 2026-05 | 16,284,901,359 | 15.1665 |
| 2026-06 | 25,857,017,172 | 24.0812 |
| 2026-07 | 26,882,725,237 | 25.0365 |

These values do **not** establish that converter memory scales linearly with
rows. They are deliberately frozen only as a danger signal. Every one is
above Jan's observed pre-run available memory.

Therefore:

**the current converter as-is is not authorized for Feb–Jul.**

## D6R8B next gate

D6R8B is a static/code-path memory-scaling audit only. It must identify the
actual sources and lifetimes that produced Jan's peak, including:

- CSV chunk arrays;
- upstream converter intermediate arrays;
- temporary stable-sort runs;
- merge memory;
- output memmap and file-cache interaction;
- NumPy/Python temporary allocations;
- the actual peak-RSS scaling driver;
- a structurally bounded redesign if required.

D6R8B may not open a Feb–Jul raw day and may not execute the converter.

Only after that audit and a separately frozen resource design can a new raw
day be considered.

## Closed surfaces

No Feb–Jul raw opening or conversion, no Jan rerun, no August, no September
or later, no non-BTC data, no policy execution, no historical PnL, no
economic arena, no network acquisition, no Railway, and no live trading.
