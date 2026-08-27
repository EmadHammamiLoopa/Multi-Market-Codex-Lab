# CODEX-EXP-020-P0 Frozen Result

Status: **DIAGNOSTIC_COMPLETE_VOLATILITY_FALSIFICATION_AND_CALIBRATION**

Date: 2026-08-27

Frozen pre-output HEAD:

`2cfbef3317b891189a77979a23de68c7e5b87379`

Result artifact:

`evidence/codex/exp020_p0_volatility_diagnostic/VOLATILITY_FALSIFICATION_CALIBRATION.json`

Result artifact SHA-256:

`cbbe2bd8a148b556cb0670b7a5adb4f49aef677e85ef77b8c4bea01a53e69249`

Parent frozen EXP019 result:

`FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED`

EXP019 status remains unchanged.

## Official adjudication

`CODEX-EXP-020-P0 = DIAGNOSTIC_COMPLETE_VOLATILITY_FALSIFICATION_AND_CALIBRATION`

EXP020 is diagnostic-only.

It does not rescue, re-adjudicate, or promote EXP019.

No independent validation claim is permitted from EXP020.

## Diagnostic A — old placebo / monotonic ranking

Using the preserved EXP019 OOS prediction records:

- n = **1,399**
- Pearson correlation between VOL and old placebo predictions = **0.9948722409817589**
- Spearman rank correlation = **0.999999990139224**
- stable sorted order identical = **false**
- maximum absolute probability difference = **0.05067994009957017**
- mean absolute probability difference = **0.04604750066511378**

Yet rank metrics were exactly equal:

- VOL AUC = **0.9685934489402698**
- old placebo AUC = **0.9685934489402698**
- VOL AP = **0.3204202299670842**
- old placebo AP = **0.3204202299670842**

Interpretation:

The old one-feature training-label placebo produced predictions whose ordering was effectively the same as the legitimate one-feature VOL model, despite materially different probability levels.

Therefore the frozen EXP019 placebo was non-discriminating for rank-based metrics in this one-feature monotonic setting.

This explains the zero AUC delta without changing the official EXP019 gate outcome.

## Diagnostic B — outer-test feature permutation

EXP020 performed 200 deterministic within-outer-day permutations of the outer-day `rv_30m_bps` values, leaving labels fixed and using the already-fitted earlier-day model.

### 2026-03-01

- real AUC = **0.5613624658945223**
- permutation mean = **0.5016583480347575**
- permutation median = **0.5026681715080922**
- permutation 95th percentile = **0.5303986642706084**
- empirical one-sided p = **0.004975124378109453**

### 2026-04-01

- real AUC = **0.6070822731128075**
- permutation mean = **0.49938842624720486**
- permutation median = **0.500246742231475**
- permutation 95th percentile = **0.5329607140103323**
- empirical one-sided p = **0.004975124378109453**

### 2026-05-01

- real AUC = **0.6870547004377574**
- permutation mean = **0.5021734469876888**
- permutation median = **0.4991655647842664**
- permutation 95th percentile = **0.5463108335365933**
- empirical one-sided p = **0.004975124378109453**

### 2026-06-01

- real AUC = **0.6096553019629944**
- permutation mean = **0.5010656366425598**
- permutation median = **0.5015223380607996**
- permutation 95th percentile = **0.5389788985942833**
- empirical one-sided p = **0.004975124378109453**

### 2026-07-01

- real AUC = **0.6786722314575744**
- permutation mean = **0.5006067449510132**
- permutation median = **0.5002237116683762**
- permutation 95th percentile = **0.5375714462561454**
- empirical one-sided p = **0.004975124378109453**

### Pooled Mar-Jul diagnostic

- n = **6,995**
- prevalence = **0.16440314510364545**
- real AUC = **0.6489475211068546**
- permutation mean AUC = **0.5538821177520734**
- permutation median AUC = **0.5534198311451631**
- permutation 95th percentile AUC = **0.5673944806040093**
- empirical one-sided p = **0.004975124378109453**

Interpretation:

Across every consumed Mar-Jul outer fold, the real causal alignment of trailing volatility with the opportunity label ranks better than 200 deterministic test-feature permutations.

The per-fold permutation nulls are centered approximately at 0.50.

This supports the diagnostic conclusion that the VOL signal contains real time alignment information on the consumed sandbox dates.

The pooled permutation null is above 0.50 because predictions from different chronological folds are concatenated with fold-specific model scales/base rates; the per-fold nulls are the cleaner within-fold falsification evidence.

This is diagnostic evidence only and is not a new independent validation PASS.

## Diagnostic C — calibration and base-rate shift

Pooled Jan-Jul training:

- n = **9,793**
- positives = **1,652**
- prevalence = **0.16869192280200143**

Aug-01:

- n = **1,399**
- positives = **15**
- prevalence = **0.010721944245889922**

Aug/train prevalence ratio:

`0.0635593220338983`

Thus Aug event prevalence was only approximately **6.36% of the pooled Jan-Jul training prevalence**.

Prediction means on Aug-01:

- mean VOL probability = **0.06853470981879853**
- mean old-placebo probability = **0.11458012488320318**
- mean R benchmark probability = **0.0633945939605966**

Observed Aug prevalence:

`0.010721944245889922`

The frozen VOL model therefore materially overpredicted the Aug event base rate on average.

### Original VOL proper-score performance

- AUC = **0.9685934489402698**
- Brier = **0.012884520692056659**
- Brier skill = **-0.21472046160953706**
- log loss = **0.09096185811853556**

Prevalence-baseline Brier:

`0.010606984157477947`

### Post-hoc prior-shift diagnostic

Using the already-observed Aug prevalence for descriptive prior-odds correction:

- AUC = **0.9685934489402698**
- Brier = **0.010553186980068475**
- Brier skill = **0.00507186365236012**
- log loss = **0.055050428510195586**
- mean corrected probability = **0.0039451528490302545**

The correction preserved rank AUC exactly while materially improving Brier and log loss.

Brier skill moved from negative to slightly positive.

However, the corrected mean probability undershot the observed Aug prevalence, and the correction explicitly used the observed Aug prevalence.

Therefore this is evidence that base-rate shift is an important component of the calibration failure, but it is not a deployable or independently validated calibration solution.

## Combined interpretation

EXP020 supports three methodological conclusions:

1. The original EXP019 one-feature training-label placebo was effectively non-discriminating for ranking because it preserved almost exactly the same ordering of Aug predictions.
2. A cleaner within-test-day feature-permutation falsification strongly degrades AUC on every consumed Mar-Jul fold, supporting genuine timing alignment of trailing volatility with the opportunity target on consumed sandbox dates.
3. The Aug-01 Brier failure is substantially associated with a severe prevalence shift from approximately 16.87% pooled Jan-Jul to approximately 1.07% on Aug-01. A post-hoc prior-shift correction materially improves proper scores while leaving ranking unchanged.

These diagnostics do not alter EXP019.

## Scientific guards

All invariants passed:

- EXP019 result SHA exact
- EXP019 OOS-record SHA exact
- EXP019 frozen FAIL unchanged
- Jan-Jul training days exact
- Mar-Jul outer days exact
- primary feature = rv_30m_bps
- 200 permutations exact
- Aug feature reparsed = false
- older August holdout opened = false
- direction scored = false
- PnL scored = false
- network accessed = false
- EXP019 re-adjudicated = false

## Next research implication

Do not reopen Aug-01 as an independent holdout.

Do not open Aug-04..Aug-23 merely to rescue EXP019.

A future predictive confirmation should preregister, before opening any still-sealed holdout:

- a falsification control that destroys **test-time feature/label alignment** rather than merely permuting one-feature training labels;
- a calibration strategy estimated from training/validation history only, without using target-holdout prevalence;
- separate ranking and calibration gates;
- no direction or PnL unless opportunity predictability is independently confirmed under that new protocol.
