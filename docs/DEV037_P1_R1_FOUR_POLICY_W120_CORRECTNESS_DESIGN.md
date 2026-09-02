# DEV037-P1-R1 — Four-Policy Correctness Screen Under Frozen W120

Status: `DESIGN_FROZEN_BEFORE_ANY_CORRECTNESS_SCORING`

Date: 2026-09-02

## 1. Objective

Evaluate the retained selective trading policies under the frozen operational
controller selected by DEV037-P0-R2.

This is the first DEV037 stage permitted to inspect validation correctness.

The practical question is:

> Given the same frozen touch and BTC45 forecasts, and the same live-compatible
> W120 coverage controller, which policy most reliably converts those forecasts
> into correct LONG / SHORT / ABSTAIN decisions?

This stage still does not evaluate PnL.

## 2. Frozen upstream controller

The only permitted controller is:

`W120`

Selected canonically by DEV037-P0-R2 without inspecting validation correctness.

Parent artifact:

`/home/emadh/Multi-Market/evidence/dev037_p0_r2_operationally_pruned_controller_v1/DEV037_P0_R2_OPERATIONALLY_PRUNED_CONTROLLER_RESULT.json`

Parent SHA256:

`494122f1aea64fb2a4c956d674330d9a400709656f0e116187d6fa2fefaa3336`

Parent bytes:

`27056`

No W360 or W720 correctness result may be computed in this experiment.

## 3. Frozen retained policy family

Exactly four policies:

### S0 — TOUCH_ONLY_SELECTIVE

Score:

`p_touch`

Direction:

BTC45 sign.

### S1 — DIRECTION_CONFIDENCE_SELECTIVE

Score:

`d = 2 × |p_long - 0.5|`

Direction:

BTC45 sign.

### S2 — PRODUCT_JOINT_SELECTIVE

Score:

`p_touch × d`

Direction:

BTC45 sign.

### S5 — META_CORRECTNESS_FILTER

Frozen six-feature OOF-trained logistic meta filter from DEV037 lineage.

Direction:

BTC45 sign.

Removed permanently before correctness evaluation:

- S3
- S4

They are not candidates and must not be scored for correctness.

## 4. Frozen action controller

For every policy separately and every validation fold:

At decision t:

`threshold_t = q80(last up to 120 prior policy scores, method="higher")`

with:

- current score excluded from its own reference;
- warm-start from the most recent OOF training scores only;
- ACT iff score_t >= threshold_t;
- LONG iff BTC45 p_long >= 0.5;
- SHORT otherwise;
- else ABSTAIN.

No threshold change is allowed.

## 5. Frozen support and folds

Exact DEV036-C1 common support lineage.

Validation folds:

- Apr = 1407 rows
- May = 1407 rows
- Jun = 1407 rows
- Jul = 1407 rows

Pooled validation:

`5628 rows`

No support shrink.

No row removal based on policy scores or outcomes.

## 6. Action correctness

True labels:

- NONE
- SHORT_FIRST
- LONG_FIRST

A correct action is:

- predicted SHORT and true label SHORT_FIRST; or
- predicted LONG and true label LONG_FIRST.

A false action is any other acted row, including:

- action on true NONE;
- LONG on SHORT_FIRST;
- SHORT on LONG_FIRST.

ABSTAIN is not counted as correct or false action.

## 7. Primary comparator

`S0 TOUCH_ONLY_SELECTIVE`

Rationale:

S0 is the simplest operational policy combining the validated touch selector
with the frozen BTC45 direction sign.

Every challenger must demonstrate value beyond this simple policy.

Challengers:

- S1
- S2
- S5

## 8. Primary endpoint

For policy S:

`ACTION_PRECISION(S) = correct_actions / all_actions`

Primary increment:

`DeltaPrecision(S) = Precision(S) - Precision(S0)`

Positive favors the challenger.

## 9. Required practical secondary endpoint

A challenger must not improve precision merely by acting less often.

Define:

`CORRECT_ACTION_RATE(S) = correct_actions / all validation rows`

Required practical increment:

`DeltaCorrectRate(S) = CorrectActionRate(S) - CorrectActionRate(S0)`

A true survivor must have:

`DeltaCorrectRate > 0`

pooled.

This protects against a policy that gains precision only by discarding too many
otherwise useful actions.

## 10. Additional serialized diagnostics

For every policy pooled and per fold:

- action count
- abstain count
- coverage
- correct action count
- false action count
- action precision
- selective risk = 1 - action precision
- correct actions / all rows
- false actions / all rows
- LONG action count
- SHORT action count
- LONG action precision
- SHORT action precision
- acted true-TOUCH count
- direction accuracy among acted true-TOUCH rows
- action count on true NONE
- fraction of actions on true NONE

These are diagnostics unless explicitly used by frozen gates below.

## 11. Frozen coverage feasibility

The already-selected W120 controller must reproduce operational feasibility.

For every policy and fold:

- coverage >= 0.10
- coverage <= 0.30
- LONG count > 0
- SHORT count > 0

If this fails to reproduce, terminate:

`PREEXECUTION_OPERATIONAL_REPRODUCTION_FAILURE_NO_RESULT`

No correctness conclusion may be reported.

## 12. Fold stability

For challenger S vs S0, compute fold-level action-precision deltas.

Required:

- at least 3/4 fold deltas > 0.

Also compute four leave-one-fold-out pooled deltas.

Required:

- all 4 LOO precision deltas > 0.

## 13. Minimum practical effect

A challenger must satisfy:

`pooled DeltaPrecision >= +0.02`

Absolute 2 percentage points.

This is frozen before correctness is observed.

## 14. Joint temporal falsification

All three challengers are tested jointly.

Predicted scores, W120 thresholds, and resulting actions remain fixed.

Within each validation fold:

1. retain the full chronological three-class outcome sequence;
2. circularly shift that sequence by a legal non-zero amount;
3. apply the same shifted labels to S0/S1/S2/S5;
4. recompute pooled action precision;
5. compute each challenger precision delta vs S0;
6. record the maximum delta across S1/S2/S5.

Legal shifts:

- minimum = 30 rows
- maximum = n_fold - 30 rows

Parameters:

- seed = 20260902
- replicates = 1999
- q95 method = `higher`
- empirical p uses plus-one denominator 2000

This controls family-wise false discovery across the three challengers.

## 15. Survivor gate

A challenger is a true DEV037-P1-R1 survivor only if ALL pass:

1. operational reproduction = PASS;
2. pooled action precision > S0;
3. pooled DeltaPrecision >= +0.02;
4. pooled DeltaCorrectRate > 0;
5. >=3/4 fold precision deltas > 0;
6. all four LOO precision deltas > 0;
7. observed DeltaPrecision > joint max-stat q95;
8. max-stat FWER empirical p <= 0.05.

No gate may be weakened after results are observed.

## 16. Survivor ranking

If multiple challengers survive, advance at most one.

Ranking:

1. smaller max-stat FWER p;
2. larger minimum fold precision delta;
3. larger median fold precision delta;
4. larger pooled DeltaPrecision;
5. larger pooled DeltaCorrectRate;
6. lower false-actions-per-all-rows;
7. lower policy complexity:
   S1 < S2 < S5;
8. lexicographic ID.

## 17. Terminal outcomes

If one or more challengers survive:

`DEV037_P1_R1_POLICY_SURVIVOR_FOUND`

Advance deterministic rank 1 only.

If no challenger survives and S0 operational reproduction passes:

`DEV037_P1_R1_NO_CHALLENGER_SURVIVOR_RETAIN_S0`

If W120 operational reproduction fails:

`PREEXECUTION_OPERATIONAL_REPRODUCTION_FAILURE_NO_RESULT`

## 18. Meaning of a survivor

A survivor means:

The policy produces more correct acted decisions than the touch-only baseline
under the same frozen W120 controller, with fold stability and joint temporal
falsification.

It does NOT yet mean:

- profitable after fees;
- profitable after slippage;
- robust to execution delay;
- acceptable drawdown;
- forward-valid;
- appropriate for leverage.

## 19. Next stage

If a challenger survives:

freeze it as the only candidate policy for DEV038.

If no challenger survives:

retain S0 as the simplest policy candidate for DEV038.

DEV038 is the intended economic execution stage.

DEV038 may then evaluate, under a separate frozen protocol:

- fees;
- spread/bid-ask crossing;
- slippage;
- entry delay;
- overlapping-signal handling;
- trade frequency;
- gross PnL;
- net PnL;
- hit rate;
- payoff ratio;
- max drawdown;
- exposure;
- risk-adjusted return;
- fixed-risk position sizing.

No forward holdout should be consumed until the DEV038 economic protocol is
frozen.

## 20. Strict prohibitions

DEV037-P1-R1 must not:

- evaluate W360 or W720 correctness;
- reintroduce S3 or S4;
- tune W120;
- tune q80;
- tune BTC45 threshold;
- tune touch model;
- change S5 features or C;
- add features;
- inspect fees/slippage;
- optimize PnL;
- open Sep-01+ forward data;
- reuse Aug-30 as fresh holdout;
- use Railway/archive/abundant-love analytically.

## 21. Permanent no-rerun rules

`DEV037-P0-R2 MUST NEVER BE RERUN`

`DEV037-P0-R1 MUST NEVER BE RERUN`

`DEV036-C1 MUST NEVER BE RERUN`

`DEV035-G4B MUST NEVER BE RERUN`

`DEV034-G3B-R1 MUST NEVER BE RERUN`

`DEV034-G3A-R1 MUST NEVER BE RERUN`

## 22. Execution discipline

Stages:

1. design freeze
2. implementation only
3. synthetic/unit CI
4. execution freeze
5. real-data no-result reproduction preflight
6. one canonical correctness screen
7. deep read-only verification
8. result freeze
9. DEV038 economic protocol design

No DEV037-P1-R1 correctness scoring is authorized by this design freeze alone.

## 23. Current state

`DEV037_P1_R1_FOUR_POLICY_W120_CORRECTNESS_DESIGN_FROZEN_IMPLEMENTATION_NEXT_NO_CORRECTNESS_SCORING`
