# DEV033-G2B Execution Freeze

Status: `EXECUTION_FROZEN_LOCAL_PREFLIGHT_REQUIRED_NO_CANONICAL_RUN_YET`

Scientific execution commit:

`a1dbb13b0aa1ef7d859afb37e8b216fb9849ae20`

Successful CI run:

`33649684772 = SUCCESS`

All 14 workflow jobs completed successfully, including:

- `dev033-g2b-screen = SUCCESS`
- `dev033-g2a-materialization = SUCCESS`
- `dev032-e2b-screen = SUCCESS`
- `dev032-e1b-screen = SUCCESS`
- `dev032-e1b-r1-harness = SUCCESS`
- retained DEV031/DEV032 regression jobs = SUCCESS
- Python 3.10 unit tests = SUCCESS
- Python 3.12 unit tests = SUCCESS

No real DEV033-G2B predictive fit has occurred yet.

## Frozen layered base

Direction-stage base remains:

`DEV030-P3 A / 120s / 16bp / 32s / PRICE / S1`

P3 canonical artifact:

`/home/emadh/Multi-Market/evidence/dev030_p3_campaign1_v1/DEV030_P3_CAMPAIGN1_RESULT.json`

SHA256:

`f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`

P3 frozen reproduction contract:

- feature count = 23
- pooled OOF support = 573
- LONG = 309
- SHORT = 264
- fold supports = 159 / 64 / 126 / 224
- pooled BA = 0.5419424831488764
- selected C = 10.0 / 10.0 / 0.1 / 0.01
- frozen prediction hashes:
  - F1 `e03d233bff936b49a0452994497f32ca5ecbe52c1f490d855fe8d06dbfa9dcf4`
  - F2 `cd2cba0a6dcf3591ec9848b78e31aef796dad15d371bbecb8517aa2507340bdd`
  - F3 `19f9acf70b0065a307c0373952cad350339768607a156c9307e5192503bb1f31`
  - F4 `b05ee6e926d6a943e1fc89828eb3801af0863fa270bc2e5db5ed7cd93e9a4b66`

## Frozen G2A identity

Canonical G2A materialization:

`/home/emadh/Multi-Market/evidence/dev033_g2a_layered_temporal_materialization_v1/DEV033_G2A_LAYERED_TEMPORAL_MATERIALIZATION.json`

SHA256:

`3336c70912bd0de0928a9fded04f3d7153fcd2df46dd2ed3d1b942a2c98922c6`

bytes:

`104750`

Verified 37/37 PASS.

Exactly:

- 24 candidates
- 2520 added-layer columns
- exact P3/E1A support and labels
- no support shrink

## Frozen G2B computation

Exactly 24 candidates:

`G2C01..G2C24`

Every candidate:

`P3 PRICE32 S1 base + one frozen G2A temporal layer`

Model lineage:

- train-only StandardScaler
- LogisticRegression
- solver = lbfgs
- l1_ratio = 0.0
- class_weight = None
- max_iter = 1000
- fit_intercept = True
- random_state = 20260825

C grid:

`0.01, 0.1, 1.0, 10.0`

Inner selection:

1. max balanced accuracy
2. max macro F1
3. min C

Primary endpoint:

`pooled BA(candidate) - pooled BA(P3)`

## Frozen joint null

- seed = 20260902
- replicates = 1999
- all 24 candidates jointly controlled
- same four validation-fold shifts applied to P3 and all candidates per replicate
- max-stat FWER

Artifact MUST serialize:

- 1999 shift tuples
- all 24 candidate-specific null vectors
- max-stat null vector
- raw p
- FWER p
- q95
- observed-minus-q95

CI explicitly tests artifact completeness and fails if any candidate-specific
null vector is absent.

## Survivor rule

Only `G2_LAYER_SURVIVOR` may alter the frozen direction base.

No failure or inconclusive candidate may be promoted.

Maximum advancement:

- 3 total
- 1 per information family
- no weak slot filling

## Canonical output

Directory:

`/home/emadh/Multi-Market/evidence/dev033_g2b_layered_temporal_screen_v1`

Artifact:

`DEV033_G2B_LAYERED_TEMPORAL_SCREEN_RESULT.json`

After the first canonical G2B execution starts:

`DEV033-G2B MUST NEVER BE RERUN`

## Process safety

Canonical execution must use:

`python -m multimarket.dev033_g2b_harness`

Interactive shell:

- no bare exit
- no parent-shell set -e / set -u / pipefail
- dedicated console log
- one BLAS/OpenMP thread per worker
- max 12 process workers
- read-only diagnosis after any canonical attempt before any other action

## Guards

No:

- Sep-01+
- new Aug-01/Aug-30 analysis
- Railway
- archive bucket
- abundant-love
- new acquisition
- PnL
- threshold optimization
- calibration rescue
- feature subset search
- alternate model family

## Next permitted action

Local preflight only.

Current state:

`DEV033_G2B_EXECUTION_FROZEN_LOCAL_PREFLIGHT_REQUIRED_NO_CANONICAL_RUN_YET`
