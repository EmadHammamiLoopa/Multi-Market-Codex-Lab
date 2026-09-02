# DEV034-G3B-R1 Canonical Result Freeze

Status: `CANONICAL_SUCCESS_ONE_TRUE_G3_SURVIVOR_DEEP_READ_ONLY_VERIFICATION_NEXT`

Date: 2026-09-02

Scientific execution commit:

`253ed5b95ecead444bf7222dd432f4168eeb2b44`

Canonical artifact:

`/home/emadh/Multi-Market/evidence/dev034_g3b_r1_common_support_screen_v1/DEV034_G3B_R1_COMMON_SUPPORT_SCREEN_RESULT.json`

Artifact SHA256:

`16200a1595d9472fe488740c0ab63e013b65824298ef1cb0b8856322416a8167`

Artifact bytes:

`873268`

Canonical execution result:

- exit code = 0
- canonical artifact exists
- read-only canonical contract = 42 PASS / 0 FAIL
- process returned success = YES
- staging residue = none
- git tree remained clean

Permanent rule activated at canonical-start time:

`DEV034-G3B-R1 MUST NEVER BE RERUN`

Upstream permanent rule remains:

`DEV034-G3A-R1 MUST NEVER BE RERUN`

## Matched comparator

`P3_COMMON_SUPPORT_REFIT`

Pooled balanced accuracy:

`0.5365784523410725`

## Joint temporal max-stat null

- seed = 20260902
- replicates = 1999
- candidates = 16
- max-stat q95 =
  `0.04403844667199219`

## Candidate terminal classifications

- G3C01 REJECTED
- G3C02 REJECTED
- G3C03 REJECTED
- G3C04 INCONCLUSIVE
- G3C05 REJECTED
- G3C06 REJECTED
- G3C07 INCONCLUSIVE
- G3C08 REJECTED
- G3C09 REJECTED
- G3C10 REJECTED
- G3C11 REJECTED
- G3C12 REJECTED
- G3C13 REJECTED
- G3C14 REJECTED
- G3C15 INCONCLUSIVE
- G3C16 SURVIVOR

## True survivor

`G3C16 FULL_FROZEN_R_CONTEXT`

Observed pooled BA:

`0.5920001546112814`

Observed matched delta BA:

`+0.05542170227020893`

Max-stat FWER p:

`0.0075`

This is above the frozen absolute BA gate, above the frozen +0.02 incremental
gate, above the joint max-stat q95, and below the frozen 0.05 FWER gate.

Layer survivors:

`["G3C16"]`

Advanced layers:

`["G3C16"]`

## Important interpretation

This is a historical-development direction-stage survivor on the exact frozen
G3A-R1 common support.

It is not:

- a forward-holdout result;
- a PnL result;
- a profitability claim;
- an execution-policy validation.

No Sep-01+ forward data was opened.
No PnL was run.

## Next permitted action

Deep read-only verification of the canonical G3B-R1 artifact.

Only after that passes may the project freeze a new layered-development base
that inherits the true G3C16 survivor and open the next scientifically distinct
strategy group.

Current state:

`DEV034_G3B_R1_CANONICAL_SUCCESS_G3C16_SURVIVOR_DEEP_VERIFY_NEXT`
