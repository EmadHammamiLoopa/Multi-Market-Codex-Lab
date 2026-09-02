# DEV034-G3A-R1 Execution Freeze

Status: `EXECUTION_FROZEN_LOCAL_REAL_DATA_PREFLIGHT_REQUIRED`

Date: 2026-09-02

Scientific implementation commit:

`54cc196dc2a69add4158b48bd8ad9f3223f3800c`

This commit includes the hardened parent-P3 lineage guard and its regression
tests.

Successful CI run for the scientific implementation commit:

`33657925824 = SUCCESS`

A later documentation-only tip also passed the full workflow:

`33657966330 = SUCCESS`

The scientific code authorized for real G3A-R1 execution remains exactly:

`54cc196dc2a69add4158b48bd8ad9f3223f3800c`

## Frozen scientific contract

Original frozen P3 T1 support:

- rows = 1374
- LONG = 684
- SHORT = 690

Single deterministic full-R common-support mask:

- rows = 1341
- LONG = 665
- SHORT = 676
- excluded = 33
- START_OF_DAY_30M_BOUNDARY = 30
- BOOK_INVALID_IN_30M_HISTORY = 3

Per-day eligible support:

- 2026-01-01 = 4
- 2026-02-01 = 422
- 2026-03-01 = 356
- 2026-04-01 = 156
- 2026-05-01 = 64
- 2026-06-01 = 121
- 2026-07-01 = 218

The exact three non-boundary excluded rows are:

- 2026-02-01T00:30:00+00:00
- 2026-06-01T00:30:00+00:00
- 2026-07-01T00:30:00+00:00

## Parent P3 hard guard

Before creating staging output, the runner must:

- verify the frozen P3 artifact exists;
- recompute and require exact P3 SHA256
  `f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`;
- parse the verified P3 JSON;
- require selected survivor `A / 120s / 16bp / 32s / PRICE`;
- reconstruct original support and require `1374 / 684 / 690`.

## Canonical output

Directory:

`/home/emadh/Multi-Market/evidence/dev034_g3a_r1_common_support_context_v1`

Artifact:

`DEV034_G3A_R1_COMMON_SUPPORT_CONTEXT.json`

After canonical G3A-R1 materialization starts:

`DEV034-G3A-R1 MUST NEVER BE RERUN`

## Prohibited activity

G3A-R1 is materialization only.

No:

- G3 direction model fit
- G3 direction metric
- temporal null
- PnL
- August or Sep-01+ analytical access
- Railway
- archive bucket
- abundant-love
- new download/acquisition

## Next permitted action

Local real-data preflight only, pinned to the scientific implementation commit.

Current state:

`DEV034_G3A_R1_EXECUTION_FROZEN_LOCAL_REAL_DATA_PREFLIGHT_REQUIRED`
