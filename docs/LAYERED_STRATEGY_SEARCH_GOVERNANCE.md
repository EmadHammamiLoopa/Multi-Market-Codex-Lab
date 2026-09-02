# Permanent Layered Strategy Search Governance

Status: `PROJECT_GOVERNANCE_FROZEN`

Date frozen: 2026-09-02

This document is a permanent scientific rule for the Multi-Market project.

## Core rule

Every new strategy group is tested as an **incremental layer on top of the last
frozen success for the same prediction stage**.

Never promote the highest-scoring failure or inconclusive candidate into the
base merely because it ranked first.

The recursive structure is:

```text
FROZEN_SUCCESS_n
    +
LARGE_PREDEFINED_CANDIDATE_GROUP
    |
same data / same target / same benchmark protocol
    |
multiplicity-controlled incremental comparison
    |
true survivors only
    |
FROZEN_SUCCESS_n+1
```

If the group produces no true survivor:

```text
KEEP FROZEN_SUCCESS_n
    +
NEXT SCIENTIFICALLY DISTINCT GROUP
```

Do NOT:

```text
best failure
    +
more refinement
```

## Stage separation

Success inheritance is stage-specific.

The project pipeline remains:

1. Opportunity ranking
2. Direction given touch
3. Touch / barrier reachability
4. Cost-adjusted edge
5. Trade / abstain
6. Net expectancy / PnL

A success in one stage is not silently converted into a success in another
stage.

Examples of retained successes:

- EXP024-P1 = opportunity-ranking success
- DEV030-P3 = direction-given-touch baseline success
- DEV030-P4 touch-vs-none head = touch/reachability component success

These may later be composed only under a separately frozen composition design.

## Current direction-stage base

The authoritative current success for the direction-given-touch stage is:

`DEV030-P3`

Selected configuration:

- BTCUSDT
- T1 DIRECTION_GIVEN_TOUCH
- target A
- horizon 120 s
- barrier 16 bp
- causal sequence window 32 s
- feature block PRICE
- M1 regularized LogisticRegression
- final label SELECTED_FOR_NEXT_DEVELOPMENT_STAGE

This remains the base until a later candidate group produces a preregistered
incremental survivor over this exact frozen success.

DEV031-P1B, DEV032-E1B, and DEV032-E2B do not replace the base because their
terminal classifications did not establish a new frozen direction success.

## Candidate-group rule

Each group must be frozen before any predictive fit and must define:

- exact candidate universe and count
- exact mathematical representation
- exact model lineage
- exact folds
- exact parent/base comparator
- exact primary endpoint
- exact multiplicity correction
- exact survivor gate
- exact maximum number of advancements
- exact stop rule

Groups should be broad enough to test a coherent information family, but
finite enough to control researcher degrees of freedom.

## Survivor inheritance

A new base may be created only from candidates that pass every frozen survivor
gate.

If multiple candidates survive:

- advancement count is capped by the group design;
- redundant variants from the same family are reduced to at most the
  preregistered family cap;
- no failed/inconclusive candidate is added merely to fill a slot.

The next group is added on top of the retained survivor/base representation.

## Failure handling

All failures and inconclusive results remain frozen.

A failed group teaches that the tested information family did not add stable
incremental value under the frozen protocol.

Failure does not authorize:

- threshold relaxation
- family relabeling
- post-hoc feature edits
- model swapping
- best-failure promotion
- forward-holdout opening

## Forward data rule

Sep-01+ remains sealed until the full historical layered development program
produces a frozen candidate that has passed the required independent historical
robustness stage.

Forward data is never used to choose which layer to add.

## Economics rule

PnL/economics is downstream.

A directional layer is not promoted because it looks profitable in an
unfrozen backtest. Directional survival must be established first under its
own benchmark.

## Current consequence

DEV032-E2B rejected all ten refinements.

Therefore:

- retain DEV030-P3 as the direction base;
- do not build on P21/P13/P35 or any E1B inconclusive;
- do not build on any E2B rejected refinement;
- withdraw the previously drafted DEV033-S1 parent-relative sequence design
  before execution;
- the next experiment must test a new coherent strategy group added directly
  to DEV030-P3.

Permanent state:

`LAYERED_SEARCH_GOVERNANCE_ACTIVE_ALWAYS_BUILD_ON_LAST_FROZEN_SUCCESS`
