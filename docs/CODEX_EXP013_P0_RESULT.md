# CODEX-EXP-013-P0 Frozen Result

Status: **INVALID**

Date: 2026-08-26

Frozen audit implementation HEAD:

`95c0fa519e8eaa32c12463f25c67e411c69439f2`

Frozen result artifact:

`evidence/codex/exp013_p0_corrected_expiry_segmented_options_flow/CORRECTED_EXPIRY_SEGMENTED_OPTIONS_FLOW_P0_AUDIT.json`

SHA-256:

`fa590862c00d207917e720e0157db495b67cbf3209bac6301f3568008ac0ce4b`

## Official adjudication

`CODEX-EXP-013-P0 = INVALID`

EXP013 must not be re-run or relabeled as PASS.

## What succeeded

The corrected Deribit expiry interpretation at 08:00 UTC removed the EXP012 expiry-integrity defect.

All five days have:

- zero expired BTC vanilla trades under corrected expiry semantics
- zero missing/invalid causal underlying references
- all integrity checks true
- all readiness checks true
- all six preregistered segments present
- support >= 80%
- longest consecutive constructable run >= 120 minutes

Observed support / longest run:

- 2026-03-01: 1269/1400, longest 139
- 2026-04-01: 1315/1400, longest 294
- 2026-05-01: 1237/1400, longest 206
- 2026-06-01: 1259/1400, longest 344
- 2026-07-01: 1254/1400, longest 259

The frozen artifact therefore records:

- `all_five_days_integrity_pass = true`
- `all_five_days_readiness_pass = true`
- `all_five_days_pass = true`

## Why the official status is nevertheless INVALID

The runner stored both positive invariants and negative scientific guards in one dictionary:

- positive invariants are expected to be `True`
- scientific guards such as `network_accessed`, `sealed_august_opened`, `target_scored`, `model_fit`, `auc_scored`, `direction_scored`, and `pnl_scored` are correctly expected to be `False`

The frozen status logic then evaluated:

`not all(invariants.values())`

Because the correctly-false guards are values in that dictionary, `all(invariants.values())` can never be true for a valid run. This deterministically forces `INVALID` even when integrity and readiness both pass.

This is an adjudication-logic defect, not a data-readiness failure.

## Scientific interpretation

EXP013 does **not** authorize promotion because its official frozen status is INVALID.

However, its immutable artifact contains complete structural evidence that the corrected-expiry segmented BTC options-flow representation satisfies the preregistered integrity and readiness gates on all five sandbox days.

The next step must use a new Experiment ID and correct only the adjudication semantics. To minimize researcher degrees of freedom, the preferred repair is an adjudication-only experiment that reads the frozen EXP013 artifact by exact SHA-256 and does not reload raw market data, alter segmentation, or recompute support.

No August data, target, model, AUC, direction, or PnL was accessed or scored in EXP013.
