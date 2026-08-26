# CODEX-EXP-016-P0 Preregistration

Status: **PREREGISTERED BEFORE ANY AUGUST FILE CONTENT IS OPENED**

Date: 2026-08-26

Experiment ID: `CODEX-EXP-016-P0`

Parent preserved commit:

`db4cc73c384eecd22de65ae194af61c00658d1f9`

Parent result:

`CODEX-EXP-015-P1 = FAIL_SEGMENTED_BTC_OPTIONS_FLOW_NO_INCREMENTAL_TIMING_INFORMATION`

## Purpose

EXP016-P0 is a **sealed-input manifest capture only** for the independent August validation set.

It is not a predictive experiment.

Its only purpose is to establish immutable SHA-256 provenance for the exact sealed August BTCUSDT Phase-L files before any August values, targets, features, models, metrics, direction, or PnL are inspected.

No August predictive claim may be made from EXP016-P0.

## Why this step is necessary

The repository does not currently contain a pre-existing August input manifest or file hashes.

Therefore the first allowed access to the sealed August files must be a provenance-only operation that hashes exact file bytes without parsing market values.

The resulting manifest will be preserved before any independent validation experiment is run.

## Exact sealed validation dates

Exactly 21 dates:

- 2026-08-01
- 2026-08-04
- 2026-08-05
- 2026-08-06
- 2026-08-07
- 2026-08-08
- 2026-08-09
- 2026-08-10
- 2026-08-11
- 2026-08-12
- 2026-08-13
- 2026-08-14
- 2026-08-15
- 2026-08-16
- 2026-08-17
- 2026-08-18
- 2026-08-19
- 2026-08-20
- 2026-08-21
- 2026-08-22
- 2026-08-23

No other August date may be opened under EXP016-P0.

## Exact file pattern

For a supplied Phase-L feature root `FEATURE_DIR`, only:

`FEATURE_DIR/BTCUSDT/YYYY-MM-DD_FEATURES250.csv`

for the 21 frozen dates above.

No ETH file.

No option-trade file.

No January-July file.

No August 02, August 03, or August 24+ file.

## Allowed operations

Before reading any file bytes:

1. verify all 21 expected file paths exist and are regular files;
2. verify the EXP016 output does not already exist.

Then for each exact file:

- read bytes only for SHA-256 hashing;
- record byte size;
- record relative path;
- record date.

No CSV parsing is allowed.

No row count is allowed.

No timestamp inspection is allowed.

No header inspection is allowed.

No market value inspection is allowed.

No feature extraction is allowed.

No target construction is allowed.

## Frozen output

Output:

`evidence/codex/exp016_p0_sealed_august_manifest/SEALED_AUGUST_PHASE_L_MANIFEST.json`

The artifact records:

- experiment ID
- status
- exact 21-date list
- one SHA-256 and byte size per exact file
- aggregate manifest SHA over the recorded file metadata
- scientific guard flags

PASS status:

`SEALED_AUGUST_PHASE_L_INPUT_MANIFEST_CAPTURED`

Any missing file, unexpected file scope, duplicate date, or internal manifest inconsistency:

`INVALID`

## Scientific guards

Must remain false:

- csv_parsed
- row_count_inspected
- timestamp_inspected
- market_values_inspected
- features_scored
- target_scored
- model_fit
- auc_scored
- direction_scored
- pnl_scored
- network_accessed

The August files are considered **opened for provenance only** once hashing begins, but remain uninspected for analytical content.

## No-rescue rule

After EXP016-P0 output exists:

- do not re-run it;
- do not replace any file;
- do not regenerate any August Phase-L input under the same validation lineage;
- do not change the 21-date set;
- do not add or remove a file;
- do not change the manifest artifact.

Any later independent validation must verify every August input against the preserved EXP016-P0 SHA-256 manifest before parsing any August CSV content.
