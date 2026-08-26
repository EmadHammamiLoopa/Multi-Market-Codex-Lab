# CODEX-EXP-008-P0 Pre-Acquisition Implementation Freeze

Status: **FROZEN BEFORE ANY EXP008 OPTION-DATA ACQUISITION**

Date: 2026-08-26

Experiment ID: `CODEX-EXP-008-P0`

Parent preregistration commit:

`65b7d18a8bacd20c98cfe54f2be8fd44a0580d89`

This document resolves implementation details that were intentionally not inferred from any 2026 options-chain rows. No EXP008 option-data file has been acquired or inspected before this freeze.

## Causal clock

The causal availability clock is Tardis `local_timestamp`, expressed in microseconds since Unix epoch UTC.

Reason: `local_timestamp` is the provider-recorded message-arrival time and is therefore the conservative time at which the observation is known to the research system.

The exchange `timestamp` field is preserved and audited but is not used to make an observation available earlier than its `local_timestamp`.

At decision minute `t`, an instrument state is eligible exactly when:

`t - 300 seconds <= local_timestamp < t`.

No equality at `t` is allowed.

## Provider row order and duplicate rule

Raw provider bytes remain immutable.

The audit processes provider capture order and reports whether `local_timestamp` is nondecreasing. Because the structural audit is streamed causally, raw `local_timestamp` must be nondecreasing for P0 readiness. A decrease is a conservative timestamp-integrity failure; the file is not re-sorted to rescue support.

Duplicate identity is:

`(local_timestamp, symbol)`.

If two rows with the same duplicate identity are byte-for-byte equivalent after CSV parsing, the derived state may treat the later copy as redundant while the raw artifact remains unchanged.

If two rows share the duplicate identity but any CSV field differs, the duplicate is conflicting and the preregistered conflicting-duplicate gate fails. No row-position rule is used to rescue a conflicting duplicate because the normalized schema exposes no explicit source sequence/version field.

## Currency classification

Only options whose normalized instrument symbol begins with `BTC-`, `BTC_`, `ETH-`, or `ETH_` are eligible.

BTC-classified rows feed only the BTC surface and ETH-classified rows feed only the ETH surface.

All other option instruments remain preserved in the raw artifact but are excluded from the derived BTC/ETH readiness view.

## Expiry clock and DTE

Expiration is parsed from the Tardis `expiration` field in microseconds since Unix epoch UTC.

At grid time `t`:

`DTE = (expiration - t) / 86400 seconds`.

The 7-day anchor is the expiry minimizing `abs(DTE - 7)` among `5 <= DTE <= 9`.

The 30-day anchor is the expiry minimizing `abs(DTE - 30)` among `25 <= DTE <= 35`.

Exact ties choose the earlier expiration timestamp.

Expired options are never eligible.

## Per-expiry underlying reference S

For one currency-expiry state at minute `t`, `S` is the median of all finite positive `underlying_price` values among fresh eligible rows for that exact expiry.

If no finite positive underlying price exists, the expiry cannot supply ATM or moneyness-based selections.

The same frozen `S` is used for ATM selection and all moneyness tie-breaks within that expiry at that minute.

No external spot, futures, perpetual, DVOL, or interpolated underlying price is substituted.

## ATM selection

Among all finite positive strikes present in the fresh selected expiry state, choose the strike minimizing:

`abs(log(strike / S))`.

Tie-breaker: lower strike.

After the strike is selected, both a call and a put at exactly that strike must be present in the fresh state and both must have finite `mark_iv`.

If either side or either mark IV is unavailable, ATM IV is unavailable. The algorithm does not move to the next-closest strike.

ATM IV is:

`0.5 * (call_mark_iv + put_mark_iv)`.

## 25-delta selections

For calls, candidate selection is based on finite `delta` and the frozen tolerance:

`abs(delta - 0.25) <= 0.05`.

For puts:

`abs(delta + 0.25) <= 0.05`.

Candidates are ordered by:

1. absolute delta distance from the target;
2. absolute log-moneyness using the frozen expiry `S`;
3. lower strike.

The selected row must then have finite `mark_iv` for RR/BF construction. Missing mark IV makes the corresponding surface value unavailable; the algorithm does not fall through to a second-best delta candidate.

## Open-interest imbalance

For the selected expiry, sum only finite strictly positive `open_interest` values separately for puts and calls.

A side with no finite positive observations contributes zero.

OI imbalance is available only if:

`put_OI + call_OI > 0`.

Then:

`OI_IMB = (put_OI - call_OI) / (put_OI + call_OI)`.

Zero, negative, empty, NaN, and infinite individual OI values are excluded from the sum and are never imputed.

## Fresh instrument state

The state contains at most the latest row for each eligible instrument symbol seen before `t`.

Rows older than 300 seconds at `t` are discarded from the eligible state.

An instrument is not forward-filled beyond 300 seconds, and no state crosses UTC midnight.

## Fixed readiness grid

Each frozen day has exactly 1,400 audit minutes:

`00:30, 00:31, ..., 23:49 UTC`.

The first 30 minutes are warm-up only. No previous-day option state is used.

The support denominator for every currency-day is always 1,400, regardless of missing source rows.

The preregistered 80% threshold therefore requires at least 1,120 all-nine-feature minutes per currency-day.

The consecutive-run gate requires at least 120 adjacent supported grid minutes.

## Parsing rules

Required CSV columns are:

- `exchange`;
- `symbol`;
- `timestamp`;
- `local_timestamp`;
- `type`;
- `strike_price`;
- `expiration`;
- `open_interest`;
- `mark_iv`;
- `underlying_price`;
- `delta`.

`type`, `strike_price`, `expiration`, `timestamp`, and `local_timestamp` must be syntactically valid for every BTC/ETH row used in the canonical view.

`open_interest`, `mark_iv`, `underlying_price`, and `delta` are provider-optional values; an empty field is treated as unavailable, but a non-empty malformed numeric value is a parse-integrity failure.

Rows with a `local_timestamp` outside the requested UTC day never enter the canonical day state and cause the date-integrity gate to fail.

## Acquisition client

The official Python package `tardis-dev` is used through its normalized CSV dataset downloader.

Frozen client version for this implementation:

`tardis-dev==4.2.1`

Frozen request parameters per day:

- exchange: `deribit`;
- data type: `options_chain`;
- symbol: `OPTIONS`;
- from date: frozen day;
- to date: frozen day + one day, exclusive;
- API key: empty;
- concurrency: 1;
- no proxy override;
- provider raw gzip bytes retained;
- existing output paths are refused rather than skipped or overwritten.

The exact source URL is recorded as:

`https://datasets.tardis.dev/v1/deribit/options_chain/YYYY/MM/DD/OPTIONS.csv.gz`.

## Source-access failure

A provider/client access denial or unavailable frozen free sample is recorded as:

`FAIL_OPTIONS_SURFACE_DATA_NOT_READY`.

It is explicitly a data-readiness/source-access failure and says nothing about predictive value.

Import/dependency failure before creation of the EXP008 output directory is not a scientific run and must be corrected before acquisition.

## Streaming audit and no predictive access

The audit reads only the acquired Tardis options-chain gzip artifacts.

It does not open Phase-L `FEATURES250`, opportunity labels, future returns, EXP004/005/007 predictive records, August data, direction labels, or PnL data.

No model package is invoked by the P0 runner.

The raw artifacts, acquisition manifest, and final readiness audit are the only EXP008-P0 evidence outputs.
