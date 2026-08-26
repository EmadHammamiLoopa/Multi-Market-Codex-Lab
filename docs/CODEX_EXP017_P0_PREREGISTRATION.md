# CODEX-EXP-017-P0 Preregistration

Status: **PREREGISTERED BEFORE ANY AUGUST GZIP DECOMPRESSION, CSV PARSING, OR FEATURE GENERATION**

Date: 2026-08-27

Experiment ID: `CODEX-EXP-017-P0`

Parent preserved commit:

`a24cc83c98bce48928977cae9092694805c6eb87`

Parent result:

`CODEX-EXP-016-P0 = SEALED_AUGUST_RAW_INPUT_MANIFEST_CAPTURED`

Parent result artifact:

`evidence/codex/exp016_p0_sealed_august_manifest/SEALED_AUGUST_RAW_INPUT_MANIFEST.json`

Parent artifact SHA-256:

`0c95efcccc235ad4115200b0bc476c3881e8af05711e9716bb9c8d2c782f0782`

## Scientific purpose

EXP017-P0 deterministically generates the frozen Phase 0D-L 250 ms derived representation for exactly one independent confirmation input:

- symbol: `BTCUSDT`
- date: `2026-08-01`

It is a **data-generation and integrity experiment only**.

It does not score a target, fit a model, compute AUC/AP, score direction, or compute PnL.

No predictive conclusion may be drawn from EXP017.

## Frozen raw provenance

EXP017 may read exactly the two raw files frozen by EXP016:

### incremental_book_L2

Relative raw path:

`incremental_book_L2/BTCUSDT/2026-08-01.csv.gz`

Expected SHA-256:

`bc7b4e6206bdbd893da75d035f63128b518ed34f3dd6490da71f96c72fe2a4cc`

### trades

Relative raw path:

`trades/BTCUSDT/2026-08-01.csv.gz`

Expected SHA-256:

`27622702d5e33e6d374ec3d6f9040e8d7550ca9229641bccb6289d64256e4afe`

Both hashes must be verified before either gzip stream is decompressed.

No network acquisition or replacement of either raw file is allowed.

## Frozen semantics lineage

Use the already-frozen Phase 0D-L feature semantics in:

`docs/V23_PHASE0DL_FEATURE_SEMANTICS_FREEZE.md`

No feature definition may be changed.

The generated grid is exactly:

- UTC day 2026-08-01
- 250 ms spacing
- 345,600 rows
- causal `local_timestamp` semantics
- no forward fill across invalid-book intervals
- identical BOOK/FLOW/TRADE/SNAPSHOT/FEATURE semantics to the frozen Phase 0D-L development pipeline

## Frozen C++ toolchain source blobs

The following exact repository blobs are the only allowed generation tools:

- `tools/v23_phase0dl_depth250.cpp`
  - Git blob SHA: `612706f3613271f22d639af96e426ebb0692c14f`
- `tools/v23_phase0dl_flow250.cpp`
  - Git blob SHA: `e270ad43a8b2a771c9e8055c9b518888fe3e58ec`
- `tools/v23_phase0dl_trade250.cpp`
  - Git blob SHA: `4dc14356a0ccd1e4d9ea292b755f59fd11b665a0`
- `tools/v23_phase0dl_snapshot_scan.cpp`
  - Git blob SHA: `10ee2175bd32b8c4475e48c2f308c8c31ae93da4`
- `tools/v23_phase0dl_features250.cpp`
  - Git blob SHA: `f76d4c374b38bf3d9ab1322ced2cfae26fa72142`

EXP017 must verify these exact Git blob SHAs before compilation.

## Frozen compilation

Compiler:

`g++`

Compile each tool from the frozen source at the frozen EXP017 commit.

Flags:

`-std=c++17 -O3 -DNDEBUG`

Link `-lz` for tools that read gzip raw input:

- depth250
- flow250
- trade250
- snapshot_scan

The final feature assembler does not require zlib.

The compiler version string, compilation commands, and executable SHA-256 hashes must be recorded in the result manifest.

## Frozen generation order

Run exactly:

1. `v23_phase0dl_depth250`
2. `v23_phase0dl_flow250`
3. `v23_phase0dl_trade250`
4. `v23_phase0dl_snapshot_scan`
5. `v23_phase0dl_features250`

All outputs must be created under a separate EXP017 derived directory supplied at runtime.

No existing Jan-July derived artifact may be overwritten.

## Frozen derived filenames

Exactly:

- `BTCUSDT/2026-08-01_BOOK250.csv`
- `BTCUSDT/2026-08-01_FLOW250.csv`
- `BTCUSDT/2026-08-01_TRADE250.csv`
- `BTCUSDT/2026-08-01_SNAPSHOTS.csv`
- `BTCUSDT/2026-08-01_FEATURES250.csv`

Each file must be absent before its generation begins.

## Frozen integrity requirements

### BOOK250

Generation tool must exit 0.

Its own frozen tool invariant requires exactly 345,600 emitted rows and zero bad raw rows.

### FLOW250

Generation tool must exit 0.

Its own frozen tool invariant requires exactly 345,600 emitted rows and zero bad raw rows.

### TRADE250

Generation tool must exit 0.

Its own frozen tool invariant must pass for the exact day.

### SNAPSHOTS

Generation tool must exit 0.

### FEATURES250

Feature assembler must exit 0.

The assembler must report:

- `rows=345600`
- `violations=0`

The final CSV must contain exactly 345,600 data rows after the header.

The first timestamp must equal 2026-08-01 00:00:00 UTC in microseconds.

The last timestamp must equal 2026-08-01 23:59:59.750 UTC in microseconds.

Successive final feature timestamps must increase exactly 250,000 microseconds.

Header must match the frozen Phase 0D-L feature schema produced by the exact assembler.

Structural inspection of timestamps, headers, row counts, validity flags, and generation diagnostics is allowed.

No predictive/statistical inspection of feature distributions is allowed.

## Frozen output provenance

For all five generated artifacts record:

- relative derived path
- SHA-256
- byte size

The result also records:

- frozen raw hashes
- frozen source Git blob SHAs
- compiler version
- executable SHA-256 hashes
- exact commands
- stderr generation diagnostics
- final structural integrity checks

Large generated CSV files are **not required to be committed to Git**.

The small EXP017 result manifest is committed to Git and becomes the provenance anchor for later independent validation.

## Status mapping

PASS:

`AUG1_PHASE_L_FEATURES_GENERATED_AND_INTEGRITY_PASS`

INVALID if any of the following occurs:

- EXP016 parent artifact hash mismatch
- raw SHA mismatch
- wrong symbol/date/path
- frozen source blob mismatch
- compilation failure
- generation command failure
- unexpected row count
- final grid/header/timestamp violation
- assembler reports nonzero violations
- missing output
- unexpected pre-existing output
- any scientific guard violation

There is no predictive FAIL state in EXP017 because no predictive hypothesis is scored.

## Scientific guards

At the end of EXP017:

- network_accessed = false
- target_scored = false
- model_fit = false
- auc_scored = false
- direction_scored = false
- pnl_scored = false

The following are expected to become true because deterministic generation requires them:

- august_raw_gzip_decompressed = true
- august_raw_csv_parsed_by_frozen_tools = true
- features_generated = true
- structural_integrity_inspected = true

No market-value distribution, target prevalence, feature-outcome relationship, model score, or profitability metric may be inspected.

## No-rescue rule

After the first EXP017 result artifact exists:

- do not rerun EXP017;
- do not change compiler flags;
- do not change source tool versions;
- do not alter feature semantics;
- do not repair or filter August rows;
- do not replace raw inputs;
- do not regenerate only a failed stage and overwrite the frozen run;
- do not score target/model/AUC/direction/PnL.

Any implementation/provenance failure after output creation requires preservation and a new Experiment ID.

A later independent predictive validation must verify the exact EXP017 `FEATURES250` SHA-256 before parsing it.
