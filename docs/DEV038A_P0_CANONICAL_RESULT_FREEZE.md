# DEV038-A-P0 Canonical Result Freeze

Status: `CANONICAL_SUCCESS_COMMON_SUPPORT_PASS`

Date: 2026-09-03

Scientific execution commit:

`0cf9ad1e966906ff154caaaf29bcc982a602ea45`

Canonical artifact:

`/home/emadh/Multi-Market/evidence/dev038a_p0_common_support_v1/DEV038A_P0_COMMON_SUPPORT_RESULT.json`

Artifact SHA256:

`fd4639c003c4888a7316386b4ddb0031bf9bfb59d1d05afe0dc3fcb08b1ea6a5`

Artifact bytes:

`8464`

Canonical console log:

`/home/emadh/Multi-Market/evidence/dev038a_p0_canonical_console_v1.log`

Canonical contract:

- 10 PASS
- 0 FAIL
- execution exit code = 0
- read-only verification = PASS
- git tree clean
- no staging residue

Permanent rule:

`DEV038-A-P0 MUST NEVER BE RERUN`

## Terminal result

`DEV038A_P0_COMMON_SUPPORT_PASS`

## Frozen candidate family

- A0 PRICE32
- A1 PRICE_BOOK32
- A2 PRICE_BOOK_FLOW32
- A3 FULL32
- A4 FULL60

Target remained exactly:

- BTCUSDT
- target A
- horizon = 120s
- barrier = 16bp

## Native valid support

A0 PRICE32:

- feature count = 23
- raw lookback = 32.25s
- aggregate valid rows = 10059

A1 PRICE_BOOK32:

- feature count = 89
- raw lookback = 32.25s
- aggregate valid rows = 10059

A2 PRICE_BOOK_FLOW32:

- feature count = 209
- raw lookback = 35.00s
- aggregate valid rows = 10048

A3 FULL32:

- feature count = 341
- raw lookback = 35.00s
- aggregate valid rows = 10048

A4 FULL60:

- feature count = 341
- raw lookback = 63.00s
- aggregate valid rows = 10016

## Exact common support

Common support equals the A4 valid support:

- rows = 10016
- A0 rows = 10059
- retained fraction vs A0 =
  `0.9957252211949498`

Thus only 43 A0 rows are lost by forcing exact five-candidate common support.

Per-day common support:

### 2026-01-01

- rows = 1436
- TOUCH = 4
- NONE = 1432
- SHA256 =
  `392de8c96e819552889a2d322274d0a8ab5decd9ba1e96f6c92c87a58559867d`

### 2026-02-01

- rows = 1434
- TOUCH = 434
- NONE = 1000
- SHA256 =
  `2f9f86e800f297ae52de20e0c699e2b4827e04e9e6ca55c2d8e02e485e386557`

### 2026-03-01

- rows = 1436
- TOUCH = 362
- NONE = 1074
- SHA256 =
  `edfa071fda1ea61810a7ecc0e7e7d2d1911b06e232973361188e64f77ded5c2f`

### 2026-04-01

- rows = 1428
- TOUCH = 158
- NONE = 1270
- SHA256 =
  `7b39848b5312c57e9983c805fdbe9365b194eed40d56f2c3d12dc3ddb4bb097f`

### 2026-05-01

- rows = 1430
- TOUCH = 62
- NONE = 1368
- SHA256 =
  `0554a6ec72c4e30c55474386d5e056296fe7ae27e3c2eb0c5acb81bb2e994586`

### 2026-06-01

- rows = 1424
- TOUCH = 118
- NONE = 1306
- SHA256 =
  `c37584c594ceee1ab4e4c93c542f9e5037ebea5a4f9e27862b3494cdc76957a1`

### 2026-07-01

- rows = 1428
- TOUCH = 220
- NONE = 1208
- SHA256 =
  `29d78a9f3557bfa74b60184bfffcf1c22138e7dbdd9e2ea20d8bb1252aa8ebf5`

## Frozen feasibility gates

All passed:

- retained fraction vs A0 >= 0.90
- all outer training folds contain TOUCH and NONE
- all outer validation folds contain TOUCH and NONE

## Forbidden activities remained false

- model fit = false
- predictive metrics = false
- PnL = false
- fees = false
- slippage = false
- forward data opened = false

## Scientific/practical consequence

DEV038-A-P1 is now allowed to compare A0-A4 on this exact common support.

A0 must be refit on the common support under the same frozen P4 T2 model
lineage; it is the common-support incumbent comparator.

No candidate-specific validation support is permitted.

Jan-Jul remains consumed development data. A later untouched period is still
required for confirmation of any DEV038-A survivor.

Current state:

`DEV038A_P0_FROZEN_PASS_P1_JOINT_COMMON_SUPPORT_SCREEN_NEXT`
