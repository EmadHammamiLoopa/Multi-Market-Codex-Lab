# CODEX-EXP-016-P0 Frozen Result

Status: **SEALED_AUGUST_RAW_INPUT_MANIFEST_CAPTURED**

Date: 2026-08-26

Frozen implementation HEAD before output:

`9d440f0afea5f5844becceea94d0f18c78e14df8`

Result artifact:

`evidence/codex/exp016_p0_sealed_august_manifest/SEALED_AUGUST_RAW_INPUT_MANIFEST.json`

Result artifact SHA-256:

`0c95efcccc235ad4115200b0bc476c3881e8af05711e9716bb9c8d2c782f0782`

Internal manifest SHA-256:

`7914c8f28859ca33880c3315afee41c5c6b8a9cde39cb8eda4c5d747099aca48`

## Official result

`CODEX-EXP-016-P0 = SEALED_AUGUST_RAW_INPUT_MANIFEST_CAPTURED`

This is a provenance-only PASS.

No August predictive analysis was performed.

## Frozen raw inputs

Exactly two BTCUSDT raw files for 2026-08-01 were opened as opaque bytes for SHA-256 hashing only.

### incremental_book_L2

Relative path:

`incremental_book_L2/BTCUSDT/2026-08-01.csv.gz`

Byte size:

`423320166`

SHA-256:

`bc7b4e6206bdbd893da75d035f63128b518ed34f3dd6490da71f96c72fe2a4cc`

### trades

Relative path:

`trades/BTCUSDT/2026-08-01.csv.gz`

Byte size:

`8954358`

SHA-256:

`27622702d5e33e6d374ec3d6f9040e8d7550ca9229641bccb6289d64256e4afe`

## Frozen verification

All EXP016 checks passed:

- exact day is 2026-08-01
- BTC only
- exact two raw data types
- both expected files existed before hashing
- SHA-256 lengths valid
- sizes positive
- data-type ordering exact
- relative paths exact

## Scientific guards

All remained false:

- gzip_decompressed
- csv_parsed
- header_inspected
- row_count_inspected
- timestamp_inspected
- market_values_inspected
- features_generated
- features_scored
- target_scored
- model_fit
- auc_scored
- direction_scored
- pnl_scored
- network_accessed

`august_raw_files_opened_for_provenance_only = true`

## Interpretation

EXP016 establishes immutable raw provenance for the sealed BTCUSDT 2026-08-01 confirmation input before any August analytical content is inspected.

This result does not authorize a predictive claim by itself.

The next stage must use a new Experiment ID and must verify these exact raw hashes before deterministic Phase-L feature generation.

Feature generation may use only the already frozen Phase 0D-L feature semantics and tooling. Predictive validation must remain a separate later experiment and must not inspect August until the generated feature artifact has itself been frozen and preserved.
