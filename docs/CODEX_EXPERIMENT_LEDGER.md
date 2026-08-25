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
| CODEX-EXP-001 | 2026-08-25 | Direct positive-executable-net labels plus fold-local calibration can rank sufficient taker moves better than future-mid Ridge | PREREGISTERED; implementation pending at ledger creation | L0 comparator; L2 primary; standardized balanced logistic long/short; C={0.1,1}; Platt calibration; p={.55,.65,.75,.85,.95}; H={10,30}s | BTCUSDT/ETHUSDT, first day Jan--Jul 2026, Phase L FEATURES250; sandbox only | 250 ms; touch/touch; 8 bp primary, 10/12 stress | NOT_RUN at registration: feature files are not committed or present | Implement fail-closed runner and tests; score only if verified sandbox files are supplied |

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
