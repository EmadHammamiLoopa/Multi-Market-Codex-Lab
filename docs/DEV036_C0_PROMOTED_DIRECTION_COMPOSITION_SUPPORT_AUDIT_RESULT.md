# DEV036-C0 — Promoted Direction × Frozen Touch Support Audit Result

Status: `PASS_HIGH_SUPPORT_C1_DESIGN_AUTHORIZED`

Date: 2026-09-02

## Result

The corrected read-only DEV036-C0 audit completed successfully.

- CHECKS_PASS = 65
- CHECKS_FAIL = 0
- diagnostic RC = 0
- no model fit
- no touch refit
- no direction refit
- no composition metric
- no temporal null
- no EXP024 gate
- no forward-data access
- no PnL

## Frozen parent reproduction

DEV030-P4:

- experiment identity = PASS
- terminal status = `FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE` = PASS
- T2 eligible for composition = PASS
- composition status = reproduced PASS
- all seven T2 daily supports/counts/support hashes = reproduced PASS

DEV034-G3B-R1:

- experiment identity = PASS
- only survivor = G3C16 = PASS
- only advanced layer = G3C16 = PASS

## Full Jan-Jul T2 support

Original reconstructed P4 T2 campaign:

- rows = 10059
- TOUCH = 1374
- NONE = 8685

After exact causal G3C16 R-context validity:

- rows = 9849
- TOUCH = 1341
- NONE = 8508
- retained fraction = 0.9791231732776617
- removed = 210

Common-support SHA256:

`dc89f3012341bd771591693b03af00b86f64f95aa4f7db4e9dc65b7e0e7f7b3f`

Common T2 label SHA256:

`4a98955aab14f5d18019cecfc3ac74d443d47ee41cacc1482407746bc2193769`

Exclusion reasons:

- START_OF_DAY_30M_BOUNDARY = 203
- BOOK_INVALID_IN_30M_HISTORY = 7

The exclusion rule is the frozen causal R-context validity rule only.

## Per-day retained support

Each day retains exactly 1407 rows.

- Jan: TOUCH 4 / NONE 1403
- Feb: TOUCH 422 / NONE 985
- Mar: TOUCH 356 / NONE 1051
- Apr: TOUCH 156 / NONE 1251
- May: TOUCH 64 / NONE 1343
- Jun: TOUCH 121 / NONE 1286
- Jul: TOUCH 218 / NONE 1189

Every day retains both classes.

## Frozen P4 outer-validation reproduction

Original pooled validation:

- rows = 5748
- TOUCH = 573
- NONE = 5175

All reproduced exactly.

Retained common-support pooled validation:

- rows = 5628
- TOUCH = 559
- NONE = 5069

Validation days:

- Apr = 1407 / TOUCH 156 / NONE 1251
- May = 1407 / TOUCH 64 / NONE 1343
- Jun = 1407 / TOUCH 121 / NONE 1286
- Jul = 1407 / TOUCH 218 / NONE 1189

All four retain both classes.

## G3C16 directional subset invariant

Frozen G3C16 support remains an exact subset of retained T2 support:

- Jan = 4
- Feb = 422
- Mar = 356
- Apr = 156
- May = 64
- Jun = 121
- Jul = 218
- total = 1341

Every G3C16 row maps to T2 TOUCH.

## Feasibility

`HIGH_SUPPORT`

DEV036-C1 composition design may open.

Current state:

`DEV036_C0_PASS_HIGH_SUPPORT_C1_DESIGN_AUTHORIZED`
