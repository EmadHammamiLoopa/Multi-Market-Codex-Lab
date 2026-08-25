# CODEX-EXP-007-P0 Preregistration

Status: **PREREGISTERED BEFORE ANY EXP007 TARGET OR MODEL SCORING**

Date: 2026-08-26

Experiment ID: `CODEX-EXP-007-P0`

Parent frozen experiment:

`CODEX-EXP-006-P0 = FAIL_DVOL_DATA_NOT_CAUSALLY_USABLE`

Parent frozen result commit:

`6184ac9309d6c8df9d2833b0c9b9d9affe1da174`

## Scientific status of EXP006

EXP006-P0 remains a valid frozen failure.

Its preregistered PASS rule required all 20 acquired
BTC/ETH symbol-days to contain exactly 1,440 unique
60-second DVOL candles.

Four context datasets failed that rule:

- BTC 2026-03-31: 1,422/1,440;
- ETH 2026-03-31: 1,422/1,440;
- BTC 2026-06-30: 1,422/1,440;
- ETH 2026-06-30: 1,422/1,440.

EXP007 does not alter, replace, reinterpret as PASS, or
otherwise rescue the frozen EXP006-P0 result.

## Frozen post-EXP006 diagnostic evidence

A read-only diagnostic performed after preserving the
EXP006-P0 failure established:

2026-03-31:
- BTC missing exactly 09:02 through 09:19 UTC;
- ETH missing exactly 09:02 through 09:19 UTC.

2026-06-30:
- BTC missing exactly 09:02 through 09:19 UTC;
- ETH missing exactly 09:02 through 09:19 UTC.

Each gap contains exactly 18 consecutive minutes.

The BTC and ETH missing timestamp sets are identical on
each affected day.

The final missing minute is 881 minutes before the next
UTC midnight.

No target, model, direction, PnL, or August data was
examined in this diagnostic.

## External maintenance evidence

Deribit publicly documented scheduled platform maintenance
at approximately 09:00 UTC on both affected dates:

- 31 March 2026: expected downtime 15-30 minutes;
- 30 June 2026: expected downtime 15-30 minutes.

The observed 09:02-09:19 UTC gaps fall inside those
documented maintenance windows.

This maintenance evidence motivates a new data-usability
question. It does not change the EXP006 result.

## Scientific question

> Does the already-frozen Deribit DVOL dataset provide
> complete causal support for a bounded <=30-minute DVOL
> feature family at every eligible March-July experiment
> decision, when genuine source-maintenance gaps remain
> missing and are never imputed?

P0 is a target-independent data-support audit only.

It must not evaluate predictability.

## Immutable input data

Use only the frozen raw artifacts preserved by EXP006-P0
under:

`evidence/codex/exp006_p0_dvol/raw/`

The exact frozen files and SHA-256 hashes from EXP006 must
be reused.

EXP007-P0 must not redownload or replace those raw files.

No August data may be accessed.

## Supervised experiment days

Potential future P1 supervised days remain:

- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

for BTC and ETH.

These are the only candidate supervised DVOL days under
EXP007.

## Context days

The frozen context days are:

- 2026-02-28 for 2026-03-01;
- 2026-03-31 for 2026-04-01;
- 2026-04-30 for 2026-05-01;
- 2026-05-31 for 2026-06-01;
- 2026-06-30 for 2026-07-01.

Context days are feature-history only.

They are not additional target-training days.

## Frozen causal availability rule

At decision time `t`, a future EXP007-P1 DVOL feature may
use only candles with timestamp:

`<= t - 60 seconds`

No incomplete current-minute candle may be used.

No future candle may be used.

## Frozen maximum lookback

Under EXP007, the maximum permitted DVOL feature lookback is:

`30 minutes`

This limit is frozen before predictive scoring.

Therefore a decision at UTC midnight may require at most
the continuous timestamp interval:

`t - 31 minutes` through `t - 1 minute`

inclusive.

For example, for a decision at 2026-04-01 00:00 UTC,
the required cross-day DVOL support is:

2026-03-31 23:29 through 23:59 UTC.

A future EXP007-P1 may not introduce a DVOL transform whose
causal support requires history older than this frozen
30-minute maximum.

A longer DVOL lookback would require a new experiment ID.

## Missing-data rule

Missing source candles remain missing.

EXP007 must not:

- interpolate missing DVOL;
- forward-fill across a missing candle;
- backward-fill;
- synthesize candles;
- substitute BTC values for ETH or vice versa;
- use another source to repair the frozen data.

A decision row is causally eligible only if every DVOL
timestamp required by that row's frozen feature
construction exists.

## P0 support checks

For both BTC and ETH, P0 must verify:

1. every supervised experiment day contains exactly
   1,440 unique minute candles from 00:00 to 23:59 UTC;

2. all supervised-day timestamps are exactly 60 seconds
   apart;

3. every context/experiment midnight boundary contains all
   31 required timestamps from 23:29 through 23:59 UTC on
   the context day;

4. those 31 context timestamps are consecutive at exactly
   60-second spacing;

5. no maintenance gap intersects a required cross-midnight
   causal-support interval;

6. OHLC schema and numerical validity remain valid on every
   candle that can enter causal feature construction;

7. the frozen EXP006 raw artifact hashes are unchanged;

8. no August data is accessed;

9. no target, future return, direction, AUC, average
   precision, PnL, or model output is inspected.

## Treatment of maintenance gaps

A source-maintenance gap outside the causal support required
by an eligible decision is not imputed and is not itself a
reason to invalidate unrelated later decisions.

If a missing timestamp lies inside the causal support
required by a decision row, that row is invalid.

This rule is frozen before any predictive scoring.

## Provisional future P1 folds

Only if EXP007-P0 passes may a separate P1 preregistration
use the already-frozen four chronological outer folds:

1. outer 2026-04-01; train 2026-03-01;
2. outer 2026-05-01; train 2026-03-01 through 2026-04-01;
3. outer 2026-06-01; train 2026-03-01 through 2026-05-01;
4. outer 2026-07-01; train 2026-03-01 through 2026-06-01.

No outer observation may enter fitting or scaling.

## P0 PASS status

EXP007-P0 returns:

`DATA_READY_MAINTENANCE_AWARE_DVOL_SANDBOX`

only if every frozen causal-support check passes.

Otherwise it returns:

`FAIL_MAINTENANCE_AWARE_DVOL_SUPPORT`

## Meaning of a P0 PASS

A P0 PASS means only:

the frozen data can causally support a separately
preregistered bounded-lookback DVOL experiment.

It is not evidence that DVOL predicts opportunities.

It is not evidence of direction.

It is not evidence of profitability.

## Prohibited actions in P0

Do not:

- fit any classifier or regressor;
- inspect the >=24 bp opportunity labels;
- calculate AUC or average precision;
- inspect future returns;
- score direction;
- calculate PnL;
- alter the 10-minute target;
- alter the 24 bp threshold;
- open August;
- modify the EXP006 raw files;
- fill the scheduled-maintenance gaps.

If P0 passes, exact DVOL features, models, common support,
falsification controls, metrics, and promotion gates must
be frozen in a separate EXP007-P1 preregistration before
any predictive output is opened.
