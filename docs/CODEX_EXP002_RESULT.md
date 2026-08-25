# CODEX-EXP-002 Frozen Sandbox Result

Date: 2026-08-25

## Verdict

**FAIL — scientifically valid frozen result.**

This is consumed Jan–Jul sandbox evidence, not validation and not a profitability claim. The result must not be rescued, retuned, rerun with different parameters, or reinterpreted as success.

- frozen preregistration/code commit: `cf22884a2df7a33286050df96326ad2e95ea2e44`
- candidate ledger rows: 80,618
- candidate ledger SHA-256: `a8adc766a68f24057090a0104be42d23f8b8851d89e520bdb8321c21969aedaa`
- result JSON SHA-256: `ae1aeeec42be433c3de4f39f45a9359a03f3da6a5a5a6dffd144603981846cca`
- August data files opened: 0
- new data downloaded/regenerated: 0

## Primary RiskAverse result

| Metric | P0 unfiltered | P1 L2 filter | NO_TRADE |
|---|---:|---:|---:|
| submitted outer orders | 57,582 | 0 | 0 |
| resting orders | 48,291 | 0 | 0 |
| filled orders | 4,238 | 0 | 0 |
| full / partial fills | 4,002 / 236 | 0 / 0 | 0 / 0 |
| fill rate | 7.360% | 0% | 0% |
| arrival miss rate | 16.135% | 0% | 0% |
| timeout rate | 76.470% | 0% | 0% |
| median / p90 / p99 fill wait | 975 / 2,615 / 3,184 ms | N/A | N/A |
| gross expectancy | **−0.988 bps/fill** | N/A | 0 |
| primary net expectancy | **−6.988 bps/fill** | N/A | 0 |
| stress net expectancy | −8.988 bps/fill | N/A | 0 |
| total primary net PnL | **−$98.58** | $0 | $0 |
| total stress net PnL | −$127.25 | $0 | $0 |
| profit factor | 0.005 | 0 | N/A |
| positive days | 0/5 | 0/5 | N/A |
| positive active hours | 0% | 0% | N/A |
| adverse-fill rate at 1 s | **75.77%** | N/A | N/A |
| 1 / 3 / 10 s markout | −0.764 / −0.865 / −0.979 bps | N/A | N/A |

The primary fee break-even was −0.988 bps: P0 lost gross before charging the frozen 6 bps maker/taker envelope. A maker rebate or zero-fee case therefore cannot turn this observed primary sample into evidence of positive gross selection.

Order capacity was not the failure. P0 median order/displayed-depth ratio was 0.0072%, p90 was 0.0593%, and p99 was 0.820%. Buy and sell outcomes were both negative: −7.026 and −6.951 net bps/fill respectively.

## Outer-fold stability

| Outer day | P0 fills | Fill rate | Gross bps/fill | Net bps/fill | Net USD | 1 s adverse fills |
|---|---:|---:|---:|---:|---:|---:|
| 2026-03-01 | 1,089 | 9.45% | −0.96 | −6.96 | −$24.70 | 72.9% |
| 2026-04-01 | 891 | 7.74% | −1.12 | −7.12 | −$21.02 | 75.0% |
| 2026-05-01 | 682 | 5.92% | −0.92 | −6.92 | −$17.06 | 80.2% |
| 2026-06-01 | 789 | 6.85% | −1.03 | −7.03 | −$19.63 | 75.9% |
| 2026-07-01 | 787 | 6.83% | −0.90 | −6.90 | −$16.17 | 76.0% |

All five P0 outer days were negative gross and net. The loss was not concentrated in one fold or one directional side.

## P1 outcome

The fill logistic and conditional Ridge fits reached the frozen inner selection stage in every fold, but none of the three preregistered expected-value cutoffs met the minimum inner coverage of 250 submissions and 20 completed fills. Under the frozen rule, each fold is a selection/model failure and P1 submits no outer order.

This is not a successful filter. P1 equals NO_TRADE, has no completed opportunity, cannot estimate expectancy, and cannot beat P0 by the required 0.50 bps on completed cycles. Its zero PnL only avoids P0’s losses; it does not demonstrate incremental L2 passive-entry economics.

## Diagnostic-only sensitivities

| Diagnostic P0 | Fills | Fill rate | Gross bps/fill | Net bps/fill | Net USD | 1 s adverse fills |
|---|---:|---:|---:|---:|---:|---:|
| Q50 probability/cancellation credit, 250 ms | 6,641 | 11.53% | −0.838 | −6.838 | −$151.37 | 64.27% |
| RiskAverse, slower 500 ms | 3,726 | 6.47% | −0.928 | −6.928 | −$85.29 | 75.98% |

Q50 produced more fills and somewhat less adverse selection, but gross expectancy remained negative. It cannot rescue the failed conservative primary result. Slower latency reduced fills and also remained negative gross and net.

## Gate disposition

Only 2 of 21 frozen boolean gates were true:

- conservative queue remained primary
- P1 zero PnL exceeded the losing P0 total PnL

The second is not evidence of a tradeable P1; it is the mechanical consequence of P1 selecting no trades. All model/coverage, completed-opportunity, primary/stress economics, PF/drawdown, stability, concentration, adverse-fill improvement, and P1 expectancy-increment gates failed or were undefined because P1 had no orders.

## Scientific interpretation

The conservative single-venue passive-entry mechanism is falsified for this frozen formulation:

1. It generated thousands of actual queue-qualified fills, disproving the red-team claim that RiskAverse queues necessarily prevent all fills.
2. The fills were adverse enough to lose before fees.
3. The low-capacity L2 filter could not find a sufficiently dense positive-EV action set on any inner fold.
4. Giving uncertain cancellations favorable Q50 credit increased activity but did not create positive gross expectancy.

No deeper model, faster latency, maker rebate, maker/maker exit, altered lifetime, looser cutoff coverage, or probability queue will be tried under EXP002. Those would be new hypotheses and IDs.

The strongest remaining research direction is a separately preregistered causal cross-venue information experiment, because changing the single-venue execution leg alone did not convert the weak local signal into positive gross selection. No new data should be collected or opened until that experiment is designed and frozen.

## Evidence

- `evidence/codex/exp002_result/CODEX_EXP002_RESULT.json`
- `evidence/codex/exp002_result/CODEX_EXP002_CANDIDATE_LEDGER.csv.gz`
- `docs/CODEX_EXP002_PREREGISTRATION.md`
- `docs/CODEX_EXP002_METHOD_REVIEW.md`
- `docs/CODEX_EXP002_RED_TEAM_REVIEW.md`
- `docs/CODEX_EXP002_DATA_AVAILABILITY.md`
