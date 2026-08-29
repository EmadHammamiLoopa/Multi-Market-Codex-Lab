# CODEX-EXP-023-P0 Frozen Result

Status:

`IMPLEMENTATION_CORRECTION_READY_FOR_FRESH_PROSPECTIVE_VALIDATION`

Date:

2026-08-29

Experiment ID:

`CODEX-EXP-023-P0`

Parent invalid experiment:

`CODEX-EXP-022-P1 = INVALID`

Parent preserved commit:

`91ae1465a20354082e9005eff1742ac3b2b73651`

EXP023-P0 preregistration commit:

`ee34a50950f7ad78b608611743f4ac0a2f480f63`

EXP023-P0 frozen implementation commit:

`306446a4a215680076ad96b32781499ba4abe6b1`

Preregistration SHA-256:

`96e5ebfe93a2ddba8403813086637e3733cb5fc8309230ac359efdfa8c9bd4cf`

Readiness result SHA-256:

`4eaf158b2517cf6c0be2efc2e7026a73a6b9986977d2c78499bb5785f142c1af`

## Official adjudication

`CODEX-EXP-023-P0 =
IMPLEMENTATION_CORRECTION_READY_FOR_FRESH_PROSPECTIVE_VALIDATION`

This experiment is an implementation-correction readiness audit only.

It makes no predictive claim.

## Corrected implementation defect

The frozen EXP022-P1 NumPy boolean defect was reproduced.

The corrected implementation verifies that:

- invariants are exact built-in Python bool values;
- NumPy boolean scalars cannot silently corrupt invariant adjudication;
- NumPy scalar values in result payloads are handled by the frozen JSON-safety policy;
- non-finite floating-point values are rejected;
- complete PASS, FAIL, INCONCLUSIVE, and INVALID-shaped result payloads are JSON-safe;
- atomic one-shot output protection remains enforced.

## Historical semantic validation

Training input remained exactly Jan-Jul 2026 BTCUSDT.

Historical training support:

`9793`

Feature columns:

`1`

For every frozen Jan-Jul day:

- `rv_exact_match = true`
- `target_and_support_exact_match = true`

The scientific configuration is unchanged from EXP022-P1.

## No prospective analysis

During EXP023-P0:

- `model_fit = false`
- `predictive_metrics_produced = false`
- `prospective_grid_opened = false`
- `no_august_market_data_accessed = true`
- `direction_scored = false`
- `pnl_scored = false`
- `leverage_scored = false`
- `older_august_holdout_opened = false`
- `historical_aug1_feature_reparsed = false`
- `network_accessed = false`
- `prospective_raw_opened = false`

No August market data was accessed.

## Scientific consequence

The implementation correction is ready to support a genuinely fresh
prospective validation experiment.

The consumed 2026-08-28 data remains diagnostic-only and may not be
used as an independent prospective confirmation.

The next prospective experiment must use a new Experiment ID and a
fresh validation day collected only after the corrected implementation
and this readiness result are frozen.
