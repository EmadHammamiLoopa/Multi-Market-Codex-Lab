# DEV038-A-P1 No-Result Matrix Preflight Result

Status: `PASS_SINGLE_CANONICAL_JOINT_SCREEN_NEXT`

Date: 2026-09-03

Scientific execution commit:

`b24237dfeb2852fdcb4917af4ca2ce1986172975`

## Preflight result

- checks PASS = 28
- checks FAIL = 0
- preflight RC = 0
- focused tests = 7 passed
- test RC = 0
- harness smoke = PASS
- smoke RC = 0
- post-preflight git tree = clean
- canonical output remained absent
- canonical log remained absent

## Frozen parent identity

DEV038-A-P0:

- SHA256 =
  `fd4639c003c4888a7316386b4ddb0031bf9bfb59d1d05afe0dc3fcb08b1ea6a5`
- bytes = 8464
- status = `DEV038A_P0_COMMON_SUPPORT_PASS`

## Common-support reproduction

Exact P0 common support reproduced:

- total rows = 10016

Per day:

- Jan = 1436, TOUCH 4, NONE 1432
- Feb = 1434, TOUCH 434, NONE 1000
- Mar = 1436, TOUCH 362, NONE 1074
- Apr = 1428, TOUCH 158, NONE 1270
- May = 1430, TOUCH 62, NONE 1368
- Jun = 1424, TOUCH 118, NONE 1306
- Jul = 1428, TOUCH 220, NONE 1208

All seven support hashes reproduced exactly.

## Matrix reproduction

All 35 candidate-day matrices were built on the exact common support and were
finite.

Feature dimensions reproduced exactly:

- A0 = 23
- A1 = 89
- A2 = 209
- A3 = 341
- A4 = 341

Every candidate totaled 10016 rows.

Cross-candidate row identity passed for every day.

## Fold class support

All passed:

- all outer training folds contain TOUCH and NONE;
- all outer validation folds contain TOUCH and NONE;
- all inner-fit partitions contain TOUCH and NONE;
- all inner-validation partitions contain TOUCH and NONE.

Observed frozen fold support:

Fold 1:
- train rows = 4306
- train TOUCH = 800
- validation Apr rows = 1428
- validation TOUCH = 158

Fold 2:
- train rows = 5734
- train TOUCH = 958
- validation May rows = 1430
- validation TOUCH = 62

Fold 3:
- train rows = 7164
- train TOUCH = 1020
- validation Jun rows = 1424
- validation TOUCH = 118

Fold 4:
- train rows = 8588
- train TOUCH = 1138
- validation Jul rows = 1428
- validation TOUCH = 220

## Explicit non-observation contract

The preflight did NOT:

- fit StandardScaler;
- fit LogisticRegression;
- select C;
- generate predictive probabilities;
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

Therefore no DEV038-A-P1 predictive result has yet been observed.

## Next action

The single canonical DEV038-A-P1 joint development screen is authorized next.

From the canonical start marker:

`DEV038-A-P1 MUST NEVER BE RERUN`

even if the canonical attempt fails.

Current state:

`DEV038A_P1_ALL_PREFLIGHTS_PASS_SINGLE_CANONICAL_JOINT_SCREEN_NEXT`
