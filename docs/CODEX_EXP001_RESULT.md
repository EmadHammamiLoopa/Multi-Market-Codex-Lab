# CODEX-EXP-001 Frozen Sandbox Result

Status: **FAIL**

Run date: 2026-08-25

Evidence scope: `SANDBOX_DEVELOPMENT_ONLY`

Code commit recorded by runner: `f2c28ea4bf5d9a6afa29374202764fdba5d2de6f`

Frozen config SHA-256: `eb14db864a65d9e78452e910948af9892e8e413b1821977ba19eb7a6fd8dae18`

Result artifact: `evidence/codex/CODEX-EXP-001_20260825T105616.652332Z.json`

## Scientific conclusion

Objective-aligned calibrated classification did **not** produce an inner-selected taker configuration under the frozen gates. For both BTCUSDT and ETHUSDT, all five walk-forward folds selected `None` for both the L0 static-book comparator and the L2 full dynamic feature block. No outer fold was scored. This is a valid frozen failure, not a software crash and not evidence from an independent validation period.

The precise result is narrower than “the classifier has no signal.” Every base and Platt model was technically fit—there were zero invalid models—but none of the 400 thresholded inner candidates survived the preregistered combination of minimum coverage and positive economics at both 8 and 12 bp. The frozen artifact intentionally retains only surviving inner configurations, so it does not contain the rejected candidates' calibration curves or economics. Those properties cannot be inferred from the zero-valued pooled sentinel metrics.

## Environment and provenance

- Published Lab HEAD before execution: `f2c28ea4bf5d9a6afa29374202764fdba5d2de6f`.
- Fresh isolated WSL checkout: `/home/emadh/Multi-Market-Codex-Lab-Exp001`.
- Original inputs remained external and read-only at `/home/emadh/Multi-Market/evidence/v23/phase0dl_features250`.
- Original repository tracked tree remained unchanged.
- WSL Python 3.14.4; NumPy 2.5.2; scikit-learn 1.9.0; Linux WSL2.
- Complete test suite: 205/205 passed, zero skipped; both native `g++` preparation tests ran.
- Provenance audit: 14/14 files passed; 345,600 rows and 51 exact columns per file; 2,646,309,809 bytes total; every SHA-256 matched the original `FEATURE250_MANIFEST.json`.
- Frozen input check: `INPUT_CHECK_PASS`.
- `2026-08-01` and `2026-08-04` through `2026-08-23` were not opened.

The runner reports `dirty: true` because the isolated checkout already contained newly generated, untracked provenance/input-check artifacts. The executed source files and configuration remained at the recorded commit and were not edited.

## Fold-level selection

Each block/fold evaluated 20 frozen combinations: two horizons, two `C` values, and five probability thresholds. “0 survivors” means no combination passed the inner economic gate; it does not mean the classifier emitted zero candidate rows.

| Symbol | Outer evaluation | Base training days | Inner calibration/selection day | L0 | L2 |
|---|---|---|---|---|---|
| BTCUSDT | 2026-03-01 | Jan 1 | Feb 1 | 0/20, `NO_CONFIGURATION` | 0/20, `NO_CONFIGURATION` |
| BTCUSDT | 2026-04-01 | Jan 1–Feb 1 | Mar 1 | 0/20, `NO_CONFIGURATION` | 0/20, `NO_CONFIGURATION` |
| BTCUSDT | 2026-05-01 | Jan 1–Mar 1 | Apr 1 | 0/20, `NO_CONFIGURATION` | 0/20, `NO_CONFIGURATION` |
| BTCUSDT | 2026-06-01 | Jan 1–Apr 1 | May 1 | 0/20, `NO_CONFIGURATION` | 0/20, `NO_CONFIGURATION` |
| BTCUSDT | 2026-07-01 | Jan 1–May 1 | Jun 1 | 0/20, `NO_CONFIGURATION` | 0/20, `NO_CONFIGURATION` |
| ETHUSDT | 2026-03-01 | Jan 1 | Feb 1 | 0/20, `NO_CONFIGURATION` | 0/20, `NO_CONFIGURATION` |
| ETHUSDT | 2026-04-01 | Jan 1–Feb 1 | Mar 1 | 0/20, `NO_CONFIGURATION` | 0/20, `NO_CONFIGURATION` |
| ETHUSDT | 2026-05-01 | Jan 1–Mar 1 | Apr 1 | 0/20, `NO_CONFIGURATION` | 0/20, `NO_CONFIGURATION` |
| ETHUSDT | 2026-06-01 | Jan 1–Apr 1 | May 1 | 0/20, `NO_CONFIGURATION` | 0/20, `NO_CONFIGURATION` |
| ETHUSDT | 2026-07-01 | Jan 1–May 1 | Jun 1 | 0/20, `NO_CONFIGURATION` | 0/20, `NO_CONFIGURATION` |

Aggregate selection: 400 candidates tested, zero survivors, zero invalid base/calibration models.

## Pooled outer metrics

Because no configuration passed inner selection, no outer trade was authorized. The artifact therefore records the no-trade sentinel values below for both symbols and both L0/L2 tracks.

| Track/symbol | Valid outer configurations | Trades at 8/10/12 bp | Net expectancy at 8/10/12 | Total net PnL at 8/10/12 | PF | Fold expectancy |
|---|---:|---:|---:|---:|---:|---|
| BTC L0 | 0/5 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 | null in all folds |
| BTC L2 | 0/5 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 | null in all folds |
| ETH L0 | 0/5 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 | null in all folds |
| ETH L2 | 0/5 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 | null in all folds |

These zeros must not be described as measured zero expectancy. They mean **no outer economic sample exists**. Promoted opportunity count is zero by policy; raw inner candidate coverage was not retained in the frozen artifact.

## Calibration and discrimination

No outer calibration metrics exist because outer scoring is conditional on inner survival. The artifact proves that Platt calibration was feasible in every model case (`invalid_models=[]`), but it does not prove that probabilities were well calibrated, discriminative, or sufficiently selective.

The completed read-only `CODEX-DIAG-001` postmortem is recorded in `docs/CODEX_EXP001_FOCUSED_CRITIQUE.md` and `evidence/codex/CODEX_DIAG_001_20260825.json`. It used only already-consumed inner slices, scored no outer day, opened no August data, and left this frozen result unchanged. It attributes the failure primarily to a cost-versus-coverage incompatibility: high-activity cells are uneconomic, while positive high-confidence cells have only one or two trades.

## Exact failure reason

The frozen gate failed at the earliest economic-selection stage:

1. 0/10 symbol/fold L0 selections produced a configuration;
2. 0/10 symbol/fold L2 selections produced a configuration;
3. consequently 0/20 possible outer block evaluations were opened;
4. structural, stability, concentration, and L2-incrementality gates could not be reached.

The defensible primary label is **inner economic/coverage failure under joint 8-and-12-bp gates**. The frozen artifact alone cannot further apportion that failure among poor calibration, weak discrimination, insufficient raw coverage, gross edge below costs, or their interaction.

## Decision

`CODEX-EXP-001` is closed as `FAIL`. Its labels, models, thresholds, and gates will not be changed or rerun under the same experiment ID. The focused critique recommends the already-ranked passive-entry/adverse-selection hypothesis for `CODEX-EXP-002`, but only after suitable nonsealed historical event-level data and conservative queue-model gates are preregistered. Neither sealed August period will be opened.
