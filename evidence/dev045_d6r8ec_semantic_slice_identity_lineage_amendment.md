# DEV045 D6R8EC — Semantic Slice Identity Lineage Amendment

Status: **FROZEN CONTRACT ONLY**

Parent: `4390605f0050bdbbf49058f41a52e954fbc3af7a` (D6R8EB slice-identity forensics, CI green required).

## What this amendment does not do

D6R2B remains a historical PASS. D6R8EB remains a permanently frozen FAIL. This amendment does not rerun, reinterpret, rescue, or replace either result.

The forensics established that the exact historical D6R2B gzip writer/slice bytes cannot be recovered. D6R2B retained compressed slice SHA256 values but not decompressed payload digests or the writer details needed to reproduce those container bytes. Therefore no successor may silently call the D6R8EB mismatch "gzip only", and the old D6R2B output SHA cannot be treated as the sole oracle for a newly reconstructed slice.

## New successor identity standard

For successor gates only, semantic slice identity is defined independently of gzip-container representation.

The source lineage must first match the frozen D4 Jan files exactly:

| Kind | Bytes | SHA256 |
|---|---:|---|
| trades | 9,691,108 | `e4aaee2b9f85016a5198e0cace5755dbd789c0f6f47ac0fc802c8f4b533833f6` |
| incremental_book_L2 | 347,513,061 | `0488a2204c9070b1e6a8769af48d54fb36e6a5658613267e2615cd3228002ded` |

The window remains exactly `1767225600000000 <= local_timestamp < 1767226200000000` for BTCUSDT on binance-futures, 2026-01-01.

The semantic payload identities frozen from the already-created D6R8EB slices are:

| Slice | Rows | Decompressed bytes | Decompressed SHA256 |
|---|---:|---:|---|
| trades | 13,073 | 1,137,750 | `cb6a1d37e4422fa99e563969b3750487a3ca3d01956a45973085f26352a220fe` |
| depth | 483,149 | 39,147,846 | `5c5d8de09c1a38083f151f632fce568fb80b9df1485f5688d2dab20431869f93` |

These digests were frozen without observing any V2 real-data output: D6R8EB failed the compressed-slice gate before V2 launched. This avoids selecting the successor payload based on a V2 parity outcome.

A successor slice must also preserve exact header bytes, selected row bytes and order, row counts, first/last local timestamps, and depth snapshot structure. A compressed gzip SHA may be recorded diagnostically, but it is neither necessary nor sufficient for semantic identity.

## Successor parity architecture

The old D6R2B output SHA is historical evidence, not the sole successor oracle because the exact D6R2B logical slice bytes are unavailable.

A future D6R8ED contract must instead:

1. verify the exact D4 raw source byte sizes and SHA256 values before selection;
2. reconstruct the exact fixed semantic slice sequentially and byte-preservingly;
3. verify the frozen decompressed payload digests, lengths, row counts, endpoints and snapshot structure **before** any converter runs;
4. feed the exact same reconstructed physical slice files to V2, the frozen old converter, and the frozen upstream hftbacktest oracle;
5. require exact fieldwise NaN-equal parity among those outputs with no tolerance or post-sort;
6. freeze the first successor PASS or FAIL under a separate attempt marker/evidence path.

This is a new successor lineage, not a rerun of D6R8EB.

## Closed surfaces

D6R8EC opens no raw content and authorizes no slice extraction or converter execution. Jan full-day, Feb-Jul, August, September+, non-BTC, replay, PnL/economic arena, network acquisition, Railway and live trading remain closed.

After this exact contract commit is CI green, the next step is to freeze **D6R8ED new semantic real-parity contract**. That later contract, not D6R8EC, would decide whether one new narrowly scoped real-slice attempt is authorized.
