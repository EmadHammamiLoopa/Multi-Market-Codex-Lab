# DEV032-E0 — Broad Microstructure Candidate Census

Status: `EXPLORATORY_CENSUS_NO_MODEL_FIT`

Date: 2026-09-02

## Purpose

DEV032-E0 inventories plausible causal microstructure mechanisms before any
broad-screen outcome is generated.

E0 does not fit models, open forward data, calculate predictive metrics, or
write a scientific result artifact.

The objective is to create a finite, auditable candidate universe for a later
broad historical screening program on already-consumed BTCUSDT Jan-Jul
development data.

## Scientific sequencing

DEV031-P1B remains an official FAIL:
`FAIL_EVENT_DEPTH_NO_STABLE_INCREMENTAL_DIRECTION_VALUE`.

Its AUC improvement is preserved as hypothesis-generating evidence only.

Sep-01+ remains sealed.

DEV032 may explore consumed historical data, but any survivor remains
exploratory until replicated on independent historical data.

## Literature anchors

The candidate census is motivated by distinct mechanism families rather than
parameter permutations:

1. Cont, Kukanov, Stoikov — order-flow imbalance and short-horizon price impact.
2. Gould & Bonart — queue imbalance as a one-tick-ahead direction predictor.
3. Stoikov — micro-price as an order-book-conditioned short-horizon fair price.
4. Xu, Gould, Howison — multi-level order-flow imbalance; deeper levels can add
   incremental information.
5. Kolm, Turiel, Westray — stationary order-flow representations can outperform
   raw LOB states.
6. Zhang, Zohren, Roberts — DeepLOB; spatial/temporal LOB representations.
7. Berti & Kasneci — TLOB and simpler MLP baselines; complex architecture is not
   automatically superior.
8. Cenesizoglu & Grass — LOB slope/imbalance/convexity encode distributional
   information.
9. State-dependent / neural Hawkes LOB literature — event-type timing and
   excitation are a materially different information family.
10. 2026 Bitcoin Hawkes/LOB forecasting work — direct relevance of event-time
    point-process features for BTC short-horizon return-sign prediction.

## Existing project features that are NOT automatically new

Already represented or tested in the current lineage:
- spread_bps
- microprice_minus_mid_bps
- OBI L1/L5/L10
- aggregated OBI L20/L50
- L5/L10 depth totals
- aggregated L20/L50 depth totals
- L1 OFI
- aggregated L5/L10 MLOFI at 250ms/1s/3s
- trade quantity/count imbalance
- replenishment/depletion L5
- raw event insert/delete/replenish/deplete pressure
- raw distance-band flow imbalance 1/4/16/32s
- raw update/group intensity counts
- PRICE-only sparse/dense/MiniRocket sequence representations

These are controls or prior evidence, not novel candidates unless the new
representation changes the scientific information geometry materially.

## Candidate design principles

A candidate is a mechanism, not a tiny parameter tweak.

Prefer:
- level-wise vectors;
- state-normalized quantities;
- event-time statistics;
- book-shape geometry;
- excitation/decay;
- causal stationary transforms;
- bounded interpretable models.

Avoid:
- exhaustive threshold grids;
- hundreds of nearly identical depths;
- post-hoc feature dropping;
- model zoo for its own sake.

## Broad-screen interpretation

Later E1/E2/E3 results are screening evidence only:
- SCREENING_SURVIVOR
- SCREENING_REJECTED
- SCREENING_INCONCLUSIVE

No DEV032 screen can itself authorize Sep-01+.

Independent replication is mandatory before forward confirmation.
