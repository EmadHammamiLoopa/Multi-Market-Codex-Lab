# DEV038-A-P1 Execution Freeze

Status: `EXECUTION_FROZEN_NO_RESULT_COMMON_SUPPORT_MATRIX_PREFLIGHT_NEXT`

Date: 2026-09-03

Scientific implementation commit:

`b24237dfeb2852fdcb4917af4ca2ce1986172975`

Dedicated CI:

- workflow run = `33691088164`
- workflow conclusion = SUCCESS
- job = `dev038a-p1`
- pytest = SUCCESS
- harness smoke = SUCCESS

The later commit `469497ec308debabb036112956013e03132fd61d`
updated the handoff only and is intentionally excluded from scientific
execution identity.

## Frozen parent

DEV038-A-P0 canonical artifact:

`/home/emadh/Multi-Market/evidence/dev038a_p0_common_support_v1/DEV038A_P0_COMMON_SUPPORT_RESULT.json`

SHA256:

`fd4639c003c4888a7316386b4ddb0031bf9bfb59d1d05afe0dc3fcb08b1ea6a5`

Bytes:

`8464`

Parent status:

`DEV038A_P0_COMMON_SUPPORT_PASS`

## Frozen common support

Aggregate:

`10016 rows`

Per-day:

- Jan = 1436
- Feb = 1434
- Mar = 1436
- Apr = 1428
- May = 1430
- Jun = 1424
- Jul = 1428

Exact support hashes must reproduce the P0 artifact before any fit.

## Frozen candidate family

Exactly:

- A0 PRICE32
- A1 PRICE_BOOK32
- A2 PRICE_BOOK_FLOW32
- A3 FULL32
- A4 FULL60

Comparator:

`A0`

Challengers:

- A1
- A2
- A3
- A4

## Frozen target

- BTCUSDT
- target A
- horizon = 120s
- barrier = 16bp
- binary TOUCH/NONE

## Frozen estimator

For every candidate:

- same P4 T2 S1 representation lineage;
- StandardScaler;
- LogisticRegression;
- exact P4 C grid;
- training-only nested C selection;
- no model-family search.

## Frozen outer folds

1. Jan-Mar -> Apr
2. Jan-Apr -> May
3. Jan-May -> Jun
4. Jan-Jun -> Jul

All candidates use the exact same common-support rows in train and validation.

## Frozen primary endpoint

`Average Precision`

Primary increment:

`Delta_AP = AP(challenger) - AP(A0)`

## Frozen survivor gates

A challenger must satisfy all:

- pooled Delta_AP >= +0.015;
- >=3/4 positive fold Delta_AP;
- all 4 LOO Delta_AP > 0;
- pooled Brier <= A0;
- pooled log loss <= A0;
- observed Delta_AP > joint max-stat q95;
- FWER p <= 0.05.

Joint null:

- 4 challengers
- seed = 20260903
- 1999 replicates
- legal fold shifts = 30 .. n_fold-30
- q95 method = higher
- plus-one empirical p denominator = 2000

## Canonical output reserved

Directory:

`/home/emadh/Multi-Market/evidence/dev038a_p1_joint_screen_v1`

Artifact:

`DEV038A_P1_JOINT_SCREEN_RESULT.json`

Canonical console:

`/home/emadh/Multi-Market/evidence/dev038a_p1_canonical_console_v1.log`

From the canonical start marker:

`DEV038-A-P1 MUST NEVER BE RERUN`

even if the attempt fails.

## Next permitted action

Real-data NO-RESULT common-support/matrix preflight only.

The preflight may:

- verify P0 parent identity;
- reconstruct all five candidate datasets;
- reconstruct exact 10016-row common support;
- verify all seven support hashes and TOUCH/NONE counts;
- build five common-support matrices;
- verify feature counts;
- verify all matrices finite;
- verify matrix/label/timestamp alignment;
- verify every frozen inner/outer partition has both classes;
- verify canonical output/log absent;
- run focused tests and harness smoke.

The preflight must NOT:

- fit StandardScaler;
- fit LogisticRegression;
- select C;
- calculate AP;
- calculate AUC;
- calculate Brier;
- calculate log loss;
- calculate top-decile metrics;
- run temporal null;
- classify survivors;
- calculate PnL;
- use fees/slippage;
- open forward data.

## Permanent no-rerun rules

`DEV038-A-P0 MUST NEVER BE RERUN`

`DEV037-P1-R1 MUST NEVER BE RERUN`

`DEV037-P0-R2 MUST NEVER BE RERUN`

`DEV037-P0-R1 MUST NEVER BE RERUN`

`DEV036-C1 MUST NEVER BE RERUN`

`DEV035-G4B MUST NEVER BE RERUN`

`DEV034-G3B-R1 MUST NEVER BE RERUN`

`DEV034-G3A-R1 MUST NEVER BE RERUN`

Current state:

`DEV038A_P1_EXECUTION_FROZEN_NO_RESULT_COMMON_SUPPORT_MATRIX_PREFLIGHT_NEXT`
