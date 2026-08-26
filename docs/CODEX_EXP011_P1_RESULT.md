# CODEX-EXP-011-P1 Frozen Result

Status: `FAIL_BTC_OPTIONS_TRADE_FLOW_NO_INCREMENTAL_TIMING_INFORMATION`

Frozen implementation head:

`4679c23e79fde7f881ef25aa121da29262c5be3a`

## Execution integrity

- configuration SHA-256: `2524b69bb36669145270caad603ac7898885a560f3db0aaed1254c57d9cc4d5d`
- OOS prediction-records SHA-256: `ff65b67cf3dedb52a263fd0850ce98ce3bac208a1b5d6dfe23f639fd518b4366`
- result artifact SHA-256: `ba203504d413c59a6ac09cc4f622d7c10554bd62c34b8eb0736202d27c917826`
- sealed August opened: false
- direction scored: false
- PnL scored: false
- all frozen implementation/provenance/causality invariants: true

The scikit-learn messages emitted during execution were deprecation `FutureWarning`s about the `penalty` argument. They did not stop execution, alter the frozen model specification, or constitute an experiment invariant failure.

## Pooled outer-test metrics

Common support: `n = 5062`, prevalence `0.1495456341`.

- R: AUC `0.6029494751`; AP `0.2306502445`; Brier `0.1247370531`; log loss `0.4139161035`; top-decile precision `0.2662721893`.
- F: AUC `0.5875844039`; AP `0.1928296474`; Brier `0.1330389262`; log loss `0.4348150454`; top-decile precision `0.2307692308`.
- RF: AUC `0.6033057319`; AP `0.2102556544`; Brier `0.1305707402`; log loss `0.4287127308`; top-decile precision `0.2564102564`.
- VOL diagnostic: AUC `0.6335013356`; AP `0.2539192503`; Brier `0.1232192920`; log loss `0.4092341967`; top-decile precision `0.3096646943`.
- RF_F_TIME_PERMUTED: AUC `0.5961354881`; AP `0.2209144915`.
- CANARY_R: AUC `0.9999420047`; AP `0.9996676876`.

## Frozen primary deltas

- RF AUC - R AUC: `+0.0003562568`
- RF AP - R AP: `-0.0203945901`
- RF top-decile precision - R: `-0.0098619329`
- R Brier - RF Brier: `-0.0058336871` (RF worse)
- R log loss - RF log loss: `-0.0147966273` (RF worse)
- RF AUC - time-permuted-flow AUC: `+0.0071702438`
- CANARY_R AUC - R AUC: `+0.3969925297`

## Calendar behavior

RF beat R in AUC on 3 of 4 outer folds:

- Apr: `+0.0384474913`
- May: `+0.0199940316`
- Jun: `+0.0231563863`
- Jul: `-0.0255729878`

This fold-win pattern does not rescue the primary result because the pooled incremental AUC is effectively zero, AP and probability quality deteriorate, and the frozen timing falsification/non-overlap gates fail.

## Non-overlap 10-minute protection

- R AUC: `0.5389429996`
- F AUC: `0.5195635439`
- RF AUC: `0.5246175988`
- RF_F_TIME_PERMUTED AUC: `0.5258225391`

RF is worse than R on non-overlapping decisions and fails the absolute `0.57` RF AUC floor.

## Gate adjudication

Passed 4 of 12 primary gates:

- at least 3/4 folds RF AUC > R: PASS
- implementation/provenance/causality invariants: PASS
- pooled RF AUC >= 0.60: PASS
- positive-control canary delta >= 0.10: PASS

Failed:

- timing falsification delta >= 0.01
- non-overlap incremental AUC >= 0.01
- non-overlap RF AUC >= 0.57
- pooled incremental AUC >= 0.01
- pooled incremental AP >= 0.01
- lower Brier
- lower log loss
- top-decile precision not lower

## Scientific interpretation

The tested aggregate BTC options trade-flow representation does not establish reproducible incremental 10-minute opportunity-timing information beyond R on the consumed March-July sandbox.

This is a valid frozen failure, not an invalid run. The positive control shows that the pipeline is sensitive to strong predictive information, while all causality/provenance invariants passed.

The failure applies to the preregistered 24-feature aggregate flow block only: total trade count, total amount, signed/absolute aggressor amount imbalance, and signed/absolute call-put amount imbalance over 1/5/15/30-minute windows, pooled across eligible BTC option strikes and expiries.

It does not test or reject structurally segmented option flow by moneyness, maturity, trade size, or other materially different representations. Any such hypothesis requires a new Experiment ID and preregistration before scoring.

No direction or PnL experiment is authorized by EXP011.
