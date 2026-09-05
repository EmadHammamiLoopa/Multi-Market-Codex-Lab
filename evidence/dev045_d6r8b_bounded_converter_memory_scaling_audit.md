# DEV045 D6R8B — Bounded Converter Memory-Scaling Audit

Status: **PASS STATIC AUDIT / STRUCTURAL REDESIGN REQUIRED**

Parent: `09bc05a9bd5625251c178386ed5fbae0f8955318`

This gate is static/read-only with respect to market data. No converter was run,
no raw day was opened, and no PnL or policy execution occurred.

## Frozen evidence used

The production converter is `src/multimarket/dev045_d6r_bounded_converter.py`,
whose frozen SHA256 is
`8f79ec81c664f1762a87bfcf8757564abbe2d7f5fd89b1c83fc78de0ac4b94ac`.

D6R4B Jan full-day conversion observed:

- base rows: 63,666,276;
- final rows: 64,314,723;
- production chunk: 500,000 rows;
- temporary sort runs: 256 total;
- final file bytes: 4,116,142,528;
- peak RSS: 9,946,800,128 bytes;
- pre-run MemAvailable: 10,097,618,944 bytes.

D6R5C later performed read-only validation of the same Jan file and observed
4,221,472,768 bytes peak RSS while the file itself is 4,116,142,528 bytes.
That observation is consistent with, but does not by itself prove, substantial
resident pages from a whole-file mmap traversal.

## What is genuinely bounded

The first conversion stages do use fixed-size buffers. The CSV parser retains
at most `chunk_rows` rows at a time. `_RunBuilder` owns one fixed temporary
record buffer. Per-flush `lexsort` indices and sorted-record copies are bounded
by the same chunk. Snapshot bid/ask buffers are likewise capped by
`chunk_rows`. SHA256 uses a 1 MiB userspace read buffer.

The exact Python heap cost of 500,000 CSV rows and their strings cannot be
proven from static inspection, but that retention does not grow with the total
day row count once `chunk_rows` is frozen.

## Where day-size scaling returns

The bounded chunk stage spills every base event twice: once into exchange-time
sort runs and once into local-time sort runs. `_TEMP_DTYPE` is 72 bytes. For
Jan this means approximately:

- one axis payload: 63,666,276 × 72 = 4,583,971,872 bytes;
- both axes: 9,167,943,744 bytes of temporary record payload, excluding NPY
  headers.

The important issue is not merely disk size. `_MergedRunStream.__enter__`
`np.load(..., mmap_mode="r")` opens every run passed to it and retains every
root memmap in `self._arrays` until the stream closes. `_corrected_events`
opens one such stream for all exchange runs and one for all local runs at the
same time. Jan had 128 runs per axis, 256 total.

Therefore the mapped working set is structurally proportional to the day's
base-event payload and run count, not only to the 500,000-row chunk size.
Linux may reclaim mapped pages, so static inspection cannot state which pages
were resident at the exact `ru_maxrss` instant. The audit therefore does **not**
claim that 9,167,943,744 temporary bytes exactly caused the observed
9,946,800,128-byte RSS. It does establish the day-size-dependent mapping risk.

The corrected merge is also traversed twice: first to count final rows, then
again to write them. This primarily doubles traversal/I/O; it can also repeat
resident-set pressure, though it does not by itself prove a doubled peak.

## Output mapping and validation

After the count pass, the converter creates the entire final shape with
`np.lib.format.open_memmap(..., mode="w+")` and writes every output row through
that mapping. Dirty/resident output pages can contribute to RSS depending on
kernel writeback and reclaim.

After closing that mapping, `_validate_final` again calls
`np.load(path, mmap_mode="r")` for the entire output file and keeps the root
mapping alive while merely *slicing* it into 500,000-row validation chunks.
Slicing bounds each logical validation operation but does not make the root
mapping windowed. D6R5C's ~4.22 GB read-only peak on the ~4.116 GB Jan file is
consistent with this risk.

The final streaming SHA256 is not a material process-RSS scaling mechanism;
it reads 1 MiB userspace blocks.

## Upstream hftbacktest converter

The production `convert_tardis` path is the project's own converter. The
frozen `hftbacktest.data.utils.tardis.convert` was a parity oracle in earlier
validation; its intermediate arrays are not part of the D6R4B production
full-day path and therefore are not a production RSS driver here.

## Static conclusion

The current converter is **not structurally memory bounded by `chunk_rows`**.
Chunking is real, but later full-run/full-file mappings reintroduce memory
pressure that scales with day size. Because Feb–Jul reference row counts all
exceed Jan and Jan already used about 98.5% of observed available memory, the
current converter remains unauthorized for Feb–Jul.

## Required D6R8C redesign

D6R8C must freeze a redesign before implementation. At minimum it must:

1. preserve the exact sort key `(timestamp, source_seq)` and all event semantics;
2. cap simultaneous merge inputs, for example with a fixed-fan-in hierarchical
   external merge, rather than keeping all day runs mapped at once;
3. use bounded/windowed readers for large run payloads and close each window;
4. avoid keeping a full-output writable mapping live while touching the whole
   final file; use a bounded output buffer while preserving the exact NPY
   dtype/shape/semantics;
5. validate via windowed mappings/readers that are closed after each window,
   while preserving cross-window exchange/local order state;
6. retain the bounded streaming SHA256;
7. derive the next resource gate from the structural bound (chunk size, fan-in,
   read windows, output buffer, and safety margin), not a naive month/Jan ratio;
8. prove synthetic and already-approved real-slice parity before considering a
   new full day.

This audit intentionally does not freeze the fan-in or window sizes. Those are
design choices for D6R8C and must be preregistered before implementation.

## Closed surfaces

No D6R4B rerun, no D6R5C rerun, no Feb–Jul raw open or conversion, no August,
no September+, no non-BTC, no 112 replay, no policy execution, no historical
PnL, no economic arena, no network acquisition, no Railway, and no live
trading are authorized by D6R8B.
