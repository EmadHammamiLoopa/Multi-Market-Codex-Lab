# DEV045 D6R8D — V2 Structurally Bounded Converter Implementation

Status: **IMPLEMENTED / SYNTHETIC CI GATE PENDING**

Parent: `2dfa40e7a55cf45da61712ad1a9860394676c9c0` (D6R8C redesign contract)

This phase implements the separately frozen V2 converter and adds synthetic-only
tests. It opens no historical market file, no Jan canonical file, and no
Feb–Jul raw data.

## Implementation

New module:

`src/multimarket/dev045_d6r8_structurally_bounded_converter.py`

The frozen old converter remains unchanged at SHA256
`8f79ec81c664f1762a87bfcf8757564abbe2d7f5fd89b1c83fc78de0ac4b94ac`.

V2 preserves the frozen conversion semantics while replacing the memory-scaling
I/O stages with:

- fixed-fan-in hierarchical external merges;
- sequential NPY window readers using bounded `np.fromfile` arrays;
- bounded merge output buffers;
- bounded corrected-stream readers;
- sequential NPY header + bounded payload writing;
- bounded final validation with cross-window clock state;
- streaming SHA256;
- atomic promotion only after validation and hashing succeed.

The V2 source contains no `mmap_mode` and no `open_memmap`.

## Synthetic proof required by CI

The new tests:

1. compare V2 against the frozen old converter on the same synthetic Tardis
   trades/depth fixture for chunk sizes 1, 2, 3 and 7;
2. require fieldwise exact equality with NaN equality and exact NPY SHA256
   equality;
3. force more than eight initial runs per axis and at least three hierarchical
   merge levels;
4. verify final validation only receives bounded non-memmap windows;
5. exercise the RSS guard without triggering it;
6. force RSS failure and validation failure and require no destination output;
7. verify temporary-directory cleanup and atomic-promotion behavior;
8. verify the production constants equal the D6R8C frozen contract.

CI success is required before D6R8D is frozen green.

## Closed surfaces

No real market data is authorized by this implementation commit. No Jan full-day
conversion or validation rerun, no Jan canonical NPY open, no Feb–Jul raw open
or conversion, no August, no September+, no non-BTC, no 112 replay, no policy
execution, no historical PnL, no economic arena, no network acquisition, no
Railway, and no live trading.

After D6R8D CI green, the next gate is D6R8E: separately freeze the exact
already-approved D6R2B Jan 10-minute real-slice paths and hashes before any
real-slice V2 parity execution.
