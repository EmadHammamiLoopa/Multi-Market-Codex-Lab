# DEV036-C1 Execution Freeze

Status: `EXECUTION_FROZEN_LOCAL_REAL_DATA_PREFLIGHT_REQUIRED`

Date: 2026-09-02

Scientific implementation commit:

`cc449a90214b2ab5e1a8e8e9b30d6f25ffcf0b0b`

Dedicated corrected CI:

- workflow run = `33680109169`
- workflow conclusion = SUCCESS
- job = `dev036-c1-composition`
- pytest = SUCCESS
- harness smoke = SUCCESS

The earlier run `33679377080` failed only because the synthetic test fixture
omitted the NONE class. That fixture was corrected before any real-data fit.

## Frozen parents

DEV030-P4 canonical artifact:

`/home/emadh/Multi-Market/evidence/dev030_p4_t2_composition_v1/DEV030_P4_T2_COMPOSITION_RESULT.json`

SHA256:

`8dbe23963def1e96da78a73d206e651aa40b0aeab8ba40419716529be33b5a16`

DEV034-G3B-R1 canonical artifact:

`/home/emadh/Multi-Market/evidence/dev034_g3b_r1_common_support_screen_v1/DEV034_G3B_R1_COMMON_SUPPORT_SCREEN_RESULT.json`

SHA256:

`16200a1595d9472fe488740c0ab63e013b65824298ef1cb0b8856322416a8167`

Bytes:

`873268`

## Frozen C0 common support

Rows:

`9849`

TOUCH:

`1341`

NONE:

`8508`

Support SHA256:

`dc89f3012341bd771591693b03af00b86f64f95aa4f7db4e9dc65b7e0e7f7b3f`

Pooled outer validation:

- rows = 5628
- TOUCH = 559
- NONE = 5069

## Frozen C1 systems

- C0 = THREE_CLASS_TRAIN_PREVALENCE
- C1 = TOUCH_PLUS_DIRECTIONAL_PRIOR
- C2 = TOUCH_PLUS_P3_COMMON_DIRECTION
- C3 = TOUCH_PLUS_BTC45_PROMOTED_DIRECTION

Primary comparison:

`C3 vs C2`

Primary endpoint:

`Delta_LL_32 = log_loss(C2) - log_loss(C3)`

## Frozen direction reproduction requirement

Before any C1 composition result may be produced, all four folds must exactly
reproduce the canonical G3B-R1 prediction hashes for:

- P3_COMMON_SUPPORT_REFIT
- G3C16

Any mismatch is a pre-execution reproduction failure and no composition result
may be emitted.

## Frozen temporal null

- shift only SHORT/LONG labels within TOUCH rows
- keep NONE positions fixed
- replicates = 1999
- seed = 20260902
- plus-one empirical p
- q95 uses method = higher

## Canonical output reserved

Directory:

`/home/emadh/Multi-Market/evidence/dev036_c1_promoted_direction_composition_v1`

Artifact:

`DEV036_C1_PROMOTED_DIRECTION_COMPOSITION_RESULT.json`

From the moment the canonical DEV036-C1 execution begins:

`DEV036-C1 MUST NEVER BE RERUN`

This applies even if the canonical attempt fails.

## Next permitted action

Local real-data preflight only.

The preflight may:

- verify exact git identity and clean tree;
- verify canonical output is absent;
- verify P4 and G3B parent identities;
- load and reconstruct the frozen 9849-row common support;
- verify 1407 rows per day;
- verify TOUCH/NONE counts;
- verify three-class support;
- verify P3 width 23 and BTC45 width 45;
- verify all matrices are finite;
- verify exact 1341 directional TOUCH support;
- verify the canonical expected prediction hashes are present in G3B-R1;
- run unit/synthetic tests and harness smoke.

The preflight must NOT:

- fit the support-matched touch estimator;
- fit P3 direction;
- fit BTC45/G3C16 direction;
- calculate real composition metrics;
- reproduce real prediction hashes by refitting;
- run the temporal null;
- write canonical output;
- open forward data;
- run PnL.

Current state:

`DEV036_C1_EXECUTION_FROZEN_LOCAL_REAL_DATA_PREFLIGHT_REQUIRED`
