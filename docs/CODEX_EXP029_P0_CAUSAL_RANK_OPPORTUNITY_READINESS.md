# CODEX-EXP-029-P0 Causal Rank-Normalized Opportunity Policy: Historical Development Readiness

Status: **PREREGISTERED BEFORE ANY EXP029-P0 ANALYTICAL EXECUTION**

Experiment ID: `CODEX-EXP-029-P0`

## Scientific role

EXP029-P0 is a development/readiness experiment using only already-consumed
historical data. It is not an independent confirmation experiment.

It must not be described as:

- prospective confirmation;
- profitability confirmation;
- direction confirmation;
- economic validation;
- deployability confirmation.

Its purpose is to construct and test exactly one frozen causal online use of
the opportunity-ranking signal that was prospectively confirmed in
CODEX-EXP-024-P1. A later experiment using genuinely fresh data is required
for independent validation.

## Frozen scientific lineage

### CODEX-EXP-004-P0

The frozen 10-minute, at-least-24-bp executable opportunity formulation was
judged worthy of predictive investigation.

EXP029 retains:

- the 600-second horizon;
- the at-least-24-bp opportunity target;
- causal decision-time information only.

### CODEX-EXP-004-P1

Volatility/regime information produced substantial ranking discrimination,
while the broader L2 information did not establish useful incremental
predictive value.

The retained lesson is that the useful information was primarily associated
with volatility/regime state. EXP029 does not reintroduce L2 because later
direction experiments failed.

### CODEX-EXP-019-P1

The one-feature volatility model produced very strong Aug-01 rank
discrimination, including approximately:

`ROC AUC ~= 0.969`

The official experiment nevertheless remained FAIL because its frozen
falsification and calibration gates did not all pass. EXP029 does not relabel
or reinterpret EXP019.

The retained lesson is that strong ranking evidence existed, but absolute
probability calibration and the original falsification construction were
problematic.

### CODEX-EXP-020-P0

This diagnostic established that:

1. a proper within-test-time feature permutation materially degraded the
   volatility-ranking signal on every consumed development fold; and
2. a large prevalence/base-rate shift existed between Jan-Jul history and
   Aug-01.

The retained lesson is that the volatility ranking contains genuine
time-aligned information while its absolute probability scale is
regime-sensitive.

### CODEX-EXP-021-P0

Historical rolling intercept correction and rolling Platt scaling did not
provide a stable calibration improvement over raw probabilities.

Frozen result:

`NO_CALIBRATION_DESIGN_READY_SANDBOX`

EXP029 does not perform another calibration rescue. It does not introduce:

- Platt scaling;
- isotonic calibration;
- intercept correction;
- prevalence correction;
- observed-holdout prior correction;
- calibration-method search.

The EXP029 causal rank is a relative rank score, not a calibrated probability.

### CODEX-EXP-024-P1

This is the strongest successful upstream predictive result.

Frozen status:

`PASS_PROSPECTIVE_VOLATILITY_RANKING_CONFIRMED`

Frozen result artifact:

`evidence/codex/exp024_p1_fresh_prospective_ranking_confirmation/PROSPECTIVE_RANKING_CONFIRMATION.json`

Frozen artifact SHA-256:

`0fda20d127e51e8ad792c6b949889f88b59e75ab98b437fd04ead285970e5c10`

Frozen EXP024-P1 implementation commit:

`cdffc6d7556a2258e59f3a63e0e11419b47e5e5c`

Frozen EXP024-P1 result-preservation commit:

`4669be4234b808286108c288f7a6eb7b3742f268`

Primary prospective metrics included:

- ROC AUC: `0.799436842365262`;
- Average Precision: `0.29797522298065926`;
- prevalence: `0.06647605432451752`;
- AP/prevalence: `4.482444483332713`;
- top-decile lift: `2.9011520737327188`.

All frozen primary ranking and temporal-null gates passed. EXP024 established
prospective opportunity ranking. It did not establish:

- directional accuracy;
- LONG/SHORT selection;
- economic profitability;
- leverage safety;
- stable absolute probability calibration.

### CODEX-EXP-026-P0

Frozen result:

`FAIL_DIRECTION_EXECUTION_PIPELINE_NOT_READY`

Frozen failure reason:

`candidate A has a validation fold with zero executed trades`

EXP029 does not rerun or reinterpret EXP026.

### CODEX-EXP-028-P0

EXP028 attempted an abstention-aware direction/execution readiness
formulation.

Frozen result commit:

`09e04a5cd6203110bdfb0e774b09e79242e542db`

Frozen artifact:

`evidence/codex/exp028_p0_abstention_aware_direction_readiness/HISTORICAL_SELECTION.json`

Frozen artifact SHA-256:

`32053a61b7a7e181857d9838d902551b4249f12e96fa1af4967cd18aa28385e1`

Frozen status:

`FAIL_ABSTENTION_AWARE_DIRECTION_PIPELINE_NOT_READY`

Observed validation-fold states:

- April: `ABSTENTION`;
- May: `ABSTENTION`;
- June: `ACTIVE`;
- July: `ACTIVE`.

The active-fold count was 2 against a frozen requirement of at least 3.

The retained lesson is that EXP029 must not mix the unresolved direction and
economic problem into its hypothesis. EXP029 returns to the layer with actual
positive evidence: opportunity ranking.

## Primary scientific hypothesis

The prospectively confirmed EXP024 opportunity signal is useful primarily as
a relative ranking signal.

Because previous work showed that absolute probability calibration is
regime-sensitive, one fixed causal online rank representation may provide a
more stable way to consume the successful opportunity signal without
recalibrating the model or searching probability thresholds.

EXP029 tests exactly one causal rank-normalization policy. It does not search
over multiple policies.

## Authorized historical data

Only the already-consumed BTCUSDT Jan-Jul 2026 historical sandbox is
authorized:

- `2026-01-01`
- `2026-02-01`
- `2026-03-01`
- `2026-04-01`
- `2026-05-01`
- `2026-06-01`
- `2026-07-01`

The exact frozen historical feature provenance and parent common-support
semantics must be preserved.

The following are forbidden:

- analytical opening of 2026-08-30;
- analytical opening of 2026-09-01 or any later date;
- opening any fresh EXP025 or EXP027 data;
- new external data;
- network acquisition or other network access;
- backfill;
- future-partition enumeration;
- future-partition inspection;
- use of any previously sealed fresh target.

## Frozen opportunity target

Symbol:

`BTCUSDT`

Decision schedule:

every 60 seconds.

Executable entry delay:

250 ms, exactly one 250 ms grid row after the decision timestamp.

Opportunity horizon:

600 seconds after entry.

Target:

```text
max(
    executable_long_gross_bps,
    executable_short_gross_bps
) >= 24 bp
```

The target is an any-direction opportunity target. Direction is used only
inside the already-frozen oracle-magnitude construction. EXP029 does not choose
or evaluate a direction.

Entry and exit quotes must satisfy the exact frozen executable-target validity
and same-day rules. No interpolation, imputation, future fill, or prior-day
fill is permitted.

## Frozen opportunity model

EXP029 uses exactly the successful EXP024 one-feature model family.

Feature:

`rv_30m_bps`

Preprocessing:

`StandardScaler`

Estimator:

`LogisticRegression`

Exact parameters:

- `C = 1.0`
- `penalty = "l2"`
- `solver = "lbfgs"`
- `class_weight = None`
- `max_iter = 1000`
- `random_state = 20260825`

No feature search, feature addition, L2 feature block, derivatives feature,
DVOL feature, options feature, classifier search, nonlinear model, calibration
model, or observed-validation calibration is permitted.

## Frozen historical folds

Exactly four chronological expanding folds are used:

1. train January-March, validate April;
2. train January-April, validate May;
3. train January-May, validate June;
4. train January-June, validate July.

For each fold:

- fit the scaler and logistic model on training data only;
- score training common support using that fitted model;
- score validation common-support rows only with that frozen fold model;
- never refit using validation labels or validation outcomes.

Training rows are never treated as validation evidence. Out-of-fold
validation rows are pooled only after each fold has been independently
processed.

## Sole new EXP029 representation

The only new scientific factor is a causal rank-normalized representation of
the already-frozen opportunity-model probability.

Let `p_t` be the opportunity-model probability at validation decision `t`.
`p_t` is not interpreted as a stable calibrated probability.

The online policy uses the relative location of `p_t` against a fixed-length
rolling distribution of previously available model scores.

## Frozen reference window

Reference window size:

`1399` scores exactly.

This value is frozen before EXP029 analytical execution. It is the exact
established common-support scale of one authorized historical day in the
parent opportunity dataset.

No alternate rolling length, multiple-window comparison, expanding window,
or EWMA is permitted. There is no reference-window search.

If an otherwise valid authorized training fold cannot supply exactly 1,399
prior training common-support probabilities, EXP029 is a clean readiness FAIL.
It must not shorten, pad, interpolate, or otherwise repair the reference.

## Reference initialization

For each fold:

1. fit the opportunity model on that fold's training data only;
2. generate model probabilities for that fold's training common support;
3. order those training probabilities in strict chronological order;
4. initialize the rolling reference with exactly the last 1,399 training
   common-support probabilities.

The initial validation reference therefore contains only information that was
available before the validation fold. No validation score may enter the
initial reference.

## Frozen causal validation update

Process validation common-support rows in strict chronological timestamp
order.

Before making the decision at validation row `t`, `reference_t` contains
exactly 1,399 previously available model probabilities.

Compute the threshold exactly as:

```python
threshold_t = np.quantile(
    reference_t,
    0.90,
    method="higher",
)
```

Compute the empirical causal rank exactly as:

```python
rank_t = (
    np.searchsorted(
        np.sort(reference_t),
        p_t,
        side="right",
    )
    / 1399.0
)
```

Eligibility is exactly:

```python
eligible_t = p_t >= threshold_t
```

The current `p_t` is not inserted before computing `threshold_t`, `rank_t`, or
`eligible_t`.

Only after all of the following have occurred:

- `p_t` has been scored;
- `rank_t` has been recorded;
- `threshold_t` has been recorded;
- `eligible_t` has been recorded;

append `p_t` to the reference and evict its oldest element. The next validation
decision therefore sees the immediately preceding 1,399 available scores.

This initialization, tie handling, denominator, and update order are frozen.

## Critical causality invariant

No score may influence:

- its own rank;
- its own threshold;
- its own eligibility through reference insertion;
- any earlier threshold;
- any earlier rank;
- any earlier eligibility decision.

Future scores must never enter past reference windows. Any violation makes
EXP029 `INVALID`.

## No quantile or policy search

There is exactly one percentile:

`0.90`

There is exactly one quantile method:

`"higher"`

No other percentile may be computed as a candidate gate. The percentile must
not be changed after observing support or selected using PnL, target
prevalence, direction performance, active-fold count, trade count, lift, AUC,
or AP.

The value 0.90 is frozen because the successful EXP024 result established
strong top-decile ranking performance.

## Ranking evaluation rows

EXP029 evaluates opportunity-ranking quality over all validation
common-support rows.

For each validation row, record only the fields needed for the frozen analysis:

- timestamp;
- raw model score `p_t`;
- causal `rank_t`;
- causal `threshold_t`;
- binary eligibility;
- binary opportunity label;
- fold identity.

The primary ranking score is `rank_t`. `threshold_t` is not a ranking score.

Pool out-of-fold predictions only after every fold has been independently
processed, preserving chronological fold and timestamp order.

## Primary ranking metrics

Report on pooled chronological out-of-fold validation rows:

- `n`;
- positives;
- negatives;
- prevalence;
- ROC AUC of causal `rank_t`;
- Average Precision of causal `rank_t`;
- AP/prevalence.

Also report ROC AUC, Average Precision, and AP/prevalence separately for each
validation fold.

## Causal 0.90 gate metrics

Using eligibility produced by the actual causal `threshold_t`, report:

- eligible signal count;
- eligible fraction;
- eligible positive count;
- eligible precision;
- eligible lift relative to validation prevalence.

This is the causal gate result. A retrospective full-validation top-decile sort
must not replace it.

A retrospective full-day top-decile metric may be reported only as a secondary
continuity diagnostic against EXP024 and cannot drive adjudication.

Pooled causal-gate precision is the positive fraction among all eligible
out-of-fold rows. Pooled causal-gate lift is that precision divided by pooled
validation prevalence. Each fold's lift uses that fold's validation
prevalence.

## Direction-independent occupancy support

For support/readiness diagnostics only, apply the frozen occupancy timing.

If an eligible decision arrives while flat:

- count one executed non-overlapping opportunity;
- occupancy starts at `t + 250 ms`;
- occupancy ends exactly 600 seconds after entry;
- actual exit is therefore `t + 600.25 s`.

Every otherwise-eligible decision before actual exit is ignored. The decision
at exactly `t + 600 s` remains blocked. There is no pyramiding.

There is no LONG/SHORT decision and no price return calculation.

For each fold report:

- eligible signal count;
- executed non-overlapping opportunity count;
- ignored eligible signals while occupied;
- exposure fraction.

Fold state is:

- `ACTIVE` when there is at least one executed non-overlapping opportunity;
- `ABSTENTION` when there are zero executed non-overlapping opportunities.

Exposure fraction is the fraction of the validation UTC day occupied by the
executed, non-overlapping 600-second holding windows.

## Fold-preserving EXP024-style temporal null

EXP029 reuses the successful EXP024 temporal-null philosophy. It does not use
the old EXP019 placebo construction that preserved nearly identical ordering.

For each validation fold:

- keep causal `rank_t` fixed;
- circularly shift that fold's binary labels only;
- never shift rows between folds.

Frozen shift step:

`30` validation rows.

An eligible pooled null-replicate shift `k` is a positive multiple of 30 that
satisfies, for every validation fold:

```text
k < n_fold
min(k, n_fold - k) >= 30
```

Use the same eligible `k` within every fold when forming one pooled null
replicate. There is no random shift selection and `k = 0` is forbidden.

For every null replicate:

1. circularly shift labels independently within each validation fold by `k`;
2. preserve causal-rank score and timestamp order;
3. concatenate shifted folds in chronological fold order;
4. compute pooled ROC AUC and Average Precision.

Report:

- number of shifts;
- AUC null q95;
- AP null q95;
- AUC empirical one-sided p-value;
- AP empirical one-sided p-value.

Each q95 uses exactly:

```python
np.quantile(
    null_values,
    0.95,
    method="higher",
)
```

Each empirical one-sided p-value uses exactly:

```text
(1 + count(null_value >= observed_value))
/
(1 + number_of_null_values)
```

No additional primary null may be introduced after observing EXP029 results.

## Frozen support requirements

Each validation fold must contain at least:

- `n >= 1200`;
- positives `>= 10`;
- negatives `>= 100`.

If an otherwise correctly constructed authorized fold lacks this support,
EXP029 is a clean development/readiness FAIL, not an opportunity-ranking PASS.

Malformed, causally invalid, or provenance-invalid support makes the result
`INVALID`.

## Frozen primary development gates

EXP029-P0 passes only if all of the following are true:

1. all provenance, chronology, causality, frozen-design, serialization,
   one-shot, and sealed-data invariants pass;
2. all four validation folds are processed;
3. every validation fold satisfies the frozen minimum support requirement;
4. pooled causal-rank ROC AUC is at least `0.60`;
5. pooled causal-rank AP/prevalence is at least `1.50`;
6. pooled causal q=0.90 gate lift is at least `1.50`;
7. at least three of four validation folds have causal q=0.90 gate lift
   strictly greater than `1.00`;
8. observed pooled causal-rank AUC is strictly greater than temporal-null AUC
   q95;
9. AUC empirical one-sided p-value is at most `0.05`;
10. observed pooled causal-rank AP is strictly greater than temporal-null AP
    q95;
11. AP empirical one-sided p-value is at most `0.05`;
12. at least three of four validation folds are `ACTIVE` under the frozen
    causal q=0.90 opportunity policy.

No gate may be removed, weakened, redefined, or rescued after observing EXP029
results.

## Raw-score continuity diagnostic

On the exact same out-of-fold validation rows, report descriptive metrics for
the original raw model score `p_t`:

- ROC AUC;
- Average Precision;
- AP/prevalence.

Also report:

- causal-rank AUC minus raw-score AUC;
- causal-rank AP minus raw-score AP.

These are descriptive and non-gating. EXP029 does not select between RAW and
RANK after observing them. The preregistered RANK policy is primary; RAW is
only a continuity reference to the successful EXP024 lineage.

## Calibration policy

Do not calculate Brier score or log loss for `rank_t` as though it were a
probability. `rank_t` is not a calibrated probability.

No calibrator may be fit.

If raw `p_t` Brier score or log loss is reported for continuity, it must be
explicitly secondary and non-gating. No calibration outcome may change EXP029
adjudication.

## No direction analysis

EXP029 must not calculate or inspect for selection:

- Candidate A;
- Candidate B;
- Candidate C;
- `long_preferred`;
- LONG/SHORT prediction accuracy;
- direction probabilities;
- directional return;
- direction-candidate ranking.

Direction is reserved for a separate later experiment.

## No economic evaluation

EXP029 must not calculate:

- gross trading PnL;
- net trading PnL;
- fee-adjusted return;
- a 14 bp economic result;
- a 20 bp stress result;
- win rate;
- profit factor;
- maximum drawdown;
- Sharpe ratio;
- position sizing;
- leverage;
- stop loss;
- take profit.

The 250 ms entry delay and 600-second duration are used only for support
occupancy. They are not economic validation.

## Secondary descriptive report

Report the following as non-gating diagnostics:

- fold-by-fold raw AUC and AP;
- fold-by-fold causal-rank AUC and AP;
- fold-by-fold causal-gate precision and lift;
- eligible fraction per fold;
- executed occupancy count per fold;
- exposure fraction per fold;
- first `threshold_t` per fold;
- median `threshold_t` per fold;
- minimum `threshold_t` per fold;
- maximum `threshold_t` per fold;
- last `threshold_t` per fold;
- active-fold count;
- total eligible signals;
- total executed non-overlapping opportunities.

No secondary metric may modify a frozen primary gate.

## Status vocabulary

### PASS

`CAUSAL_RANK_OPPORTUNITY_POLICY_READY_FOR_DIRECTION_DEVELOPMENT`

PASS means only that the preregistered causal rank-normalized opportunity
policy preserved sufficient historical ranking evidence and support on the
already-consumed development sandbox to justify a separately preregistered
direction-development experiment.

PASS does not mean independent confirmation, prospective confirmation,
direction accuracy, positive expectancy, profitability, tradability, or
leverage readiness.

### FAIL

`FAIL_CAUSAL_RANK_OPPORTUNITY_POLICY_NOT_READY`

Use FAIL when implementation, provenance, and causality remain valid but one or
more scientific development/readiness gates fail. Examples include:

- insufficient predictive ranking;
- temporal-null failure;
- inadequate causal-gate enrichment;
- fewer than three ACTIVE folds;
- clean authorized support insufficiency.

FAIL is preserved and cannot be rescued under the same experiment ID.

### INVALID

`INVALID`

Use INVALID for:

- provenance failure;
- future-data access;
- wrong fold chronology;
- training/validation leakage;
- the current score entering its own reference;
- a future score entering a past reference;
- wrong reference length;
- wrong percentile or quantile method;
- wrong model, feature, or target;
- unauthorized data;
- network access;
- serialization failure;
- one-shot violation;
- unexpected implementation/runtime protocol defect;
- any other frozen-design violation.

## Frozen runtime guards

The following must remain exact built-in `False` values:

- `AUG30_ANALYTICALLY_OPENED = False`
- `SEP01_OR_LATER_OPENED = False`
- `NETWORK_ACCESSED = False`
- `DIRECTION_SCORED = False`
- `PNL_SCORED = False`
- `LEVERAGE_SCORED = False`

## One-shot and provenance requirements

The future implementation must:

- require an explicit full frozen implementation commit;
- require an explicit output path;
- refuse an existing final output;
- refuse an existing `.part` output;
- verify clean tracked-tree state;
- verify the exact preregistration SHA-256;
- verify frozen ancestry;
- verify exact historical input paths, byte sizes, and SHA-256 values before
  analytical use;
- write atomically from `.part` to final exactly once;
- reject NaN and infinity;
- normalize supported NumPy scalar types;
- require exact built-in-boolean invariants;
- externally report final artifact SHA-256 without recursively embedding its
  own hash;
- never rerun after a result artifact exists.

The immutable result must contain sufficient run provenance for independent
audit, including timestamps, run ID, frozen commit, command/argv, environment
versions, configuration and configuration SHA-256, historical input manifest,
fold roles, support counts, all primary and secondary metrics, temporal-null
construction and results, each frozen gate, causal-window invariants, and the
sealed-data guards.

## Next-experiment rule

Only after EXP029-P0 is frozen:

If PASS, a separately preregistered experiment may test direction
predictability conditioned on this exact frozen opportunity policy. That later
experiment may not alter:

- the `rv_30m_bps` opportunity feature;
- the opportunity-model family or parameters;
- the 24 bp opportunity target;
- the 600-second horizon;
- the 60-second decision cadence;
- `q = 0.90`;
- reference-window size 1,399;
- reference initialization;
- causal update order;
- `method = "higher"`.

The next experiment must first test direction as a predictive question. A
direction-development PASS must not be immediately converted into a trading
PnL claim. Execution economics remain a later, distinct experimental stage.

If FAIL, no fresh holdout is opened for this policy. Any material redesign
requires a new experiment ID.

## Fresh data remain sealed

No EXP029-P0 result, PASS or FAIL, authorizes opening 2026-08-30 or 2026-09-01
and later for a new predictive analysis.

Fresh prospective validation requires a separately frozen protocol after the
full opportunity and direction policy is ready.

## No-rescue rule

After EXP029 analytical execution, do not:

- change `q`;
- change 1,399;
- add another reference window;
- change `method="higher"`;
- switch to expanding history;
- add calibration;
- add features;
- add direction filtering;
- add PnL filtering;
- weaken temporal-null gates;
- weaken ranking gates;
- weaken the ACTIVE-fold requirement;
- rerun under EXP029.

Any such material change requires a new experiment ID.
