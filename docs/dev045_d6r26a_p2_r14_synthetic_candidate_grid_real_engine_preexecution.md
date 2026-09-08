# DEV045 D6R26A P2 R14 — Synthetic candidate-grid real-engine preexecution

Parent R13A GREEN HEAD:

`37b45cdfcd36e40149b549c0d611c514a3d91f51`

R14 is the first synthetic layer to exercise the exact patched real engine
across the complete candidate **side × distance** grid:

- BID: distances 0, 1, 2, 4;
- ASK: distances 0, 1, 2, 4.

The five phase cohorts remain the already-frozen R1/R12 orchestration
dimension, giving 40 canonical lanes per day.

## Engine coverage

Every side-distance pair is submitted to the exact patched hftbacktest 2.4.4
engine and tested through accepted post-only placement and the exact
5-second candidate terminal/cancel lifecycle.

BBO fill probes are additionally run on both sides:

- BID D0;
- ASK D0.

This tests real-engine fill symmetry without inventing unrealistic synthetic
trade-through sequences for deeper candidate distances.

## Bound surfaces

R14 binds:

- R11 exact patched-engine lifecycle;
- the corrected R11 cancel-latency semantics;
- R12 one-day / 40-lane orchestration;
- R13A bounded local + exchange dual stream;
- R10 rolling features;
- R8B feature/label semantics;
- R9 only as the immutable synthetic parity reference.

## Previous-failure guards

R14 carries forward the D6R13/D6R14 lessons:

- no fixed event target;
- no fixed wakeup target;
- natural end-of-source remains valid at the data-driver layer;
- total RSS is not a bounded-memory acceptance gate;
- no full historical decoded history is introduced.

The candidate's five-second terminal is an economic/label lifecycle boundary,
not an ingestion wakeup quota.

## Scope

R14 is synthetic PREEXECUTION only.

It does not:

- open Jan-Jul historical files;
- run a historical candidate;
- write the P2 attempt marker;
- write canonical label partitions;
- fit models;
- compute PnL;
- open August or September+;
- open non-BTC data.

`P2_ATTEMPT_CONSUMED=NO`.

After R14 GREEN, the next missing layer is the bounded sequential
multi-candidate lane driver that applies this generic engine primitive to
successive isolated decision epochs. Only after that is GREEN do we build
the final historical one-shot binding/preflight.
