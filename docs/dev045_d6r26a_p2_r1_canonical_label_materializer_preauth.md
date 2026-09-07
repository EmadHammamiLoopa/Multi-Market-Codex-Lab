# DEV045-D6R26A-P2-R1 — Canonical Candidate Label Materializer Pre-Authorization

## Status

Implementation/pre-authorization only. This phase does **not** open or hash Jan–Jul historical sources, run candidate simulation, write canonical labels, fit a model, compute PnL, or authorize live trading.

Parent P2 design: `a0e22b680c59c4ba26cb1dddc902182fcc962bda`.

Jan–Jul real data role: `CONSUMED_DEVELOPMENT`. The final real bucket remains separate, unassigned, sealed, and one-shot.

## Purpose

P2-R1 freezes the pure mechanics that a later authorized P2 execution must use:

- exact source-identity registry shape;
- deterministic 7 day × 40 lane plan;
- five isolated phase lanes covering every valid one-second decision epoch;
- 30-second causal feature warmup;
- canonical candidate-row schema;
- explicit fill/markout censoring fields;
- deterministic partition bytes/SHA identities;
- deterministic immutable day manifests;
- atomic publish contract;
- fail-closed authorization boundary.

No historical source identity values are invented here. A successor authorization commit must recover and freeze the already-established Jan–Jul path/bytes/SHA256 identities before any historical source is opened for label generation.

## Frozen lineage references

- D6R24 execution: `b04a18f8eb5b4689abd15d7cdf6a6c889ee36212`
- D6R24 result freeze: `06eff337e4a039cf47c8b10a41aa91e52df4c792`
- Q8 execution: `bc6b66fdf2634cdacf04f2738722b36a9f1619d8`
- Q8 freeze: `fc7733a776cff8fc726be630dae4d389abd00e8c`
- hftbacktest upstream: `a244a14250b42d97fc305569c93c4117cd5e1dff`
- frozen patched binary SHA256: `5174f486abc4b29cfef565672548798ea68ec54c0f6c04077bcbdf43f5033752`

These are lineage references only; they do not authorize simulator execution in P2-R1.

## Source identity boundary

The execution successor must provide exactly seven `FrozenSourceIdentity` records, one for each Jan–Jul day. Every record binds day, exact path, byte size, and SHA256. Any missing/extra day, duplicate path, byte mismatch, path mismatch, or SHA mismatch fails closed before label generation.

P2-R1 itself performs no filesystem open/hash operation and does not read an authorization environment variable. Its authorization function is a pure exact-token validator only.

## Materialization plan

Per day: 2 sides × 4 distances `(0,1,2,4)` × 5 phases `(0,1,2,3,4)` = 40 independent lanes. Across seven days = 280 lanes.

Within a lane, candidate epochs are five seconds apart, matching the maximum candidate lifetime. The five phases cover every valid one-second epoch exactly once for each side × distance. The first 30 seconds are feature warmup; end-of-source labels must remain explicit/censored rather than silently dropped.

## Row contract

One row is one `decision epoch × side × distance`. It binds source identity, day-start and decision clocks, lane identity, local BBO, candidate quote, fixed size/GTX/scenario/latencies, placement outcome, all 25 frozen F0–F3 local features plus observability timestamps, fill labels for every horizon, and markout status/value for every horizon.

The validator recomputes phase, lane id and candidate price from the causal inputs. Feature timestamps may not exceed decision-local time. Censoring may never be collapsed into observed no-fill, and a non-observed markout may not carry a numeric markout value.

## Artifacts

Authorized execution will use `PARQUET_ZSTD`, partitioned by day × side × distance × phase, with bytes+SHA256 per partition, exactly 40 partitions/day, deterministic sorted-key JSON day manifests, manifest SHA256, and temp-write → fsync → hash-verify → atomic-rename-once publication.

P2-R1 only freezes these mechanics; it writes no canonical artifact.

## Parallelism and memory

One historical day at a time, bounded memory, maximum 8 independent lanes in parallel. Parallelism may not alter causal semantics or labels.

## Closed surfaces

Historical source open/hash, candidate simulation, canonical label write, model fit/selection, threshold tuning, quote/inventory strategy execution, PnL/economic arena, fee rescue, size/leverage tuning, August, September+, non-BTC, network acquisition, and live trading all remain unauthorized.

## Next gate

After dedicated CI is green: recover and freeze the exact historical source registry, then create the explicit authorized P2 execution contract. Historical opening remains forbidden until that successor gate is complete.
