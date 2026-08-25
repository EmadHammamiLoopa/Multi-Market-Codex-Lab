# CODEX-EXP-001 Focused Critique

Status: **HYPOTHESIS-GENERATING DIAGNOSTIC; FROZEN RESULT UNCHANGED**

Diagnostic ID: `CODEX-DIAG-001`

Parent experiment: `CODEX-EXP-001` (`FAIL`)

Artifact: `evidence/codex/CODEX_DIAG_001_20260825.json`

Artifact SHA-256: `85c9c14692d2a304d1c710c0aa5c8de1e82f888870b04f3fa0946e78bcc3cfc0`

## Scope and safeguards

This critique explains the already-recorded failure; it does not rescue, amend, or rerun `CODEX-EXP-001`. The diagnostic reused only the inner calibration/selection slices that the frozen run had already consumed. It did not score an outer day, tune a replacement configuration, or open a sealed August path. The original repository and feature files remained unchanged.

The diagnostic repeated the frozen model fits and retained rejected-candidate summaries that the frozen result intentionally omitted. All 400 frozen candidates remained failures. Positive post-hoc cells below are descriptive failure analysis, not candidate promotions.

## What failed

| Gate component | BTC failures / 200 | ETH failures / 200 | Combined failures / 400 |
|---|---:|---:|---:|
| Minimum 20 non-overlapping trades | 184 | 178 | 362 (90.5%) |
| Positive expectancy/total/PF at 8 bp | 190 | 169 | 359 (89.8%) |
| Positive expectancy/total at 12 bp | 194 | 173 | 367 (91.8%) |
| Full frozen gate | 200 | 200 | 400 (100%) |

The expectancy, total-PnL, and PF counts at a given cost coincide because they are sign-equivalent for every nonempty candidate; empty candidates also fail all three. The counts are component failures and must not be added together because a candidate can fail several components.

The two most favorable cells are too small to support inference:

| Symbol | Post-hoc best cell | Non-overlapping trades | Net bp/trade at 8 bp | Net bp/trade at 12 bp |
|---|---|---:|---:|---:|
| BTCUSDT | fold 2, L2, 30 s, C=0.1, p=0.85 | 2 | 26.44 | 22.44 |
| ETHUSDT | fold 1, L0, 10 s, C=1.0, p=0.85 | 1 | 58.53 | 54.53 |

Conversely, the highest-activity BTC cell produced 44 trades with gross 1.51 bp/trade, net -6.49 bp/trade at 8 bp and -10.49 at 12 bp. The highest-activity ETH cell produced 49 trades with gross -2.90 bp/trade, net -10.90 at 8 bp and -14.90 at 12 bp. Activity and sufficient gross edge did not coexist.

## Calibration, discrimination, and opportunity coverage

Each summary below covers 40 inner side-models: five folds, two feature blocks, two horizons, two regularization values, and one direction.

| Symbol / side | Median prevalence | Median ROC AUC | Median average precision | Median Brier | Median ECE | Median positive-utility rows |
|---|---:|---:|---:|---:|---:|---:|
| BTC long | 2.73% | 0.558 | 0.0385 | 0.0267 | 0.0117 | 2 |
| BTC short | 3.17% | 0.537 | 0.0439 | 0.0309 | 0.0165 | 0 |
| ETH long | 5.11% | 0.557 | 0.0662 | 0.0488 | 0.0219 | 5 |
| ETH short | 5.16% | 0.558 | 0.0762 | 0.0491 | 0.0214 | 12 |

The median inner selection slice contains about 172,759 valid rows. Across long and short models together, median positive-utility coverage was only 0.0006% for BTC and 0.0029% for ETH. The median number of rows assigned probability at least 0.5 was one for BTC and 15 for ETH. Consequently, the apparently modest aggregate Brier/ECE values are dominated by the low-probability majority and do not establish reliable calibration in the actionable tail.

Discrimination is weak rather than uniformly absent: median AUC is roughly 0.54--0.56, and 73 of 160 side-models have AUC below 0.55. Median average-precision lift over prevalence is only about 1.44x for BTC and 1.32x for ETH. This is insufficient to create a stable high-confidence tail with enough independent actions.

The expected-utility condition is also more restrictive than the nominal probability grid suggests. Fold-local payoff means imply median utility break-even probabilities of 0.714/0.747 for BTC long/short and 0.656/0.688 for ETH long/short. Thus the `utility > 0` rule often dominates the 0.55 and 0.65 thresholds, while higher thresholds leave almost no opportunities.

## Causal diagnosis

The primary diagnosis is **a cost-versus-coverage incompatibility for the tested single-venue taker hypothesis**:

1. The Phase L inputs contain at most weak ranking information for a positive executable outcome.
2. At action rates approaching the 20-trade floor, observed gross returns are below the 8--12 bp cost envelope.
3. Restricting to the high-probability/positive-utility tail occasionally finds a large move, but leaves only one or two non-overlapping trades in the favorable cells.
4. Platt fitting succeeds technically, but the actionable tail is too sparse to validate its calibration or support stable selection.

This is not evidence that a larger nonlinear model on the same labels and same single-venue features will overcome costs. Such a model would be a post-failure rescue with higher overfitting risk and no new economic mechanism.

## Recommended next hypothesis

The next experiment should remain the previously ranked, materially different `CODEX-EXP-002`: **a conservative passive-entry adverse-selection filter**. The hypothesis is that the small measured microstructure edge is real but cannot pay two taker crossings; a passive entry admitted only when fill probability is adequate and post-fill adverse selection is low may change the cost equation.

`CODEX-EXP-002` should be preregistered and implemented only if nonsealed historical event-level L2 plus trades and sufficiently trustworthy timestamps are available. Its minimum design requirements are:

- no reuse of `CODEX-EXP-001` as a tuned taker baseline and no August access;
- a passive-fill/no-fill model separated from a conditional post-fill markout model;
- conservative queue-position sensitivity, including RiskAverse or no-priority-improvement assumptions;
- order-entry/response latency, cancellation, partial-fill, timeout, inventory, and adverse-selection accounting;
- no optimistic maker credit in the primary case, with taker fallback separately costed;
- chronological inner selection and untouched outer scoring, with minimum fill/opportunity and stability gates frozen before execution;
- automatic rejection if profitability depends on one optimistic queue parameter or disappears in the conservative/no-credit case.

If suitable raw event history is not available, `CODEX-EXP-002` should remain `NOT_RUN`; the next defensible information hypothesis is the preregistered causal cross-venue OFI baseline, not a more expressive model over the same Phase L feature matrix.

## Decision

`CODEX-EXP-001` remains closed as `FAIL`. No thresholds, gates, labels, or models will be changed under that identifier. `CODEX-DIAG-001` is retained solely as consumed-sandbox failure analysis. No independent evidence or profitable strategy has been established.
