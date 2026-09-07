# DEV045-D6R26A-P2-R2 — Frozen Jan–Jul Source Registry

## Status

Registry freeze only. Parent: `00c0779b36432e088dc6fd039559ed0095c84b2c`.

This phase recovers and freezes the already-established Jan–Jul source identities from the frozen D6R17 lineage used by D6R24. It does not rediscover them from local files and performs no historical file I/O, rehash, mmap, simulator execution, candidate-label materialization, model fit, PnL, or live trading.

## Provenance

The exact source registry is inherited from `dev045_d6r17_real_historical_economic_driver_contract.py`, whose canonical replay validator binds each source to exact `path`, `rows`, `bytes`, and `SHA256` before execution.

Recovered witnesses:

- 2026-01-01 → DEV045-D6R7B
- 2026-02-01 → DEV045-D6R15
- 2026-03-01 through 2026-07-01 → DEV045-D6R16

The seven source records are embedded verbatim into R2 and cross-checked against the current inherited D6R17 constants. Any lineage drift fails closed in CI.

## Registry manifest

Deterministic registry SHA256:

`763e70b21d89a1047499e867f30f6f4e4bc576e2a389d01af347a416ed365634`

The payload binds experiment/design identity, data role, source-contract lineage, and all seven records including day, path, rows, bytes, SHA256, ingestion witness, and witness head.

## Safety boundary

All of the following remain false in R2:

- historical file I/O/open/rehash
- candidate simulation
- canonical label write
- model fit/selection
- threshold tuning
- PnL/economic arena
- fee rescue
- size/leverage tuning
- August / September+ / non-BTC / network / live trading

## Next gate

Create an explicit P2 execution-authorization contract that consumes this frozen registry and preserves the one-shot/fail-closed materialization semantics from P2-R1. Historical source opening remains forbidden until that successor gate is frozen and GREEN.
