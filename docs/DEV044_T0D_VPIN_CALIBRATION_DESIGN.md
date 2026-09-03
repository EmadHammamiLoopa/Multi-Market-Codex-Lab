# DEV044-T0D — Canonical VPIN Bucket Calibration Design

Status:

`IMPLEMENTED_CI_PENDING_NO_PNL`

Date: 2026-09-03

## Purpose

Materialize the single numeric VPIN bucket-volume constant required by frozen
T16 before any DEV044 Apr-Jul economic scoring.

This stage is NO-PNL and NO-LABEL.

## Authorized input

Exactly three BTCUSDT TRADE250 development files:

- 2026-01-01
- 2026-02-01
- 2026-03-01

Source root:

`/home/emadh/Multi-Market/evidence/v23/phase0dl_trade250/BTCUSDT`

No Apr-Jul volume is used for calibration.

No Sep-01+ input is authorized.

No non-BTC input is authorized.

## Input integrity

Each TRADE250 file must have exactly:

- 345,600 rows;
- exact 250 ms timestamp spacing;
- nonnegative finite buy/sell/unknown quantities and counts;
- exact frozen header.

Because frozen FEATURE250 integrity reported zero unknown trades/quantity, T0D
fails closed if unknown quantity/count is nonzero.

## Frozen formula

For each Jan-Mar day:

1. split directional trade quantity (buy+sell) into 48 non-overlapping
   30-minute blocks;
2. retain positive-volume blocks;
3. pool all positive blocks across the three days;
4. compute their median;
5. divide by exactly 50.

`VPIN_BUCKET_VOLUME = median(pooled positive 30m directional volume) / 50`

No outcome, return, label, signal or PnL enters this calculation.

## Canonical artifact

Output directory:

`/home/emadh/Multi-Market/evidence/dev044_t0d_vpin_calibration_v1`

Artifact:

`DEV044_T0D_VPIN_CALIBRATION_RESULT.json`

The canonical artifact records:

- execution commit;
- source days;
- source TRADE250 SHA256 per day;
- directional quantity per day;
- positive 30m block counts;
- per-day median 30m directional quantity;
- pooled median 30m directional quantity;
- final VPIN bucket volume;
- rolling buckets = 50;
- calibration block seconds = 1800;
- explicit `pnl_run=false`;
- explicit `labels_opened=false`;
- explicit forward guards.

## One-shot semantics

Once the canonical output directory exists, do not rerun T0D to tune the
bucket volume.

If execution fails after canonical start, inspect read-only and do not choose a
different calibration formula using downstream results.

## Implementation

`src/multimarket/dev044_t0d_vpin_calibration.py`

Tests:

`tests/test_dev044_t0d_vpin_calibration.py`

## Next after green CI

Freeze the exact T0D execution identity, then run the single canonical
NO-PNL calibration locally.

After calibration passes, T16 has a frozen numeric toxicity-state scale.

Then:

`DEV044-T0E COMPLETE APR-JUL STATE + A0 MATERIALIZATION / NO-PNL SUPPORT AUDIT`

Only after T0E may numerical T1 eligibility gates be frozen.

## Current state

`DEV044_T0D_IMPLEMENTED_CI_PENDING_CANONICAL_CALIBRATION_NO_PNL`
