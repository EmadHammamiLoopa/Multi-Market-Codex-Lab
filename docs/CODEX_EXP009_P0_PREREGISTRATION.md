# CODEX-EXP-009-P0 Preregistration

Status: **PREREGISTERED BEFORE ANY EXP009 OPTIONS-TRADE ACQUISITION**

Date: 2026-08-26

Experiment ID: `CODEX-EXP-009-P0`

Parent frozen scientific result commit:

`5701f7210fc1b991f4b3ca72076139f2bf4c3fc6`

Parent conclusion:

`CODEX-EXP-007-P1 = FAIL_DVOL_NO_INCREMENTAL_TIMING_INFORMATION`

EXP009 is a new information-family experiment. It does not rescue EXP007 or alter the running EXP008 experiment.

## Scientific question

Are historical Deribit option trades causally and structurally sufficient to support a small, preregistered short-horizon options trade-flow feature family for a later incremental opportunity-timing test?

P0 is data-readiness only. It may not inspect the opportunity target, future returns, model metrics, direction labels, threshold optimization, or PnL.

## Frozen source

- provider: Tardis historical datasets;
- exchange: Deribit;
- data type: `trades`;
- grouped symbol: `OPTIONS`;
- raw format: provider CSV gzip artifact;
- official dataset path/client only;
- raw provider bytes retained unchanged.

The provider documents `OPTIONS` as the grouped symbol for Deribit options and supports `trades` downloadable CSV data. The first day of each month is available as a public sample under the provider's documented dataset access model. Source capability evidence is external background only and is not an experimental result.

## Frozen dates

Only these UTC days may be acquired or inspected:

- 2026-03-01;
- 2026-04-01;
- 2026-05-01;
- 2026-06-01;
- 2026-07-01.

No August data may be opened. No January/February trade data or context days are required.

## Frozen currencies

Only BTC and ETH option instruments are eligible.

Own-underlying use in a later predictive experiment is frozen as:

- BTC option flow -> BTCUSDT target market;
- ETH option flow -> ETHUSDT target market.

No cross-underlying pooling is allowed in P0 support accounting.

## Frozen causal clock

Causal availability is determined by Tardis `local_timestamp`.

For a later decision minute `t`, a trade can contribute only when:

`local_timestamp < t`.

Trades stamped exactly at `t` are unavailable at that decision.

No future timestamp, backward-fill, forward-fill, or synthetic trade is allowed.

The exchange timestamp is preserved and audited but cannot make a trade available earlier than `local_timestamp`.

## Frozen instrument parsing

BTC and ETH are classified from the option symbol prefix.

The option symbol must be parseable into at least:

- underlying currency;
- expiration;
- strike;
- option type call/put.

Rows whose BTC/ETH option symbol is malformed cause a parse-integrity failure.

No external instrument metadata may repair a malformed symbol under EXP009-P0.

## Frozen trade semantics

Required trade fields are semantically equivalent to:

- exchange;
- symbol;
- timestamp;
- local_timestamp;
- trade id;
- side;
- price;
- amount.

`side` must identify buy versus sell according to the provider-normalized trade schema.

`amount` must be finite and strictly positive for an eligible trade.

Trade price is audited for finite positivity but is not used to create predictive price-return features in P0.

## Frozen flow windows

The intended later-use trade-flow family uses exact trailing windows ending strictly before decision minute `t`:

- 1 minute;
- 5 minutes;
- 15 minutes;
- 30 minutes.

A trade belongs to a window of length `W` exactly when:

`t - W <= local_timestamp < t`.

No previous-day trade is carried across UTC midnight.

The fixed readiness grid therefore begins at 00:30 UTC.

## Frozen flow primitives

For each currency and each frozen trailing window, P0 audits whether the following quantities are causally constructible:

1. buy amount;
2. sell amount;
3. total amount;
4. signed amount = buy amount - sell amount;
5. amount imbalance = (buy amount - sell amount) / (buy amount + sell amount), available only when total amount > 0;
6. buy trade count;
7. sell trade count;
8. total trade count;
9. count imbalance = (buy count - sell count) / (buy count + sell count), available only when total count > 0;
10. call amount;
11. put amount;
12. call-put amount imbalance = (call amount - put amount) / (call amount + put amount), available only when denominator > 0.

These are structural primitives only. P0 does not assess predictive value.

No delta weighting, gamma weighting, moneyness bucket, expiry bucket, trade-size quantile, IV weighting, dealer-position proxy, or learned representation is allowed under EXP009-P0. Those require a separately preregistered later experiment or diagnostic.

## Fixed readiness grid

For each frozen day and each currency independently, audit exactly the one-minute UTC grid:

`00:30, 00:31, ..., 23:49`.

This is exactly 1,400 decision minutes per currency-day.

At every grid minute, support is evaluated using only same-day trades satisfying the frozen causal window rules.

## Frozen support definition

A grid minute has complete EXP009 trade-flow support for one currency only if all four frozen windows (1m, 5m, 15m, 30m) independently contain at least one eligible trade and therefore both amount and count imbalance are defined.

The call-put amount imbalance must also be defined in every window, requiring positive total call+put amount in that window.

Because every eligible trade is either call or put, this is equivalent to requiring at least one eligible BTC/ETH option trade in each window with valid option type and positive amount; nevertheless the audit must report the components separately.

## Structural diagnostics

For each currency-day, P0 reports:

- eligible grid minutes = 1,400;
- minutes with at least one 1m trade;
- minutes with at least one 5m trade;
- minutes with at least one 15m trade;
- minutes with at least one 30m trade;
- minutes with complete all-window support;
- complete-support fraction;
- longest consecutive complete-support run;
- first and last complete-support minute;
- total trade count;
- buy/sell counts;
- call/put counts;
- total positive amount;
- malformed eligible-row count.

No return, label, AUC, AP, Brier, log loss, direction, or PnL diagnostic is allowed.

## Timestamp and duplicate integrity

P0 must report for each frozen day:

- minimum and maximum `local_timestamp`;
- whether BTC/ETH `local_timestamp` values are within the requested UTC day;
- whether provider capture order is nondecreasing in `local_timestamp`;
- exact duplicate trade-id count;
- conflicting duplicate trade-id count;
- malformed BTC/ETH row count.

A duplicate trade id whose parsed economically relevant fields are identical may be treated as redundant in a derived audit while the raw artifact remains unchanged.

A duplicate trade id with conflicting BTC/ETH trade fields fails the duplicate-integrity gate.

## Frozen readiness gates

P0 passes only if every condition below is satisfied.

### Acquisition integrity

1. all five frozen raw daily `trades/OPTIONS` artifacts are acquired through the frozen source family;
2. SHA-256 and byte size are recorded for all five;
3. no raw artifact is overwritten;
4. no August data is accessed.

### Schema / parse integrity

5. all required trade field semantics are present;
6. `timestamp` and `local_timestamp` parse correctly;
7. BTC/ETH option symbols parse correctly;
8. `side` is valid buy/sell for all eligible BTC/ETH rows;
9. `price` and `amount` are finite and strictly positive for all eligible BTC/ETH rows;
10. no unresolved conflicting duplicate trade id exists;
11. no BTC/ETH row from outside the requested UTC day enters the canonical day view.

### Currency presence

12. BTC option trades are present on all five days;
13. ETH option trades are present on all five days.

### Flow support

For every one of the ten currency-days independently:

14. at least 80% of the fixed 1,400-minute grid has complete all-window flow support;
15. at least one consecutive 120-minute complete-support run exists.

The 80% threshold is exactly 1,120 supported minutes and may not be weakened after acquisition.

## Frozen statuses

PASS:

`DATA_READY_OPTIONS_TRADE_FLOW_SANDBOX`

FAIL:

`FAIL_OPTIONS_TRADE_FLOW_DATA_NOT_READY`

INVALID is reserved for protocol violations such as opening August, changing the frozen rules after acquisition starts, replacing the source family silently, overwriting raw artifacts, or inspecting target/model/direction/PnL information during P0.

## P0 prohibitions

EXP009-P0 may not:

- construct or inspect the 24bp opportunity target;
- inspect any future return;
- fit a predictive model;
- calculate AUC/AP/Brier/log loss;
- inspect target direction;
- calculate trading PnL;
- tune support thresholds;
- tune window lengths;
- drop BTC or ETH after seeing coverage;
- select favorable months;
- add moneyness/expiry/size buckets after inspecting raw trades;
- use August.

## After P0

A P0 PASS authorizes a separately preregistered EXP009-P1 incremental-information experiment.

P1 must freeze its actual feature family, falsification tests, model, folds, and promotion gates before scoring.

A P0 PASS is not evidence of predictability or profitability.

A P0 FAIL remains a valid frozen result and may not be rescued under the same Experiment ID.
