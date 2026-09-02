# DEV038-A-P0 Execution Freeze

Status: `EXECUTION_FROZEN_SINGLE_COMMON_SUPPORT_CANONICAL_AUDIT_NEXT`

Date: 2026-09-03

Scientific implementation commit:

`0cf9ad1e966906ff154caaaf29bcc982a602ea45`

Dedicated CI:

- workflow run = `33689739595`
- workflow conclusion = SUCCESS
- job = `dev038a-p0`
- pytest = SUCCESS
- harness smoke = SUCCESS

## Frozen candidate family

Exactly:

- A0 PRICE32
- A1 PRICE_BOOK32
- A2 PRICE_BOOK_FLOW32
- A3 FULL32
- A4 FULL60

## Frozen target

- BTCUSDT
- target A
- horizon = 120s
- barrier = 16bp

## P0 scope

P0 is support-only.

It may:

- load authorized Jan-Jul development data;
- build the five frozen candidate representations;
- map the frozen TOUCH/NONE target;
- compute native support counts/hashes;
- compute exact common-support intersection;
- verify label agreement on common timestamps;
- compute feature counts/lookback spans;
- verify class presence in all frozen train/validation folds.

It must not:

- fit any model;
- calculate AP/AUC/Brier/log loss;
- calculate policy correctness;
- calculate PnL;
- use fees/slippage;
- open forward data.

## Frozen feasibility gates

P0 PASS requires:

- common support retained fraction vs A0 >= 0.90;
- every outer validation fold contains both TOUCH and NONE;
- every outer training fold contains both TOUCH and NONE.

## Canonical output reserved

Directory:

`/home/emadh/Multi-Market/evidence/dev038a_p0_common_support_v1`

Artifact:

`DEV038A_P0_COMMON_SUPPORT_RESULT.json`

From the canonical P0 start marker:

`DEV038-A-P0 MUST NEVER BE RERUN`

even if the attempt fails.

## Permanent upstream rules

`DEV037-P1-R1 MUST NEVER BE RERUN`

`DEV037-P0-R2 MUST NEVER BE RERUN`

`DEV037-P0-R1 MUST NEVER BE RERUN`

`DEV036-C1 MUST NEVER BE RERUN`

`DEV035-G4B MUST NEVER BE RERUN`

`DEV034-G3B-R1 MUST NEVER BE RERUN`

`DEV034-G3A-R1 MUST NEVER BE RERUN`

Current state:

`DEV038A_P0_EXECUTION_FROZEN_SINGLE_COMMON_SUPPORT_CANONICAL_AUDIT_NEXT`
