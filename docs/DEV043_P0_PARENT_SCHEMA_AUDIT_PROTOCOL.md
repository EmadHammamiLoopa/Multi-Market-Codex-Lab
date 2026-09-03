# DEV043-P0 Parent / Schema Audit Protocol

Status:

`PROTOCOL_FROZEN_BEFORE_ANY_DEV043_REAL_RESULT`

Date: 2026-09-03

## Scope

DEV043-P0 is a no-result parent/schema/common-support audit only.

It verifies that the frozen H1800/B32 target can be factorized mechanically as:

`TOUCH = LONG_FIRST or SHORT_FIRST`

and, conditional on TOUCH:

`DIRECTION = LONG_FIRST or SHORT_FIRST`

without fitting any model or producing any predictive/economic metric.

## Frozen parents

### DEV041 canonical oracle headroom parent

Artifact:

`/home/emadh/Multi-Market/evidence/dev041_p2_model_free_headroom_v1/DEV041_P2_MODEL_FREE_HEADROOM_RESULT.json`

- bytes = 429239
- SHA256 =
  `542117791966f9049cb49e5b578d7857b3e1178f44be83172c7edfac56244a15`

Frozen semantic survivor:

`H1800_B32`

### DEV042-P0 common-support parent

Artifact:

`/home/emadh/Multi-Market/evidence/dev042_p0_feature_schema_audit_v1/DEV042_P0_FEATURE_SCHEMA_AUDIT_RESULT.json`

- bytes = 12989
- SHA256 =
  `d9259a53d24492f478615c986ed73981f052d483a764935a8dfd68d17212b882`

Per-day frozen common-support rows:

`1409`

Pooled common support:

`9863`

### DEV042-P3 closed predictive parent

Artifact:

`/home/emadh/Multi-Market/evidence/dev042_p3_predictive_screen_v1/DEV042_P3_PREDICTIVE_SCREEN_RESULT.json`

- bytes = 155134
- SHA256 =
  `bdb411e8536d94bb21deca5bfb7f31998023dacd727c27c3a67993b0bc07ac3f`

Frozen status:

`DEV042_NO_PREDICTIVE_SURVIVOR_FOR_H1800_B32`

## Allowed P0 checks

P0 may verify only:

- parent artifact identities;
- exact BTC Jan-Jul calendar;
- exact 1409-row common support per day;
- exact per-day common-support timestamp SHA256;
- exact H1800/B32 target schema;
- exact one-record-per-common-support-row alignment;
- exact factorization invariants:
  - NONE -> event NONE and no conditional direction;
  - LONG_FIRST -> event TOUCH and conditional LONG;
  - SHORT_FIRST -> event TOUCH and conditional SHORT;
- invalid/ambiguous rows never become valid Stage-A or Stage-B samples;
- Stage-B support is a strict subset of valid Stage-A support unless every
  valid row touches;
- feature-family dimensions/hashes remain identical to frozen DEV042 schema.

## Explicitly forbidden outputs

P0 must NOT serialize or print:

- TOUCH count;
- NONE count;
- TOUCH prevalence;
- LONG count;
- SHORT count;
- conditional direction prevalence;
- ambiguity count/prevalence;
- class metrics;
- estimator fit;
- probabilities;
- action coverage;
- economics;
- null statistics;
- candidate ranking;
- survivor status.

Boolean invariant results and support/hash identities are allowed.

## Pass contract

P0 passes only if ALL:

1. all parent identities match;
2. seven exact BTC Jan-Jul days are loaded;
3. every day reproduces common-support count = 1409;
4. every day reproduces frozen common-support timestamp SHA256;
5. one H1800/B32 record exists per common-support row;
6. all valid labels map deterministically to the frozen Stage-A/Stage-B schema;
7. invalid/ambiguous rows map to no training label;
8. Stage-B support is contained in Stage-A valid support;
9. exact feature dimensions remain 15/60/51/111/111;
10. no forbidden result is calculated or serialized;
11. Sep-01+ and non-BTC markets remain sealed.

If any check fails:

`DEV043_P0_PARENT_SCHEMA_AUDIT_FAIL`

If all pass:

`DEV043_P0_PARENT_SCHEMA_AUDIT_PASS`

## Next authorization

A passing P0 authorizes DEV043-A implementation + synthetic/unit CI only.

No real Stage-A predictive scoring is authorized by P0.

## Current state

`DEV043_P0_PROTOCOL_FROZEN_IMPLEMENTATION_AND_SYNTHETIC_CI_NEXT`
