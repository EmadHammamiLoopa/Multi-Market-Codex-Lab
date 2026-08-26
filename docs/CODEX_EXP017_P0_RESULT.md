# CODEX-EXP-017-P0 Frozen Result

Status: **AUG1_PHASE_L_FEATURES_GENERATED_AND_INTEGRITY_PASS**

Date: 2026-08-27

Frozen implementation HEAD before output:

`dfe18964f06789f7bf44dfd077e388b06714f4fc`

Result artifact:

`evidence/codex/exp017_p0_aug1_phase_l_generation/AUG1_PHASE_L_GENERATION.json`

Result artifact SHA-256:

`97c76a19a34971c7cef9eb01ad6c5b39d4e2c9885ed39a41054adef397ce4561`

## Official result

`CODEX-EXP-017-P0 = AUG1_PHASE_L_FEATURES_GENERATED_AND_INTEGRITY_PASS`

This is a structural/provenance PASS only.

No target, model, AUC, direction, or PnL was scored.

## Frozen final FEATURES250 artifact

Local derived path:

`BTCUSDT/2026-08-01_FEATURES250.csv`

Byte size:

`176179285`

SHA-256:

`62c72f13f7176d9b4d9bdb69ad940cdcc56858698d64b4a061cecbb4a09ec5f5`

Rows:

`345600`

Header columns:

`51`

First timestamp:

`1785542400000000`

Last timestamp:

`1785628799750000`

Grid:

`250000 us exact`

## Derived artifacts

### BOOK250

SHA-256:

`19ca88a6ba965ce3fbd44946345ddce9c23a30d69ccfa79856d25a6fd6aa2489`

Byte size:

`66282212`

### FLOW250

SHA-256:

`acc4e785eed47c1438ae1a857947d9f5e0a69b8e1231de69bdde15329692e877`

Byte size:

`19232072`

### TRADE250

SHA-256:

`b3dcca0475e58f4042ea600481b866dec2400fa091d2792a8039b7b31046b1f3`

Byte size:

`10778739`

### SNAPSHOTS

SHA-256:

`97358f8c76e5d506732b2c30927008ce78c04ec92b828dce64ed4c7a2418928b`

Byte size:

`138`

### FEATURES250

SHA-256:

`62c72f13f7176d9b4d9bdb69ad940cdcc56858698d64b4a061cecbb4a09ec5f5`

Byte size:

`176179285`

## Frozen generation diagnostics

BOOK250:

- parsed_rows = `73345308`
- bad_rows = `0`
- groups = `3217210`
- snapshots = `7`
- integrity_latches = `0`
- emitted = `345600`

FLOW250:

- parsed_rows = `73345308`
- bad_rows = `0`
- groups = `3217210`
- snapshots = `7`
- integrity_latches = `0`
- emitted = `345600`

TRADE250:

- parsed_rows = `1073872`
- bad_rows = `0`
- emitted = `345600`

SNAPSHOTS:

- parsed_rows = `73345308`
- bad_rows = `0`
- snapshot_rows = `21311`
- snapshot_groups = `7`

FEATURES250 assembler:

- rows = `345600`
- book_valid = `345595`
- l0_valid = `345595`
- l1_valid = `345511`
- l2_valid = `345511`
- snapshot_groups = `7`
- snapshot_masked_bins = `7`
- unknown_trades = `0`
- unknown_qty = `0`
- violations = `0`

## Frozen checks

All passed:

- all_compile_returncodes_zero
- all_five_derived_outputs_exist
- all_generation_returncodes_zero
- all_raw_sha_verified
- all_source_git_blobs_verified
- assembler_reported_rows_345600
- assembler_reported_violations_zero
- exp016_parent_sha_verified
- features_first_timestamp_exact
- features_grid_exact_250ms
- features_header_matches_frozen_schema_exactly
- features_last_timestamp_exact
- features_rows_exact_345600

## Frozen compiler/toolchain

Compiler:

`g++ (Ubuntu 15.2.0-16ubuntu1) 15.2.0`

Executable SHA-256:

- depth250: `f7415909bddb1406ecf530990227070344381fb92b15c0b1701c108415903a4b`
- flow250: `8250b99fd69de8109d1496309295d14f6b84b97360504e686f278bf9980c5a5d`
- trade250: `4cc7b217ea4720b8d4c75dcd6f1be15ddad7e2b09616d6d8164f41b6518bb3e5`
- snapshot_scan: `d9c2ce6f7aa53f459df1250b28d2502108ed638e1134c957bd784949e7d083e2`
- features250: `06d7c495eb1722356d460a08d42762e920882a42612caf0ad70aa65bac99087c`

## Scientific guards

Expected true due to deterministic generation:

- august_raw_gzip_decompressed = true
- august_raw_csv_parsed_by_frozen_tools = true
- features_generated = true
- structural_integrity_inspected = true

All predictive/economic guards remained false:

- market_value_distributions_inspected = false
- target_scored = false
- model_fit = false
- auc_scored = false
- direction_scored = false
- pnl_scored = false
- network_accessed = false

## Scientific interpretation

EXP017 establishes that the sealed BTCUSDT 2026-08-01 raw inputs can be deterministically transformed through the exact frozen Phase 0D-L toolchain into a structurally valid 250 ms feature artifact.

This result makes no predictive claim.

Any later independent predictive experiment must verify the exact FEATURES250 SHA-256:

`62c72f13f7176d9b4d9bdb69ad940cdcc56858698d64b4a061cecbb4a09ec5f5`

before parsing the August feature artifact.

The next predictive experiment requires a new Experiment ID and preregistration before inspecting August target prevalence, feature distributions, model output, AUC/AP, direction, or PnL.
