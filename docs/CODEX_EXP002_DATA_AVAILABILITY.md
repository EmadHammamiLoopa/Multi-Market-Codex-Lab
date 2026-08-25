# CODEX-EXP-002 Data Availability and Provenance

Date: 2026-08-25
Status: **PASS — suitable Jan–Jul event data already exist**

## Scope and seal

The original workspace `/home/emadh/Multi-Market` was inspected read-only. The verifier uses an explicit whitelist containing only the first day of January through July 2026 for BTCUSDT and ETHUSDT. Any path containing `2026-08` is rejected before opening.

No August data file was opened. No file was downloaded, reconstructed, regenerated, or modified in the original workspace.

## Located inputs

| Input | Original path pattern | Files | Verification |
|---|---|---:|---|
| Tardis incremental MBP | `data/v23_phase0dl_l2_raw/incremental_book_L2/{symbol}/{day}.csv.gz` | 14 | SHA-256, bytes, header, raw audit |
| Tardis trades | `data/v23_phase0dl_l2_raw/trades/{symbol}/{day}.csv.gz` | 14 | SHA-256, bytes, header, raw audit |
| BOOK250 | `evidence/v23/phase0dl_book250/{symbol}/{day}_BOOK250.csv` | 14 | SHA-256, rows, manifest pass |
| FLOW250 | `evidence/v23/phase0dl_flow250/{symbol}/{day}_FLOW250.csv` | 14 | SHA-256, manifest pass |
| TRADE250 | `evidence/v23/phase0dl_trade250/{symbol}/{day}_TRADE250.csv` | 14 | SHA-256, manifest pass |
| Snapshot indices | `evidence/v23/phase0dl_snapshots/{symbol}/{day}_SNAPSHOTS.csv` | 14 | Current SHA-256, manifest pass |
| FEATURES250 | `evidence/v23/phase0dl_features250/{symbol}/{day}_FEATURES250.csv` | 14 | SHA-256, rows, manifest pass |

Allowed days are exactly `2026-01-01`, `2026-02-01`, `2026-03-01`, `2026-04-01`, `2026-05-01`, `2026-06-01`, and `2026-07-01`. Symbols are exactly BTCUSDT and ETHUSDT.

## Manifests checked

- `data/v23_phase0dl_l2_raw/ACQUISITION_MANIFEST.json`
- `evidence/v23/phase0dl_l2_audit.json`
- `evidence/v23/phase0dl_book250/BOOK250_MANIFEST.json`
- `evidence/v23/phase0dl_flow250/FLOW250_MANIFEST.json`
- `evidence/v23/phase0dl_trade250/TRADE250_MANIFEST.json`
- `evidence/v23/phase0dl_snapshots/SNAPSHOT_MANIFEST.json`
- `evidence/v23/phase0dl_features250/FEATURE250_MANIFEST.json`

All stage manifests pass, contain no failures, and retain `confirmation_analytically_opened=false`. All 28 raw audit entries pass with zero bad rows. BOOK250 and FEATURES250 each contain the expected 345,600 rows per day and symbol.

## Exact verification result

- raw expected/verified: **28/28**
- derived expected/verified: **70/70**
- manifest/hash/schema errors: **0**
- verification report SHA-256: `4a5f07fcc4c636b3be914a1d5f8078efb8758daca07d6513844bcee6c8f084ca`
- evidence: `evidence/codex/CODEX_EXP002_INPUT_PROVENANCE_20260825.json`
- verifier: `tools/codex_exp002_verify_inputs.py`

The snapshot manifest does not store output hashes, so the verifier records their current SHA-256 values without pretending they were previously sealed. All other output hashes are compared to their existing manifests.

## Causal suitability

Raw trades contain aggressor side, exact price, quantity, exchange timestamp, and local arrival timestamp. The derived BOOK250 state contains best prices and displayed L1 quantities. Snapshot indices identify book resets. Together these are sufficient for the frozen conservative primary simulation: queue starts behind displayed L1 quantity at arrival and advances only from later, oppositely directed aggressor trades at the exact order price.

FEATURES250 is never used to manufacture fills. It supplies decision-time state only. Fill labels come from raw trade events plus the frozen queue rules.

Conclusion: `CODEX-EXP-002` is eligible to proceed. `NOT_RUN_MISSING_EVENT_DATA` does not apply.
