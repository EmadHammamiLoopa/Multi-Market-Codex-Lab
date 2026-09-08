# DEV045 D6R26A P2 R10 — Bounded rolling feature accumulator freeze

Parent R9 HEAD: `6dfa308399f8c6b4780dcfedfc9509dae8bcfbed`.

R10 freezes a bounded-memory rolling implementation of the already-frozen R8B feature mathematics. It is an optimization layer only: R8B remains the semantic reference and R9 remains the raw-event decoder reference.

## Purpose

The Jan-Jul files contain tens to hundreds of millions of events per day. Materializing full 30-second book/flow history for every decision epoch would be unnecessarily expensive. R10 therefore maintains only rolling sufficient statistics and a short recent-book anchor surface.

Frozen rolling state:

- BBO OFI sums: 1s and 5s;
- aggressive buy/sell quantity: 1s and 5s;
- bid/ask add quantity: 1s;
- bid/ask cancel quantity: 1s;
- squared log-mid returns: 1s, 5s, and 30s;
- recent valid books: only enough for 250ms depth-change and 1s spread as-of features;
- first valid book timestamp for the 30s support/warmup guard.

Window semantics remain exactly left-open/right-closed `(t-W,t]`.

Synthetic equivalence tests compare all 25 rolling values against `R8B.compute_features` on the same causal history with tight floating-point tolerance. R10 does not alter feature names, feature order, causal observability, fill labels, markout labels, queue semantics, or candidate definitions.

## Scope

R10 does not open historical Jan-Jul data, import hftbacktest, start candidate simulation, write the attempt marker, write canonical labels, fit models, compute PnL, or open August/September+/non-BTC data.

Next after R10 GREEN: real candidate-lane executor preexecution, which will consume R9 raw-event semantics and R10 bounded feature state while using R8A engine/writer hooks and frozen P1 labels on synthetic hftbacktest fixtures only.
