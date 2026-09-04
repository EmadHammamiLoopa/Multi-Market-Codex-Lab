# DEV045-D4 Raw Historical Provenance Handoff

Date: 2026-09-04

## Current status

`D3_GATE=CLOSED`

`D4_P1_COMPRESSED_BYTE_PROVENANCE=GREEN`

`D4_P2_FREEZE=IN_PROGRESS`

Parent D3 commit:

`ea758d5b8171ba213e332c0d639ae64629049b07`

D3 dedicated CI:

`33900113250` — SUCCESS

Generic D3 CI:

`33900113132` — SUCCESS

## Why D4 exists

D4 freezes the exact historical input bytes before any historical economic
result is observed.

This prevents result-driven file substitution, wrong-day substitution,
cross-market mixing, accidental August/September expansion, and reruns against
different raw bytes.

## Path-resolution diagnostic

The initial assumed worktree-relative root did not contain the raw files.

That first D4 attempt failed only at path resolution.

It did NOT hash bytes and did NOT inspect historical content.

The authoritative correction is:

`RAW_BYTES_HASHED=NO`

for that failed first attempt.

The later metadata-only root search found exactly one complete 14-file root.

Resolved local root:

`/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw`

Coverage:

- 7/7 BTCUSDT trades files
- 7/7 BTCUSDT incremental_book_L2 files
- 14/14 total
- Jan-Jul authorized days only

Other discovered old roots did not contain the required complete two-stream
set and are not D4 authorities.

## D4-P1 compressed-byte provenance

D4-P1 hashed only the compressed `.csv.gz` bytes.

No gzip decompression occurred.

No CSV header was read.

No CSV row was parsed.

The first and second SHA-256 passes matched exactly.

Temporary evidence manifest SHA-256:

`27e0eee1ddc95b1bdff915e10a81e92173fc708bdb88e42d089cc92e8535519c`

Result:

`DEV045_D4_P1_COMPRESSED_BYTE_PROVENANCE=GREEN`

## Frozen portable manifest

Repository artifact:

`evidence/dev045_d4_raw_provenance.tsv`

Frozen portable manifest SHA-256:

`7fa6cf76ee8c6da98c5758756c887f0fb7b4d2e5eaf6b0e9f87551dce9981c12`

The repository manifest deliberately stores logical relative paths rather than
the machine-specific absolute root.

mtime is deliberately not part of frozen identity.

Frozen identity consists of:

- stream kind
- authorized day
- compressed byte size
- compressed-byte SHA-256
- exact logical BTCUSDT relative path

## Exact 14 compressed-byte identities

- trades / 2026-01-01 — 9691108 bytes — `e4aaee2b9f85016a5198e0cace5755dbd789c0f6f47ac0fc802c8f4b533833f6`
- incremental_book_L2 / 2026-01-01 — 347513061 bytes — `0488a2204c9070b1e6a8769af48d54fb36e6a5658613267e2615cd3228002ded`
- trades / 2026-02-01 — 57631972 bytes — `dfd19ab53abbc90118ce3c861521ecb17dbed6ce7bcc7410c07f296460454508`
- incremental_book_L2 / 2026-02-01 — 865907076 bytes — `a1e9fc0fcc20d309d171ed1b6367ebe17948c84dd025a07a5d13c80f0b023cc4`
- trades / 2026-03-01 — 50842755 bytes — `50d3762a883f3f1cddc6869bbc2dbaaacf5bb52637ac0b51b85ae4dfcafdcb50`
- incremental_book_L2 / 2026-03-01 — 737199360 bytes — `a5468fb97f161b05a89f8dcc39d8c88a58fb6dc60caeb69aa783facff66c27e1`
- trades / 2026-04-01 — 33823287 bytes — `31959ff7bcf8aae71fe4826987a6cbafc7897c6e881a2d555b89b99ac4def804`
- incremental_book_L2 / 2026-04-01 — 675132621 bytes — `d1d08211ebcc8b576c4b9d50158ff39971f66dd463cffe1929dacd3d17223cfd`
- trades / 2026-05-01 — 26110327 bytes — `272f6d8ac29d14098c27d9fdaf95795ac5ed371024a000f279feaa38cf5605e1`
- incremental_book_L2 / 2026-05-01 — 557562555 bytes — `284b95a8d84d1fdda10f73d80ba8cfb5f1f2ee60db9bd00937f3701e5948faf4`
- trades / 2026-06-01 — 34960370 bytes — `f1f695bf6ef198f209a115250d1b99194bb21dfa4693cab2dcb4a10a969be53e`
- incremental_book_L2 / 2026-06-01 — 893502369 bytes — `581361873d3a692362257217e27961332ee25786dca27f280048be2ed150837d`
- trades / 2026-07-01 — 41982532 bytes — `eefc51c11e55b6d0224e760479bff87fc1f052773ae3c8ae08700395fa229a87`
- incremental_book_L2 / 2026-07-01 — 923475379 bytes — `b2e8bbed3db89695f055dc3010a0fff074732d82ae18117a1602b5593c90d1f1`

## Historical content remains closed

At D4-P2:

`RAW_BYTES_HASHED=YES`

`RAW_GZIP_DECOMPRESSED=NO`

`RAW_CSV_HEADER_READ=NO`

`RAW_CSV_ROWS_PARSED=NO`

`TARDIS_CONVERTER_RUN=NO`

`HISTORICAL_POLICY_REPLAY=NO`

`HISTORICAL_PNL_COMPUTED=NO`

`ECONOMIC_ARENA_EXECUTED=NO`

`CANONICAL_PNL_WRITTEN=NO`

`AUGUST_OPENED=NO`

`SEP_PLUS_OPENED=NO`

`NON_BTC_OPENED=NO`

`NETWORK_MARKET_DATA_ACQUISITION=NO`

`RAILWAY_TOUCHED=NO`

`LIVE_TRADING_AUTHORIZED=NO`

## D4-P2 freeze requirements

Freeze together:

1. portable 14-row manifest;
2. provenance validation contract;
3. provenance tests;
4. this handoff;
5. dedicated D4 CI.

Dedicated CI verifies repository identity without requiring the private local
raw files.

## Next gate after D4 CI GREEN

The next phase is a separate raw-content preflight.

Only then may we decompress enough content to validate:

Depth header:

`exchange,symbol,timestamp,local_timestamp,is_snapshot,side,price,amount`

Trades header:

`exchange,symbol,timestamp,local_timestamp,id,side,price,amount`

And verify:

- BTCUSDT only;
- exact authorized day;
- exchange/symbol consistency;
- snapshot presence;
- timestamp ordering;
- no August;
- no September+;
- no non-BTC.

## Converter gate after raw-content preflight

Only the frozen official hftbacktest Tardis converter lineage is authorized.

Frozen converter blob:

`1ca038895d30f320561d6b28ffa13c1d788ea6bf`

Required file order:

1. trades
2. incremental_book_L2

Required timestamp conversion:

microseconds -> nanoseconds

No custom converter substitution is allowed.

## Before first historical one-shot

Reread all frozen authorities:

- M3
- M4
- M4->M6 binding
- M5 preregistration and fees
- M5A
- M5B
- D1
- D2
- D3
- D4 manifest
- raw-content preflight
- converter identity

Only then may the first historical replay be authorized.

## One-shot rule

The first historical result is evidence.

It must not trigger:

- retuning;
- threshold changes;
- latency changes;
- fee changes;
- day selection;
- policy rescue;
- result-driven rerun.

Any later experiment must be separately prospective and preregistered.
