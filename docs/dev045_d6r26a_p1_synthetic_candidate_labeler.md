# DEV045-D6R26A-P1 — Synthetic Candidate Labeler

Parent P0: `33c61a4e3904659ea44a0edfe763f31e31c58ba8`.

P1 implements only the deterministic labeling contract needed before any Jan-Jul historical candidate materialization. It does not open historical sources, fit models, compute PnL, or run an economic arena.

## Clock domains

Fill horizons are measured from `decision_local_ns`. Markout horizons are measured from each fill's exchange execution timestamp. These origins are intentionally different and must not be mixed.

## Fill semantics

For each frozen horizon, the any-fill label is exactly `FILLED_WITHIN_TAU`, `NOT_FILLED_WITHIN_TAU`, or `CENSORED`. A censored observation is never rewritten as a no-fill. Partial fills remain first-class: fill fraction, first-fill time, and full-fill time/status are retained separately.

A GTX candidate that reaches the exchange and expires because it would take liquidity is an observed post-only rejection and therefore an observed no-fill. If placement outcome itself cannot be observed before the source boundary, the candidate is censored.

## Markout semantics

Markout is side-signed fill-price-to-future-mid movement in bps. Spread capture is already embedded in the fill price and is not added separately. Candidate-level markout aggregates included partial fills by executed quantity. If a required future midpoint is not observable through the full horizon, the markout target is censored.

## Lane isolation

The P0 five-phase lane design remains binding. Candidate decisions within a lane must be separated by at least five seconds.

## Feature safety

Every decision feature must satisfy `feature_observable_local_time <= decision_local_time`. Future information fails closed.

## Engine identity

Dedicated CI builds the exact pinned hftbacktest 2.4.4 source at `a244a14250b42d97fc305569c93c4117cd5e1dff`, applies the already-frozen safe patch, verifies GTX/order-status identities, and reruns the repository's existing real-engine M4 execution probes alongside P1 label tests.

## Closed surfaces

- historical source open/hash: NO
- canonical label materialization: NO
- model fit: NO
- PnL: NO
- economic arena: NO
- network acquisition: NO
- live trading: NO

Next gate after green CI: `D6R26A-P2` canonical Jan-Jul candidate-label materialization design/authorization, not model fitting.
