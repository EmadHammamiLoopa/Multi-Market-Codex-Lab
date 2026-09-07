# DEV045-D6R26A-P2-R5 — Real Engine Binding, Pre-Historical

## Status

Real-engine probe only. Parent R4: `af961cd3404529873aea8b066da11e55eaaf918e`.

R5 imports and exercises the exact patched `hftbacktest 2.4.4` engine only against in-memory synthetic fixtures. It does not open Jan–Jul historical sources, bind the canonical R4 runner to real historical I/O, write attempt markers or canonical labels, fit models, compute PnL, or authorize live trading.

## Purpose

R5 proves the exact mechanics required before any historical candidate-label run:

- exact hftbacktest version/status identity;
- GTX post-only TIF identity;
- passive GTX order at the best bid is accepted on `PartialFillExchange`;
- risk-adverse queue behavior does not fill merely when queue-ahead reaches zero;
- a subsequent aggressive trade fills the fixed 0.001 candidate order;
- a crossing GTX order is represented as `EXPIRED` and maps to `POST_ONLY_REJECTED_AT_ARRIVAL`;
- all probes use `risk_adverse_queue_model + partial_fill_exchange + 250ms/250ms` on in-memory synthetic events.

## Exact simulator lineage

- hftbacktest version: `2.4.4`
- upstream commit: `a244a14250b42d97fc305569c93c4117cd5e1dff`
- frozen patched binary SHA256: `5174f486abc4b29cfef565672548798ea68ec54c0f6c04077bcbdf43f5033752`

CI reuses the exact patched-wheel cache already introduced in P1. It builds from upstream only on cache miss.

## Historical boundary

All Jan–Jul source I/O remains forbidden. R5 contains no canonical source opener and does not call the R4 canonical runner. `ATTEMPT_MARKER_WRITE_AUTHORIZED=False`, so R5 cannot consume the P2 canonical attempt.

## Next gate

After R5 dedicated CI is GREEN, create the historical hook-binding implementation that binds R4 to the already-frozen source registry and real engine while keeping execution disabled. Only after that binding is frozen and GREEN may a separate explicit authorization command open Jan–Jul and consume the one-shot P2 attempt.
