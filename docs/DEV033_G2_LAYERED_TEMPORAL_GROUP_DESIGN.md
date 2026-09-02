# DEV033-G2 — Layered Raw-Temporal Microstructure Group Design v1

Status: `DESIGN_FROZEN_NO_MATERIALIZATION_OR_MODEL_FIT`

Date: 2026-09-02

Governance:
`docs/LAYERED_STRATEGY_SEARCH_GOVERNANCE.md`

## 1. Role in the layered search

This is the first experiment designed under the permanent layered-search rule.

The direction-stage base is NOT the best DEV032 candidate.

The frozen direction-stage base remains the last true success:

`DEV030-P3`

Selected base:

- BTCUSDT
- T1 DIRECTION_GIVEN_TOUCH
- target A
- horizon = 120 s
- barrier = 16 bp
- causal PRICE sequence-summary window = 32 s
- feature block = PRICE
- model family = M1 regularized LogisticRegression
- terminal label = SELECTED_FOR_NEXT_DEVELOPMENT_STAGE

Canonical P3 artifact:

`/home/emadh/Multi-Market/evidence/dev030_p3_campaign1_v1/DEV030_P3_CAMPAIGN1_RESULT.json`

SHA256:

`f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`

The base remains unchanged unless a DEV033-G2 candidate passes every frozen
incremental survivor gate.

## 2. Why this group is scientifically distinct

DEV032-E1B broadly screened fixed engineered microstructure vectors added to a
PRICE control.

DEV032-E2B adaptively refined inconclusive microstructure vectors and rejected
all ten refinements.

DEV033-G2 does NOT make another engineered-summary refinement.

It tests a distinct representation question:

> Does preserving the raw causal temporal path of microstructure state add
> stable direction-given-touch information on top of the already-successful P3
> PRICE32 summary layer?

All candidates preserve explicit one-second temporal position.

## 3. Candidate count

Exactly:

`8 information families x 3 causal windows = 24 primary candidates`

No candidate may be added after any G2 predictive result is observed.

Candidate windows:

- 8 s
- 16 s
- 32 s

The base PRICE representation always remains the frozen P3 32-second success.

Only the added layer varies.

## 4. Common target and data

Exactly the frozen P3 target:

- symbol = BTCUSDT
- task = T1 DIRECTION_GIVEN_TOUCH
- target = A
- horizon = 120 s
- barrier = 16 bp

Historical development scope:

- Jan-Jul 2026 only
- exact P3 candidate-day/fold lineage
- exact P3 matched S1 support must be reproduced

No support shrink is allowed merely because an added feature is inconvenient.

Any candidate unable to materialize on exact P3 support fails closed before
model fitting.

## 5. The eight raw-temporal information families

Every family is represented as fixed one-second bins ordered newest to oldest.
Every value is causal at the decision timestamp.

### T01 — L1_QUEUE_IMBALANCE_PATH

Per one-second bin:

`(bid_qty_L1 - ask_qty_L1) / max(bid_qty_L1 + ask_qty_L1, eps)`

One channel.

### T02 — MULTISCALE_DEPTH_IMBALANCE_PATH

Per bin, cumulative depth imbalance at exact levels:

- L1
- L5
- L10
- L20

Four channels.

For cumulative level L:

`(sum_bid_qty_1:L - sum_ask_qty_1:L) / max(sum_bid + sum_ask, eps)`

### T03 — MICROPRICE_DISPLACEMENT_PATH

Per bin:

1. L1 microprice-minus-mid in basis points
2. generalized L5 microprice-minus-mid in basis points
3. generalized L10 microprice-minus-mid in basis points
4. generalized L20 microprice-minus-mid in basis points

Four channels.

No interaction expansion.

### T04 — MLOFI_TOP10_PATH

Per bin, exact stationary signed multilevel order-flow values at ranks 1..10.

Ten channels.

The signed-flow convention must be inherited from the frozen E1A stationary
order-flow implementation.

### T05 — EVENT_PRESSURE_8CLASS_PATH

Eight exact event classes:

- BI
- BD
- BR
- BP
- AI
- AD
- AR
- AP

For each class within each one-second bin:

`class_qty_share = sum(abs(dq)_class) / max(sum(abs(dq)_all_classes), eps)`

Eight channels.

### T06 — EVENT_ACTIVITY_8CLASS_PATH

For the same eight event classes, per bin:

`class_count_share = class_event_count / max(all_event_count, 1)`

Eight channels.

This separates event frequency from event quantity pressure.

### T07 — BOOK_GEOMETRY_PATH

Per one-second bin:

1. bid top-10 depth slope
2. ask top-10 depth slope
3. bid-vs-ask slope difference
4. near-vs-far convexity imbalance
5. mean bid inter-level gap
6. mean ask inter-level gap

Six channels.

Exact slope/gap definitions must be inherited from the already-frozen E1A
book-geometry formulas; no new fitted geometry parameters.

### T08 — RESILIENCE_STATE_PATH

Per one-second bin:

1. bid-side depth recovery state
2. ask-side depth recovery state
3. bid recovery minus ask recovery
4. spread recovery state

Four channels.

Exact depletion/recovery event definitions must be inherited from the frozen
E1A/DEV032 resilience lineage.

## 6. Three temporal windows

For each T01..T08, materialize:

- W08 = 8 bins
- W16 = 16 bins
- W32 = 32 bins

One bin = one causal second.

Bin ordering is frozen:

- position 0 = newest completed causal one-second bin
- final position = oldest bin in the candidate window

No future/partial post-decision event enters a bin.

## 7. Exact 24 candidate IDs

### 8-second additions

- G2C01 = P3 + T01_W08
- G2C02 = P3 + T02_W08
- G2C03 = P3 + T03_W08
- G2C04 = P3 + T04_W08
- G2C05 = P3 + T05_W08
- G2C06 = P3 + T06_W08
- G2C07 = P3 + T07_W08
- G2C08 = P3 + T08_W08

### 16-second additions

- G2C09 = P3 + T01_W16
- G2C10 = P3 + T02_W16
- G2C11 = P3 + T03_W16
- G2C12 = P3 + T04_W16
- G2C13 = P3 + T05_W16
- G2C14 = P3 + T06_W16
- G2C15 = P3 + T07_W16
- G2C16 = P3 + T08_W16

### 32-second additions

- G2C17 = P3 + T01_W32
- G2C18 = P3 + T02_W32
- G2C19 = P3 + T03_W32
- G2C20 = P3 + T04_W32
- G2C21 = P3 + T05_W32
- G2C22 = P3 + T06_W32
- G2C23 = P3 + T07_W32
- G2C24 = P3 + T08_W32

Candidate order is immutable.

## 8. Representation construction

For each candidate:

`X_candidate = [ X_P3_PRICE32 , flatten(raw_temporal_addition) ]`

P3 columns always come first.

Temporal addition is flattened in deterministic order:

1. newest bin to oldest bin
2. within each bin, channel order exactly as defined above

No feature deletion.

No PCA/SVD.

No candidate-specific interactions.

No learned embedding.

## 9. Model lineage

All 24 candidates use exactly the same model family as the successful P3 base:

- StandardScaler fit train-only
- LogisticRegression
- solver = lbfgs
- l1_ratio = 0.0
- class_weight = None
- max_iter = 1000
- fit_intercept = True
- random_state = 20260825

C grid remains exactly:

`0.01, 0.1, 1.0, 10.0`

C selection remains chronological and train-only using the frozen P3 fold
semantics.

This group tests information-layer value, not model-family multiplication.

## 10. Base reproduction gate

Before any G2 candidate can be interpreted, the implementation must reproduce
the frozen P3 selected base exactly:

- candidate identity A / 120 s / 16 bp / 32 s / PRICE
- four outer-fold prediction hashes
- four selected C values
- pooled balanced accuracy
- pooled macro F1
- pooled MCC
- pooled ROC AUC diagnostic

All exact hashes/C values must match.
Floating metrics must match within absolute tolerance 1e-15.

A reproduction mismatch invalidates G2 before candidate interpretation.

## 11. Primary benchmark

Because P3 was selected under its preregistered balanced-accuracy protocol,
the primary incremental endpoint remains:

`delta_BA = BA(candidate) - BA(P3_base)`

ROC AUC is retained as a diagnostic, not silently substituted as the primary
benchmark.

For each candidate record:

- pooled BA
- pooled macro F1
- pooled MCC
- pooled ROC AUC diagnostic
- four fold BAs
- four fold delta_BA vs P3
- four LOO pooled delta_BA values
- predicted minority fraction
- both-classes-predicted per fold

## 12. Joint multiplicity-controlled temporal null

Exactly 1999 replicates.

Seed:

`20260902`

For each replicate:

- apply one legal circular label shift independently within each of the four
  validation folds;
- use the same four shifts for the P3 base and all 24 candidates;
- keep all fitted probabilities/predictions fixed;
- compute shifted BA(candidate) - BA(P3) for every candidate;
- retain the maximum delta across all 24 candidates.

Store:

- all 1999 four-fold shift tuples
- all 24 candidate-specific null vectors
- max-stat null vector
- per-candidate raw plus-one p
- per-candidate max-stat FWER plus-one p
- q95 using empirical higher quantile
- observed-minus-q95

Artifact-completeness tests must explicitly fail if any candidate-specific null
vector is missing. This permanently addresses the E2B retention deviation.

## 13. G2 strong incremental survivor gate

A candidate is `G2_LAYER_SURVIVOR` only if ALL:

1. pooled BA(candidate) > pooled BA(P3)
2. pooled BA(candidate) >= 0.54
3. pooled delta_BA >= +0.02
4. >=3/4 fold delta_BA vs P3 are positive
5. >=3/4 candidate fold BA > 0.50
6. both classes predicted in every fold
7. pooled predicted-minority fraction >= 0.10
8. all four LOO pooled delta_BA values > 0
9. observed delta_BA > joint 24-candidate max-stat q95
10. max-stat FWER p <= 0.05
11. all support/provenance/causality/finiteness/reproduction guards PASS

These retain the spirit and thresholds of the frozen P3 success protocol while
making the comparison explicitly incremental to the already-successful base.

## 14. Inconclusive / rejected labels

`G2_LAYER_INCONCLUSIVE` only if:

- pooled delta_BA > 0
- >=3/4 positive fold deltas
- all four LOO delta_BA values > 0

but one or more strong-survivor gates fail.

Otherwise:

`G2_LAYER_REJECTED`

No inconclusive candidate becomes the next base.

## 15. Advancement

At most three G2 survivors may advance.

At most one candidate per T01..T08 information family.

If multiple windows from the same family survive, rank within that family by:

1. smaller max-stat FWER p
2. larger minimum fold delta_BA
3. larger median fold delta_BA
4. larger pooled delta_BA
5. shorter window

No weak slot filling.

If survivors from different families are sufficiently distinct, the next
layered base-composition design may test their union under a separately frozen
experiment. They are not automatically concatenated after G2.

## 16. Stage split

### DEV033-G2A

Materialization only:

- exact P3 support
- exact P3 labels
- exact 24 raw temporal additions
- daily hashes
- campaign hashes
- all finite
- no model
- no metric
- no null
- no PnL

### DEV033-G2B

Predictive layer screen only after G2A is frozen and read-only verified.

## 17. Stop / next-group rule

If G2 has one or more true survivors:

- only true survivors may inform the next base;
- freeze the winning layer(s);
- next group is added on top of a separately frozen successful composition.

If G2 has zero true survivors:

- retain DEV030-P3 unchanged as the direction base;
- do not promote the highest G2 failure;
- move to the next distinct candidate group on the same P3 base.

This is the permanent layered-search rule.

## 18. Forward/economic guards

Remain closed:

- Aug-01 analytical opening
- Aug-30 analytical opening
- Sep-01+
- Railway
- market-raw-archive
- abundant-love
- new acquisition/download
- PnL
- threshold optimization
- calibration rescue
- feature subset search
- alternate model-family search

Current state:

`DEV033_G2_DESIGN_FROZEN_G2A_FORMULA_IMPLEMENTATION_NEXT`
