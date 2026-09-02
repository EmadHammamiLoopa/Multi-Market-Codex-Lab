# DEV038-A-P2 No-Result Reproduction Preflight Result

Status: `PASS`

Date: 2026-09-03

Scientific execution commit:

`a1ac3ea806def0f38b8952295b68fab8eb18e3a1`

Frozen protocol:

`docs/DEV038A_P2_NO_RESULT_PREFLIGHT_PROTOCOL.md`

Protocol commit:

`c51974065fee3d713dce6878d59e8e68351fbf3b`

## File guards

- HEAD identity = PASS
- clean tree = PASS
- canonical P2 output absent = PASS
- canonical P2 log absent = PASS
- no staging residue = PASS

Frozen parent identities:

DEV037-P0-R2:
- SHA256 = `494122f1aea64fb2a4c956d674330d9a400709656f0e116187d6fa2fefaa3336`
- bytes = 27056
- identity = PASS

DEV037-P1-R1:
- SHA256 = `9a9ade5fbc9e564f192786e75551277174907afad26c76a927099e7d859f0cee`
- bytes = 236045
- identity = PASS

DEV038-A-P1:
- SHA256 = `16292d1f730561427a4623a052441f3ab20db0a96eeefac06b6f0a0391c5e549`
- bytes = 287084
- identity = PASS

## Frozen lineage reproduction

- seven historical days = PASS
- every day rows = 1407
- campaign rows = 9849
- validation rows per Apr-Jul fold = 1407

All 12 controller/fold operational records reproduced the frozen
DEV037-P0-R2 artifact exactly.

For every W120/W360/W720 fold:

- frozen public operational record exact = PASS
- independently reconstructed causal thresholds exact = PASS
- independently reconstructed actions exact = PASS
- action domain valid = PASS
- thresholds finite = PASS

All four W120 action hashes reproduced DEV037-P1-R1 exactly:

- F1 = `7f8371ad0ade35c83ed1b52a24eb2cca78547c4726cf42b317fc0e2a88b162fc`
- F2 = `8a79e4decb5b4e193fc17b5197ee0f9d0f96f38c250d82f7c5b071b63ef4720d`
- F3 = `75f4fd456cbc7d66badc0bb24200684dfdad72b1e0b732edb05608710b294d94`
- F4 = `73533fcbae004d7a716313c118f5cf587e1f6c45dbbc7c08b8f60570f67a9e28`

Operational action counts:

Fold 1 Apr:
- W120 = 240
- W360 = 188
- W720 = 170

Fold 2 May:
- W120 = 246
- W360 = 223
- W720 = 213

Fold 3 Jun:
- W120 = 293
- W360 = 321
- W720 = 344

Fold 4 Jul:
- W120 = 321
- W360 = 348
- W720 = 377

These are operational counts only and contain no correctness information.

## Final preflight result

- checks PASS = 82
- checks FAIL = 0
- Python preflight RC = 0
- focused tests = 6 passed
- test RC = 0
- harness smoke = PASS
- smoke RC = 0
- git status = clean
- canonical output present = NO
- canonical log present = NO
- staging residue = none

## Explicit no-result guarantee

The preflight did not calculate or inspect:

- action precision
- correct action count
- false action count
- correct-action rate
- false-action rate
- action-on-NONE fraction
- fold correctness deltas
- LOO correctness deltas
- temporal null
- survivor classification
- PnL
- fees
- slippage
- forward data

Therefore no DEV038-A-P2 correctness result has yet been observed.

## Authorization

The single canonical DEV038-A-P2 controller correctness screen is authorized.

From the canonical start marker:

`DEV038-A-P2 MUST NEVER BE RERUN`

No second canonical attempt is permitted even if the run fails after the
start marker.

Current state:

`DEV038A_P2_PREFLIGHT_PASS_SINGLE_CANONICAL_CONTROLLER_CORRECTNESS_SCREEN_NEXT`
