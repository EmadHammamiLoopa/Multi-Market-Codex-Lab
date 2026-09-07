# DEV045-D6R26A-P2-R2 — Frozen Jan–Jul Source Registry

## Status

Registry freeze only. Parent: `00c0779b36432e088dc6fd039559ed0095c84b2c`.

This phase recovers and freezes the already-established Jan–Jul source identities from frozen ingestion lineage. It performs no historical file I/O, rehash, mmap, simulator execution, candidate-label materialization, model fit, PnL, or live trading.

## Provenance

The D6R17 contract provides the Jan–Jul registry shape and all identities except for one known transcription defect in the June SHA field. Its June string has 63 hexadecimal characters and therefore cannot be a valid SHA256.

The authoritative frozen D6R16 PASS evidence at commit `5411877e3bd1f8fcd9812176bc3dc39dbf18bf88`, file `evidence/dev045_d6r16_2026-06-01.json`, records the verified adapter identity:

`ac97ad27c9d58b3b3e249547b8ae7c74cf2ebfde07965103bd9c8c05d0df1160`

R2 uses this exact witness value; it is not inferred, repaired by pattern, or rehashed from the local source. The June path, rows, bytes, ingestion witness, and witness head remain identical to D6R17. All non-June records must continue to equal D6R17 exactly or CI fails closed.

Recovered witnesses:

- 2026-01-01 → DEV045-D6R7B
- 2026-02-01 → DEV045-D6R15
- 2026-03-01 through 2026-07-01 → DEV045-D6R16

## Registry manifest

Deterministic registry SHA256:

`97c631d621118d5cd4d294825dec545c92d85c62456403a6974ca38a70ece3f4`

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

After R2 is GREEN, create an explicit P2 execution-authorization contract that consumes this frozen registry and preserves the one-shot/fail-closed materialization semantics from P2-R1. Historical source opening remains forbidden until that successor gate is frozen and GREEN.
