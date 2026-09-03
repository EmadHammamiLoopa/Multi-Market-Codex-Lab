# DEV044-T0D Execution Freeze

Status:

`DEV044_T0D_EXECUTION_FROZEN_CANONICAL_CALIBRATION_NEXT`

Date: 2026-09-03

## Scientific execution identity

`daf24758a969ef4e425ff04e6956491986acf039`

This commit contains:

- T0D calibration runner;
- synthetic/unit tests;
- the T0D CI job;
- the pure-calculation/local-I/O separation fix.

Later branch commits are documentation/handoff only and are not the scientific
execution identity.

## CI verification

Successful GitHub Actions runs:

- run `33762530075` / #1167 = success
- run `33762553042` / #1168 = success

Relevant jobs on both successful runs:

- `dev044-t0-strategy-contract = success`
- `dev044-t0a-a0-oof = success`
- `dev044-t0b-state-materialization = success`
- `dev044-t0c-flow-toxicity = success`
- `dev044-t0d-vpin-calibration = success`

The earlier run #1166 failed only because the synthetic fixture had not yet
been updated to provide the new source-identity field. No calibration formula
changed.

## Frozen canonical input

Exactly BTCUSDT TRADE250:

- 2026-01-01
- 2026-02-01
- 2026-03-01

No Apr-Jul input.
No labels.
No returns.
No PnL.
No Sep-01+.
No non-BTC input.

## Frozen calibration formula

`VPIN_BUCKET_VOLUME = median(pooled positive non-overlapping Jan-Mar 30m directional volume) / 50`

Constants:

- block = 1800 s
- rolling VPIN buckets = 50
- T16 veto threshold remains `toxicity >= 0.80`

## Canonical output

Directory:

`/home/emadh/Multi-Market/evidence/dev044_t0d_vpin_calibration_v1`

Artifact:

`DEV044_T0D_VPIN_CALIBRATION_RESULT.json`

The directory must not exist before canonical start.

## Canonical-run rule

Run exactly once after all pre-start guards pass.

Once the canonical output directory is created, T0D must not be rerun to seek a
different bucket volume.

If a post-start problem occurs, perform read-only forensic verification; do not
change the formula and rerun.

## Next after canonical PASS

Freeze:

- artifact bytes;
- artifact SHA256;
- numeric `vpin_bucket_volume`;
- pooled median 30m directional quantity;
- source TRADE250 SHA256 identities.

Then open:

`DEV044-T0E COMPLETE APR-JUL STATE + A0 MATERIALIZATION / NO-PNL SUPPORT AUDIT`

## Current state

`DEV044_T0D_EXECUTION_FROZEN_SINGLE_CANONICAL_NO_PNL_CALIBRATION_NEXT`
