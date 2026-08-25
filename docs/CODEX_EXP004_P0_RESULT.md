# CODEX-EXP-004-P0 Result

Status: **MODEL_WORTHY_SANDBOX**

Frozen pre-score commit: `bf08be682768a4f7ae05f0dccb2a88825cfc65c4`

Configuration SHA-256: `ea073c797a4c57e45d9cf260391dc58865e34a68b41ea9258c44c52c807381cc`

Preserved result SHA-256: `a89b79c497a492b1306f13f9c1869fb7ef2337762977f43006afc263cf684141`

Result artifact: `evidence/codex/exp004_result/HEADROOM_AUDIT.json`

## Scientific question

Before spending additional research budget on prediction, do fixed-horizon BTCUSDT/ETHUSDT executable moves contain enough magnitude and enough distributed opportunity density relative to 8--12 bp costs to justify a new predictive experiment?

This phase is intentionally model-free. The future-aware direction oracle is an upper-bound descriptive diagnostic only and is not trading evidence.

## Frozen selection result

Eligible horizons under the preregistered `nonoverlap` gates:

- 10 minutes
- 15 minutes
- 30 minutes
- 60 minutes

The frozen rule chooses the **shortest eligible horizon**, therefore the selected next-hypothesis horizon is:

**10 minutes (600 seconds).**

## Horizon headroom table

| Horizon | Eligible | Valid decisions | >=24 bp events | >=24 bp fraction | Symbol-days with event | Median events/symbol-day | BTC events | ETH events | Max symbol-day share | >=36 bp events |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1m | NO | 20,132 | 385 | 1.91% | 14 | 11.5 | 100 | 285 | 39.48% | 135 |
| 3m | NO | 6,692 | 483 | 7.22% | 13 | 23.5 | 168 | 315 | 27.33% | 190 |
| 5m | NO | 4,004 | 461 | 11.51% | 12 | 24.5 | 164 | 297 | 25.16% | 216 |
| 10m | **YES** | 1,988 | 383 | 19.27% | 12 | 26.5 | 157 | 226 | 19.58% | 217 |
| 15m | **YES** | 1,316 | 352 | 26.75% | 13 | 26.5 | 151 | 201 | 17.05% | 203 |
| 30m | **YES** | 644 | 253 | 39.29% | 14 | 20.5 | 116 | 137 | 11.86% | 169 |
| 60m | **YES** | 308 | 173 | 56.17% | 14 | 13.0 | 77 | 96 | 10.98% | 130 |

## Why 1m, 3m, and 5m remain rejected

All three shorter horizons had substantial raw headroom counts, but each failed the frozen concentration gate:

- 1m: maximum symbol-day share = **39.48%**;
- 3m: **27.33%**;
- 5m: **25.16%**.

The preregistered maximum was 25%. The 5-minute miss is numerically narrow, but it remains a valid frozen FAIL and is not rounded, softened, or rescued after seeing the output.

This result is informative: the economic-magnitude problem begins to disappear before 10 minutes, but the distribution across the seven consumed sandbox days remains too concentrated at the shorter horizons under the frozen stability rule.

## 10-minute stability detail

At 10 minutes:

- pooled valid non-overlap decisions: **1,988**;
- >=24 bp events: **383 (19.27%)**;
- >=36 bp events: **217**;
- BTC >=24 bp events: **157**;
- ETH >=24 bp events: **226**;
- symbol-days with >=24 bp event: **12/14**;
- median >=24 bp events per symbol-day: **26.5**;
- largest symbol-day contribution: **19.58%**.

The two symbol-days without a >=24 bp non-overlap event were BTCUSDT and ETHUSDT on 2026-01-01. This is a strong warning that opportunity occurrence is regime-dependent rather than stationary.

February was exceptionally active, especially ETHUSDT, but the pooled 10-minute result still passed the predeclared concentration gate rather than depending on a single symbol-day.

## Interpretation

`MODEL_WORTHY_SANDBOX` means only that a later causal predictor has enough economic headroom and event density to be worth testing at the selected 10-minute fixed horizon.

It does **not** establish:

- predictability;
- profitability;
- strategy validation;
- live readiness;
- permission to open August.

The most important next scientific question is now narrower than the original trading problem:

> Can causally available state at decision time predict whether a >=24 bp executable fixed-horizon opportunity will occur over the next 10 minutes?

Direction is deliberately deferred. If opportunity occurrence itself is not predictably rankable out of sample, adding a direction model cannot rescue this branch rationally.

## Next authorized experiment

The next experiment should therefore be `CODEX-EXP-004-P1`, an **opportunity-predictability experiment** using the already-consumed Jan--Jul sandbox data only.

It should:

1. freeze 10 minutes as the sole horizon;
2. define the primary opportunity label from the P0 fixed-horizon executable oracle: `max(long_gross, short_gross) >= 24 bp`;
3. use only causal information available at decision time;
4. start with low-capacity models and train-only transforms;
5. use chronological walk-forward and purging for the 10-minute label horizon;
6. evaluate discrimination, calibration, coverage, temporal stability, and economic ranking;
7. keep direction prediction out of the primary hypothesis;
8. add no OI/funding/basis/liquidation data yet, so the effect of the new horizon/target can be isolated from the effect of new information.

Only if P1 demonstrates stable opportunity predictability should a separately preregistered directional stage or new derivatives-native information source be authorized.

August remains sealed.
