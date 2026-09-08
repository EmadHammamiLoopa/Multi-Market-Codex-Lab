# DEV045 D6R26A P2 R23A — Execution-head lineage amendment

Parent R23 GREEN HEAD:

`124dc037b1fab545a336d830419d40ed55138c8c`

## Why this amendment exists

R23 CI correctly proved that its readiness logic cannot consume P2.

However, immediately before historical execution a real-path contradiction was
found:

R23 v1 compared the live repository HEAD to its parent R22 SHA.

Once R23 itself had been committed, the live HEAD was necessarily R23 rather
than R22, so `run_real_readiness_preflight()` could never succeed from the
frozen R23 checkout.

No historical source was opened and no attempt was consumed.

## Amendment

R23A keeps every R23 readiness rule but moves the exact execution-HEAD value
into the final one-shot wrapper.

The final wrapper will contain the literal frozen R23A commit SHA and will
perform:

`git rev-parse HEAD == EXPECTED_R23A_HEAD`

before calling R23A.

R23A independently receives the same SHA and verifies that the repository HEAD
reported by the readiness hook matches it exactly.

This avoids a self-referential source constant while still giving the actual
one-shot command an immutable exact-HEAD gate.

## Unchanged seals

R23A still performs no:

- NPY load;
- mmap;
- source hash;
- row scan;
- historical engine execution;
- attempt-marker write;
- canonical label write;
- model fit;
- PnL.

Source SHA and row verification remain in R22 immediately before the first
historical context and before the first simulator lane.

`P2_ATTEMPT_CONSUMED=False`.

## Next

After R23A GREEN there is no further design/preexecution stage.

The next command will hardcode the exact R23A GREEN SHA, rerun the metadata
readiness preflight locally, then invoke the frozen R22 successor campaign.

Once the R22 marker is successfully written immediately before the first
historical lane, P2 becomes consumed and cannot be rerun or resumed.
