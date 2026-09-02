# DEV038-A-P2 — Final Controller Correctness Screen

Status: `DESIGN_FROZEN_BEFORE_ANY_DEV038A_P2_CORRECTNESS_SCORING`

Date: 2026-09-03

## 1. Project objective

This is a personal investment/trading research project.

The practical objective is robust profitability after realistic costs while
preserving capital and abstaining when evidence is weak.

Documentation is retained because it protects the project against leakage,
overfitting, post-hoc rescue, and false confidence in weak trading rules.

DEV038-A-P2 is the final predictive-development experiment before the project
closes predictive search and moves to forward/economic falsification.

## 2. Why this experiment exists

DEV038-A-P1 retained A0 PRICE32 as the opportunity representation.

DEV037 retained S0 TOUCH_ONLY_SELECTIVE with controller W120 because W120 was
selected operationally for label-free coverage stability.

W360 and W720 were operationally feasible controller candidates, but their
validation correctness was never scored.

Therefore P2 tests exactly one remaining pre-existing operational knob:

`controller reference window`

No new feature, model, target, direction rule, policy score, or threshold
quantile is introduced.

This is explicitly a post-P1 development deviation. It was not part of the
original DEV038-A-P1 mandatory-next-stage route.

Apr-Jul remain consumed development data.

## 3. Frozen upstream components

Opportunity representation:

`A0 PRICE32`

Target:

- symbol = BTCUSDT
- horizon = 120 seconds
- barrier = 16 bps
- TOUCH = LONG_FIRST or SHORT_FIRST within 120s/16bp
- NONE = no first-passage touch

Direction:

`BTC45`

Direction action:

- LONG if frozen p_long >= 0.5
- SHORT otherwise

Policy:

`S0 TOUCH_ONLY_SELECTIVE`

Policy score:

`score = p_touch`

No alternative policy score is permitted.

## 4. Frozen controller family

Exactly:

### C0 — W120

- reference window = 120 prior scores
- comparator/incumbent

### C1 — W360

- reference window = 360 prior scores
- challenger

### C2 — W720

- reference window = 720 prior scores
- challenger

No W240, W480, W600, or any other window is permitted.

## 5. Frozen sequential threshold rule

For each controller:

At decision index t:

1. use only scores observed before t;
2. warm-start from the most recent OOF training scores available before the
   validation day;
3. retain only the most recent W scores;
4. compute:
   `threshold_t = quantile(reference_buffer, 0.80, method="higher")`
5. ACT iff:
   `p_touch_t >= threshold_t`
6. direction = frozen BTC45 sign;
7. append score_t only after the decision.

The current score cannot enter its own threshold.

No label is used to compute thresholds.

q80 is frozen.

No q70/q75/q85/q90 search is permitted.

## 6. Support and folds

Use the exact frozen DEV037/DEV036-C1 common support:

- Jan-Jul rows = 9849
- TOUCH = 1341
- NONE = 8508
- support SHA256 =
  `dc89f3012341bd771591693b03af00b86f64f95aa4f7db4e9dc65b7e0e7f7b3f`

Outer validation folds:

- Apr
- May
- Jun
- Jul

Pooled validation rows:

`5628`

All C0/C1/C2 must use identical rows and identical frozen component
probabilities.

## 7. Action semantics

Every controller emits:

- LONG
- SHORT
- ABSTAIN

Correct action:

- LONG on LONG_FIRST; or
- SHORT on SHORT_FIRST.

False action:

Any acted row that is not correct, including:

- acting on NONE;
- wrong direction on TOUCH.

## 8. Primary endpoint

Primary endpoint:

`ACTION_PRECISION = correct_actions / actions`

Primary comparator:

`C0 W120`

For challenger C:

`DeltaPrecision(C) = ActionPrecision(C) - ActionPrecision(C0)`

Minimum practical effect:

`DeltaPrecision >= +0.020 absolute`

This is frozen before P2 correctness scoring.

## 9. Mandatory preservation endpoint

A controller cannot win by merely reducing activity and discarding correct
trades.

Define:

`CorrectActionRate = correct_actions / all_validation_rows`

Required:

`DeltaCorrectActionRate >= 0`

versus C0.

No tolerance band and no post-result interpretation such as "not materially
worse" is permitted.

## 10. Required secondary decision metrics

Serialize pooled and per-fold:

- action count
- abstain count
- coverage
- correct action count
- false action count
- action precision
- correct action rate
- false action rate
- LONG actions
- SHORT actions
- LONG precision
- SHORT precision
- acted-TOUCH direction accuracy
- action-on-NONE fraction
- threshold summary
- rolling coverage diagnostics

## 11. Operational feasibility guards

Required for each validation fold:

- coverage >= 0.05
- coverage <= 0.40
- LONG count > 0
- SHORT count > 0
- action count > 0
- abstain count > 0

Required pooled:

- coverage >= 0.10
- coverage <= 0.30

## 12. Fold stability

A challenger must satisfy:

- positive DeltaPrecision in at least 3/4 folds;
- all four leave-one-fold-out pooled DeltaPrecision values > 0.

## 13. False-action safeguards

A challenger must also satisfy:

- pooled FalseActionRate < C0;
- pooled ActionOnNONEFraction < C0.

These are mandatory because the current practical bottleneck is excessive
false actions, especially actions occurring on true NONE rows.

## 14. Joint temporal falsification

C1 and C2 are tested jointly against C0.

Predicted scores/actions remain fixed.

Within each validation fold:

1. circularly shift the full chronological three-class label sequence;
2. use the same shifted labels for C0/C1/C2;
3. recompute pooled action precision;
4. compute C1-C0 and C2-C0 DeltaPrecision;
5. retain the maximum challenger DeltaPrecision.

Parameters:

- replicates = 1999
- seed = 20260903
- legal shift minimum = 30 rows
- legal shift maximum = n_fold - 30 rows
- q95 method = higher
- empirical p uses plus-one denominator 2000

This controls family-wise false discovery across the two challengers.

## 15. Survivor gate

C1 or C2 survives only if ALL pass:

1. pooled ActionPrecision > C0;
2. pooled DeltaPrecision >= +0.020;
3. >= 3/4 positive fold DeltaPrecision values;
4. all four LOO DeltaPrecision values > 0;
5. pooled DeltaCorrectActionRate >= 0;
6. pooled FalseActionRate < C0;
7. pooled ActionOnNONEFraction < C0;
8. pooled coverage in [0.10, 0.30];
9. every fold coverage in [0.05, 0.40];
10. LONG and SHORT both emitted every fold;
11. observed DeltaPrecision > joint max-stat q95;
12. max-stat FWER empirical p <= 0.05.

No gate may be weakened after results are seen.

## 16. Survivor ranking

If both C1 and C2 survive, advance exactly one using:

1. smaller FWER p;
2. larger minimum fold DeltaPrecision;
3. larger median fold DeltaPrecision;
4. larger pooled DeltaPrecision;
5. larger DeltaCorrectActionRate;
6. lower ActionOnNONEFraction;
7. smaller controller window;
8. lexicographic candidate ID.

## 17. Terminal outcomes

If at least one challenger survives:

`DEV038A_P2_CONTROLLER_SURVIVOR_FOUND`

Advance rank 1 only.

If neither survives:

`DEV038A_P2_NO_CONTROLLER_SURVIVOR_RETAIN_W120`

Advance C0 W120.

## 18. Permanent predictive stop rule

Regardless of outcome, DEV038-A-P2 closes this predictive-development branch.

After P2 there is NO:

- W240
- W480
- W600
- additional window search
- q70/q75/q85/q90 search
- XGBoost
- Random Forest
- neural network rescue
- new feature family
- new opportunity representation
- new meta-filter
- BTC45 threshold tuning
- target geometry tuning
- Apr-Jul PnL optimization
- cost-optimized threshold search

If no challenger survives, freeze:

`A0 PRICE32 + BTC45 + S0 + W120`

If a challenger survives, freeze:

`A0 PRICE32 + BTC45 + S0 + winning controller`

No further controller search follows.

## 19. What P2 does not establish

P2 is development-only.

It does not establish:

- forward validity;
- profitability;
- executable entry quality;
- fee robustness;
- slippage robustness;
- acceptable drawdown;
- production readiness.

## 20. Mandatory next route after P2

After freezing the controller:

1. freeze untouched forward-confirmation protocol;
2. run the frozen integrated policy prospectively/untouched;
3. only after forward confirmation proceed to DEV038-B economic/execution
   falsification;
4. economic testing must use realistic bid/ask, delay, fees, slippage, exits,
   overlap handling, drawdown, and risk metrics under a separately frozen
   protocol.

## 21. Strict prohibitions during P2

P2 must not:

- open Sep-01+ forward data;
- reuse Aug-30 as fresh holdout;
- run PnL;
- run fees;
- run slippage;
- change model family;
- change opportunity representation;
- change direction logic;
- change target geometry;
- change q80;
- optimize position sizing;
- introduce leverage.

## 22. Permanent no-rerun rules

`DEV038-A-P1 MUST NEVER BE RERUN`

`DEV038-A-P0 MUST NEVER BE RERUN`

`DEV037-P1-R1 MUST NEVER BE RERUN`

`DEV037-P0-R2 MUST NEVER BE RERUN`

`DEV037-P0-R1 MUST NEVER BE RERUN`

`DEV036-C1 MUST NEVER BE RERUN`

## 23. Execution discipline

Stages:

1. P2 design freeze
2. implementation only
3. synthetic/unit CI
4. execution freeze
5. no-result reproduction preflight
6. one canonical joint controller correctness screen
7. deep read-only verification
8. result freeze
9. predictive search closed

No real P2 correctness scoring is authorized by this design freeze alone.

## 24. Current state

`DEV038A_P2_FINAL_CONTROLLER_SCREEN_DESIGN_FROZEN_IMPLEMENTATION_NEXT_NO_REAL_SCORING`
