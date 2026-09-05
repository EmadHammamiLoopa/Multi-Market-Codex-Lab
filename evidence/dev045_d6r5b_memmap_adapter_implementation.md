# DEV045-D6R5B — Read-only canonical Jan memmap adapter implementation

Status at this commit: **IMPLEMENTATION FROZEN; REAL JAN EXECUTION NOT PERFORMED BY THIS COMMIT.**

## Parent

- D6R5A contract head: `8c5a377bb8270d39ec9cd3736299bef68e9de79b`
- D6R5A CI run: `33932094244`
- D6R5A CI: `completed / success`

## Implementation scope

`src/multimarket/dev045_d6r5_memmap_adapter.py` adds the only supported production entrypoint:

`open_canonical_jan()`

It accepts no path argument and therefore cannot select another day/file through the supported production API.

Before exposing the mapped array it fails closed on:

- canonical path existence and `.npy` suffix;
- exact byte size;
- exact SHA256 using bounded streamed reads;
- file identity changing during hash/open;
- `np.memmap` type;
- read-only mapping;
- exact ndim, rows, dtype, field order, and itemsize.

The open call uses the frozen contract semantics:

`np.load(path, mmap_mode="r", allow_pickle=False)`

Traversal is through bounded physical-order memmap slices only. A requested chunk must satisfy `1 <= chunk_rows <= 500000`. Each slice is checked for exact dtype/fields/itemsize, read-only status, and `local_ts >= exch_ts`.

## Explicit non-actions

This implementation does not:

- open the real Jan artifact during CI;
- open raw Tardis CSV;
- call a converter;
- write/replace/move/delete the canonical NPY;
- open Feb-Jul;
- open August or September+;
- open non-BTC data;
- sort or reorder events;
- execute policies;
- compute PnL;
- execute the economic arena;
- acquire market data from the network;
- touch Railway;
- authorize live trading.

Synthetic temporary NPY files are used only by unit tests to verify the adapter mechanics without opening market data.

## Next gate

After this exact commit is independently verified and CI is green, the next separate gate is a local read-only canonical-Jan adapter validation using the frozen file. Historical policy replay and PnL remain unauthorized.
