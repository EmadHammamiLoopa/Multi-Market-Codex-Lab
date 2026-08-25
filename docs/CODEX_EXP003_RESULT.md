# CODEX-EXP-003 Result

Status: **PERMANENT SCIENTIFIC FAIL**

Frozen pre-score commit: `e6109a78c7ec9ed74364260732e63252030bb735`

Configuration SHA-256: `8e18432c593ea21fed73df57f60877bba388c346b846425b06f0e06e177b0171`

## Scientific question

Does causal Binance Spot and Bybit information received at least
500 ms before a Binance USD-M futures decision add sufficient
incremental information beyond Binance-futures-only L2 to identify
economically large executable 10 s / 30 s moves after realistic
8--12 bp round-trip costs?

## Data integrity

- Frozen external files acquired: **56/56**
- Audit observed files: **56**
- Aggregate compressed/input bytes: **1941817406**
- Aggregate rows: **125271066**
- Local timestamp regressions: **0**
- Exchange timestamp regressions: **0**
- Malformed rows: **0**
- Duplicate trade IDs removed: **0**
- Continuity gaps over 2 s were retained and invalidated according to
  the frozen segmentation rule.
- No August data was opened.
- Raw external data remain local/ignored and are not committed.

The untracked pre-score audit orchestration script is preserved only
as provenance. It did not alter the frozen scorer, features, gates,
model, labels, costs, or timestamps.

## Primary 500 ms result

| Track | Actions | Net @8 bp/action | Total @8 bp | PF @8 | Max DD | PnL/DD | Net @12 bp/action | Total @12 bp | Positive folds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| X0 | 79 | -7.4492 | -588.49 | 0.362 | 620.02 | -0.949 | -11.4492 | -904.49 | 0/5 |
| X1 | 237 | -8.0962 | -1918.79 | 0.133 | 1940.05 | -0.989 | -12.0962 | -2866.79 | 0/5 |
| X2 | 134 | -7.4488 | -998.14 | 0.192 | 1042.76 | -0.957 | -11.4488 | -1534.14 | 0/5 |
| XALL | 142 | -8.8544 | -1257.32 | 0.090 | 1278.58 | -0.983 | -12.8544 | -1825.32 | 0/5 |

Primary XALL minus X0:

- expectancy delta @8 bp: **-1.4052 bp/action**
- total-net delta @8 bp: **-668.84 bp**

Cross-venue information therefore made the frozen primary economics
worse rather than better.

The primary passed only the activity/common-support basics and failed
the economic, stability, stress, complete-selection, and incremental
performance requirements.

## Frozen diagnostics

| Mode | X0 actions | X0 net @8 | XALL actions | XALL net @8 | Delta XALL-X0 | XALL total @8 |
|---|---:|---:|---:|---:|---:|---:|
| PRIMARY_500MS | 79 | -7.4492 | 142 | -8.8544 | -1.4052 | -1257.32 |
| DIAGNOSTIC_250MS | 69 | -5.1057 | 164 | -7.3175 | -2.2118 | -1200.07 |
| STRESS_1000MS | 60 | -3.4507 | 80 | -9.5506 | -6.0998 | -764.04 |
| TIMESTAMP_PERMUTATION | 79 | -7.4492 | 0 | 0.0000 | 7.4492 | 0.00 |
| SIGN_PLACEBO | 79 | -7.4492 | 138 | -9.0226 | -1.5734 | -1245.12 |
| TIME_PLACEBO | 94 | -7.2641 | 0 | 0.0000 | 7.2641 | 0.00 |
| FUTURE_LEAK_CANARY | 72 | -7.4301 | 604 | 5.8508 | 13.2810 | 3533.91 |

### Delay interpretation

The optimistic 250 ms diagnostic did not uncover a hidden profitable
cross-venue edge. XALL remained materially worse than X0.

At 1000 ms, XALL deteriorated further.

Therefore this experiment does not support the hypothesis that an
economically useful cross-venue signal merely decays between 250 and
500 ms.

### Placebos

Timestamp permutation and the 60-second time placebo produced no XALL
outer actions. Sign reversal remained strongly negative.

These diagnostics show that timing and signed external features affect
model behavior, but the real causal external information still did not
produce positive executable economics.

## Future-leak positive control

The intentionally invalid future-information canary produced:

- actions: **604**
- net expectancy @8 bp: **5.8508 bp/action**
- total @8 bp: **3533.91 bp**
- PF @8: **3.295**
- PnL/maxDD: **20.016**
- net expectancy @12 bp: **1.8508 bp/action**
- total @12 bp: **1117.91 bp**
- positive folds: **5/5**

Future information is forbidden and this result is not trading
evidence. Its scientific role is positive-control sensitivity:
the same research pipeline can exploit strong information when it is
deliberately made available.

Future-canary outer AUC gains over causal XALL:

{
  "long": 0.16101898295796013,
  "short": 0.15987051869918534
}

## Verdict

`CODEX-EXP-003 = FAIL`

This failure is permanent and is not rescued by any diagnostic.

Together with EXP001 and EXP002, the evidence now rejects escalation
of the existing 10--30 second BTC/ETH public-microstructure directional
family under the tested personal-system cost/latency constraints.

The next research question must change the economic problem rather than
add capacity to the failed information set.

## Next authorized direction

No model rescue is authorized.

The next phase is a new experiment family beginning with a
**model-free Economic Headroom Audit** over longer horizons.

Its purpose is to measure where executable move magnitude and
opportunity density become large enough relative to 8--12 bp costs
before spending additional research budget on prediction.

August remains sealed.

