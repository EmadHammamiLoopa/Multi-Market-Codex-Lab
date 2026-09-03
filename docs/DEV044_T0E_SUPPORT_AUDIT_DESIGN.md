# DEV044-T0E — Complete Apr-Jul Action/Support Materialization Design

Status:

`IMPLEMENTED_CI_PENDING_NO_PNL`

Date: 2026-09-03

## Purpose

Materialize the exact Apr-Jul DEV044 action support before any economic scoring.

This stage is NO-PNL.

## Official support

Official paired U/A support is exactly the frozen DEV043-A OOF validation support
for Apr-Jul.

No extra timestamps are introduced for the paired economic arena.

## Frozen parent identities

T0D canonical artifact:

- bytes = `1314`
- SHA256 =
  `c0cf0362f2f4a0559ff28c95e72824f5a8e5fa34a20394c33fe71f263f88143c`
- frozen VPIN bucket volume = `45.56983`

A0 replay remains identity-checked against the frozen DEV043-A artifact and
metrics.

## Materialized outputs

For each Apr-Jul day T0E writes a deterministic action CSV containing:

- local timestamp
- A0 p_touch
- toxicity availability
- toxicity value when available
- T01-T16 core actions
- all 32 TxxU/TxxA candidate actions

No return, target, trade outcome, PnL, PF or drawdown column is written.

## T16 warm-up rule

Before 50 completed VPIN buckets:

`T16 = ABSTAIN`

No fake toxicity value is used in T16 logic.

The internal StrategyState placeholder used for non-T16 calculations is never
passed to T16 decision logic when toxicity is unavailable.

## Raw-event lineage

T09/T12/T13/T14 are materialized via the exact DEV032 C++ extractor adapter.

T10 uses the frozen normalized MLOFI transform.

T16 uses the frozen T0D bucket volume.

## Support diagnostics

Per day and pooled:

- rows
- A0 gate pass/fail rows
- toxicity available/unavailable rows
- per-core LONG/SHORT/ABSTAIN/active counts
- per-candidate LONG/SHORT/ABSTAIN/active counts
- support hashes
- action CSV bytes/SHA256

These diagnostics may later be used to freeze minimum activity gates before PnL.

## Prohibited in T0E

- returns
- first-passage trade outcomes
- PnL
- profit factor
- drawdown
- strategy ranking
- economic winner selection
- Sep-01+ access
- non-BTC access

## Implementation

`src/multimarket/dev044_t0e_support_audit.py`

Tests:

`tests/test_dev044_t0e_support_audit.py`

## Next after green CI

1. freeze T0E execution identity;
2. run one canonical local T0E materialization/support audit;
3. inspect only action/activity/support counts;
4. freeze numeric T1 viability gates and block-max-stat geometry;
5. then authorize DEV044-T1 economic strategy arena.

## Current state

`DEV044_T0E_IMPLEMENTED_CI_PENDING_CANONICAL_SUPPORT_AUDIT_NO_PNL`
