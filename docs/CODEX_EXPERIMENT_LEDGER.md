# Codex Experiment Ledger

This ledger is append-only at the experiment-row level. A changed hypothesis receives a new ID; failed results remain. Detailed machine-readable run artifacts belong under `reports/codex/` and are ignored only when explicitly declared local.

## Status vocabulary

- `PREREGISTERED`: question/config frozen before scoring.
- `NOT_RUN`: implementation exists but required inputs or environment are unavailable.
- `RUNNING`: active deterministic run; no result interpretation yet.
- `PASS_SANDBOX`: all frozen development gates passed; not independent evidence.
- `FAIL`: valid run failed one or more frozen gates.
- `INVALID`: result cannot answer the question because data, leakage, schema, or execution assumptions failed.

## Experiment register

| ID | Date | Hypothesis / purpose | Code state | Features and model | Data | Costs | Result | Decision |
|---|---|---|---|---|---|---|---|---|
| CODEX-AUDIT-000 | 2026-08-25 | Reconstruct the complete baseline lineage and distinguish evidence from claims | Baseline `f193b199...`; docs-only dirty tree | Source, tests, docs, manifests, committed results; no model | Full Git history and committed artifacts | N/A | Audit completed; no established net edge; raw Phase L inputs absent | Proceed only with cost-aligned sandbox work |
| CODEX-BASELINE-TEST-000 | 2026-08-25 | Determine whether the named baseline test suite executes unchanged in the supplied environment | `f193b199...` | 49 baseline test modules | Synthetic fixtures and committed code | N/A | Initial discovery failed before tests because package path and SciPy/scikit-learn/XGBoost dependencies were absent | Create isolated environment; rerun unchanged suite; do not call this a code failure |
| CODEX-EXP-001 | 2026-08-25 | Direct positive-executable-net labels plus fold-local calibration can rank sufficient taker moves better than future-mid Ridge | PREREGISTERED and implemented at `66db437...` | L0 comparator; L2 primary; standardized balanced logistic long/short; C={0.1,1}; Platt calibration; p={.55,.65,.75,.85,.95}; H={10,30}s | BTCUSDT/ETHUSDT, first day Jan--Jul 2026, Phase L FEATURES250; sandbox only | 250 ms; touch/touch; 8 bp primary, 10/12 stress | NOT_RUN: all 14 required feature files are absent; no numeric result inferred | Keep runnable implementation; score only if verified sandbox files are supplied |
| CODEX-EXP-002 | 2026-08-25 | Low-capacity L2 filtering can improve passive-entry/taker-exit economics over identical unfiltered passive attempts | Frozen `cf22884...` | Side-aligned 8-feature logistic fill + conditional Ridge markout; EV cutoff {0,.10,.25}; RiskAverse primary | BTCUSDT/ETHUSDT, first day Jan--Jul 2026; raw Tardis trades + BOOK250/FEATURES250; sandbox only | 250 ms; 3 s lifetime; maker 2 + taker 4 bps, 3 + 5 stress | **FAIL**: P0 4,238 fills, −0.99 gross/−6.99 net bps; all 5 days negative; P1 no eligible inner cutoff in any fold | Preserve unchanged; next hypothesis may be causal cross-venue information, designed before new data |

## Verification and run history

| Run ID | Code state | Command / scope | Result | Evidence |
|---|---|---|---|---|
| CODEX-TEST-BOOTSTRAP-001 | `f193b199...` | Bundled Python, baseline discovery | Environment failure: package path plus SciPy/scikit-learn/XGBoost absent | Console record; no strategy result |
| CODEX-TEST-BASELINE-002 | `66db437...` working tree | `.venv` full discovery before Windows timezone dependency | 147 tests reached; 23 import errors all traced to absent `tzdata`; 2 native tests skipped | Environment diagnosis; no baseline assertion |
| CODEX-TEST-BASELINE-003 | `66db437...` working tree | `.venv\\Scripts\\python.exe -m unittest discover -s tests -q` after `tzdata` | 204 tests passed, 2 skipped because `g++` is not installed; 184 of the passing tests are unchanged baseline tests and 20 are then-current Codex tests | Console record; full rerun follows after final test addition |
| CODEX-TEST-EXP001-001 | `66db437...` working tree | Codex seal/outcome/calibration suite after model-adapter test addition | 21/21 passed | `tests/test_codex_research.py`, `tests/test_codex_exp001.py` |
| CODEX-RUN-EXP001-001 | baseline HEAD plus dirty implementation | Input-check only; no model fit | `NOT_RUN_MISSING_INPUT`; 14/14 required files absent; config SHA-256 `eb14db864a65d9e78452e910948af9892e8e413b1821977ba19eb7a6fd8dae18`; sealed opened = false | `evidence/codex/CODEX-EXP-001_20260825T100804.553162Z.json` |
| CODEX-TEST-FINAL-001 | `05d0f867faf19ff606f983814630c66cedf6ee55` | `.venv\\Scripts\\python.exe -m unittest discover -s tests -q` | 205/205 passed; 2 skipped (`g++` unavailable); 184 unchanged baseline + 21 Codex tests; exit 0 | `evidence/codex/CODEX_TEST_VERIFICATION_20260825.json` |
| CODEX-RUN-EXP001-002 | clean `05d0f867faf19ff606f983814630c66cedf6ee55` | Frozen input-check only; no model fit | `NOT_RUN_MISSING_INPUT`; 14/14 required files absent; same config SHA-256; dirty = false; sealed opened = false | `evidence/codex/CODEX-EXP-001_20260825T101702.351202Z.json` |
| CODEX-TEST-WSL-001 | published `f2c28ea4bf5d9a6afa29374202764fdba5d2de6f` | Fresh isolated WSL clone; `.venv/bin/python -m unittest discover -s tests -q` | 205/205 passed; zero skipped; both native `g++` tests ran; exit 0 | `evidence/codex/CODEX_WSL_TEST_VERIFICATION_20260825.json` |
| CODEX-PROVENANCE-EXP001-001 | published `f2c28ea...`; external immutable source at original baseline `f193b199...` | Read-only filename/date, exact header, row-count, and SHA-256 audit against original `FEATURE250_MANIFEST.json` | PASS: 14/14; 345,600 rows and 51 columns each; 2,646,309,809 bytes; no sealed path opened; original tracked tree unchanged | `evidence/codex/CODEX_EXP001_INPUT_PROVENANCE_20260825.json` |
| CODEX-RUN-EXP001-003 | published `f2c28ea...`; untracked evidence only | Frozen `--check-inputs` against original external directory | `INPUT_CHECK_PASS`; all 14 hashes recorded; sealed opened = false | `evidence/codex/CODEX-EXP-001_20260825T105102.591594Z.json` |
| CODEX-RUN-EXP001-004 | published `f2c28ea...`; config SHA-256 `eb14db864a65d9e78452e910948af9892e8e413b1821977ba19eb7a6fd8dae18` | Frozen full run, unchanged | **FAIL**: 400 inner candidates tested; 0 survivors; 0 invalid models; L0=None and L2=None in all 5 folds for both symbols; no outer scoring; sealed opened = false | `evidence/codex/CODEX-EXP-001_20260825T105616.652332Z.json`; `docs/CODEX_EXP001_RESULT.md` |
| CODEX-DIAG-001 | frozen `CODEX-EXP-001` implementation; diagnostic-only tool | Refit already-consumed inner slices and retain rejected-candidate gate, calibration, discrimination, and coverage summaries; no outer scoring | HYPOTHESIS-GENERATING ONLY: 362/400 candidates failed minimum trades, 359/400 failed 8 bp economics, 367/400 failed 12 bp economics; sparse high-confidence tail; frozen FAIL unchanged; sealed opened = false | `evidence/codex/CODEX_DIAG_001_20260825.json`; `docs/CODEX_EXP001_FOCUSED_CRITIQUE.md` |
| CODEX-PROVENANCE-EXP002-001 | pre-score working tree | Explicitly whitelisted read-only Jan--Jul SHA/schema/manifest audit in original WSL workspace | PASS: 28/28 raw and 70/70 derived files; zero errors; no download/regeneration; no August data file opened | `evidence/codex/CODEX_EXP002_INPUT_PROVENANCE_20260825.json`; `docs/CODEX_EXP002_DATA_AVAILABILITY.md` |
| CODEX-TEST-EXP002-001 | frozen `cf22884a2df7a33286050df96326ad2e95ea2e44` | `.venv\\Scripts\\python.exe -m unittest discover -s tests -q` | 217 tests passed; 2 existing skips; 12 EXP002 causal/queue/model tests; exit 0 | `tests/test_codex_exp002.py` |
| CODEX-RUN-EXP002-001 | frozen `cf22884a2df7a33286050df96326ad2e95ea2e44` | Frozen full Jan--Jul passive queue/markout walk-forward | **FAIL**: 4,238 P0 fills, −0.988 gross and −6.988 primary net bps/fill, −$98.58; 75.77% adverse at 1 s; P1 no eligible inner cutoff in 5/5 folds; Q50 also negative gross; sealed opened = false | `evidence/codex/exp002_result/CODEX_EXP002_RESULT.json`; candidate ledger SHA-256 `a8adc766...`; `docs/CODEX_EXP002_RESULT.md` |

## Run record requirements

Every machine run must append or link a record with:

```text
run_id
experiment_id
started_at_utc / finished_at_utc
status and failure_reason
git_commit and dirty_tree
command
python/platform/package versions
config JSON and SHA-256
input file path/size/SHA-256
symbol/date/split role
feature columns
model/hyperparameters/random seed
latency, entry/exit semantics, fees, slippage, queue model
all fold metrics and pooled metrics
sealed-period assertions
output SHA-256
```

## Frozen CODEX-EXP-001 configuration

The prose preregistration is in `docs/CODEX_FRAMEWORK_PROPOSAL.md`. The implementation's default config is authoritative only where it is identical to this table.

| Field | Frozen value |
|---|---|
| Symbols | BTCUSDT, ETHUSDT |
| Days | 2026-01-01, 02-01, 03-01, 04-01, 05-01, 06-01, 07-01 |
| Sealed | 2026-08-01 and 2026-08-04 through 2026-08-23 |
| Feature tracks | L0 comparator; L2 primary |
| Horizons | 10 s, 30 s |
| Entry latency | 250 ms |
| Training stride | 4 rows = 1 s |
| Base model | StandardScaler + LogisticRegression(class_weight=balanced) |
| C | 0.1, 1.0 |
| Calibration | Platt logistic, first inner-validation half |
| Selection | second inner-validation half after embargo |
| Probability thresholds | 0.55, 0.65, 0.75, 0.85, 0.95 |
| Inner survival | >=20 trades; positive expectancy/total at 8 and 12 bp; PF >1 at 8 |
| Outer costs | 8, 10, 12 bp round trip |
| Primary action | higher of eligible long/short calibrated expected net utility; tie = no trade |
| Overlap | next action after entry latency + holding horizon |
| Random seed | 20260825 |

## Interpretation guardrails

- January--July output is always labeled `SANDBOX`; it cannot become validation through wording.
- `NOT_RUN` is the only valid numeric status when required feature files are absent. Documentation values are not re-emitted as if reproduced.
- An experiment that fails one gate is `FAIL`, even if a post-hoc cell looks good.
- Calibration, threshold, transform, or model fitting on an outer day makes the run `INVALID`.
- Access to a sealed date makes the run `INVALID` and is designed to raise before file opening.
- A `PASS_SANDBOX` stops tuning and triggers a new-period preregistration; it does not authorize live collection or trading.

## Next entries

After the isolated environment is built, append the completed baseline-test status. After the runner is invoked, append either a hashed result record or the precise missing-input `NOT_RUN` artifact. No result row is replaced.
