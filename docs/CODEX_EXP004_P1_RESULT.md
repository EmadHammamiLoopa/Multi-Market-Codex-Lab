# CODEX-EXP-004-P1 Result

Status: **FAIL_OPPORTUNITY_NOT_PREDICTABLE**

Frozen pre-score commit: `2a15bd14b8c20ad1b1315a5742317e5e87d46865`

Configuration SHA-256: `835598bdda2fbf93aeba620f3c2f4101854106e13364d516ea23cc7069daa651`

Preserved result SHA-256: `d37a9ecca6cf71161152f60d3c2cbacdbd7a1f5ee7e3189c5c6e0ac5e78e5588`

Result artifact: `evidence/codex/exp004_p1_result/OPPORTUNITY_PREDICTABILITY.json`

## Scientific question

Can causally available state at decision time rank whether a `>=24 bp` executable fixed-horizon opportunity will occur during the next 10 minutes, using only the already-consumed Binance USD-M futures price/regime and L2 information?

P1 intentionally did not predict direction and did not compute trading PnL.

## Primary result

Track R produced substantial rank discrimination but failed the complete preregistered evidence standard:

- pooled n: **13,990**;
- prevalence: **20.16%**;
- ROC AUC: **0.66996**;
- average precision: **0.34194**;
- AP / prevalence: **1.696x**;
- top-decile lift: **2.135x**;
- Brier skill versus prevalence: **-0.04156**.

Track R passed 9 of the 10 absolute predictive gates. The only absolute gate failure was the preregistered positive-Brier-skill requirement.

The negative Brier skill means the fixed uncalibrated probability estimates were worse than the pooled prevalence forecast in squared-probability error even though their ranking was materially informative.

## Stability

Track R outer-fold AUCs were:

| Outer day | Prevalence | ROC AUC | Average precision | Top-decile lift |
|---|---:|---:|---:|---:|
| 2026-03-01 | 31.8% | 0.6280 | 0.4380 | 1.651x |
| 2026-04-01 | 21.1% | 0.6153 | 0.2851 | 1.355x |
| 2026-05-01 | 8.9% | 0.6662 | 0.1699 | 2.368x |
| 2026-06-01 | 18.1% | 0.6163 | 0.2493 | 1.340x |
| 2026-07-01 | 20.9% | 0.6613 | 0.3605 | 2.242x |

All five outer folds exceeded ROC AUC 0.55 and all five exceeded top-decile lift 1.0.

By symbol:

- BTCUSDT: AUC **0.6489**, AP **0.2803**, top-decile lift **2.094x**;
- ETHUSDT: AUC **0.6666**, AP **0.3752**, top-decile lift **1.741x**.

On the deterministic non-overlapping 10-minute subset:

- R: n **1,390**, prevalence **18.06%**, AUC **0.6410**, AP **0.2951**, top-decile lift **2.072x**;
- RL2: n **1,388**, prevalence **18.08%**, AUC **0.6315**, AP **0.2819**, top-decile lift **1.870x**.

Therefore the dense-grid ranking result is not explained solely by overlapping 10-minute labels.

## Volatility baseline

The volatility-only baseline was unexpectedly strong:

- AUC **0.66298**;
- AP **0.33325**;
- AP/prevalence **1.653x**;
- Brier skill **+0.02774**;
- top-decile lift **2.014x**.

Track R improved over this baseline by only:

- **+0.00699 AUC**;
- **+0.00868 AP**;
- **+0.0243 absolute top-decile precision**.

This means most of the apparent predictive structure is already captured by a simple trailing-volatility regime variable. The broader regime feature set improved ranking only modestly and degraded probability calibration.

## Time-permutation falsification

The preregistered within-symbol/day training-label permutation placebo achieved:

- AUC **0.65429**;
- AP **0.33128**;
- top-decile lift **2.046x**.

Real Track R exceeded the placebo AUC by only **0.01567**, below the frozen required margin of **0.03**.

This falsification failure is the decisive diagnostic result. It indicates that much of the real model's ranking power can be reproduced after destroying within-day label timing while preserving day/symbol prevalence and regime structure. The experiment therefore does not establish sufficiently strong incremental event-timing information beyond coarse regime structure.

This does not mean the real R model has zero information. It means the preregistered evidence standard for calling the opportunity timing predictably rankable was not met.

## Positive control

The forbidden future-magnitude canary produced:

- AUC **0.99977**;
- AP **0.99900**;
- Brier skill **0.93624**;
- top-decile lift **4.961x**.

Its AUC improvement over real R was **+0.32981**, far above the frozen `+0.10` sensitivity requirement.

The pipeline therefore clearly detects strong information when deliberately provided. The P1 failure should not be interpreted as general pipeline blindness.

## Sign diagnostics

Both sign diagnostics passed. Inverting the signed R features or signed RL2/flow features did not improve all primary discrimination metrics simultaneously.

The failure is therefore not caused by the preregistered sign diagnostic.

## L2 incremental result

RL2 was not incrementally informative.

On its pooled support:

- RL2 AUC: **0.65947**;
- R on common RL2 support AUC: **0.66886**;
- RL2 AP: **0.33299**;
- R on common support AP: **0.34034**;
- RL2 top-decile lift: **2.052x**;
- R on common support top-decile lift: **2.135x**.

RL2 failed all three preregistered incremental gates:

1. AUC improvement >= 0.01;
2. AP improvement >= 0.01 absolute;
3. top-decile precision not lower than R.

The evidence therefore does not support using current L2/flow features as the missing 10-minute opportunity-timing information source.

## Final adjudication

`CODEX-EXP-004-P1 = FAIL_OPPORTUNITY_NOT_PREDICTABLE`

The failure is permanent under this experiment ID and is not rescued by the strong raw AUC or lift.

The combined P0/P1 interpretation is:

1. **economic headroom exists** at 10 minutes and longer;
2. **volatility/regime state ranks high-opportunity periods reasonably well**;
3. the broader current feature set adds little beyond a volatility-only baseline;
4. the within-day timing evidence is not sufficiently stronger than the preregistered permutation placebo;
5. current L2/flow does not add incremental information;
6. the positive-control canary confirms adequate pipeline sensitivity.

## Next authorized research direction

Do not rescue P1 by changing the 24 bp threshold, horizon, logistic capacity, classifier family, probability threshold, or opening August.

The next defensible hypothesis changes the **information set**, not the model:

> Derivatives-native state such as open interest, funding/premium/basis state, and their causal changes may contain incremental information about 10-minute opportunity timing beyond the volatility/regime baseline.

Before any predictive model is run with such data, the next phase should be a model-free data-availability and provenance audit on the same consumed January--July sandbox dates. It should establish causal timestamps, completeness, source semantics, staleness, and data-quality limits before a predictive preregistration is frozen.

August remains sealed.
