# DEV043-A Canonical TOUCH/NONE Result Freeze

Status:

`DEV043_A_TOUCH_SURVIVOR_A0_TOUCH_PRICE_LOGIT`

Date: 2026-09-03

Scientific execution commit:

`342547b45f1fecd361a17daad5c7450a755c6330`

Permanent rules:

`DEV043-A MUST NEVER BE RERUN`

`NO SECOND ATTEMPT`

`NO FOURTH STAGE-A MODEL`

`NO THRESHOLD RESCUE`

`NO CALIBRATION RESCUE`

`NO HYPERPARAMETER RESCUE`

`NO NULL REDESIGN`

## Canonical artifact

Path:

`/home/emadh/Multi-Market/evidence/dev043_a_touch_screen_v1/DEV043_A_TOUCH_SCREEN_RESULT.json`

Bytes:

`89918`

SHA256:

`38ee159618a1ed13727eb6a86df83b93c92c2aad50251fcfb1618d890efd2eb7`

## Canonical log

Path:

`/home/emadh/Multi-Market/evidence/dev043_a_canonical_console_v1.log`

Bytes:

`5037`

SHA256:

`fd12327bf0b3bd2946af393863d5146aedc7b2aab91b8b860152105abfb3d535`

## Canonical process

- canonical run RC = 0
- read-only verification RC = 0
- verification = 30 PASS / 0 FAIL
- git tree clean
- no staging residue
- Sep-01+ sealed
- all non-BTC markets sealed

## Common Stage-A OOF support

Pooled support:

`5516`

Target counts:

- TOUCH = 2683
- NONE = 2833

TOUCH prevalence:

`0.48640319071791155`

## Survivor

Exactly one candidate passed every frozen Stage-A gate:

`A0_TOUCH_PRICE_LOGIT`

### A0 pooled diagnostics

- TOUCH AP = `0.6519588168911605`
- AP lift over prevalence = `0.16555562617324898`
- ROC AUC = `0.6685251651144681`
- Brier = `0.23346678523374584`
- prior Brier = `0.2498151267773465`
- log loss = `0.6702005066176944`
- balanced accuracy = `0.6304782211776729`

### A0 per-fold AP lifts

- Apr = `0.12917408394875396`
- May = `0.1372403369595171`
- Jun = `0.13636550823951282`
- Jul = `0.1253127610143313`

All four folds have positive AP lift.

### A0 leave-one-fold-out AP lifts

- omit Apr = `0.17236840292020228`
- omit May = `0.13691291981405296`
- omit Jun = `0.17513748303524612`
- omit Jul = `0.1659043840772374`

All four LOO AP lifts are positive.

### A0 joint temporal null

- observed AP lift = `0.16555562617324898`
- joint max-stat q95 = `0.10733857559202414`
- observed - q95 = `0.05821705058122484`
- FWER p = `0.0005`
- null PASS = true

A0 passes every frozen Stage-A eligibility gate.

## Non-survivors

### A1_TOUCH_PRESSURE_LOGIT

- pooled AP lift = `0.12436472805214122`
- ROC AUC = `0.6184526674927926`
- Brier = `0.25645145129845953`
- prior Brier = `0.2498151267773465`
- FWER p = `0.0105`
- null PASS = true

A1 fails the frozen Brier-better-than-prior gate and is not eligible.

### A2_TOUCH_COMBINED_HGB

- pooled AP lift = `0.07787350477019445`
- ROC AUC = `0.6059638157864442`
- Brier = `0.2880148062355332`
- FWER p = `0.3495`
- null PASS = false

A2 fails multiple frozen stability/null/calibration gates.

## Scientific interpretation

The event-occurrence component of H1800/B32 is genuinely predictable OOF using
the frozen price/momentum representation.

This is materially stronger than the direct three-class DEV042 formulation for
isolating opportunity occurrence.

The result supports the DEV043 factorization hypothesis at Stage A.

However Stage A alone is NOT a trading strategy.

No Stage-C economic claim is authorized.

## Authorization

DEV043-B conditional LONG/SHORT implementation + synthetic/unit CI is now
authorized.

Stage B must use actual historical TOUCH rows only.

No Stage-B real predictive scoring is authorized until:

1. Stage-B implementation is complete;
2. Stage-B synthetic/unit CI is green;
3. Stage-B execution identity is separately frozen.

## Current state

`DEV043_A_FROZEN_SURVIVOR_A0_STAGE_B_IMPLEMENTATION_NEXT`
