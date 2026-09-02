# DEV038-A-P1 Canonical Result Freeze

Status: `CANONICAL_SUCCESS_NO_CHALLENGER_SURVIVOR_RETAIN_A0`

Date: 2026-09-03

Scientific execution commit:

`b24237dfeb2852fdcb4917af4ca2ce1986172975`

Canonical artifact:

`/home/emadh/Multi-Market/evidence/dev038a_p1_joint_screen_v1/DEV038A_P1_JOINT_SCREEN_RESULT.json`

Artifact SHA256:

`16292d1f730561427a4623a052441f3ab20db0a96eeefac06b6f0a0391c5e549`

Artifact bytes:

`287084`

Canonical console:

`/home/emadh/Multi-Market/evidence/dev038a_p1_canonical_console_v1.log`

Canonical contract:

- process exit = 0
- read-only verification = PASS
- contract checks = 13 PASS / 0 FAIL
- staging residue = none
- git tree clean

Permanent rule:

`DEV038-A-P1 MUST NEVER BE RERUN`

## Terminal result

`DEV038A_P1_NO_CHALLENGER_SURVIVOR_RETAIN_A0`

Advanced opportunity representation:

`A0 PRICE32`

Survivor ranking:

`[]`

No challenger advanced.

## Frozen common support

- rows = 10016
- candidate IDs = A0, A1, A2, A3, A4
- all candidates used exact common support

## Pooled candidate results

### A0 — PRICE32

- AP = 0.2845541815789841
- ROC AUC = 0.7276441344419956
- Brier = 0.08769552270492408
- log loss = 0.3109620859642918
- TOUCH prevalence = 0.09772329246935202
- top-decile precision = 0.29545454545454547
- top-decile lift vs prevalence = 3.0233789507983055

### A1 — PRICE_BOOK32

- AP = 0.26178748866383383
- Delta AP vs A0 = -0.022766692915150266
- positive folds = 0/4
- all LOO positive = false
- FWER p = 1.0
- survivor = false

### A2 — PRICE_BOOK_FLOW32

- AP = 0.2635287777262429
- Delta AP vs A0 = -0.02102540385274121
- positive folds = 1/4
- all LOO positive = false
- FWER p = 1.0
- survivor = false

### A3 — FULL32

- AP = 0.2658056266027904
- Delta AP vs A0 = -0.01874855497619371
- positive folds = 2/4
- all LOO positive = false
- FWER p = 1.0
- survivor = false

### A4 — FULL60

- AP = 0.2751576355994575
- Delta AP vs A0 = -0.009396545979526605
- positive folds = 2/4
- all LOO positive = false
- FWER p = 0.9985
- survivor = false

## Joint temporal null

- seed = 20260903
- replicates = 1999
- joint max-stat q95 = 0.010896986544460252
- shift tuple count = 1999
- max-null count = 1999
- all null identity checks = PASS

## Interpretation

The richer BOOK/FLOW/FULL representations did not improve the primary
opportunity-ranking endpoint. All four challengers had negative pooled
Delta AP versus A0 and none satisfied the frozen fold-stability or
multiplicity-controlled survivor gates.

Some challengers improved pooled Brier/log loss relative to A0, but calibration
improvement alone was never a promotion criterion. The frozen primary endpoint
was Average Precision and all challenger AP deltas were negative.

A0 therefore remains the frozen opportunity representation.

This result does not establish profitability, executable economics, or forward
validity.

## Forward/economic guards remained false

- candidate-specific support = false
- fees = false
- forward data opened = false
- model family changed = false
- PnL = false
- slippage = false
- target geometry tuned = false

## Next-stage deviation note

The originally frozen DEV038-A-P1 design pointed directly to untouched forward
confirmation after P1. The project owner has now authorized one final,
explicitly separate development experiment before forward/economic work:

`DEV038-A-P2 FINAL CONTROLLER CORRECTNESS SCREEN`

This is recorded as a post-P1 development deviation, not as if it were part of
the original P1 plan.

Apr-Jul remain consumed development data.

No PnL or forward data is opened by this deviation.

Current state:

`DEV038A_P1_FROZEN_RETAIN_A0_DEV038A_P2_FINAL_CONTROLLER_DESIGN_NEXT`
