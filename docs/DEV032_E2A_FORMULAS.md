# DEV032-E2A — Frozen Formula Specification v1

Status: `FORMULA_FREEZE_BEFORE_E2A_IMPLEMENTATION_OR_REAL_DATA_ACCESS`

Date: 2026-09-02

Parent design:
`docs/DEV032_E2_WAVE2_ADAPTIVE_REFINEMENT_DESIGN.md`

Parent design commit:
`cdb6951c07db3c542c074cf4cb72f7a6aa280995`

## 1. Common state and support

Reuse DEV032-E1A causal book/event semantics exactly.

At decision time t:

- book state is post-group after all rows with local_timestamp <= t;
- snapshot rows rebuild state and are not event flow;
- raw event classification and signed dq conventions are inherited unchanged;
- causal lookback is 32 s;
- exact support must remain 1374 rows;
- LONG = 684;
- SHORT = 690;
- no matched-subset rescue;
- all deterministic materialized values must be finite.

E2A materializes deterministic raw features only.

Train-only transforms for E2R05/E2R06 are deferred to E2B and are NEVER fit
globally in E2A.

Use eps = 1e-12 wherever a positive denominator guard is required.

## 2. E2R01 — QUEUE_IMBALANCE_X_SPREAD_STATE

Source registry concept: B06.

Base queue imbalance:
use exact E1A S05 cumulative OBI values at
L={1,2,3,5,10,20,50}.

Spread state:
`spread_bps = 10000*(ask1-bid1)/mid`.

Emit exactly 14 features:

For each L:
1. `obi_L`
2. `obi_L * log1p(spread_bps)`

No spread binning, threshold search, or polynomial expansion.

## 3. E2R02 — QUEUE_IMBALANCE_EVENT_PERSISTENCE

Source registry concept: B07.

Use exact L1 queue imbalance at every valid eligible event group in [t-32s,t].

Let q_i be the chronological L1 queue-imbalance sequence and tau_i event times.

Emit exactly 6 features:

1. current q
2. mean(q_i)
3. population std(q_i)
4. fraction of q_i with same nonzero sign as current q
5. sign persistence = mean of indicator(sign(q_i)=sign(q_{i-1})) over adjacent
   pairs, zero if fewer than 2 observations
6. OLS slope of q_i versus age-seconds from first observation, zero if fewer
   than 2 distinct event times

If no historical event-group observations exist, use current q for features
1-2 and zeros for 3-6.

## 4. E2R03 — MICROPRICE_X_QUEUE_IMBALANCE

Source registry concept: C04.

Use exact E1A S09 spread-normalized generalized microprice at
L={1,5,10,20,50}.

Use exact E1A S05 cumulative OBI at the same depths
L={1,5,10,20,50}.

Emit exactly 10 features:

For each L:
1. spread-normalized microprice displacement
2. its product with OBI_L

No additional nonlinear transform.

## 5. E2R04 — MICROPRICE_ACCELERATION_CURVATURE

Source registry concept: C06.

Use generalized L10 microprice displacement m(t) in bp, same state definition as
E1A S10.

At valid eligible event-group observations in [t-32s,t], compute disjoint-band
means for:

- [0,1]s
- (1,4]s
- (4,16]s
- (16,32]s

Empty band mean = nearest older available band mean; if no observation exists in
the 32s window, use current m(t).

Let band means be m1,m4,m16,m32 from newest to oldest band.

Emit exactly 6 features:

1. m1-m4
2. m4-m16
3. m16-m32
4. (m1-m4) - (m4-m16)
5. (m4-m16) - (m16-m32)
6. OLS quadratic coefficient from fitting
   `m_band = a + b*x + c*x^2`
   at fixed band midpoints x={0.5,2.5,10,24} seconds.

No polynomial degree above 2.

## 6. E2R05 — TRAIN_ONLY_PCA_MLOFI

Source registry concept: D08.

E2A materializes the exact 20-dimensional raw top-20 MLOFI vector inherited
from E1A S12 for every support row.

No PCA is fit in E2A.

E2B fold pipeline:

1. StandardScaler fit on the outer-training rows only for the 20 raw MLOFI
   columns;
2. PCA fit on the scaled outer-training rows only;
3. fixed `n_components = 5`;
4. PCA solver = `full`;
5. no whitening;
6. transform outer validation using training-fitted scaler and PCA;
7. concatenate B00 PRICE23 first, then the 5 PCA scores;
8. apply the frozen LogisticRegression/C-selection lineage.

PCA component signs are deterministic for prediction because training and
validation use the same fitted transform; no post-fit sign normalization is
introduced.

## 7. E2R06 — TRAIN_ONLY_LOW_RANK_SVD_ORDER_FLOW

Source registry concept: D09.

E2A materializes the exact 40-dimensional raw stationary order-flow block
inherited from E1A S15.

No SVD is fit in E2A.

E2B fold pipeline:

1. StandardScaler fit on outer-training rows only for the 40 raw columns;
2. TruncatedSVD fit on scaled outer-training rows only;
3. fixed `n_components = 5`;
4. algorithm = `randomized`;
5. `n_iter = 7`;
6. `random_state = 20260902`;
7. transform validation with training-fitted scaler and SVD;
8. concatenate B00 PRICE23 first, then 5 SVD scores;
9. apply the frozen LogisticRegression/C-selection lineage.

No component-count tuning.

## 8. E2R07 — DEPTH_DISPERSION_WEIGHTED_VARIANCE

Source registry concept: E08.

At t, use top 50 bid and ask levels.

For each side:

- `w_i = q_i / sum(q)`
- `d_i = abs(price_i-mid)/mid*10000`
- centroid `mu = sum(w_i*d_i)`
- weighted variance `var = sum(w_i*(d_i-mu)^2)`
- weighted std `sd = sqrt(var)`

Emit exactly 6 features:

1. bid variance
2. ask variance
3. ask variance - bid variance
4. bid weighted std
5. ask weighted std
6. ask weighted std - bid weighted std

No higher moments.

## 9. E2R08 — EVENT_TYPE_RUN_LENGTH_PERSISTENCE

Source registry concept: F09.

Use the exact dominant-group event alphabet and tie rule from E1A S24:
BI,BD,BR,BP,AI,AD,AR,AP.

Across eligible event groups in [t-32s,t], derive chronological dominant states.

Map each state to directional pressure sign:

- BI, BR, AD, AP => +1
- AI, AR, BD, BP => -1

Emit exactly 8 features:

1. current dominant-state run length in number of groups
2. current directional-sign run length in groups
3. maximum directional-sign run length in 32s
4. mean directional-sign run length in 32s
5. fraction of adjacent transitions retaining same directional sign
6. fraction of groups with +1 pressure sign
7. normalized signed run imbalance =
   (sum positive-run lengths - sum negative-run lengths) /
   max(total run lengths,eps)
8. seconds since last directional sign change, clipped to [0,32]

If fewer than one eligible group: all zeros except feature 8 = 32.

## 10. E2R09 — SIGNED_EVENT_TIME_MOMENTUM

Source registry concept: G12.

Use the same four directional event classes as E1A S25:

- bid add
- bid remove
- ask add
- ask remove

Assign signs:

- bid add = +1
- ask remove = +1
- ask add = -1
- bid remove = -1

Each classified raw event row contributes its signed absolute quantity change
`s_i * abs(dq_i)`.

Compute over fixed horizons W={1,4,16,32}s:

`M_W = sum(s_i*abs(dq_i)) / max(sum(abs(dq_i)),eps)`.

Emit exactly 8 features:

1-4. M_1, M_4, M_16, M_32
5. M_1 - M_4
6. M_4 - M_16
7. M_16 - M_32
8. OLS slope of {M_1,M_4,M_16,M_32} against log2 horizons
   {0,2,4,5}

No horizon search.

## 11. E2R10 — SHOCK_CONDITIONED_RECOVERY_CURVE

Source registry concept: I06.

Use the exact depletion-shock definition from E1A S32:

- delete/deplete event;
- pre-group top-5 level;
- removed quantity >=25% of q_old.

For the most recent qualifying shock on each side within 32s, define top-10 side
depth D0 immediately pre-shock.

Sample post-shock recovery ratios at fixed causal elapsed horizons:

- h=1s
- h=4s
- h=16s
- current t

For a horizon h, use the most recent valid book state at or before shock_time+h
and no later than current t.

`R_h = (D_h - D_min_1s) / max(D0-D_min_1s,eps)`

where D_min_1s is the minimum top-10 depth in [shock,shock+1s] available by t.

Clip each R_h to [-1,2].

Per side emit:

1. R_1
2. R_4
3. R_16
4. R_current
5. OLS slope of available fixed-horizon recovery values versus
   x={1,4,16,32}, with current assigned x=min(seconds_since_shock,32)
6. seconds since shock, clipped [0,32]

If no shock: recovery values and slope = 0; seconds since shock = 32.

Total exactly 12 features, bid first then ask.

## 12. Parent-anchor mapping

Frozen parent mapping for E2B:

- E2R01 -> P07
- E2R02 -> P07
- E2R03 -> P09
- E2R04 -> P09
- E2R05 -> P13
- E2R06 -> P13
- E2R07 -> P17
- E2R08 -> P21
- E2R09 -> P35
- E2R10 -> P32

No parent remapping after E2 outcomes exist.

## 13. Materialization feature counts

Deterministic E2A output blocks:

- E2R01 = 14
- E2R02 = 6
- E2R03 = 10
- E2R04 = 6
- E2R05 raw input = 20
- E2R06 raw input = 40
- E2R07 = 6
- E2R08 = 8
- E2R09 = 8
- E2R10 = 12

Total raw E2A materialized columns:

`130`

PCA/SVD transformed scores are not part of the E2A global materialization
count because they are fit train-only inside E2B folds.

## 14. E2A prohibitions

E2A must not:

- fit LogisticRegression;
- compute AUC/logloss/Brier;
- run temporal nulls;
- fit PCA/SVD globally;
- inspect Sep-01+;
- open Railway/archive/abundant-love;
- run PnL;
- optimize thresholds;
- change support;
- alter E1A/E1B artifacts.

## 15. Formula freeze rule

Any material change to:

- feature definition;
- horizon;
- depth;
- interaction;
- PCA/SVD rank;
- PCA/SVD fitting rule;
- shock rule;
- run-length sign convention;
- parent mapping

after this document is committed requires a new DEV032-E2 formula version
before any E2A materialization.

No formula may be changed after E2 predictive outcomes exist.

Current state:

`DEV032_E2A_FORMULAS_FROZEN_IMPLEMENTATION_NEXT_NO_MODEL_FIT`
