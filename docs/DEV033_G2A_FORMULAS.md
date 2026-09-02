# DEV033-G2A — Exact Raw-Temporal Formula Contract v1

Status: `FORMULAS_FROZEN_BEFORE_IMPLEMENTATION`

Date: 2026-09-02

Parent design:
`docs/DEV033_G2_LAYERED_TEMPORAL_GROUP_DESIGN.md`

## 1. Time convention

For decision timestamp `t` and candidate window W in {8,16,32} seconds,
define bins:

`B_k = (t-(k+1)s, t-k s]`

for:

`k = 0,1,...,W-1`

Therefore:

- k=0 is the newest one-second bin;
- k=W-1 is the oldest bin;
- the decision-time event/state may be included;
- nothing with timestamp > t is ever included.

Flatten order is immutable:

1. k=0 to W-1
2. channel order within each bin

## 2. Snapshot-state sampling convention

Families T01, T02, T03, T07, and the state components of T08 require an order
book state at each bin endpoint:

`e_k = t - k s`

The sampled state is the latest valid post-group book state with timestamp
`<= e_k`.

The sampled state must be derived by replaying the same frozen raw incremental
book semantics used by DEV032-E1A:

- snapshot resets book;
- grouped rows share timestamp;
- event classification is based on the pre-group book;
- state sampling occurs only after the full timestamp group has been applied;
- at least 50 valid levels per side are retained for families requiring them.

No interpolation.

No backward use of a state with timestamp > endpoint.

If no valid causal state exists for any required endpoint on an otherwise
frozen P3 support row, G2A fails closed rather than shrinking support.

## 3. Common helpers

For nonnegative x,y:

`imb(x,y) = (x-y)/(x+y)`

when x+y > 0, otherwise 0.

Mid:

`mid = (best_bid + best_ask)/2`

Basis-point displacement:

`bps(p) = 10000*(p-mid)/mid`

All denominators use the frozen positive epsilon convention only where the
existing lineage requires it.

## 4. T01 — L1_QUEUE_IMBALANCE_PATH

At every endpoint state:

`q_bid = best_bid_qty`
`q_ask = best_ask_qty`

Channel:

`T01 = imb(q_bid,q_ask)`

Channels per bin: 1.

Widths:

- W08 = 8
- W16 = 16
- W32 = 32

## 5. T02 — MULTISCALE_DEPTH_IMBALANCE_PATH

Exact cumulative levels:

`L = {1,5,10,20}`

At each endpoint state:

`B_L = sum(bid_qty[1:L])`
`A_L = sum(ask_qty[1:L])`

Channel:

`I_L = imb(B_L,A_L)`

Channel order:

1. L1
2. L5
3. L10
4. L20

Channels per bin: 4.

Widths:

- W08 = 32
- W16 = 64
- W32 = 128

This is the same cumulative-depth imbalance definition used in
`dev032_e1a_feature_core.cumulative_depth_imbalance`.

## 6. T03 — MICROPRICE_DISPLACEMENT_PATH

Exact levels:

`L = {1,5,10,20}`

For each L:

`B = cumulative bid quantity through L`
`A = cumulative ask quantity through L`
`den = A+B`

Generalized microprice:

`micro_L = (best_ask*B + best_bid*A)/den`

if den>0; otherwise mid.

Channel:

`micro_disp_L_bps = 10000*(micro_L-mid)/mid`

Channel order:

1. L1
2. L5
3. L10
4. L20

Channels per bin: 4.

Widths:

- W08 = 32
- W16 = 64
- W32 = 128

This inherits the exact generalized-microprice semantics frozen in E1A.

## 7. Frozen event classification for T04/T05/T06

Every eligible incremental-book row inside a complete timestamp group is
classified from pre-group old quantity and row new quantity.

Eight-class alphabet:

- BI: bid insert, old=0 and new>0
- BD: bid delete, old>0 and new=0
- BR: bid replenish, old>0 and new>old
- BP: bid partial depletion, old>new>0
- AI: ask insert
- AD: ask delete
- AR: ask replenish
- AP: ask partial depletion

For event e:

`dq = new_qty - old_qty`
`absdq = abs(dq)`

Rank is the frozen insertion rank against the pre-group side.

Only events with valid pre-group state are eligible.

## 8. T04 — MLOFI_TOP10_PATH

For every bin and level rank j in 1..10:

`signed_dq_e = +dq_e` for bid-side events

`signed_dq_e = -dq_e` for ask-side events

Then:

`num_j = sum(signed_dq_e for events of rank j in bin)`

`den_j = sum(absdq_e for events of rank j in bin)`

`T04_j = num_j / den_j`

when den_j>0, else 0.

This follows the frozen E1A stationary signed-flow convention while retaining
one-second temporal position instead of collapsing across the full 32 seconds.

Channel order:

rank 1 through rank 10.

Channels per bin: 10.

Widths:

- W08 = 80
- W16 = 160
- W32 = 320

## 9. T05 — EVENT_PRESSURE_8CLASS_PATH

For every bin:

`D = sum(absdq_e for all eight eligible classes in bin)`

For each class c:

`T05_c = sum(absdq_e for class c in bin)/D`

if D>0, else 0.

Channel order:

BI, BD, BR, BP, AI, AD, AR, AP.

Channels per bin: 8.

Widths:

- W08 = 64
- W16 = 128
- W32 = 256

## 10. T06 — EVENT_ACTIVITY_8CLASS_PATH

For every bin:

`N = count(all eligible classified events in bin)`

For class c:

`T06_c = count(class c events in bin)/N`

if N>0, else 0.

Channel order:

BI, BD, BR, BP, AI, AD, AR, AP.

Channels per bin: 8.

Widths:

- W08 = 64
- W16 = 128
- W32 = 256

T05 and T06 intentionally distinguish quantity pressure from event frequency.

## 11. T07 — BOOK_GEOMETRY_PATH

At each endpoint state compute the following exact six channels.

First, frozen top-10 book slopes.

For side distances in basis points from mid and quantities q:

`slope = OLS(distance_bps, log1p(q))`

Channels 1-2:

1. bid_slope_L10
2. ask_slope_L10

Channel 3:

`bid_slope_L10 - ask_slope_L10`

For convexity, inherit the frozen near/far depth-ratio convention:

`bid_near_far = sum(bid_qty[1:10]) / sum(bid_qty[1:50])`

`ask_near_far = sum(ask_qty[1:10]) / sum(ask_qty[1:50])`

Channel 4:

`bid_near_far - ask_near_far`

Inter-level gaps in basis points:

bid:

`10000*(bid_price_i-bid_price_{i+1})/mid`

ask:

`10000*(ask_price_{i+1}-ask_price_i)/mid`

Channels 5-6:

5. mean bid gap over first 9 gaps
6. mean ask gap over first 9 gaps

Channels per bin: 6.

Widths:

- W08 = 48
- W16 = 96
- W32 = 192

## 12. T08 — RESILIENCE_STATE_PATH

T08 inherits frozen E1A shock semantics.

### Depth shock definition

An eligible top-5 removal/depletion event is a depth shock when:

- class in {BD,BP,AD,AP}
- old quantity > 0
- removed quantity >= 25% of old quantity

For each side, retain the most recent depth shock not older than 32 seconds.

Let:

- D0 = side top-10 cumulative depth at shock pre-state
- Dmin = minimum side top-10 depth observed within first 1 second after shock
- Dt = current side top-10 depth at endpoint

Recovery:

`R = (Dt-Dmin)/max(D0-Dmin,eps)`

clipped to [-1,2].

If no eligible prior shock exists, recovery = 0.

### Spread recovery definition

A spread shock occurs when post-group spread satisfies both:

- post_spread >= 1.25 * pre_spread
- post_spread - pre_spread >= 0.5 bp

For the most recent spread shock <=32 seconds old:

- Spre = pre-shock spread
- Sshock = shock spread
- St = current spread

`SR = (Sshock-St)/max(Sshock-Spre,eps)`

clipped to [-1,2].

If none exists, SR=0.

### T08 channels

At each endpoint:

1. bid_depth_recovery
2. ask_depth_recovery
3. bid_depth_recovery - ask_depth_recovery
4. spread_recovery

Channels per bin: 4.

Widths:

- W08 = 32
- W16 = 64
- W32 = 128

## 13. Candidate width contract

Added-layer widths:

| Family | W08 | W16 | W32 |
|---|---:|---:|---:|
| T01 | 8 | 16 | 32 |
| T02 | 32 | 64 | 128 |
| T03 | 32 | 64 | 128 |
| T04 | 80 | 160 | 320 |
| T05 | 64 | 128 | 256 |
| T06 | 64 | 128 | 256 |
| T07 | 48 | 96 | 192 |
| T08 | 32 | 64 | 128 |

The P3 base width is not redefined here.
G2A materializes only the added layer plus exact P3 support/labels/provenance.

G2B later reconstructs:

`P3 base + G2A added layer`

## 14. Materialization identity

G2A must store for every one of the 24 candidates:

- immutable candidate ID
- family ID
- window
- channel names
- flattened feature names
- feature count
- daily matrix SHA256
- campaign matrix SHA256

Support and labels must match the exact selected P3 candidate support.

## 15. Prohibitions

G2A must not:

- fit StandardScaler
- fit LogisticRegression
- compute BA/AUC/F1/MCC
- run nulls
- access Sep-01+
- access Railway/archive/abundant-love
- run PnL
- change P3 support
- use DEV032 winners/failures to alter formulas

Current state:

`DEV033_G2A_FORMULAS_FROZEN_IMPLEMENTATION_NEXT`
