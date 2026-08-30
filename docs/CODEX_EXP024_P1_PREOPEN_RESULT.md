# CODEX-EXP-024-P1 Pre-Open Validation Result

Status:

`PREOPEN_VALIDATION_PASS`

Date:

2026-08-30

Experiment ID:

`CODEX-EXP-024-P1`

This result is a pre-open implementation and protocol readiness result only.

It is NOT a prospective predictive PASS/FAIL result.

## Frozen lineage

EXP024-P1 preregistration commit:

`1e76685945d5615f63b2525aacb33f576b461961`

EXP024-P1 frozen implementation commit:

`cdffc6d7556a2258e59f3a63e0e11419b47e5e5c`

Preregistration SHA-256:

`dc835423dc516a14a1e5b79a43b364bf8d8180f8288670aeac9e679db778caf3`

Scientific configuration SHA-256:

`3a9edfa6d2c9d15591373237574eb9552f09755eff2f0265e434621508e83b88`

Authoritative PREOPEN_VALIDATION artifact SHA-256:

`9436df752351ab501eb2df78527192622fd4817604efc82892a524e850630c1f`

## Historical validation

Historical training support:

`9793`

Feature columns:

`1`

Frozen training days:

- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

For every frozen Jan-Jul day:

- `rv_exact_match = true`
- `target_and_support_exact_match = true`

## Pre-open invariants

All pre-open invariants passed:

- `complete_status_payloads_json_safe = true`
- `corrected_invariant_typing_exact = true`
- `execution_guards_all_false = true`
- `exp023_correction_readiness_exact = true`
- `fixed_model_parameters_exact = true`
- `frozen_references_exact = true`
- `historical_days_exact_jan_jul = true`
- `historical_semantics_exact = true`
- `no_august_market_data_accessed = true`
- `no_prospective_metrics_scored = true`
- `one_legitimate_feature_only = true`
- `one_shot_output_protection_exact = true`
- `preregistration_sha_exact = true`
- `scientific_configuration_exact = true`
- `synthetic_p0_authorization_exact = true`
- `synthetic_p0_authorization_rejections_exact = true`
- `temporal_null_exact = true`

## Prospective state

During this pre-open validation:

- `prospective_grid_opaque_verified = false`
- `prospective_grid_analytically_opened = false`
- `model_fit = false`
- `prospective_metrics_scored = false`

No 2026-08-30 prospective data was opened.

No 2026-08-28 data was reopened.

No prospective ranking metric was calculated.

## Scientific consequence

The frozen EXP024-P1 implementation is ready for one-shot prospective execution
only after:

1. EXP024-P0 completes the full 2026-08-30 UTC collection;
2. EXP024-P0 finalization returns
   `PROSPECTIVE_BOOKTICKER_DATA_READY`;
3. the P0 result is preserved and frozen;
4. the prospective grid is authorized by the frozen P0 audit.

Until then, execute mode remains forbidden.
