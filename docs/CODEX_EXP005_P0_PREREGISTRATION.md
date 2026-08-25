# CODEX-EXP-005-P0 Preregistration

Status: **PREREGISTERED BEFORE ANY EXP005 DOWNLOAD OR MODEL OUTPUT**

Date: 2026-08-25

Experiment ID: `CODEX-EXP-005-P0`

## Motivation

`CODEX-EXP-004-P0` established that 10 minutes is the shortest fixed horizon with sufficiently distributed executable economic headroom on the consumed January--July sandbox.

`CODEX-EXP-004-P1` then failed the frozen opportunity-predictability criteria despite strong rank metrics because:

- Track R pooled ROC AUC was approximately 0.670;
- volatility-only ROC AUC was approximately 0.663;
- the time-permutation placebo remained approximately 0.654;
- the real-vs-placebo AUC delta was only approximately +0.0157, below the frozen +0.03 diagnostic requirement;
- pooled Brier skill was negative for R;
- RL2 failed all prespecified incremental-information gates versus R on common support.

The next hypothesis therefore changes the **information family**, not the model class, horizon, target, market, or validation logic.

## Scientific question

Before fitting another predictor:

> Is there sufficiently complete, point-in-time, causally alignable derivatives-native state for BTCUSDT and ETHUSDT on Binance USD-M Futures to test whether funding/open-interest/premium state adds within-regime timing information for the frozen 10-minute >=24 bp opportunity target?

This phase is a **data availability, schema, timing, and quality audit only**.

No predictive model and no trading PnL are permitted in P0.

## Frozen scope

### Target market

- Binance USD-M Futures.
- Symbols: `BTCUSDT`, `ETHUSDT` only.

### Dates

Only the already-consumed sandbox dates:

- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

No August data may be downloaded, listed, opened, inspected, or inferred.

### Candidate external record family

Primary candidate source family:

- historical Binance USD-M derivatives/ticker-state records from Tardis or an equivalent immutable historical source if and only if the exact Tardis record family proves unavailable.

The intended information categories are:

1. open interest;
2. funding rate / next or predicted funding information when natively present;
3. mark price;
4. index price;
5. futures premium or basis derivable causally from contemporaneous mark/index/contract prices when the source schema supports it.

Liquidation-event streams are **out of scope** for EXP005-P0.

No new venue is allowed in P0.

## Acquisition freeze

Before any remote download begins, the acquisition program must freeze and print:

- source/exchange identifier;
- data type / record family;
- exact symbol;
- exact UTC date;
- requested URL or source key;
- destination path;
- whether a file already exists;
- download status;
- compressed byte count;
- SHA-256 after download.

The acquisition program may request only the 14 frozen symbol-days.

A request builder must reject any date outside the seven frozen dates before network access.

A request builder must reject any symbol outside BTCUSDT/ETHUSDT before network access.

## Raw-data preservation

Raw downloaded files must:

- live under a dedicated ignored directory, proposed:
  `data/codex_exp005_derivatives_raw/`;
- never be modified in place;
- never be committed to Git;
- be referenced by exact SHA-256 in a committed acquisition manifest;
- be re-used read-only for all later EXP005 phases.

No redownload is permitted merely because a later analysis is inconvenient.

## Timing and causality audit

For every record family actually present in the source schema, P0 must separately identify:

- exchange/event timestamp, if present;
- collector/local receipt timestamp, if present;
- whether timestamps are monotone within file;
- count of timestamp regressions;
- count of duplicate rows under a deterministic key;
- count and duration of gaps;
- first and last timestamp per symbol-day;
- update-frequency distribution.

If both exchange and local/receipt timestamps exist, later predictive phases must use the **receipt/local timestamp for availability**. Exchange timestamp is audit metadata only.

If only exchange timestamps exist, EXP005-P0 must explicitly mark that limitation and P1 may not claim sub-second collector-vantage causality from that source.

## Schema audit

The audit must report the exact raw columns and determine whether each intended information category is:

- `PRESENT_NATIVE`;
- `DERIVABLE_CAUSALLY`;
- `ABSENT`;
- `AMBIGUOUS_SCHEMA`.

No missing economic field may be fabricated, forward-filled from another venue, or silently substituted.

## Data-quality metrics

For every symbol-day and each accepted numeric state field, report:

- total rows;
- finite/non-null rows;
- missing fraction;
- zero fraction where economically meaningful;
- unique-value count;
- median update interval;
- p90/p99 update interval;
- longest gap;
- first/last valid timestamp;
- day coverage fraction;
- timestamp regressions;
- duplicate count.

For open interest, additionally report:

- non-positive count;
- extreme one-step relative changes;
- whether the field appears stepwise/stale for long intervals.

For funding, additionally report:

- number of distinct values;
- number of actual changes per day;
- whether changes appear scheduled rather than continuously informative.

For mark/index-derived premium or basis, additionally report:

- finite overlap count;
- median / p95 absolute premium in bps;
- sign changes;
- impossible or implausible price values.

These are descriptive data-quality statistics only.

## Frozen causal feature candidates for a later P1

P0 does not fit them, but it must determine whether the raw data can support the following fixed candidate transforms at a 1-minute decision grid:

### Open-interest state

- current log open interest;
- 1m, 5m, 15m, 30m log changes;
- 5m and 30m z-score versus trailing history using past-only observations.

### Funding state

- current funding rate;
- change since previous native update;
- time until next known scheduled funding timestamp when deterministically defined from venue rules rather than future records.

### Premium/basis state

- current mark-index premium bps when both are available;
- 1m, 5m, 15m, 30m change in premium;
- trailing 30m premium z-score using past-only values.

All later transforms must use the most recent record available at or before the decision timestamp and must enforce a frozen staleness limit selected **before** predictive scoring.

P0 must therefore report enough update-gap statistics to choose a defensible staleness limit without looking at predictive outcomes.

## P0 data-readiness gates

A candidate derivatives-state family is `DATA_READY_SANDBOX` only if all of the following hold:

1. all 14 frozen symbol-days are acquired and SHA-256 recorded;
2. no August path/request/file is accessed;
3. no schema ambiguity remains for the fields used in the proposed transforms;
4. a causal availability timestamp is defined for every retained record;
5. each symbol has at least 95% decision-time coverage at a 1-minute grid for open interest;
6. each symbol has at least 95% decision-time coverage for mark/index premium if that track is to be used;
7. no symbol-day has more than 5% malformed or non-finite retained rows in the accepted state fields;
8. timestamp regressions are either zero or deterministically resolved by a preregistered ordering rule without using future values;
9. all proposed P1 feature transforms can be generated using past-only information;
10. raw files remain immutable and ignored by Git.

Funding is allowed to be naturally sparse/scheduled and therefore is not required to satisfy 95% *change* frequency. It must, however, have a well-defined current state at decision times if included in P1.

## Possible P0 statuses

- `DATA_READY_SANDBOX` — all required acquisition/timing/schema/data-quality gates pass;
- `PARTIAL_DATA_READY` — one or more candidate economic fields are unusable, but a clearly defined subset remains suitable for a separately preregistered P1;
- `FAIL_DERIVATIVES_DATA_NOT_READY` — data cannot support a defensible causal P1;
- `INVALID` — sealed data opened, scope violated, provenance lost, or causality cannot be reconstructed.

`PARTIAL_DATA_READY` does not authorize silently dropping a failed field in P1. The exact retained subset must be frozen in a new P1 preregistration.

## No-rescue rules

After P0 output is opened, do not rescue the experiment by:

- adding exchanges;
- adding symbols;
- changing sandbox dates;
- opening August;
- adding liquidations;
- substituting undocumented fields;
- interpolating across large gaps;
- fitting any predictive model;
- choosing staleness based on AUC or economic outcomes.

Any such change requires a new experiment ID.

## Required implementation tests before acquisition

The acquisition/audit implementation must have synthetic/unit tests for:

1. rejection of non-frozen symbols;
2. rejection of non-frozen dates before network/file open;
3. deterministic destination naming;
4. SHA-256 manifest generation;
5. no-overwrite behavior for existing raw files;
6. schema-field classification;
7. local/receipt timestamp preference when both timestamps exist;
8. deterministic duplicate handling;
9. update-gap calculations;
10. decision-grid coverage calculations;
11. past-only as-of alignment;
12. raw-data directory remains ignored by Git.

## Stop condition

After implementation and tests, freeze the exact pre-acquisition commit and stop for review.

Only then may the 14 raw files be acquired exactly once.

No EXP005 predictive model is authorized by this document.
