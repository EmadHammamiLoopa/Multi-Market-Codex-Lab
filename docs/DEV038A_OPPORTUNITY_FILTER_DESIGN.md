# DEV038-A — Opportunity Filter Upgrade Design

Status: `DESIGN_FROZEN_BEFORE_ANY_DEV038A_REAL_FIT`

Date: 2026-09-03

## 1. Objective

DEV038-A is a distinct post-DEV037 development stage.

It does NOT optimize PnL.

It addresses the dominant weakness exposed by DEV037-P1-R1:

- retained S0 action precision was only ~10.18%;
- ~81.64% of S0 actions occurred on true NONE rows.

Therefore the current bottleneck is opportunity selection / TRADE-vs-ABSTAIN,
not directional sign.

DEV038-A asks:

> Can richer causal TOUCH_VS_NONE representations improve opportunity filtering
> while keeping the already-promoted BTC45 direction component unchanged?

## 2. Data-use status

Apr-Jul correctness has already been observed in DEV037.

Therefore Jan-Jul is now development data only.

No candidate tested in DEV038-A may be described as forward-confirmed or
production-ready based solely on Jan-Jul.

A later untouched forward period is required for confirmation.

## 3. Frozen target geometry

Exactly the previously validated opportunity target:

- symbol = BTCUSDT
- target = A
- horizon = 120 seconds
- barrier = 16 bps

No alternative target geometry is allowed in DEV038-A.

## 4. Frozen model family

Exactly the existing P4 T2 model family:

- StandardScaler
- LogisticRegression
- same C grid and nested training-only C selection lineage as P4

No model-family expansion.

No tree model.
No neural net.
No boosting.
No calibration layer.

DEV038-A isolates representation quality, not estimator choice.

## 5. Frozen candidate family

Exactly five TOUCH_VS_NONE representation candidates.

### A0 — PRICE32

- window = 32s
- block = PRICE

This is the frozen incumbent P4 touch representation.

### A1 — PRICE_BOOK32

- window = 32s
- block = PRICE_BOOK

Adds order-book state to PRICE.

### A2 — PRICE_BOOK_FLOW32

- window = 32s
- block = PRICE_BOOK_FLOW

Adds causal order-flow features.

### A3 — FULL32

- window = 32s
- block = PRICE_BOOK_FLOW_DYNAMICS

Adds full causal microstructure dynamics.

### A4 — FULL60

- window = 60s
- block = PRICE_BOOK_FLOW_DYNAMICS

Tests whether a longer full-microstructure regime window improves opportunity
selection.

No sixth candidate may be added after any DEV038-A real-data metric is seen.

## 6. Candidate rationale

The family is intentionally small and nested.

A0 establishes the exact incumbent.

A1 tests static book state.

A2 tests whether recent order flow helps distinguish TOUCH from NONE.

A3 tests richer short-window dynamics.

A4 tests whether richer context needs a longer regime horizon.

This avoids broad strategy mining.

## 7. Stage structure

### DEV038-A-P0 — common-support / feasibility audit

No model fit.

Audit all five candidates jointly on exact Jan-Jul candidate-day construction.

Required outputs:

- valid row count by day and candidate;
- common-support intersection across all five candidates;
- TOUCH/NONE counts on common support;
- per-day class presence;
- retained fraction vs incumbent A0;
- support hashes;
- feature counts;
- exact lookback spans.

P0 must not calculate predictive metrics.

### DEV038-A-P1 — joint development screen

Only if P0 establishes sufficient common support.

All five candidates are fit/evaluated jointly on the SAME common support.

Outer folds remain:

- train Jan-Mar -> validate Apr
- train Jan-Apr -> validate May
- train Jan-May -> validate Jun
- train Jan-Jun -> validate Jul

## 8. Common-support requirement

For fair comparison, DEV038-A-P1 must score all candidates on the exact
intersection support produced by P0.

No candidate-specific validation rows.

Required feasibility:

- common Jan-Jul rows >= 90% of A0 valid support;
- every validation fold contains both TOUCH and NONE;
- every outer-training fold contains both TOUCH and NONE.

If this fails, DEV038-A stops before model fitting.

## 9. Primary predictive endpoint

Primary endpoint:

`Average Precision (AP)`

Primary comparator:

`A0 PRICE32`

For challenger A:

`Delta_AP = AP(A) - AP(A0)`

Positive favors challenger.

## 10. Required secondary endpoints

For every candidate:

- ROC AUC
- Brier score
- log loss
- top-decile precision
- top-decile lift vs prevalence

A candidate may not advance if AP improves while both Brier and log loss worsen.

## 11. Fold stability

A challenger must have:

- >= 3/4 positive fold Delta_AP values;
- all four leave-one-fold-out pooled Delta_AP values > 0.

## 12. Minimum practical effect

Required pooled effect:

`Delta_AP >= +0.015`

absolute AP.

This is frozen before any DEV038-A P1 result.

## 13. Joint temporal null

All four challengers A1-A4 are tested jointly against A0.

Within each validation fold:

- keep predictions fixed;
- circularly shift TOUCH/NONE labels;
- apply the same shifted labels to A0-A4;
- recompute pooled AP;
- compute challenger Delta_AP values;
- record max challenger Delta_AP.

Parameters:

- seed = 20260903
- replicates = 1999
- legal shift = 30 .. n_fold-30
- q95 method = higher
- plus-one FWER empirical p

## 14. Survivor gate

A1-A4 is a DEV038-A development survivor only if ALL pass:

1. pooled AP > A0;
2. pooled Delta_AP >= +0.015;
3. >=3/4 positive fold Delta_AP;
4. all 4 LOO Delta_AP > 0;
5. Brier <= A0;
6. log loss <= A0;
7. observed Delta_AP > joint max-stat q95;
8. FWER p <= 0.05.

No gate may be weakened.

## 15. Survivor ranking

If multiple challengers survive, advance one only.

Ranking:

1. smaller FWER p;
2. larger minimum fold Delta_AP;
3. larger median fold Delta_AP;
4. larger pooled Delta_AP;
5. lower Brier;
6. lower log loss;
7. lower complexity:
   A1 < A2 < A3 < A4;
8. candidate ID.

If none survive:

retain A0.

## 16. What DEV038-A success means

A DEV038-A survivor means:

A richer causal opportunity representation improves historical TOUCH_VS_NONE
ranking on consumed Jan-Jul development data under common support and joint
falsification.

It does NOT mean:

- profitable;
- forward-confirmed;
- safe for live trading.

## 17. Confirmation requirement

After DEV038-A development selection, the selected representation must be frozen
before opening an untouched later period.

Forward confirmation must occur in a separately named stage.

No candidate is allowed to be re-selected after forward data is opened.

## 18. Economic stage sequencing

Only after the opportunity representation is frozen should the project proceed
to execution economics:

- executable bid/ask entry;
- exit protocol;
- costs;
- slippage;
- overlapping-trade handling;
- net PnL;
- drawdown;
- position sizing.

## 19. Strict prohibitions

DEV038-A must not:

- change BTC45 direction features;
- retest S1/S2/S5;
- use ETH/G4;
- tune target barrier/horizon;
- tune W120;
- tune action coverage using Jan-Jul correctness;
- optimize fees/slippage;
- calculate PnL;
- open Sep-01+ forward data;
- reuse Aug-30 as fresh holdout.

## 20. Permanent no-rerun rules

`DEV037-P1-R1 MUST NEVER BE RERUN`

`DEV037-P0-R2 MUST NEVER BE RERUN`

`DEV037-P0-R1 MUST NEVER BE RERUN`

`DEV036-C1 MUST NEVER BE RERUN`

`DEV035-G4B MUST NEVER BE RERUN`

`DEV034-G3B-R1 MUST NEVER BE RERUN`

`DEV034-G3A-R1 MUST NEVER BE RERUN`

## 21. Current state

`DEV038A_OPPORTUNITY_FILTER_DESIGN_FROZEN_P0_COMMON_SUPPORT_AUDIT_NEXT`
