# DEV038-A-P2 Execution Freeze

Status: `EXECUTION_FROZEN_AFTER_GREEN_CI_NO_REAL_CORRECTNESS_SCORING`

Date: 2026-09-03

Scientific implementation commit:

`a1ac3ea806def0f38b8952295b68fab8eb18e3a1`

Execution branch:

`research/dev038a-p2-execution-frozen`

The later handoff-only commit is intentionally excluded from scientific
execution identity.

Frozen design:

`docs/DEV038A_P2_FINAL_CONTROLLER_SCREEN_DESIGN.md`

Design commit:

`d8648c3fac3b085703c99dc4aefa0b17591b8d06`

Implementation lineage:

- core:
  `e2356dff66c686113bd6d85e17d1fdb871a498b0`
- runner:
  `4909a13e42c1071171d8b746c3daa615bf47d46c`
- harness:
  `9c5a21d752d783720f13ff01ac0016da4ff7278d`
- tests:
  `9e01d9e0c05b5eef760150197cedd87f320b4c89`
- CI wiring:
  `a1ac3ea806def0f38b8952295b68fab8eb18e3a1`

CI result:

`GREEN`

as confirmed by the project owner.

## Frozen candidate family

- C0 = A0 PRICE32 + BTC45 + S0 + W120
- C1 = A0 PRICE32 + BTC45 + S0 + W360
- C2 = A0 PRICE32 + BTC45 + S0 + W720

No other controller, quantile, feature, model, target, or policy is permitted.

## Frozen parents

DEV037-P0-R2:

- SHA256 =
  `494122f1aea64fb2a4c956d674330d9a400709656f0e116187d6fa2fefaa3336`
- bytes = 27056

DEV037-P1-R1:

- SHA256 =
  `9a9ade5fbc9e564f192786e75551277174907afad26c76a927099e7d859f0cee`
- bytes = 236045

DEV038-A-P1:

- SHA256 =
  `16292d1f730561427a4623a052441f3ab20db0a96eeefac06b6f0a0391c5e549`
- bytes = 287084

## Next permitted action

Real-data NO-RESULT reproduction preflight only.

The preflight may:

- load the three frozen parents and verify exact SHA/bytes/status;
- reconstruct the exact DEV036-C1 support;
- rebuild frozen S0 score streams;
- reproduce W120/W360/W720 operational action/abstention/LONG/SHORT counts and
  coverage against DEV037-P0-R2;
- verify identical validation rows for C0/C1/C2;
- verify thresholds and actions are finite and causal;
- verify the canonical P2 output and log are absent;
- run focused unit tests and harness smoke.

The preflight must NOT calculate or print:

- action precision;
- correct action count;
- false action count;
- correct-action rate;
- false-action rate;
- action-on-NONE fraction;
- fold correctness deltas;
- leave-one-fold-out correctness deltas;
- temporal null;
- survivor classification;
- PnL;
- fees;
- slippage;
- forward data.

Only after a clean no-result preflight may the one canonical joint correctness
screen be authorized.

## Permanent no-rerun rules

- DEV038-A-P1 MUST NEVER BE RERUN
- DEV038-A-P0 MUST NEVER BE RERUN
- DEV037-P1-R1 MUST NEVER BE RERUN
- DEV037-P0-R2 MUST NEVER BE RERUN
- DEV037-P0-R1 MUST NEVER BE RERUN
- DEV036-C1 MUST NEVER BE RERUN

## Current state

`DEV038A_P2_EXECUTION_FROZEN_NO_RESULT_REPRODUCTION_PREFLIGHT_NEXT`
