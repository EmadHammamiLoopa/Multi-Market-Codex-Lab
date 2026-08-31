# CODEX-EXP-024-P0 Result

Official status:

`PROSPECTIVE_BOOKTICKER_DATA_READY`

Collection day:

`2026-08-30 UTC`

Symbol:

`BTCUSDT`

Frozen acquisition/finalization implementation:

`2eb478bb5969c6f2bb8a7eb0b72eda8baa45ec23`

Preregistration SHA-256:

`1630ab4591b20a26640a45c980b28b788516434110795d5d406f0189d92a6bd2`

EXP023 readiness artifact SHA-256:

`4eaf158b2517cf6c0be2efc2e7026a73a6b9986977d2c78499bb5785f142c1af`

P0 audit SHA-256:

`70e8861b844c88e394741edde9ba17b9a25544b45728ae8e64d868a3faff4acd`

Raw artifact:

- bytes: `970963611`
- SHA-256: `f30d791082e83468bb806af1035815c6c167a6d7b24068164820e2123847c33b`
- accepted quotes: `20196643`
- rejected records: `0`
- connection epochs: `1`
- transport errors: `0`
- collection-end records: `1`
- collection ended after UTC day: `true`

Finalized 250 ms grid:

- rows: `345600`
- valid rows: `345595`
- valid coverage: `0.9999855324074074`
- bytes: `33451762`
- SHA-256: `a74bd9e040561f3bf6f4eb9c42b81f7c76681e6b4b918b636cf97e95a0bd273b`
- future quote violations: `0`
- stale/unavailable rows: `0`
- reconnect-invalid rows: `1`

All frozen integrity gates passed.

No predictive metrics were calculated in P0. No model was fit, and no
direction, PnL, leverage, or AUC was scored.

Operational transparency:

Three launch attempts before the successful finalizer execution aborted before
`run()` and before prospective raw analytical parsing or creation of the P0
grid/audit:

1. missing NumPy dependency;
2. missing websockets dependency;
3. malformed Railway Start Command rejected by argparse.

A subsequent dependency import precheck passed. The first actual finalizer
execution completed successfully and produced the immutable P0 audit and grid.

The prospective grid remains opaque to EXP024-P1 until the frozen P1
one-shot execution authorizes the P0 audit, verifies grid size/SHA-256, and
then opens the grid analytically.
