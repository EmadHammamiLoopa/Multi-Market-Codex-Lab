# DEV034-G3B-R1 Execution Freeze

Status: `EXECUTION_FROZEN_LOCAL_REAL_DATA_PREFLIGHT_REQUIRED`

Date: 2026-09-02

Scientific implementation commit:

`0b4082e4dbc76cba6b2624051433b6072ce19ad4`

This is the tested scientific implementation containing:

- matched-support screen core
- frozen G3A-R1/P3 loader
- matched P3 common-support refit comparator
- 16-candidate runner
- harness
- synthetic/unit tests

Dedicated CI job:

`dev034-g3b-r1-screen = SUCCESS`

Workflow run:

`33660377010`

The execution must reset to exactly:

`0b4082e4dbc76cba6b2624051433b6072ce19ad4`

## Frozen parent identities

P3 artifact SHA256:

`f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`

G3A-R1 artifact:

`/home/emadh/Multi-Market/evidence/dev034_g3a_r1_common_support_context_v1/DEV034_G3A_R1_COMMON_SUPPORT_CONTEXT.json`

G3A-R1 SHA256:

`43f4460d6990846218f3d0618a261d3852d3a198a50420ff05afbc97c832425e`

G3A-R1 bytes:

`28890`

G3A-R1 permanent rule:

`DEV034-G3A-R1 MUST NEVER BE RERUN`

## Frozen matched support

Campaign:

- rows = 1341
- LONG = 665
- SHORT = 676

Pooled outer validation:

- rows = 559
- LONG = 302
- SHORT = 257

Validation folds:

- Apr = 156 / 85 LONG / 71 SHORT
- May = 64 / 40 LONG / 24 SHORT
- Jun = 121 / 55 LONG / 66 SHORT
- Jul = 218 / 122 LONG / 96 SHORT

## Predictive protocol

Comparator:

`P3_COMMON_SUPPORT_REFIT`

Every candidate:

`P3_COMMON_SUPPORT_REFIT feature base + one frozen G3 context block`

Exactly 16 candidates:

`G3C01..G3C16`

Model lineage:

- StandardScaler fit on training rows only
- LogisticRegression L2 / lbfgs
- C grid 0.01 / 0.1 / 1.0 / 10.0
- threshold 0.5
- random_state 20260825

Joint temporal null:

- 1999 replicates
- seed 20260902
- 16-way max-stat FWER
- same validation-fold shifts for comparator and all candidates

## Canonical output reserved

Directory:

`/home/emadh/Multi-Market/evidence/dev034_g3b_r1_common_support_screen_v1`

Artifact:

`DEV034_G3B_R1_COMMON_SUPPORT_SCREEN_RESULT.json`

After canonical predictive execution starts:

`DEV034-G3B-R1 MUST NEVER BE RERUN`

## Next permitted action

Local real-data preflight only.

The preflight may:

- load and verify frozen artifacts
- reconstruct matched matrices
- verify exact support/class counts
- verify candidate widths/hashes
- run no estimator fit
- score no metric
- run no temporal null
- write no canonical output

Current state:

`DEV034_G3B_R1_EXECUTION_FROZEN_LOCAL_REAL_DATA_PREFLIGHT_REQUIRED`
