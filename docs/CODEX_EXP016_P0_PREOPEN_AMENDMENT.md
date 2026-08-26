# CODEX-EXP-016-P0 Pre-Open Protocol Amendment

Date: 2026-08-26

Status: **AMENDED BEFORE ANY AUGUST FILE BYTES WERE READ**

Experiment ID: `CODEX-EXP-016-P0`

## Reason for amendment

The first EXP016 preflight stopped during a metadata-only path existence check because:

`/home/emadh/Multi-Market/evidence/v23/phase0dl_features250/BTCUSDT/2026-08-01_FEATURES250.csv`

did not exist.

The preflight did not open or hash any August file bytes, did not create an EXP016 output artifact, and did not inspect CSV content, timestamps, market values, features, targets, models, AUC, direction, or PnL.

Repository review then established that the initial 21-date derived-feature assumption was inconsistent with the frozen Phase 0D-L lineage:

- `v23_phase0dl_fetch.py` froze first-of-month samples through 2026-08-01.
- Phase 0D-L preparation and feature assembly froze development days only through 2026-07-01.
- The original Phase 0D-L preregistration designated only 2026-08-01 as its untouched confirmation sample day.
- It explicitly stated that 2026-08-04..2026-08-23 was an older Phase J/K holdout and was not to be repurposed for Phase L.
- The Phase 0D-L development result was FAIL and kept 2026-08-01 analytically sealed.

Therefore the originally committed EXP016 assumption that 21 August `FEATURES250` files already existed was incorrect.

## Corrected EXP016-P0 scope

EXP016-P0 remains a provenance-only experiment, but its input is corrected to the raw BTCUSDT Phase 0D-L confirmation source for exactly:

`2026-08-01`

and exactly two raw files:

1. `incremental_book_L2/BTCUSDT/2026-08-01.csv.gz`
2. `trades/BTCUSDT/2026-08-01.csv.gz`

The only allowed content access is raw-byte SHA-256 hashing after both exact paths are confirmed to exist.

No gzip decompression, CSV parsing, header reading, row counting, timestamp inspection, market-value inspection, feature generation, target scoring, model fitting, AUC scoring, direction scoring, or PnL scoring is permitted in EXP016-P0.

## Downstream lineage

If EXP016-P0 passes and its raw hashes are preserved:

1. a separately named experiment will deterministically generate the 2026-08-01 Phase-L derived files using the already frozen Phase 0D-L semantics and C++ tools;
2. that generation experiment will verify structure without predictive scoring;
3. only after the generated feature artifact is preserved may a separately preregistered volatility confirmation experiment parse 2026-08-01 analytically.

The older 2026-08-04..2026-08-23 holdout is not opened by this amendment.

## Scientific status

This amendment does not rescue or reinterpret any prior result.

It corrects a pre-output data-lineage assumption discovered before any August bytes were opened.
