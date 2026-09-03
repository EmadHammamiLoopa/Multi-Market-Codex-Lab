# DEV044-T0D Canonical VPIN Calibration Result Freeze

Status:

`DEV044_T0D_VPIN_BUCKET_CALIBRATION_PASS`

Date: 2026-09-03

## Scientific execution identity

`daf24758a969ef4e425ff04e6956491986acf039`

DEV044-T0D MUST NEVER BE RERUN.

## Canonical artifact

Path:

`/home/emadh/Multi-Market/evidence/dev044_t0d_vpin_calibration_v1/DEV044_T0D_VPIN_CALIBRATION_RESULT.json`

Bytes:

`1314`

SHA256:

`c0cf0362f2f4a0559ff28c95e72824f5a8e5fa34a20394c33fe71f263f88143c`

## Frozen calibration result

Pooled median non-overlapping 30-minute directional BTC volume:

`2278.4915`

Frozen VPIN bucket volume:

`45.56983`

Rolling VPIN buckets:

`50`

Calibration block:

`1800 seconds`

Frozen T16 veto threshold remains:

`toxicity >= 0.80 -> ABSTAIN`

No threshold search occurred.

## Canonical input identities

### 2026-01-01

TRADE250 SHA256:

`485b64c613dda9d883efb80eaaf66fa0ed2c14e2ddfc0e0e9a711cc924fa00e7`

Rows:

`345600`

Directional quantity:

`47941.292`

Positive 30-minute blocks:

`48`

Median 30-minute directional quantity:

`773.1505`

### 2026-02-01

TRADE250 SHA256:

`ec64da03bbb2f197f8136293329e3015f704a1bbaa02b79f0f5c78e812b18db0`

Rows:

`345600`

Directional quantity:

`186842.822`

Positive 30-minute blocks:

`48`

Median 30-minute directional quantity:

`2424.716`

### 2026-03-01

TRADE250 SHA256:

`1c76a21cbf87bde88eda23c383adcdbcf03fd02002c8ac320f45f5f5f2078320`

Rows:

`345600`

Directional quantity:

`219111.21099999998`

Positive 30-minute blocks:

`48`

Median 30-minute directional quantity:

`3284.9700000000003`

## Verification

All pre-start guards passed:

- HEAD identity PASS
- clean tree PASS
- canonical output absent PASS
- Jan-Mar BTC TRADE250 inputs present PASS

Canonical run:

- status = `DEV044_T0D_VPIN_BUCKET_CALIBRATION_PASS`

Read-only verification:

- artifact exists PASS
- artifact bytes PASS
- artifact SHA256 PASS
- calibration days PASS
- rolling buckets PASS
- block seconds PASS
- no PnL PASS
- no labels PASS
- Apr-Jul economic scoring unopened PASS
- Sep-01+ sealed PASS
- other markets sealed PASS

## Permanent rules

- do not rerun DEV044-T0D
- do not recalibrate bucket volume
- do not replace the Jan-Mar calibration days
- do not tune bucket count after viewing Apr-Jul
- do not tune the T16 toxicity threshold after viewing Apr-Jul
- do not use Apr-Jul economic results to alter VPIN scaling

## Next authorized stage

`DEV044-T0E COMPLETE APR-JUL STATE + A0 MATERIALIZATION / NO-PNL SUPPORT AUDIT`

T0E may materialize:

- Apr-Jul 60-second decision support;
- all frozen T01-T16 causal state inputs;
- DEV032 raw-event adapter states;
- frozen T10 normalized flow;
- frozen T16 VPIN using bucket volume `45.56983`;
- frozen A0 OOF p_touch stream;
- U/A action counts and support diagnostics.

T0E MUST NOT compute returns, trade outcomes, PnL, profit factor, drawdown, or
economic ranking.

## Current state

`DEV044_T0D_CANONICAL_PASS_FROZEN_T0E_NO_PNL_SUPPORT_AUDIT_AUTHORIZED`
