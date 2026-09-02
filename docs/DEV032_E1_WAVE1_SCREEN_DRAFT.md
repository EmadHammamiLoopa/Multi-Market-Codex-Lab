# DEV032-E1 — Wave-1 Broad Historical Microstructure Screen Draft

Status: `DRAFT_FROM_E0_CENSUS_NO_MODEL_FIT_YET`

This document freezes the intended 36-strategy composition conceptually.
Implementation details, exact feature formulas, hashing, tests, and execution
commit require a subsequent implementation freeze before any real E1 fit.

## Fixed scientific task

Unless invalidated before execution:
- BTCUSDT
- consumed Jan-Jul 2026 development sandbox only
- T1 DIRECTION_GIVEN_TOUCH
- target A
- 120 s horizon
- 16 bp first-passage barrier
- 32 s causal information window
- exact four chronological folds:
  - Jan-Mar -> Apr
  - Jan-Apr -> May
  - Jan-May -> Jun
  - Jan-Jun -> Jul
- exact frozen first-passage/executable semantics
- no Aug-01
- no Aug-30
- no Sep-01+
- no Railway/archive/abundant-love

## Wave-1 strategy universe — exactly 36

### Controls

- S00 PRICE23 — exact frozen P3 baseline.
- S01 EVENT_DEPTH26 only — isolates the P1A event/depth block.
- S02 PRICE23 + EVENT_DEPTH26 — exact P1B representation.
- S03 AGG_PRICE_BOOK — frozen aggregated price+book snapshot control.

### Queue/depth imbalance

- S04 L1_QUEUE_IMBALANCE — raw best bid/ask queue imbalance.
- S05 MULTIDEPTH_OBI_VECTOR — cumulative OBI at fixed L1/L2/L3/L5/L10/L20/L50.
- S06 DISTANCE_WEIGHTED_OBI — inverse-distance weighted bid/ask liquidity imbalance.
- S07 LOG_DEPTH_RATIO_VECTOR — signed log bid-depth/ask-depth ratios at fixed levels.

### Microprice / fair-value pressure

- S08 GENERALIZED_MULTILEVEL_MICROPRICE — cumulative-depth generalized microprice.
- S09 SPREAD_NORMALIZED_MICROPRICE — generalized microprice displacement divided by spread.
- S10 MICROPRICE_EVENT_VELOCITY — causal event-time microprice displacement velocity summaries.

### Multi-level / stationary order flow

- S11 RAW_MLOFI_TOP10 — raw level-indexed MLOFI vector top 10.
- S12 RAW_MLOFI_TOP20 — raw level-indexed MLOFI vector top 20.
- S13 DISTANCE_BUCKET_MLOFI — raw MLOFI in fixed 0-5/5-15/15-50/>50 bp buckets.
- S14 DEPTH_NORMALIZED_MLOFI — level flow normalized by contemporaneous local depth.
- S15 STATIONARY_STANDARDIZED_ORDER_FLOW — fixed raw flow vector standardized train-only.

### Book shape / geometry

- S16 BOOK_SLOPE_L10 — separate bid/ask depth slope top 10.
- S17 BOOK_SLOPE_L50 — separate bid/ask depth slope top 50.
- S18 SLOPE_IMBALANCE_CONVEXITY — ask-vs-bid slope imbalance + near/far convexity.
- S19 PRICE_GAP_ASYMMETRY — first gaps and mean inter-level gap asymmetry.
- S20 DEPTH_CENTROID_ENTROPY — side-specific depth centroid + normalized entropy.

### Event-type pressure

- S21 NEAR_DEEP_EVENT_PRESSURE — insert/delete/replenish/deplete pressure split near vs deep.
- S22 EVENT_TYPE_RATIOS — add/cancel and replenish/deplete ratios by side.
- S23 NET_LIQUIDITY_CREATION — signed liquidity creation/destruction rates.
- S24 EVENT_TRANSITION_MATRIX — fixed low-dimensional event-type transition probabilities.

### Event timing / activity

- S25 INTERARRIVAL_MOMENTS — mean/std/CV of event inter-arrival times by side/type.
- S26 BURSTINESS_FANO — event burstiness and Fano-factor block.
- S27 MULTISCALE_INTENSITY_RATIOS — fixed 1s/16s and 4s/32s event-intensity ratios.
- S28 TIME_SINCE_LAST_EVENTS — time since last insert/delete/replenish/deplete by side.

### Hawkes/excitation-inspired fixed features

- S29 EXPONENTIAL_EVENT_INTENSITIES — fixed causal exponential-decay event intensities.
- S30 ADD_CROSS_EXCITATION — fixed bid-add/ask-add self-vs-cross excitation contrasts.
- S31 DELETE_DEPLETE_EXCITATION — fixed delete/deplete self-vs-cross excitation contrasts.

These are deterministic Hawkes-inspired features in Wave 1, not fitted full
Hawkes models. Fitted Hawkes/neural Hawkes are reserved for later refinement if
the family survives.

### Resilience

- S32 DEPTH_RECOVERY — causal depth recovery after depletion/deletion shocks.
- S33 SPREAD_QUEUE_RESILIENCE — spread recovery and best-queue refill asymmetry.

### Raw stationary sequence

- S34 STATIONARY_FLOW_MLP — fixed stationary raw order-flow sequence + small MLP.
- S35 STATIONARY_FLOW_TCN — same frozen sequence information + compact 1D TCN.

No PRICE-only sequence model is reopened. P8/P9/P10 remain terminal.

## Model policy

For S00-S33:
- StandardScaler fit on training only;
- L2 LogisticRegression;
- same fixed C grid;
- same chronological inner selection;
- probability-first C selection retained for fit stability;
- no threshold optimization.

For S34:
- one fixed small MLP architecture only.

For S35:
- one fixed compact TCN architecture only.

No HGB/XGBoost/Transformer model multiplication in E1.

## Primary screening endpoint

The E1 scientific target is directional ranking/discrimination.

Primary:
- pooled OOF ROC AUC.

Primary incremental statistic:
- pooled AUC(candidate) - pooled AUC(S00).

Stability diagnostics:
- fold AUC;
- number of positive fold AUC deltas vs S00;
- leave-one-fold-out pooled AUC deltas;
- worst-fold AUC.

Probability diagnostics are retained:
- log loss;
- Brier;
- BA at 0.5;
- macro-F1;
but E1 is not a probability-calibration promotion experiment.

## Max-stat multiple-testing control

For each preregistered eligible temporal-label shift:
1. apply the identical within-validation-day shift to labels;
2. keep candidate predictions fixed;
3. calculate AUC delta versus S00 for all eligible non-control strategies;
4. retain the maximum AUC delta across the full Wave-1 candidate set.

This produces a family-wise null distribution of the best result obtainable
from the entire screen by chance.

For each candidate record:
- observed pooled AUC delta;
- raw temporal-null p;
- max-stat family-wise empirical p;
- q95 of the max-stat null.

No candidate can be called a strong screening survivor solely because its
uncorrected p-value is <= .05.

## Screening-survivor gates

A non-control candidate is a STRONG_SCREENING_SURVIVOR only if all are true:
1. pooled AUC > S00 pooled AUC;
2. pooled AUC >= 0.56;
3. >= 3/4 fold AUC deltas vs S00 are positive;
4. every leave-one-fold-out pooled AUC delta vs S00 is positive;
5. observed pooled AUC delta > q95 of Wave-1 max-stat temporal null;
6. family-wise empirical p <= 0.05;
7. all causality/support/provenance invariants pass.

Candidates missing only max-stat significance but showing stable ranking may be
SCREENING_INCONCLUSIVE rather than promoted.

Everything else is SCREENING_REJECTED.

## Important interpretation

Even STRONG_SCREENING_SURVIVOR is exploratory because Wave 1 is evaluated on
consumed BTC Jan-Jul development outcomes.

At most the best three scientifically distinct survivor mechanisms may advance
to refinement/replication.

No E1 result can:
- consume Sep-01+;
- claim deployability;
- claim profitability;
- trigger PnL;
- retroactively change DEV031-P1B;
- justify feature deletion based on E1 outcomes.

## Wave 2 rule

Wave 2 is opened only for families with at least one stable E1 survivor or
scientifically interesting near-survivor.

Wave 2 hard cap: 24 strategies.

Every Wave-2 candidate is explicitly labeled adaptive/exploratory.

## Wave 3 rule

Wave 3 hard cap: 12 finalists.

After Wave 3, BTC Jan-Jul search closes regardless of outcome.

Top 1-3 frozen mechanisms then require independent historical replication before
any forward holdout.
