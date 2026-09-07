# DEV045-D6R26A-P2-R6 — historical source identity preflight

## Purpose

R6 is the final read-only source-identity gate before any canonical Jan–Jul candidate simulation.

It verifies each frozen Jan–Jul BTCUSDT `.npy` source against the R2 registry using:

- exact path
- exact file byte size
- exact NumPy row count
- exact 64-byte event item size
- exact SHA256

The verifier uses `np.load(..., mmap_mode="r", allow_pickle=False)` for header/shape inspection and chunked file hashing. It does not load a full historical day into memory.

## Data role

All Jan–Jul sources are `CONSUMED_DEVELOPMENT` data. R6 does not create or claim an independent holdout.

## Attempt semantics

R6 does **not** consume the P2 canonical materialization attempt.

The P2 attempt is consumed only at:

`FIRST_CANONICAL_CANDIDATE_SIMULATION_LANE_START`

Therefore authorization failure, missing source, byte/row/SHA mismatch, or R6 result-write failure are pre-attempt failures.

## Explicitly closed surfaces

R6 authorizes only read-only historical source identity verification.

It does not authorize:

- simulator import
- candidate simulation
- canonical runner binding
- canonical label writes
- attempt marker writes
- model fitting
- PnL/economic evaluation
- live trading
- August or September+ data
- non-BTC data
- network acquisition

## Frozen lineage

Parent R5:

`0524ebd92b6f600d9b1a844c707076f11e4a54f6`

Frozen source registry SHA256:

`97c631d621118d5cd4d294825dec545c92d85c62456403a6974ca38a70ece3f4`

R6 authorization environment variable:

`DEV045_D6R26A_P2_R6_AUTHORIZE`

Exact token:

`YES_FROZEN_JAN_JUL_SOURCE_IDENTITY_PREFLIGHT_ONLY`

## Execution sequence

1. R6 code/tests/CI become GREEN.
2. Sync exact R6 HEAD to the local frozen worktree.
3. Run one local read-only preflight over all seven frozen source paths.
4. Freeze the resulting JSON artifact and SHA256.
5. Only after R6 PASS, build/freeze the canonical historical hook binding and final execution authorization.

No canonical candidate lane is started in R6.
