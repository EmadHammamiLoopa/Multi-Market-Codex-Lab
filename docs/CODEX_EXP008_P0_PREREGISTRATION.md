# CODEX-EXP-008-P0 Preregistration

Status: **PREREGISTERED BEFORE ANY EXP008 OPTION-DATA ACQUISITION**

Date: 2026-08-26

Experiment ID: `CODEX-EXP-008-P0`

Parent frozen result commit:

`5701f7210fc1b991f4b3ca72076139f2bf4c3fc6`

Parent conclusion:

`CODEX-EXP-007-P1 = FAIL_DVOL_NO_INCREMENTAL_TIMING_INFORMATION`

## Scientific role

EXP008 is a new information-family experiment.

It does not rescue EXP007.

EXP007 tested aggregate options-implied volatility state through Deribit DVOL.

EXP008 asks whether historical Deribit options-chain data are causally and structurally sufficient to support a small, preregistered options-surface feature family for a later predictive experiment.

P0 is data-readiness only.

No target, future return, AUC, average precision, direction, threshold optimization, or PnL may be inspected in P0.

## Frozen source

Source family:

- exchange: Deribit;
- provider: Tardis historical datasets;
- data type: `options_chain`;
- grouped symbol: `OPTIONS`;
- raw format: provider CSV gzip artifact;
- source-local timestamps must be preserved.

The metadata-only pre-probe established before this preregistration that the Deribit `OPTIONS` grouped symbol advertises `options_chain` and that provider export coverage extends beyond all frozen dates below.

That pre-probe is source-capability evidence only and is not an experimental result.

## Frozen dates

Only these UTC calendar days may be acquired or inspected:

- 2026-03-01;
- 2026-04-01;
- 2026-05-01;
- 2026-06-01;
- 2026-07-01.

No January or February options-chain data are required.

No context day before a supervised date is allowed.

August remains sealed.

## Why no context day is required

Any later predictive use of this family must begin no earlier than 00:30 UTC on each supervised day.

Options-surface state and any trailing transforms must be constructed only from observations occurring inside the same UTC day.

No previous-day carry, forward-fill across midnight, or synthetic pre-midnight state is permitted.

## Frozen currencies

Only BTC and ETH option instruments are eligible.

Future predictive pairing, if P0 passes, is own-underlying only:

- BTCUSDT target market ↔ BTC option surface;
- ETHUSDT target market ↔ ETH option surface.

No BTC option feature may be used for ETHUSDT and vice versa.

## Frozen causal availability rule

For a later decision at time `t`, an option observation is eligible only when its source/local timestamp is strictly earlier than `t` and no later than the frozen staleness limit below.

Maximum state staleness:

`300 seconds`.

No future timestamp is allowed.

No backward-fill, forward-fill, interpolation, synthetic quote, or alternative vendor may repair a missing option state.

P0 must establish that timestamp fields needed to enforce this rule are present and parseable.

## Frozen surface anchors

The intended surface family uses two maturity anchors selected independently at each eligible state time.

### Short anchor

Select the available expiry with time-to-expiry closest to 7 calendar days subject to:

`5 <= DTE <= 9`.

### Medium anchor

Select the available expiry with time-to-expiry closest to 30 calendar days subject to:

`25 <= DTE <= 35`.

If two expiries are equally close to an anchor, select the earlier expiry.

If no expiry exists inside the frozen band, that anchor is unavailable for that state time.

No wider DTE band may be introduced after acquisition.

## Frozen per-expiry instrument selections

For each selected expiry and underlying, the option chain must support the following selections.

### ATM option state

Use the strike minimizing absolute log-moneyness:

`abs(log(K / S))`

where `K` is strike and `S` is the contemporaneous underlying/index reference supplied by the chain.

If multiple strikes tie, select the lower strike.

ATM implied volatility is the mean of the available call and put mark-IV values at that selected strike when both are finite.

If only one side is finite, ATM IV is unavailable.

### 25-delta call

Select the call whose delta is closest to `+0.25`, requiring:

`abs(delta - 0.25) <= 0.05`.

Tie-breaker: smaller absolute log-moneyness, then lower strike.

### 25-delta put

Select the put whose delta is closest to `-0.25`, requiring:

`abs(delta + 0.25) <= 0.05`.

Tie-breaker: smaller absolute log-moneyness, then lower strike.

No wider delta tolerance may be introduced under this experiment ID.

## Frozen intended surface feature family

P0 does not calculate predictive metrics, but readiness is defined relative to this exact later-use family.

For each 7-day and 30-day anchor:

1. ATM mark IV;
2. 25-delta risk reversal:
   `IV_call25 - IV_put25`;
3. 25-delta butterfly:
   `0.5 * (IV_call25 + IV_put25) - ATM_IV`;
4. put/call open-interest imbalance:
   `(put_OI - call_OI) / (put_OI + call_OI)`
   using all finite positive-open-interest options for that selected expiry.

Across anchors:

5. ATM term spread:
   `ATM_IV_30d - ATM_IV_7d`.

This yields a maximum raw surface family of nine values:

- ATM7;
- RR25_7;
- BF25_7;
- OI_IMB_7;
- ATM30;
- RR25_30;
- BF25_30;
- OI_IMB_30;
- ATM_TERM_30_MINUS_7.

No skew spline, SABR fit, volatility-surface neural representation, gamma-exposure estimate, dealer-position proxy, volume-derived feature, additional delta bucket, or additional expiry anchor is allowed under EXP008 without a new experiment ID.

## P0 acquisition protocol

Acquisition must occur only after this preregistration is committed.

For each of the five frozen dates:

1. acquire the provider's raw `deribit/options_chain/.../OPTIONS.csv.gz` artifact using the official documented access path/client;
2. write to a fresh experiment-specific raw directory;
3. never overwrite an existing raw artifact;
4. record byte size and SHA-256 immediately after acquisition;
5. record acquisition timestamp and exact source identifier;
6. perform no filtering before preserving the raw artifact;
7. do not access August.

If the provider denies access, requires credentials not available to the study, or fails to expose the frozen free sample through its official mechanism, P0 may end with a source-access failure status. That is a data-readiness failure, not evidence about predictive value.

## Required schema fields

P0 must establish, directly from the frozen raw source, semantically equivalent fields sufficient for all of the following:

- source/local timestamp;
- instrument identifier;
- option type (call/put);
- expiry;
- strike;
- underlying/index reference price;
- mark implied volatility;
- option delta;
- open interest.

Bid/ask IV and additional Greeks may be preserved if present but are not required by the frozen feature family.

Missing required semantics cause P0 failure.

## Timestamp and duplicate integrity

P0 must report for each frozen day:

- minimum and maximum source timestamp;
- whether timestamps parse as UTC-aware instants;
- whether any observation falls outside the requested UTC day;
- duplicate row count under a deterministic key of timestamp + instrument identifier;
- monotonicity after deterministic sort;
- malformed row count.

Duplicate source records may not be silently dropped in the raw artifact.

A canonicalized derived view may resolve exact duplicate records only if the raw artifact remains immutable and the duplicate rule is reported.

Conflicting duplicate records at the same timestamp/instrument key cause P0 failure unless the provider exposes a documented sequence/version field that deterministically orders them.

## Structural coverage audit

P0 must evaluate structural support on a fixed one-minute UTC grid from 00:30 through 23:49 inclusive for each frozen day.

For each minute `t`, use only the latest causally available chain state with source timestamp:

`t - 300 seconds <= source_timestamp < t`.

For BTC and ETH separately, determine whether all nine frozen surface values are constructible at that minute with no imputation.

P0 must report:

- eligible minutes;
- minutes with both expiry anchors;
- minutes with ATM support at both anchors;
- minutes with valid 25-delta call and put at both anchors;
- minutes with finite OI imbalance at both anchors;
- minutes with all nine values available;
- longest consecutive all-feature support run;
- first and last all-feature-supported minute.

## Frozen readiness gates

P0 passes only if every condition below is satisfied.

### Acquisition integrity

1. all five frozen raw daily artifacts acquired through the frozen source family;
2. all five raw SHA-256 hashes recorded;
3. no raw artifact overwritten;
4. no August data accessed.

### Schema integrity

5. all required field semantics are present;
6. timestamp parsing is valid;
7. instrument type/expiry/strike/underlying/mark-IV/delta/OI are parseable;
8. no unresolved conflicting duplicate timestamp/instrument state exists.

### Currency/date integrity

9. BTC options are present on all five days;
10. ETH options are present on all five days;
11. no observation outside the requested UTC day enters a day's canonical view.

### Surface support

For each currency-day independently:

12. at least 80% of the fixed 00:30–23:49 minute grid has all nine frozen surface values causally available;
13. at least one consecutive 120-minute run has all nine values available.

All ten currency-days must satisfy both support gates.

The 80% and 120-minute thresholds are frozen before acquisition and may not be weakened after inspecting data.

## P0 statuses

PASS:

`DATA_READY_OPTIONS_SURFACE_SANDBOX`

Use only if every frozen readiness gate passes.

FAIL:

`FAIL_OPTIONS_SURFACE_DATA_NOT_READY`

Use for acquisition, schema, timestamp, duplicate, or structural-support failure when the experiment otherwise executed according to protocol.

INVALID:

Use only for experiment-protocol violation such as:

- accessing August;
- modifying the frozen preregistration after acquisition begins;
- silently replacing the source family;
- overwriting raw artifacts;
- inspecting target/future-return/model metrics during P0;
- material implementation error that invalidates the audit.

## P0 prohibitions

P0 may not:

- construct the 24-bp opportunity target;
- inspect future returns;
- fit any predictive model;
- calculate ROC AUC or average precision;
- inspect direction;
- calculate strategy PnL;
- tune DTE bands;
- tune delta tolerances;
- drop ETH or BTC after seeing coverage;
- choose only favorable months;
- substitute DVOL for missing option-chain values;
- open August.

## After P0

A P0 PASS authorizes a separately preregistered EXP008-P1 incremental-information test.

A P0 PASS is not evidence of predictability or profitability.

A P0 FAIL remains a valid frozen result and may not be rescued under the same experiment ID.
