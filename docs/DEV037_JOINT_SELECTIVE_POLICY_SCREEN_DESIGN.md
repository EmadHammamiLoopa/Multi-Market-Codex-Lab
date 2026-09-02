# DEV037-P0/P1 — Joint Selective Trading Policy Screen v1

Status: `DESIGN_FROZEN_BEFORE_ANY_DEV037_MODEL_OR_POLICY_SCORING`

Date: 2026-09-02

## 1. Project objective

DEV037 is part of a personal investment/trading research project.

The practical objective is to convert the already-validated predictive
components into a robust executable decision rule:

`LONG / SHORT / ABSTAIN`

The purpose of this stage is not academic novelty.

The purpose is to identify a selective trading policy that can later be tested
under realistic transaction costs, slippage, execution delay, drawdown, risk
controls, position sizing, and net PnL.

Strict documentation remains because it protects against overfitting and
capital-risk from weak strategies.

## 2. Why selective trading is the next stage

Upstream evidence now separates the problem into components.

### Opportunity / touch

DEV030-P4 T2 is a validated historical TOUCH_VS_NONE component.

### Direction

DEV034-G3C16 / BTC45 is a validated promoted direction component.

### Composition

DEV036-C1 established:

1. BTC45 materially improves composition relative to P3;
2. all primary C3-vs-C2 gates passed;
3. temporal-null p = 0.0005;
4. but the multiplicative C3 composition was not robustly superior to the
   simpler touch-plus-directional-prior baseline.

Therefore the next problem is not new feature discovery.

It is selective decision policy.

## 3. External design rationale

DEV037 adopts three practical ideas that are widely used in modern predictive
decision systems:

1. **Selective classification / reject option**
   - a model may abstain when confidence is insufficient;
   - accuracy/risk is evaluated jointly with coverage.

2. **Forecast separated from decision generation**
   - the existing forecast models remain frozen;
   - policy logic converts forecasts into actions.

3. **Explicit risk filtering**
   - weak/ambiguous signals should result in no trade rather than a forced
     trade.

No external implementation or pre-trained model is imported.

These ideas inform the policy family only.

## 4. Frozen predictive inputs

DEV037 must use the exact DEV036-C1 lineage.

### Touch forecast

Support-matched P4 S1 touch probability:

`p_touch`

### Direction forecast

Frozen BTC45 / G3C16 conditional LONG probability:

`p_long`

Direction action:

- LONG if p_long >= 0.5
- SHORT if p_long < 0.5

Direction confidence:

`d = 2 × |p_long - 0.5|`

Thus:

- d = 0 means completely ambiguous;
- d = 1 means maximal directional confidence.

No P3 policy is a candidate in DEV037.

P3 remains historical comparator lineage only.

## 5. Frozen support and folds

Use exact DEV036-C1 C0 common support:

- Jan-Jul rows = 9849
- TOUCH = 1341
- NONE = 8508
- support SHA256 =
  `dc89f3012341bd771591693b03af00b86f64f95aa4f7db4e9dc65b7e0e7f7b3f`

Outer validation:

- Apr = 1407
- May = 1407
- Jun = 1407
- Jul = 1407
- pooled = 5628

Three-class labels:

- 0 = NONE
- 1 = SHORT_FIRST
- 2 = LONG_FIRST

No support shrink is allowed.

## 6. Two-stage DEV037 structure

### DEV037-P0 — policy feasibility / score audit

Read-only or no-label policy-mechanics stage.

It may:

- reproduce frozen touch and BTC45 fold probabilities;
- build all frozen policy scores;
- derive training-only thresholds;
- report expected validation coverage;
- verify every policy produces both actions and abstentions;
- verify no policy has degenerate LONG-only or SHORT-only behavior.

It must not inspect validation correctness when choosing thresholds.

### DEV037-P1 — one joint canonical policy screen

All policy candidates are evaluated together in one canonical run on identical
folds, rows, model probabilities, labels, and null structure.

## 7. Common threshold principle

Every candidate targets approximately:

`20% action coverage`

Thresholds must be derived from **expanding one-day-ahead out-of-fold (OOF)
predictions inside the outer-training period**, not from in-sample fitted
probabilities.

For each outer fold:

1. Jan and Feb are seed days because the frozen component lineages require at
   least one inner-fit day and one inner-validation day for C selection;
2. construct chronological OOF component predictions beginning with Mar and
   continuing through the final day of the current outer-training period;
3. each OOF scored day is predicted only by component models fit on strictly
   earlier days;
4. for each scored day, the immediately preceding fit day is the inner
   validation day and all earlier fit days are inner-fit days;
5. concatenate those OOF training scores;
6. derive the policy threshold from those OOF scores only.

For score s:

`threshold = OOF_train_quantile(s, 0.80, method="higher")`

Validation rule:

`ACT iff validation_score >= frozen_OOF_training_threshold`

The first two historical days are seed days and are not themselves OOF scored
days.

This creates a practical selective screen while avoiding validation-label
threshold optimization and avoiding in-sample score-distribution leakage.

The 20% target is frozen before DEV037-P1.

No alternative 10%, 15%, 25%, or 30% threshold may be tested in this experiment
after results are observed.

Those would require separately named future experiments.

## 8. Exactly six frozen policies

Policy IDs and order are immutable.

### S0 — TOUCH_ONLY_SELECTIVE

Score:

`s0 = p_touch`

Act when:

`s0 >= train_q80(s0)`

Direction:

BTC45 sign.

Purpose:

Determine whether simply selecting the strongest touch forecasts is sufficient.

### S1 — DIRECTION_CONFIDENCE_SELECTIVE

Score:

`s1 = d`

Act when:

`s1 >= train_q80(s1)`

Direction:

BTC45 sign.

Purpose:

Benchmark direction-confidence selection without explicit touch prioritization.

### S2 — PRODUCT_JOINT_SELECTIVE

Score:

`s2 = p_touch × d`

Act when:

`s2 >= train_q80(s2)`

Direction:

BTC45 sign.

Purpose:

Continuous joint confidence in touch occurrence and direction certainty.

This is a decision score, not the failed DEV036 three-class probability product.

### S3 — BALANCED_MIN_PERCENTILE

On outer-training rows only, construct empirical percentile transforms:

`r_touch = percentile_rank_train(p_touch)`

`r_dir = percentile_rank_train(d)`

For validation rows, map p_touch and d through the frozen training empirical CDFs.

Score:

`s3 = min(r_touch, r_dir)`

Act when:

`s3 >= train_q80(s3)`

Direction:

BTC45 sign.

Purpose:

Require both components to be reasonably strong; one high score cannot fully
compensate for one weak score.

### S4 — GEOMETRIC_BALANCED_PERCENTILE

Use the same training-only percentile transforms.

Score:

`s4 = sqrt(r_touch × r_dir)`

Act when:

`s4 >= train_q80(s4)`

Direction:

BTC45 sign.

Purpose:

Balanced soft conjunction with less harsh behavior than S3.

### S5 — META_CORRECTNESS_FILTER

This is a frozen meta-labeling style policy.

S5 must be trained only on the same expanding one-day-ahead OOF training
component predictions described above. It must never use in-sample component
probabilities as meta-training features.

OOF training meta target:

`meta_correct = 1`

only if the BTC45 sign is exactly correct:

- predicted LONG and true class LONG_FIRST, or
- predicted SHORT and true class SHORT_FIRST.

Otherwise:

`meta_correct = 0`

including true NONE rows.

Meta features are exactly:

1. p_touch
2. d
3. p_touch × d
4. r_touch
5. r_dir
6. min(r_touch, r_dir)

Model:

- StandardScaler fit on OOF outer-training meta rows only
- LogisticRegression
- L2
- solver = lbfgs
- class_weight = None
- fit_intercept = True
- max_iter = 1000
- random_state = 20260825
- C = 1.0 fixed

No C search.

Meta score:

`s5 = P(meta_correct = 1)`

Act when:

`s5 >= OOF_train_q80(s5)`

Direction:

BTC45 sign.

Purpose:

Directly estimate whether acting on the frozen BTC45 direction is likely to be
correct, while keeping the meta model very small and fully specified.

## 9. Why these six and no others

The family covers six materially distinct policy mechanisms:

- touch confidence only;
- direction confidence only;
- direct multiplicative joint confidence;
- strict balanced conjunction;
- soft balanced conjunction;
- supervised meta correctness filtering.

Excluded from DEV037:

- RL policy learning;
- dynamic position sizing;
- volatility regime thresholds;
- ETH/G4 features;
- new raw-market features;
- composition weight tuning;
- cost-optimized thresholds;
- PnL-optimized thresholds.

This keeps the policy screen focused and interpretable.

## 10. Action semantics

Every candidate outputs exactly one of:

- ABSTAIN
- SHORT
- LONG

For an acted validation row:

### Correct action

- SHORT and true class SHORT_FIRST; or
- LONG and true class LONG_FIRST.

### False action

Any acted row that is not a correct action, including:

- acting when true class is NONE;
- wrong direction on a TOUCH row.

Thus action precision directly measures whether a policy's trades would have
selected the correct first-passage event before transaction costs.

## 11. Primary policy endpoint

For candidate S:

`ACTION_PRECISION(S) = correct_actions / total_actions`

Primary comparator:

`S0 TOUCH_ONLY_SELECTIVE`

Primary increment:

`Delta_APrecision(S) = ACTION_PRECISION(S) - ACTION_PRECISION(S0)`

Rationale:

S0 is the simplest practical policy using the independently successful touch
model and the frozen BTC45 sign.

A more complex selective policy must improve actual action correctness, not
merely forecast metrics.

## 12. Mandatory coverage guard

A policy cannot win by almost never trading.

For every validation fold:

- action coverage must be >= 0.05
- action coverage must be <= 0.40

Pooled:

- action coverage must be >= 0.10
- action coverage must be <= 0.30

These are feasibility guards, not optimized targets.

## 13. Secondary decision metrics

Serialize for every candidate:

- action count
- abstain count
- coverage
- correct action count
- false action count
- action precision
- selective risk = 1 - action precision
- correct actions per all validation rows
- false actions per all validation rows
- LONG action count
- SHORT action count
- LONG/SHORT action ratio
- precision on LONG actions
- precision on SHORT actions
- accuracy conditional on true TOUCH among acted TOUCH rows
- fraction of actions occurring on true NONE rows

Also serialize four-fold values and pooled values.

## 14. Stability requirements

A candidate may be a survivor only if:

- action precision > S0 pooled action precision;
- at least 3/4 folds improve action precision vs S0;
- all four leave-one-fold-out pooled action-precision deltas > 0;
- coverage guards pass;
- candidate emits at least one LONG and one SHORT action in every validation fold.

## 15. Joint temporal falsification

All five challenger policies S1-S5 are tested jointly against S0.

Predicted scores/actions remain fixed.

Within each validation fold, circularly shift the full chronological
three-class outcome sequence.

Legal shift:

- minimum 30 rows;
- maximum n_fold - 30 rows.

For each replicate:

1. use one legal circular shift per fold;
2. apply the same shifted labels to S0-S5;
3. recompute pooled action precision;
4. compute each challenger delta vs S0;
5. record the maximum challenger delta across S1-S5.

Parameters:

- replicates = 1999
- seed = 20260902
- max-stat q95 uses method = higher
- FWER p uses plus-one denominator 2000

This controls family-wise false discovery across the five challengers.

## 16. Survivor gate

A challenger S1-S5 is a true DEV037 survivor only if ALL pass:

1. pooled action precision > S0;
2. pooled delta action precision >= +0.02 absolute;
3. >=3/4 positive fold deltas vs S0;
4. all four LOO deltas > 0;
5. pooled coverage within [0.10, 0.30];
6. every validation fold coverage within [0.05, 0.40];
7. LONG and SHORT both emitted in every validation fold;
8. observed delta > joint five-challenger max-stat q95;
9. FWER empirical p <= 0.05.

No gate may be weakened after results are observed.

## 17. Survivor ranking

If multiple candidates survive, advance at most one.

Ranking:

1. smaller FWER p;
2. larger minimum fold action-precision delta;
3. larger median fold action-precision delta;
4. larger pooled action-precision delta;
5. lower pooled false-action rate;
6. lower policy complexity in this order:
   S1 < S2 < S3 < S4 < S5;
7. lexicographic candidate ID.

S0 is comparator and cannot be called a challenger survivor.

## 18. Terminal outcomes

If one or more challengers survive:

`DEV037_POLICY_SURVIVOR_FOUND`

Advance only deterministic rank 1.

If none survive but S0 itself satisfies all coverage/action-balance feasibility
guards:

`DEV037_NO_CHALLENGER_SURVIVOR_RETAIN_TOUCH_ONLY_POLICY`

If S0 is itself operationally degenerate:

`DEV037_POLICY_FAMILY_NOT_OPERATIONALLY_USABLE`

No post-hoc threshold refinement follows a zero-survivor result.

## 19. What a survivor means

A survivor means:

A selective LONG/SHORT/ABSTAIN decision rule identifies historically more
correct actions than the simplest touch-selective BTC45-sign policy, under
matched folds and multiplicity-controlled temporal falsification.

It does NOT yet mean:

- profitable after fees;
- profitable after slippage;
- robust to execution delay;
- acceptable drawdown;
- forward-valid;
- safe for leverage.

## 20. Next stage after DEV037

If a policy survives:

DEV038 should evaluate the frozen policy under realistic execution/economic
conditions.

DEV038 may introduce:

- entry delay;
- fees;
- bid/ask crossing;
- slippage;
- trade frequency;
- gross/net PnL;
- hit rate;
- payoff ratio;
- maximum drawdown;
- Sharpe-like risk-adjusted return;
- exposure;
- capital-at-risk;
- simple fixed-risk position sizing.

If no challenger survives but S0 remains usable:

DEV038 may evaluate S0 as the retained simplest policy, subject to a separately
frozen economic protocol.

No final forward holdout should be consumed until the economic protocol and
candidate policy are frozen.

## 21. Strict prohibitions

DEV037 must not:

- open Aug-30 as fresh data;
- open Sep-01+ forward data;
- use Railway/archive/abundant-love analytically;
- run real PnL;
- tune fees/slippage assumptions;
- tune q80 after results;
- search target coverage after results;
- tune BTC45 threshold;
- tune touch model;
- add new predictive features;
- alter G3C16;
- use ETH/G4 features;
- search position sizing;
- introduce leverage;
- select policies after separate independent runs.

All six policies must appear in one joint canonical screen.

## 22. Upstream permanent rules

`DEV036-C1 MUST NEVER BE RERUN`

`DEV035-G4B MUST NEVER BE RERUN`

`DEV034-G3B-R1 MUST NEVER BE RERUN`

`DEV034-G3A-R1 MUST NEVER BE RERUN`

## 23. OOF component-prediction requirements

For every outer fold, the implementation must serialize an OOF training ledger.

Required fields per OOF training day, beginning with Mar:

- prediction day;
- component fit days;
- touch selected C;
- BTC45 selected C;
- OOF row count;
- OOF TOUCH/NONE count;
- p_touch prediction hash;
- p_long prediction hash.

No OOF day may appear in its own component fit set.

All policy thresholds S0-S5 and the S5 meta fit must derive only from the
concatenated OOF training rows.

The outer validation probabilities are produced by the frozen component
lineages fit on the full outer-training period.

This requirement is a pre-result guard.

## 24. Execution discipline

Stages:

1. DEV037 joint-policy design freeze
2. implementation only
3. unit/synthetic CI
4. execution freeze
5. real-data P0 policy feasibility preflight
6. one canonical DEV037-P1 joint screen
7. deep read-only verification
8. only then DEV038 economic/PnL protocol design

No real DEV037 policy scoring is authorized by this design freeze.

## 25. Current state

`DEV037_JOINT_SELECTIVE_POLICY_DESIGN_FROZEN_IMPLEMENTATION_NEXT_NO_REAL_SCORING`
