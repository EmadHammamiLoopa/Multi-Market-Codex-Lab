# DEV045-D6R26A-P2-R3 — Execution Authorization Contract

## Status

Contract-only successor to R2. Parent: `d5e445e19b8d3539fcc465bf248ddd9dee4aafd2`.

R3 binds P2 execution to the frozen Jan–Jul registry SHA256 `97c631d621118d5cd4d294825dec545c92d85c62456403a6974ca38a70ece3f4` and the exact P2 authorization token. This commit itself does not open historical sources, import hftbacktest, start candidate simulation, or write labels.

## Attempt consumption

Authorization failure and source-identity precheck failure do not consume the canonical attempt.

The attempt is consumed at:

`FIRST_CANONICAL_CANDIDATE_SIMULATOR_LANE_START_AFTER_EXACT_SOURCE_IDENTITY_VERIFICATION`

After that marker exists, rerun, resume, and automatic retry are forbidden. Any execution failure is terminal evidence. Partial outputs are evidence, not canonical completion.

## Completion

Canonical completion requires all 280 lane partitions, with one historical day processed at a time, source open once/day, read-only source access, at most 8 independent lanes in parallel, and final manifest publication only after all partition identities are verified.

## Permanently closed surfaces

P2 never authorizes model fit/selection, threshold tuning, quote/inventory strategy execution, PnL/economic arena, fee rescue, size/leverage tuning, August, September+, non-BTC, network acquisition, final real bucket opening, or live trading.

## Next gate

After dedicated CI is GREEN, implement the execution runner that enforces this contract. The runner may not be invoked until its own implementation/CI gate is frozen and explicitly authorized.
