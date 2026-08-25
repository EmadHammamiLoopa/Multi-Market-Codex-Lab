# CODEX-EXP-003 Data Plan

Status: **PRE-SCORE FROZEN DESIGN — NO EXTERNAL MARKET DATA ACQUIRED OR OPENED**

Date: 2026-08-25

## Scope

The experiment changes only the information set. Execution and labels remain Binance USDS-M futures, taker entry/taker exit, a 250 ms target reaction step, 10 s and 30 s horizons, and the 8/12 bp cost envelope used by `CODEX-EXP-001`.

The already-published Binance-futures `FEATURES250` files remain the target/X0 input. New inputs are limited to Binance Spot and Bybit linear perpetual public market data. No OKX data, alternate contract, extra date, or alternate representation may be added under this experiment ID.

As of this plan's freeze, only public documentation and public exchange metadata have been queried. No January–July external CSV, preview, range request, header, or payload has been downloaded or opened. August market files remain sealed.

## Frozen sources

Public Tardis metadata queried on 2026-08-25 confirms the exact symbols and data types below. The filtered response is preserved at `evidence/codex/exp003_metadata/TARDIS_FILTERED_EXCHANGE_METADATA_20260825.json`.

| Role | Tardis exchange ID | Exact symbol(s) | Instrument type | Frozen data types | Coverage through |
|---|---|---|---|---|---|
| Target/execution comparator | `binance-futures` | `BTCUSDT`, `ETHUSDT` | perpetual | existing `FEATURES250`; metadata also confirms snapshots/trades | 2026-08-25 |
| External X1 | `binance` | `BTCUSDT`, `ETHUSDT` | spot | `book_snapshot_5`, `trades` | 2026-08-25 |
| External X2 | `bybit` | `BTCUSDT`, `ETHUSDT` | perpetual | `book_snapshot_5`, `trades` | 2026-08-25 |

Tardis describes `book_snapshot_5` as a wide, tick-level top-five book reconstructed from the exchange's real-time L2 feed and emitted whenever one of the tracked levels changes. The normalized schema is identical across exchanges: receipt and exchange timestamps plus five ordered price/amount levels on each side. Tardis also states that crossed levels are removed during reconstruction. `trades` records aggressor side, price, amount, exchange timestamp, and receipt timestamp. See the official [downloadable CSV schema](https://docs.tardis.dev/downloadable-csv-files) and [data-type reference](https://docs.tardis.dev/downloadable-csv-data-types).

No source/date may substitute `incremental_book_L2`, quotes, book ticker, `book_snapshot_25`, REST candles, or an exchange-native format. If either frozen representation is absent or malformed for any source/symbol/day, the affected common-support rows are invalid; representation switching is prohibited.

## Dates and file count

The only allowed external days are:

- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

The frozen download set contains 56 files: 2 external exchanges × 2 data types × 2 symbols × 7 days. Tardis documents that first-of-month CSVs are available as samples without an API key. Daily files are split and ordered by `local_timestamp`, not exchange timestamp.

Frozen URL pattern:

```text
https://datasets.tardis.dev/v1/{exchange}/{data_type}/2026/{month}/01/{symbol}.csv.gz
```

Frozen sandbox layout:

```text
data/codex_exp003_external/{exchange}/{data_type}/{symbol}/{YYYY-MM-DD}.csv.gz
```

The post-freeze downloader constructs this request set internally. It rejects every exchange, data type, symbol, and day outside the constants above, rejects sealed date names before opening a path, requires a full frozen commit matching clean tracked `HEAD`, refuses overwrite and partial-file recovery, validates gzip/CSV structure, and records SHA-256, byte count, header, and row count.

## Collector topology

Official historical-data pages state:

| Feed | Tardis collector | Exchange infrastructure reported by Tardis | Consequence |
|---|---|---|---|
| Binance Spot | GCP `asia-northeast1` (Tokyo) since 2020-05-18 | AWS `ap-northeast-1` (Tokyo) | same metro/region class, but not proof of clock identity |
| Binance USDS-M Futures | GCP `asia-northeast1` (Tokyo) since 2020-05-14 | AWS `ap-northeast-1` (Tokyo) | target receipt clock is provider-side, not trader-side |
| Bybit Derivatives | GCP `asia-northeast1` (Tokyo) since 2020-05-28 | AWS Singapore | different source-to-collector path; receipt ordering is vantage-specific |

References: [Binance Spot historical details](https://docs.tardis.dev/historical-data-details/binance), [Binance Futures historical details](https://docs.tardis.dev/historical-data-details/binance-futures), and [Bybit historical details](https://docs.tardis.dev/historical-data-details/bybit).

This supports a Tardis-collector-vantage availability study after a conservative delay. It does not establish synchronized collector-host clocks, co-located Binance execution feasibility, or a universal venue-leadership claim. Those limitations are frozen in the timestamp audit.

OKX is excluded from the primary experiment. Tardis documents an AWS Hong Kong collector for the relevant 2026 period, whereas older OKX history used Tokyo. Adding it would change the timestamp topology and hypothesis.

## Integrity and availability checks after freeze

Before feature construction, every acquired file must pass all checks below:

1. exact expected path, exchange, symbol, data type, and local-timestamp day;
2. gzip decompression and a nonempty canonical header;
3. at least one data record;
4. local timestamps nondecreasing in file order;
5. exchange and symbol fields constant and exact on every row;
6. `book_snapshot_5` has five strictly ordered positive levels per side and an uncrossed best bid/ask; malformed rows are retained as invalidity breaks, never repaired;
7. `trades` has a known `buy`/`sell` aggressor, positive price/amount, and duplicate nonempty trade IDs are removed preserving first receipt order;
8. all timestamps fall within the frozen day by `local_timestamp`;
9. SHA-256 and byte size recorded before analysis; and
10. no date named `2026-08-01` or `2026-08-04` through `2026-08-23` is opened, hashed, previewed, or requested.

Tardis explicitly warns that exchange timestamps can regress and that downloadable CSVs omit disconnect events. The parser therefore never rejects or reorders a file because an exchange timestamp regresses. Omitted disconnects are handled conservatively through a frozen receipt-gap/staleness policy, with the residual limitation reported rather than inferred away. See the official [data FAQ](https://docs.tardis.dev/faq/data).

## Acquisition sequence

1. Finish method, timestamp, red-team, and preregistration documents.
2. Finish implementation and synthetic tests.
3. Run the complete repository test suite without external market data.
4. Commit and publish the exact pre-score state.
5. Stop and review that commit.
6. Only after explicit continuation, invoke `multimarket-codex-exp003-acquire` with the exact commit and acknowledgement flag.
7. Audit all 56 files and publish the input manifest before any scoring command.

The downloader exists so the acquisition contract can be reviewed before data exist. It has not been invoked.
