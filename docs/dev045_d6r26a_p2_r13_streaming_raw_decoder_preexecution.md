# DEV045 D6R26A P2 R13 — Streaming raw decoder preexecution

Parent R12 GREEN HEAD:

`2e6fcbb8c96dae386e548eb72e5e1ba7ed6e2e5d`

R13 closes the bounded-memory gap between the frozen raw decoder and the
frozen rolling feature accumulator.

Before R13:

- R9 defined exact raw-event semantics but its reference decoder returns a
  complete `DecodedHistory`;
- R10 provided bounded rolling feature state;
- R11 proved the exact real-engine candidate lifecycle on synthetic data;
- R12 proved one-day / 40-lane orchestration with synthetic callbacks.

For full historical days, constructing a complete decoded history would
defeat the bounded-memory architecture. R13 therefore freezes a streaming
local-time-group decoder.

The streaming decoder:

- consumes raw rows incrementally;
- binds directly to R9 event semantics;
- keeps only current L2 state and the current local timestamp group;
- emits at most one final post-market book observation per local timestamp;
- preserves source-order flows within that timestamp;
- emits the final book before same-timestamp flows for the frozen R10
  downstream ordering;
- requires candidate decisions to occur only after the local group is fully
  flushed;
- is tested for exact parity against R9's batch reference decoder;
- is tested through R10 against R8B batch feature definitions.

R13 is PREEXECUTION ONLY.

It does not:

- open Jan-Jul;
- import/start the simulator against historical data;
- start any candidate historical lane;
- write the P2 attempt marker;
- write canonical Parquet labels;
- fit a model;
- compute PnL;
- open August or September+;
- open non-BTC data.

`P2_ATTEMPT_CONSUMED=NO`.

After R13 GREEN, the next missing layer is a synthetic multi-candidate
real-engine lane executor using this streaming decoder and R10 bounded
feature state. Only after that layer is frozen do we build the final
historical one-shot binding.
