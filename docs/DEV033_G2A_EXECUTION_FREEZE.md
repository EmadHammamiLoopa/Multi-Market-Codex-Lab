# DEV033-G2A Execution Freeze

Status: `EXECUTION_FROZEN_LOCAL_PREFLIGHT_REQUIRED_NO_CANONICAL_RUN_YET`

Scientific execution commit:

`36da3830a73099349870d18a3cd6865c69386a9d`

Successful CI run:

`33647622692 = SUCCESS`

All 13 jobs passed, including:

- dev033-g2a-materialization = SUCCESS
- dev032-e2a-materialization = SUCCESS
- dev032-e1b-screen = SUCCESS
- dev032-e2b-screen = SUCCESS
- dev031-p1a-materialization = SUCCESS
- dev031-p1b-incremental = SUCCESS
- retained unit/regression jobs = SUCCESS

Preserved failed implementation CI:

`33647146579`

Failure was compile-only in the new C++ extractor because `gzFile` was
incorrectly declared as `gzFile*`, creating a double pointer. No real data
materialization occurred. The source was corrected in commit:

`36da3830a73099349870d18a3cd6865c69386a9d`

## Frozen G2A scope

Materialization only.

Exactly 24 candidates:

- 8 temporal information families
- windows 8s / 16s / 32s
- every candidate is an added temporal layer intended for later composition
  with the frozen DEV030-P3 direction success

Exact support contract:

- rows = 1374
- LONG = 684
- SHORT = 690

No model fit.
No predictive metric.
No null.
No PnL.
No Sep-01+.
No Railway/archive/abundant-love.

## Frozen parent identities

DEV030-P3 direction success:

`/home/emadh/Multi-Market/evidence/dev030_p3_campaign1_v1/DEV030_P3_CAMPAIGN1_RESULT.json`

SHA256:

`f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`

Exact support source:

DEV032-E1A artifact:

`/home/emadh/Multi-Market/evidence/dev032_e1a_wave1_materialization_v1/DEV032_E1A_WAVE1_MATERIALIZATION.json`

SHA256:

`76e1c97e8b9a899bc27f3193316cbfc85efba8b0a7aa037d4c46fcc6a8be4a50`

bytes:

`44689`

## Canonical output

Directory:

`/home/emadh/Multi-Market/evidence/dev033_g2a_layered_temporal_materialization_v1`

Artifact:

`DEV033_G2A_LAYERED_TEMPORAL_MATERIALIZATION.json`

After the first canonical materialization starts:

`DEV033-G2A MUST NEVER BE RERUN`

## Interactive shell safety

Mandatory:

- no bare exit
- no parent-shell set -e / set -u / pipefail
- dedicated console log
- after any canonical attempt, diagnose read-only before any other action

## Next permitted action

Local preflight only.

Current state:

`DEV033_G2A_EXECUTION_FROZEN_LOCAL_PREFLIGHT_REQUIRED_NO_CANONICAL_RUN_YET`
