# DEV032-E0 Candidate Registry v1

Status: `CANDIDATE_UNIVERSE_DRAFT_BEFORE_SCREENING`

Legend:
- CONTROL = prior/current comparator
- TESTED = materially tested already; not a novel E1 claim
- W1 = recommended Wave-1 representative
- LATER = retain for E2/E3 only if parent family survives
- EXCLUDE = duplicate, scientifically weak, or forbidden by current stop rules

## A. Controls / existing representations

| ID | Candidate | Status | Reason |
|---|---|---|---|
| A01 | PRICE23 frozen P3 baseline | CONTROL/W1 | mandatory anchor |
| A02 | EVENT_DEPTH26 only | CONTROL/W1 | isolates event/depth block |
| A03 | PRICE23 + EVENT_DEPTH26 | CONTROL/W1 | exact P1B representation |
| A04 | aggregated PRICE_BOOK snapshot block | TESTED/W1 | historical control |
| A05 | aggregated PRICE_BOOK_FLOW block | TESTED | prior MLOFI/OFI family |
| A06 | full aggregated Phase0DL block | TESTED | prior information family |

## B. Queue / depth imbalance

| ID | Candidate | Status |
|---|---|---|
| B01 | best-queue imbalance raw L1 | W1 |
| B02 | cumulative OBI vector L1/L2/L3/L5/L10/L20/L50 | W1 |
| B03 | distance-weighted OBI with inverse-bp weights | W1 |
| B04 | exponential-distance weighted OBI | W1 |
| B05 | signed log depth-ratio vector by level | W1 |
| B06 | queue-imbalance × spread-state interaction | LATER |
| B07 | queue-imbalance persistence over event time | LATER |
| B08 | local nonlinear/spline transform of L1 queue imbalance | LATER |

## C. Microprice / fair-value pressure

| ID | Candidate | Status |
|---|---|---|
| C01 | existing microprice-minus-mid | TESTED |
| C02 | multi-level generalized microprice using cumulative depth | W1 |
| C03 | microprice displacement normalized by spread | W1 |
| C04 | microprice displacement × queue imbalance | LATER |
| C05 | microprice event-time slope / velocity | W1 |
| C06 | microprice acceleration / curvature | LATER |

## D. Multi-level order-flow / stationary order flow

| ID | Candidate | Status |
|---|---|---|
| D01 | aggregated MLOFI L5/L10 historical | TESTED |
| D02 | raw level-indexed MLOFI vector top 10 | W1 |
| D03 | raw level-indexed MLOFI vector top 20 | W1 |
| D04 | raw price-distance MLOFI vector 0-5/5-15/15-50/>50bp | W1 |
| D05 | depth-normalized MLOFI vector | W1 |
| D06 | signed sqrt-volume normalized flow vector | W1 |
| D07 | z-scored stationary order-flow vector using train-only history | W1 |
| D08 | principal components of level-wise MLOFI fit train-only | LATER |
| D09 | low-rank SVD stationary order flow fit train-only | LATER |
| D10 | OFI decay-profile ratios short/medium/long | LATER |

## E. Book shape / geometry

| ID | Candidate | Status |
|---|---|---|
| E01 | bid/ask depth slope top 10 levels | W1 |
| E02 | bid/ask depth slope top 50 levels | W1 |
| E03 | slope imbalance ask-vs-bid | W1 |
| E04 | convexity near-vs-far depth | W1 |
| E05 | first-gap / second-gap asymmetry | W1 |
| E06 | mean inter-level price gap asymmetry | W1 |
| E07 | depth centroid distance from mid | W1 |
| E08 | depth dispersion / weighted variance | LATER |
| E09 | entropy of depth distribution by side | W1 |
| E10 | Theil/Gini concentration by side | LATER |
| E11 | cost-of-immediacy / virtual market impact for fixed notional | LATER |
| E12 | shape-regime interactions (slope × convexity × spread) | LATER |

## F. Event-type pressure and asymmetry

| ID | Candidate | Status |
|---|---|---|
| F01 | aggregate insert/delete/replenish/deplete pressure 32s | TESTED |
| F02 | event-type pressure split near 5bp vs 5-50bp | W1 |
| F03 | event-type pressure split top-book vs deep-book levels | W1 |
| F04 | insertion/deletion ratio by side | W1 |
| F05 | replenish/deplete ratio by side | W1 |
| F06 | cancellation-to-addition imbalance | W1 |
| F07 | net liquidity creation/destruction rate | W1 |
| F08 | event-type transition matrix summary | W1 |
| F09 | event-type run lengths / sign persistence | LATER |
| F10 | event-type surprise relative to rolling historical rate | LATER |

## G. Event timing / intensity / burstiness

| ID | Candidate | Status |
|---|---|---|
| G01 | raw update/group count 32s | TESTED |
| G02 | inter-arrival mean/std/CV by bid/ask event type | W1 |
| G03 | reciprocal mean inter-arrival intensity by event type | W1 |
| G04 | burstiness index (CV-based) by side/event class | W1 |
| G05 | Fano factor counts across subwindows | W1 |
| G06 | short/long intensity ratio 1s/16s | W1 |
| G07 | short/long intensity ratio 4s/32s | W1 |
| G08 | time-since-last insert/delete/deplete/replenish | W1 |
| G09 | age of best bid/ask price level | LATER |
| G10 | age-weighted queue imbalance | LATER |
| G11 | event-clock realized variance / activity interaction | LATER |
| G12 | signed event-time momentum | LATER |

## H. Hawkes / excitation-inspired

| ID | Candidate | Status |
|---|---|---|
| H01 | fixed exponential-decay signed event intensities | W1 |
| H02 | bid-add vs ask-add cross-excitation contrasts | W1 |
| H03 | bid-delete vs ask-delete cross-excitation contrasts | W1 |
| H04 | add→delete and delete→add excitation asymmetry | W1 |
| H05 | replenish→deplete excitation asymmetry | W1 |
| H06 | 4-class linear Hawkes fitted train-only | LATER |
| H07 | 8-class side×event Hawkes fitted train-only | LATER |
| H08 | state-dependent Hawkes with spread regime | LATER |
| H09 | neural Hawkes | LATER/EXPENSIVE |
| H10 | full event-stream likelihood representation | LATER/EXPENSIVE |

## I. Book resilience / recovery

| ID | Candidate | Status |
|---|---|---|
| I01 | depth recovery after depletion shock | W1 |
| I02 | time-to-replenish after deletion | W1 |
| I03 | spread recovery after widening | W1 |
| I04 | queue refill rate after best-level loss | W1 |
| I05 | asymmetric resilience bid vs ask | W1 |
| I06 | shock-conditioned recovery curve parameters | LATER |

## J. Raw sequence models

| ID | Candidate | Status |
|---|---|---|
| J01 | PRICE-only sparse/dense/MiniRocket | EXCLUDE/CLOSED |
| J02 | raw stationary order-flow sequence + small MLP | W1 |
| J03 | raw stationary order-flow sequence + 1D CNN/TCN | W1 |
| J04 | event-type/intensity sequence + small GRU | LATER |
| J05 | compact DeepLOB-style CNN-LSTM | LATER |
| J06 | compact TLOB/dual-attention | LATER |
| J07 | large Transformer sweep | EXCLUDE |
| J08 | architecture search / NAS | EXCLUDE |

## K. Model-family controls

Models are not independent scientific mechanisms and must not multiply the
candidate count without control.

Wave-1 recommended model policy:
- primary low-capacity L2 Logistic Regression for all engineered-vector
  candidates;
- one shared nonlinear check using HistGradientBoosting only for selected
  mechanism representatives where preregistered;
- small MLP only for stationary/high-dimensional vector or sequence candidates.

Do not cross every feature block with every model.

## L. Candidate counts

Current registry:
- total concepts = 92
- W1-tagged concepts before de-duplication/model consolidation = 46
- LATER concepts = retained for adaptive refinement only
- EXCLUDE/CLOSED concepts = preserved as negative search constraints

The Wave-1 target remains approximately 36 strategies after combining highly
correlated W1 concepts into fixed representative blocks.

Final E1 strategy count and exact definitions must be frozen in a separate
DEV032-E1 design before any broad-screen model fit.
