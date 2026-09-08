# DEV045 D6R26A P2 R12 — One-day lane driver preexecution

Parent R11 GREEN HEAD:

`21eeec972aec1f1b75474595db0ca843931aa9e7`

R12 freezes the one-day orchestration boundary required before the final
historical one-shot binding.

It proves, without opening Jan-Jul historical sources:

- exactly one frozen day is selected;
- exactly 40 canonical lanes are present:
  - 2 sides;
  - 4 candidate distances;
  - 5 phase cohorts;
- the day source is opened exactly once;
- lanes execute in the frozen canonical order;
- every returned partition identity is checked;
- the source is closed exactly once;
- failure stops immediately and still closes the source;
- R4 campaign semantics remain authoritative;
- R8A real mmap/engine/writer primitives remain frozen but unbound;
- R11 exact real-engine candidate lifecycle remains authoritative.

R12 CI uses synthetic/in-memory callbacks only.

R12 does **not**:

- open Jan-Jul;
- import/start the real simulator for historical data;
- write the P2 attempt marker;
- write canonical labels;
- fit models;
- compute PnL;
- touch August or September+;
- touch non-BTC;
- authorize live trading.

`P2_ATTEMPT_CONSUMED` remains `NO`.

After R12 GREEN, the next stage is the final one-shot execution binding.
That later binding must wire the already-frozen source verifier, read-only
mmap opener, real-engine lifecycle, lane materializer and atomic writer into
R4 while preserving the exact attempt-consumption boundary.

Historical execution remains separately gated and is not authorized by R12.
