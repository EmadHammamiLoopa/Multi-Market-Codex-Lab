# DEV037-P0-R1 Canonical Result Freeze

Status: `CANONICAL_SUCCESS_NO_CONTROLLER_OPERATIONALLY_FEASIBLE`

Date: 2026-09-02

Scientific execution commit:

`6f2a65423fe0b70fc82b1558ff49aa2ef87a9256`

Canonical artifact:

`/home/emadh/Multi-Market/evidence/dev037_p0_r1_adaptive_coverage_controller_v1/DEV037_P0_R1_ADAPTIVE_COVERAGE_CONTROLLER_RESULT.json`

Artifact SHA256:

`df7a116e516ff70439c912b0ac8e5c3ad5e04c50195264f5d8fd2b53d3750429`

Artifact bytes:

`39526`

Canonical contract:

- 16 PASS
- 0 FAIL
- process exit = 0
- read-only verification = PASS
- staging residue = none
- git tree clean

Permanent rule:

`DEV037-P0-R1 MUST NEVER BE RERUN`

## Terminal result

`DEV037_P0_R1_NO_CONTROLLER_OPERATIONALLY_FEASIBLE`

No controller among W120 / W360 / W720 was globally feasible across all 24
policy-fold combinations.

Controller ranking was empty.

No controller window was selected.

## Why global feasibility failed

The failure is concentrated in the bounded percentile-combination policies S3
and S4 on Fold 1 / Apr.

W120:

- S3 coverage = 0.8713574982
- S4 coverage = 0.8699360341

W360:

- S3 coverage = 0.7789623312
- S4 coverage = 0.7796730633

W720:

- S3 coverage = 0.5707178394
- S4 coverage = 0.5707178394

The other policies on Fold 1 were mostly operationally feasible.

Subsequent folds show S3/S4 can also operate near the intended range, e.g.
Fold 2-4, especially under W120.

This pattern is consistent with a score-transport/tie-saturation issue rather
than a general failure of adaptive rolling quantiles.

## Mechanistic interpretation

S3 and S4 are built from empirical percentile transforms bounded in [0,1].

When validation component scores move beyond the OOF reference range, many
mapped percentile values saturate at 1.0.

The rolling q80 threshold can therefore also equal 1.0.

Because the frozen action rule is:

`ACT iff score >= threshold`

large tied masses at score == threshold can all be admitted simultaneously,
causing severe over-coverage.

This explains why increasing W from 120 to 720 reduces but does not eliminate
the Fold-1 S3/S4 over-coverage.

## Controller aggregate ranking statistics

W120:

- mean absolute coverage error = 0.0687988628
- worst absolute coverage error = 0.6713574982
- mean rolling60 error = 0.1333034537
- rolling60 outside count = 10569

W360:

- mean absolute coverage error = 0.0804311774
- worst absolute coverage error = 0.5796730633
- mean rolling60 error = 0.1649717689
- rolling60 outside count = 16335

W720:

- mean absolute coverage error = 0.0752783701
- worst absolute coverage error = 0.3707178394
- mean rolling60 error = 0.1706025387
- rolling60 outside count = 18381

No window is promoted because global feasibility was frozen as all six policies
passing all four folds.

## What was NOT inspected

The canonical artifact confirms all forbidden-activity guards remained false:

- validation correctness not inspected;
- action precision not calculated;
- correct-action count not calculated;
- false-action count not calculated;
- no temporal null;
- no policy survivor classification;
- no PnL;
- no fees;
- no slippage;
- no forward data.

Therefore no policy has been rejected on action quality or profitability.

## Scientific/practical consequence

Do not run DEV037-P1.

Do not rerun DEV037-P0-R1.

Do not simply pick W120 because it has the lowest average coverage error; the
frozen global-feasibility criterion failed.

A new separately frozen operational revision may address the percentile
saturation/tie behavior without using validation correctness.

Current state:

`DEV037_P0_R1_FROZEN_NO_CONTROLLER_S3_S4_PERCENTILE_TIE_SATURATION_NEXT_DISTINCT_OPERATIONAL_REVISION_REQUIRED`
