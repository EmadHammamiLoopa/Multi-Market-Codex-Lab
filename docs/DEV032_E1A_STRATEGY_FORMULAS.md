# DEV032-E1A — Frozen Strategy Formula Specification

Status: `FORMULA_FREEZE_BEFORE_IMPLEMENTATION_OR_REAL_DATA_ACCESS`

Experiment stage:
`DEV032-E1A`

Purpose:
define exact deterministic feature mathematics for the 36 Wave-1 strategies
before any DEV032 real-data extraction or predictive fitting.

## Common causal state

At a decision time `t`, the reconstructed L2 book is the post-group book after
all raw rows with `local_timestamp <= t` have been applied atomically by equal
local_timestamp groups.

Raw event features use only non-snapshot groups whose pre-group book is already
valid, exactly following DEV031-P1A semantics.

For an event at price `p`:
- `q_old` = quantity before the update;
- `q_new` = update amount;
- `dq = q_new - q_old`;
- bid signed quantity change = `+dq`;
- ask signed quantity change = `-dq`;
- distance in bp is measured to the valid pre-group mid.

Snapshot rows reset/rebuild state and are never counted as market-event flow.

All rolling windows are inclusive at the right endpoint:
`t-W <= event_time <= t`.

No future group is consumed.

## Shared conventions

For bid levels:
`(b_i, q^b_i)`, i=1 is best bid.

For ask levels:
`(a_i, q^a_i)`, i=1 is best ask.

`mid = (b_1 + a_1)/2`
`spread = a_1 - b_1`

For any nonnegative pair B,A:
`imb(B,A) = (B-A)/(B+A)` when B+A>0, else 0.

For any positive pair B,A:
`log_ratio(B,A) = log((B+eps)/(A+eps))`
with frozen `eps = 1e-12`.

For all fixed-size level strategies, insufficient simultaneous depth is
feature-invalid. No zero padding of missing book levels.

## Strategy definitions

### S00 PRICE23
Exact frozen P3 PRICE23 matrix from DEV031-P1A. No recomputation.

### S01 EVENT_DEPTH26
Exact frozen DEV031-P1A EVENT_DEPTH26 matrix. No recomputation.

### S02 PRICE23 + EVENT_DEPTH26
Exact concatenation S00 then S01.

### S03 AGG_PRICE_BOOK
Fixed aggregated snapshot control using:
- spread_bps
- microprice_minus_mid_bps
- obi_l1
- obi_l5
- obi_l10
- log_bid_qty_l1
- log_ask_qty_l1
- log_bid_depth_l5
- log_ask_depth_l5
- log_bid_depth_l10
- log_ask_depth_l10
all at decision time, plus causal 250ms mid log return.

Exact S03 feature count = 12.

### S04 L1_QUEUE_IMBALANCE
One feature:
`imb(q^b_1, q^a_1)`.

### S05 MULTIDEPTH_OBI_VECTOR
Seven features:
cumulative depth imbalance at
L={1,2,3,5,10,20,50}.

For L:
`B_L=sum_{i<=L} q^b_i`
`A_L=sum_{i<=L} q^a_i`
feature = `imb(B_L,A_L)`.

### S06 DISTANCE_WEIGHTED_OBI
Two fixed weighted imbalances.

For each level:
`d_i = abs(price_i-mid)/mid * 10000`.

Inverse-distance weight:
`w_i = 1/(1+d_i)`.

Exponential-distance weight:
`v_i = exp(-d_i/10)`.

Features:
- inverse_distance_obi using top 50 each side;
- exp10bp_distance_obi using top 50 each side.

### S07 LOG_DEPTH_RATIO_VECTOR
Seven features for L={1,2,3,5,10,20,50}:
`log_ratio(B_L,A_L)`.

### S08 GENERALIZED_MULTILEVEL_MICROPRICE
Use cumulative top-L depth for L={1,5,10,20,50}.

`micro_L = (a_1*B_L + b_1*A_L)/(A_L+B_L)`

Feature:
`10000*(micro_L-mid)/mid`.

Five features.

### S09 SPREAD_NORMALIZED_MICROPRICE
Same five generalized microprice values as S08 divided by spread in bp.

If spread_bps <= 0, invalid.

### S10 MICROPRICE_EVENT_VELOCITY
Using generalized L10 microprice displacement `m(t)`, store valid event-group
observations over 32s.

Features:
- last-minus-first / elapsed_seconds;
- OLS slope versus elapsed seconds;
- 4s mean minus 32s mean;
- 1s mean minus 16s mean.

At least two valid event observations required.

### S11 RAW_MLOFI_TOP10
Ten level-indexed signed-flow features over 32s.

At each eligible raw event group, map the updated price to its pre-group same-side
rank among top 10. Accumulate signed quantity change:
bid +dq, ask -dq.

For each level j:
`sum signed_dq_j / sum abs(dq_j)`, zero denominator => 0.

### S12 RAW_MLOFI_TOP20
Same as S11 for top 20 levels.

### S13 DISTANCE_BUCKET_MLOFI
Four disjoint pre-group-mid distance buckets:
- [0,5] bp
- (5,15] bp
- (15,50] bp
- >50 bp

Each feature:
`sum signed_dq / sum abs(dq)` over 32s.

Unlike P1A cumulative 5/15/50bp bands, these are disjoint.

### S14 DEPTH_NORMALIZED_MLOFI
For each top-10 same-side pre-group level event:
`normalized_dq = dq / max(q_old, q_new, eps)`.

Signed bid +, ask -.

Aggregate by top-10 level over 32s using arithmetic mean of signed normalized dq
for each level; no events => 0.

Ten features.

### S15 STATIONARY_STANDARDIZED_ORDER_FLOW
Raw top-10 signed flow totals over four fixed horizons 1/4/16/32s.

40 raw features.

Standardization is NOT performed in the extractor.
The Wave-1 train-only StandardScaler supplies the stationary normalization.
No full-history z-score is allowed.

### S16 BOOK_SLOPE_L10
For each side separately fit OLS:
`log1p(q_i) = alpha + beta * distance_bp_i`
for top 10 levels.

Features:
- bid beta
- ask beta

### S17 BOOK_SLOPE_L50
Same as S16 on top 50.

### S18 SLOPE_IMBALANCE_CONVEXITY
Features:
- beta_bid_L20 - beta_ask_L20
- beta_bid_L50 - beta_ask_L50
- bid near/far convexity
- ask near/far convexity

Convexity:
`depth_top10 / depth_top50`.

### S19 PRICE_GAP_ASYMMETRY
Features:
- first_gap_bid_bp - first_gap_ask_bp
- second_gap_bid_bp - second_gap_ask_bp
- mean_gap_bid_top10_bp - mean_gap_ask_top10_bp
- mean_gap_bid_top50_bp - mean_gap_ask_top50_bp

Bid gaps use `b_i-b_{i+1}`; ask gaps use `a_{i+1}-a_i`.

### S20 DEPTH_CENTROID_ENTROPY
For each side top 50:
`w_i=q_i/sum q`.

Centroid:
`sum w_i * distance_bp_i`.

Normalized entropy:
`-sum w_i log(w_i) / log(50)`.

Features:
- bid centroid
- ask centroid
- centroid difference ask-bid
- bid entropy
- ask entropy
- entropy difference bid-ask.

### S21 NEAR_DEEP_EVENT_PRESSURE
Event types: insert, delete, replenish, deplete.
Regions:
- near <=5bp
- deep (5,50]bp

For each type/region use the same directional pressure convention as P1A:
- insert/replenish: (bid-ask)/(bid+ask)
- delete/deplete: (ask-bid)/(ask+bid)

8 features over 32s.

### S22 EVENT_TYPE_RATIOS
Counts over 32s.

Per side:
- cancel_to_add = delete/(insert+delete), denominator 0 =>0
- replenish_to_deplete = replenish/(replenish+deplete), denominator0=>0

Plus directional differences bid minus ask for each ratio.

6 features.

### S23 NET_LIQUIDITY_CREATION
Over 32s quantity-weighted:
- bid net = positive dq sum
- ask net = positive ask-side dq sum
where replenishment/insertion add liquidity and depletion/deletion remove it.

Represent:
- normalized bid net creation = sum dq_bid / sum abs(dq_bid)
- normalized ask net creation = sum dq_ask / sum abs(dq_ask)
- directional creation imbalance = imb(positive_bid_creation, positive_ask_creation)
- directional destruction imbalance = imb(ask_destroy, bid_destroy)
with zero denominators ->0.

### S24 EVENT_TRANSITION_MATRIX
Event alphabet:
`BI,BD,BR,BP,AI,AD,AR,AP`
where P=depletion.

Using chronological eligible event groups over 32s, classify each group by its
dominant event type using highest count; ties resolved by the frozen alphabet
order above.

Compute 8x8 transition counts, row-normalize, then emit exactly 16 contrasts:
for each of 8 source states:
- probability next event is bid-side minus ask-side;
- probability next event is liquidity-add (I/R) minus remove (D/P).

No outgoing transitions => both 0.

### S25 INTERARRIVAL_MOMENTS
For four directional event classes:
- bid add = insert+replenish
- bid remove = delete+deplete
- ask add
- ask remove

Over 32s compute inter-arrival intervals in seconds.

Per class:
- mean
- population std
- coefficient of variation std/mean

If fewer than 2 event times:
mean=32, std=0, CV=0.

12 features.

### S26 BURSTINESS_FANO
Same four directional classes.

Burstiness:
`B=(std_IA-mean_IA)/(std_IA+mean_IA)`, denominator0=>0.

Fano:
split 32s into eight fixed 4s bins;
`variance(counts)/mean(counts)`, mean0=>0.

8 features.

### S27 MULTISCALE_INTENSITY_RATIOS
For each of four directional event classes:
`intensity_W = count_W/W`.

Features per class:
- intensity_1s / (intensity_16s + eps)
- intensity_4s / (intensity_32s + eps)

Ratios are clipped at frozen maximum 32 to bound empty/near-empty instability.

8 features.

### S28 TIME_SINCE_LAST_EVENTS
For eight exact event classes BI,BD,BR,BP,AI,AD,AR,AP:
seconds since last event at or before t.

If absent in preceding 32s => 32.

8 features.

### S29 EXPONENTIAL_EVENT_INTENSITIES
For the same eight classes over 32s:
`I_tau(t)=sum exp(-(t-t_i)/tau)`.

Frozen tau values:
1s and 8s.

16 features.

No fitted Hawkes parameters.

### S30 ADD_CROSS_EXCITATION
Using S29 insert/replenish intensities.

Define for tau in {1s,8s}:
- bid_add_tau = BI_tau + BR_tau
- ask_add_tau = AI_tau + AR_tau

Exact six features:
1. imb(bid_add_1s, ask_add_1s)
2. imb(bid_add_8s, ask_add_8s)
3. bid_add_1s / (bid_add_8s + eps), clipped 32
4. ask_add_1s / (ask_add_8s + eps), clipped 32
5. (bid_add_1s-ask_add_1s) - (bid_add_8s-ask_add_8s)
6. (bid_add_1s+ask_add_1s) / (bid_add_8s+ask_add_8s+eps), clipped 32

6 features.

### S31 DELETE_DEPLETE_EXCITATION
Analogous to S30 using remove intensities:
- bid_remove_tau = BD_tau + BP_tau
- ask_remove_tau = AD_tau + AP_tau

Exact six features:
1. imb(ask_remove_1s, bid_remove_1s)  [upward-pressure convention]
2. imb(ask_remove_8s, bid_remove_8s)
3. bid_remove_1s / (bid_remove_8s + eps), clipped 32
4. ask_remove_1s / (ask_remove_8s + eps), clipped 32
5. (ask_remove_1s-bid_remove_1s) - (ask_remove_8s-bid_remove_8s)
6. (bid_remove_1s+ask_remove_1s) / (bid_remove_8s+ask_remove_8s+eps), clipped 32

6 features.

### S32 DEPTH_RECOVERY
Define a depletion shock on a side as an eligible delete/deplete event affecting a
pre-group top-5 level with removed quantity >=25% of q_old.

For the most recent shock in preceding 32s:
- pre-shock top10 side depth D0;
- minimum top10 depth within first 1s after shock Dmin;
- current top10 depth Dt.

Recovery fraction:
`(Dt-Dmin)/max(D0-Dmin,eps)`, clipped to [-1,2].

Features:
- bid recovery fraction
- ask recovery fraction
- seconds since bid shock (32 if none)
- seconds since ask shock.

If no shock on a side: recovery=0, seconds=32.

### S33 SPREAD_QUEUE_RESILIENCE
Spread shock:
spread widens by >=25% and >=0.5bp relative to previous eligible group.

For most recent shock <=32s:
- spread recovery = (shock_spread-current_spread)/
  max(shock_spread-pre_shock_spread,eps), clipped [-1,2].
- seconds since spread shock; 32 if none.

Queue refill shock:
best-side queue loses >=25% in one eligible group.

For most recent bid/ask queue shock:
- refill fraction = (current_q-best_postshock_q)/
  max(pre_shock_q-best_postshock_q,eps), clipped [-1,2].

Features:
- spread recovery
- seconds since spread shock
- bid queue refill
- ask queue refill.

### S34 STATIONARY_FLOW_TEMPORAL_SHAPE
Use the S15 top-10 signed level-flow vectors accumulated in four disjoint
lookback bands:
- (0,1]s
- (1,4]s
- (4,16]s
- (16,32]s

For each band and level j:
- signed_j = sum signed_dq assigned to pre-group level j;
- abs_total = sum absolute dq across levels 1..10 in that band;
- normalized_j = signed_j / abs_total when abs_total>0, else 0.

Thus each band forms one 10-level signed vector normalized by the band's total
absolute top-10 flow.

Emit:
- each band total signed imbalance (4)
- each band L1 norm (4)
- cosine similarity consecutive bands 1-4,4-16,16-32 (3)
- near-level (1-3) minus deep-level (8-10) signed flow per band (4)

15 features.

Zero vector cosine =>0.

### S35 EVENT_PRESSURE_TEMPORAL_SHAPE
For four event pressure classes:
insert, delete, replenish, deplete.

Compute directional pressure separately in four disjoint time bands:
(0,1],(1,4],(4,16],(16,32] seconds.

16 base features.

Add for each event type:
- short-minus-long pressure: band1 - band16_32
- OLS slope across band midpoints

8 additional features.

Total 24 features.

## Exact support contract

E1A must preserve the exact frozen DEV031-P1A T1 timestamps and labels:
- total 1,374
- LONG 684
- SHORT 690

No strategy may silently shrink support.

If a strategy cannot produce finite features for all exact P3 T1 rows, E1A
fails closed before any predictive fit.

No matched-subset rescue is allowed.

## Formula freeze rule

Any material formula change after this document is committed requires a new
DEV032 formula version before real extraction.

No formula may be changed after seeing E1 predictive results.


## Pre-implementation event-occurrence clarification

Frozen before any DEV032 real-data extraction:

1. For S22-S23 and S25-S31, each classified non-snapshot raw update row is one
   event occurrence. Multiple rows sharing one atomic local_timestamp are
   simultaneous events with identical event time.

2. S24 is intentionally group-level rather than row-level. Each eligible atomic
   local_timestamp group contributes at most one dominant event class. Groups
   with zero classified quantity-changing events contribute no transition
   state. Dominance is highest event count; ties follow the frozen alphabet
   BI,BD,BR,BP,AI,AD,AR,AP.

3. S33 best-queue shock semantics are side-specific:
   pre-group best-queue quantity is compared with the post-group current
   best-queue quantity on that side. A loss >=25% is a shock. This deliberately
   treats disappearance/replacement of the previous best level as a liquidity
   shock rather than requiring price-level identity.

These clarifications are formula semantics, not outcome-driven changes.


## Final pre-execution semantic corrections

Frozen before any DEV032 real-data extraction or predictive result:

1. Level rank for S11/S12/S14/S15/S34 is the **pre-group insertion rank** of
   the updated price on that side, not exact pre-existing price identity.
   Therefore a newly inserted price receives the rank position it would occupy
   in the unchanged pre-group side book. Rank > configured top-L is ignored.

2. The first disjoint age band for S34/S35 is `[0,1]s`, not `(0,1]s`.
   Events in the atomic group at decision timestamp t are causal and included,
   consistent with the global window rule `event_time <= t`.
   Remaining bands stay `(1,4]`, `(4,16]`, `(16,32]`.

3. S33 always uses the chronologically most recent eligible spread/queue shock.
   A true recovery value of exactly zero is a valid value and must not be used
   as a sentinel for “no shock found”.

These corrections are implementation/semantic consistency fixes discovered
before any DEV032 real-data extraction, model fit, or predictive metric.
