# CODEX-EXP-014-P0 Preregistration

Status: **PREREGISTERED BEFORE ANY EXP014 OUTPUT**

Date: 2026-08-26

Experiment ID: `CODEX-EXP-014-P0`

Parent preserved commit:

`b90ba48f5ff8d11dfc362206b67c5d1945e95eb6`

Parent result:

`CODEX-EXP-013-P0 = INVALID`

Frozen parent artifact:

`evidence/codex/exp013_p0_corrected_expiry_segmented_options_flow/CORRECTED_EXPIRY_SEGMENTED_OPTIONS_FLOW_P0_AUDIT.json`

Frozen parent artifact SHA-256:

`fa590862c00d207917e720e0157db495b67cbf3209bac6301f3568008ac0ce4b`

## Scientific purpose

EXP014 is an **adjudication-only correction** of the frozen EXP013 artifact.

It does not generate new market evidence.

It must not:

- read raw option trades
- read Phase-L data
- recompute support
- recompute longest runs
- recompute segment counts
- recompute moneyness or maturity
- access August
- score target
- fit a model
- compute AUC/AP
- score direction
- compute PnL

Its only allowed input is the frozen EXP013 JSON artifact identified by the exact SHA-256 above.

## Known adjudication defect in EXP013

EXP013 stored two categories in one `invariants` dictionary:

1. positive invariants expected to equal `True`
2. scientific guard flags expected to equal `False`

The frozen EXP013 runner then used:

`all(invariants.values())`

This necessarily evaluates to false whenever the scientific guards are correctly false, causing a deterministic `INVALID` status even when all data integrity and readiness gates pass.

EXP014 corrects only this polarity error.

## Frozen positive invariants

The following keys must exist in EXP013 `invariants` and equal `True`:

- `exp012_result_sha256_verified`
- `all_five_option_raw_hashes_verified`
- `btc_only`
- `only_march_to_july_loaded`
- `atm_log_moneyness_boundary_exact_0_025`
- `atm_numeric_boundary_tolerance_only_1e_12`
- `deribit_option_expiry_hour_exact_08_utc`
- `maturity_boundaries_exact_7_and_30_days`
- `flow_windows_frozen_1_5_15_30`
- `decision_grid_0030_to_2349`
- `strict_underlying_reference_before_trade`

## Frozen scientific guards

The following top-level keys and their corresponding `invariants` keys must exist and equal `False`:

- `network_accessed`
- `sealed_august_opened`
- `target_scored`
- `model_fit`
- `auc_scored`
- `direction_scored`
- `pnl_scored`

## Frozen parent-state requirements

EXP013 must remain recorded as:

`status = INVALID`

EXP014 must not mutate or relabel the EXP013 artifact.

EXP013 must also record:

- `experiment_id = CODEX-EXP-013-P0`
- `all_five_days_integrity_pass = true`
- `all_five_days_readiness_pass = true`
- `all_five_days_pass = true`

There must be exactly five daily records, for:

- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

For every daily record:

- `integrity_pass = true`
- `readiness_pass = true`
- `pass = true`
- `invalid_expired_trades = 0`
- all `integrity_checks` values are true
- all `readiness_checks` values are true

EXP014 does not recompute these fields; it only verifies the immutable recorded values.

## Frozen adjudication

If the exact artifact hash matches, parent-state requirements pass, all positive invariants are true, all scientific guards are false, and all five daily recorded integrity/readiness states pass:

`DATA_READY_CORRECTED_EXPIRY_SEGMENTED_BTC_OPTIONS_FLOW_SANDBOX`

If artifact provenance is valid and integrity is recorded true but readiness is recorded false:

`FAIL_CORRECTED_EXPIRY_SEGMENTED_BTC_OPTIONS_FLOW_DATA_NOT_READY`

Any hash mismatch, schema mismatch, missing key, polarity violation, inconsistent aggregate/day flags, unexpected date, parent status other than INVALID, or guard violation:

`INVALID`

## Output

EXP014 writes only a small adjudication artifact containing:

- experiment ID
- frozen EXP013 SHA-256
- corrected status
- verification checks
- copied aggregate integrity/readiness booleans
- scientific guards

It must not copy or recalculate market-level counts unless necessary to verify consistency.

## No-rescue rule

After EXP014 output exists, do not change:

- the expected EXP013 SHA
- positive invariant list
- scientific guard list
- required dates
- status mapping

Any further change requires a new Experiment ID.
