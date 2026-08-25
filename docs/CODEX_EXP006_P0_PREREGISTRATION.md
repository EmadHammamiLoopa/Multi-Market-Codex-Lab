# CODEX-EXP-006-P0 Preregistration

Status: **PREREGISTERED AFTER NON-SCORING AVAILABILITY PROBES AND BEFORE FULL P0 ACQUISITION/AUDIT OR ANY TARGET/MODEL SCORING**

Date: 2026-08-26

Experiment ID: `CODEX-EXP-006-P0`

Parent frozen result:

`CODEX-EXP-005-P1 = FAIL_DERIVATIVES_NO_INCREMENTAL_TIMING_INFORMATION`

Parent preserved result commit:

`33f9803f9423ff7eb1e9fd428f612320d657ddef`

## Scientific motivation

EXP004 established that economically meaningful 10-minute executable opportunities exist in the consumed January-July sandbox, while regime/volatility information was materially more predictive than the tested short-horizon microstructure information.

EXP005 then tested whether Binance perpetual-derivatives state — open interest, funding, and premium/basis — added within-regime timing information. It failed its frozen incremental and timing-falsification gates.

EXP006 changes the information family rather than rescuing EXP005.

The new candidate is options-implied volatility state from the Deribit volatility index (DVOL).

## P0 question

> Is causally usable BTC and ETH Deribit options-implied volatility-index history sufficiently complete, well-formed, and reproducible on the required sandbox dates to justify a separately preregistered P1 test of incremental 10-minute opportunity timing beyond regime baseline R?

P0 is a data-readiness and causality audit only.

It must not score predictive performance.

## Prior non-scoring availability probes

Before this preregistration, two read-only API probes were performed.

No files were written by those probes.
No target labels were scored.
No model was fit.
No direction or PnL was scored.
No August data was accessed.

Observed:

- BTC and ETH 60-second DVOL returned no data for 2026-01-01 or 2026-02-01.
- 2026-03-01 was successfully reconstructed through pagination for both BTC and ETH.
- Both had exactly 1,440 unique minute candles from 00:00 through 23:59 UTC with zero minute gaps.
- 2026-02-20 was only partially available from 22:12 UTC.
- Data was available from 2026-02-21 onward in the availability probe.
- The apparent 1,000-row daily truncation was confirmed to be API pagination rather than an incomplete March day.

These probes authorize only the present P0 acquisition/audit.

They are not predictive evidence.

## Source

Public Deribit API endpoint:

`public/get_volatility_index_data`

Currencies:

- BTC
- ETH

Resolution:

- 60 seconds

Returned observations are volatility-index OHLC candles:

`timestamp, open, high, low, close`

API pagination must be followed until `continuation = null`.

No authenticated/private data is used.

## Frozen acquisition dates

The candidate P1 design uses only the first UTC day of March through July 2026.

To permit causal trailing DVOL construction at UTC midnight, the immediately preceding UTC day is also acquired as context.

Required dates:

- 2026-02-28
- 2026-03-01
- 2026-03-31
- 2026-04-01
- 2026-04-30
- 2026-05-01
- 2026-05-31
- 2026-06-01
- 2026-06-30
- 2026-07-01

for both BTC and ETH.

Exactly 20 symbol-day datasets are required.

No August date may be requested or opened.

January and February 1 will not be reconstructed, imputed, substituted, or sourced post hoc merely to recreate the EXP004/EXP005 five-fold design.

## Provisional future P1 chronological design

If and only if P0 passes, P1 may be separately preregistered with four expanding chronological outer folds:

1. outer 2026-04-01; train 2026-03-01;
2. outer 2026-05-01; train 2026-03-01 through 2026-04-01;
3. outer 2026-06-01; train 2026-03-01 through 2026-05-01;
4. outer 2026-07-01; train 2026-03-01 through 2026-06-01.

The preceding context days are feature-history only and do not become target-training days.

This four-fold design is frozen before any EXP006 target/model scoring.

## Causal candle-availability rule

The API exposes OHLC candles, while timestamp anchoring must not be assumed to make the current minute fully observable.

Therefore any future P1 decision at time `t` may use only a DVOL candle whose timestamp is:

`<= t - 60 seconds`

This conservative one-resolution lag guarantees that the selected 60-second candle is completed before the decision even under start-of-candle timestamp semantics.

No current incomplete minute may be used.

No interpolation from a future candle is allowed.

## P0 required integrity checks

For every required symbol-day:

1. exactly 1,440 unique timestamps;
2. first timestamp exactly 00:00 UTC;
3. last timestamp exactly 23:59 UTC;
4. every adjacent timestamp exactly 60 seconds apart;
5. no duplicate timestamps;
6. every row contains exactly five fields;
7. timestamp is integer milliseconds;
8. open/high/low/close are finite positive numbers;
9. high >= max(open, close);
10. low <= min(open, close);
11. high >= low;
12. pagination terminates normally;
13. canonical data SHA-256 is recorded;
14. no August path/request is accessed.

BTC and ETH are audited separately.

## Canonical raw-data policy

Each acquired symbol-day must be preserved in a deterministic canonical artifact containing only:

- source identifier;
- currency;
- UTC date;
- resolution;
- sorted unique candle data.

Acquisition-time metadata belongs in a separate manifest so that identical market data produces the same canonical data SHA-256.

Raw numerical values must not be altered, interpolated, rounded, filled, or winsorized.

## P0 descriptive diagnostics

P0 may inspect only target-independent properties of DVOL itself, including:

- coverage;
- gaps;
- duplicates;
- OHLC validity;
- level distribution;
- minute-to-minute variation;
- zero-change frequency;
- extreme finite changes;
- continuity across the context-day / first-day boundary.

P0 must not inspect:

- opportunity labels;
- future returns;
- direction;
- AUC;
- average precision;
- correlation with the opportunity target;
- PnL;
- model coefficients selected against target performance.

## Information-family boundary

EXP006 is an own-currency Deribit DVOL experiment.

P0/P1 under this experiment ID may not add:

- full options-chain data;
- strike-level open interest;
- put/call ratios;
- option skew;
- risk reversals;
- butterfly measures;
- term-structure surfaces from individual options;
- Binance derivatives features as rescue features;
- cross-venue microstructure;
- news;
- macro;
- on-chain data;
- another model family after results are seen.

Any such materially different information source requires a new experiment ID.

## P0 PASS status

P0 may return:

`DATA_READY_DVOL_SANDBOX`

only if all 20 required symbol-day datasets pass the frozen integrity and causality-readiness checks.

If required data cannot be acquired completely or cannot be made causally usable under the frozen availability rule, P0 returns:

`FAIL_DVOL_DATA_NOT_CAUSALLY_USABLE`

P0 success is not predictive evidence.

## Stop / no-rescue rule

P0 must not:

- fit a classifier or regressor;
- score the 24 bp opportunity target;
- change the 10-minute target;
- change the 24 bp threshold;
- score direction;
- score PnL;
- open August;
- use January/February substitutes to fabricate the former five-fold design.

If P0 passes, a separate `CODEX-EXP-006-P1` preregistration must freeze the exact DVOL feature transforms, model, controls, metrics, promotion gates, and common-support rules before any predictive scoring begins.
