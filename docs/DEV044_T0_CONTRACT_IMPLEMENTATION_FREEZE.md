# DEV044-T0 Contract Implementation Freeze

Status:

`DEV044_T0_CONTRACT_GREEN_FROZEN`

Date: 2026-09-03

## Scientific implementation identity

`8e6a690336aca79cdf2453bc076c476b79103e7a`

This commit contains the final T0 contract implementation after correction of
the finite round-distance sentinel inconsistency.

The correction changed only the default sentinel:

- before: `round_distance_bps = inf`
- after: `round_distance_bps = 1_000_000.0`

No strategy signal, threshold, direction rule, A0 gate, execution rule, cost
rule, or candidate identity changed.

## CI verification

GitHub Actions run:

`33756419155`

Run number:

`1130`

Conclusion:

`success`

Dedicated job:

`dev044-t0-strategy-contract = success`

Follow-up handoff-only workflow run:

`33756441630`

Run number:

`1131`

Conclusion:

`success`

## Frozen T0 identities

Design:

`docs/DEV044_T0_STRATEGY_CONTRACT_EXECUTION_PARITY_DESIGN.md`

Implementation:

`src/multimarket/dev044_t0_strategy_contract.py`

Tests:

`tests/test_dev044_t0_strategy_contract.py`

Candidate family:

- exactly 16 core strategies;
- exactly 32 T1 candidates;
- T01U/T01A ... T16U/T16A.

A0 gate:

`p_touch >= 0.50`

No A0 threshold search.

U/A parity:

`A = U + suppression-only A0 gate`

No A0-created action and no A0 direction reversal.

## Permanent T0 rules

T0 strategy contracts are now frozen for the first T1 arena.

Do not alter T01-T16 rules after seeing DEV044 economic results.

Do not add T17 as a T1 rescue.

Do not change A0 threshold after viewing PnL.

Do not introduce strategy-specific exits in T1.

Any materially different strategy rule belongs to a later separately named
family or to T2 after T1 finalist promotion.

## Data state

No DEV044 real PnL has been run.

Sep-01+ remains sealed.

All non-BTC markets remain sealed.

## Next authorized stage

`DEV044-T0A A0 OOF SCORE + CAUSAL STRATEGY-STATE MATERIALIZATION`

This stage is no-PnL.

Current state:

`DEV044_T0_GREEN_FROZEN_T0A_MATERIALIZATION_AUTHORIZED_NO_PNL`
