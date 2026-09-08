# DEV045 D6R26A P2 R13A — Dual-stream EOF/memory amendment

Parent R13 GREEN HEAD:

`88a423c295e197fcfec2a4e5e8ad08c086d19a88`

R13 itself remains frozen and unchanged.

## Why this amendment exists

R13 successfully converted the **local-time** R9 decoder to streaming form, but
the R9 semantic reference also contains `decode_exchange_midpoints()`, whose
batch implementation materializes the complete exchange-time midpoint series.

Advancing directly from R13 would therefore leave one full-day
history-materialization path in the architecture.

R13A closes that gap before any historical P2 execution.

## Previous-failure anti-regression

The earlier DEV045 D6R13/D6R14 lineage established two important rules that are
carried forward explicitly here:

1. natural end-of-source is a valid terminal condition;
2. no fixed event/wakeup target may be required for successful completion.

The final local and exchange timestamp groups are flushed when the source ends.
A reference EOD count may never become a stopping quota.

The earlier memory forensic also showed that total RSS can be dominated by
file-backed mmap pages. R13A therefore does not use total RSS as a boundedness
criterion. Decoder boundedness is architectural: retained state is limited to
the active L2 book plus the currently open timestamp group, rather than all
previously emitted books, flows, or midpoints.

## Frozen decoder surfaces

- local stream: unchanged R13 `LocalStreamingDecoder`;
- exchange stream: new incremental `ExchangeStreamingDecoder`;
- both consume exact R9 event semantics;
- exchange output is exact parity with `R9.decode_exchange_midpoints`;
- final groups flush on natural source exhaustion;
- unknown event kinds and timestamp regressions fail closed;
- real-path full-history materialization is forbidden.

`decode_exchange_streaming()` exists only as a small synthetic parity helper.
Historical execution must consume `iter_exchange_midpoints()` or
`DualStreamingDecoder` incrementally.

## Scope

R13A is PREEXECUTION ONLY.

It does not open Jan-Jul, import the historical simulator, start a historical
candidate lane, write the P2 attempt marker, write canonical labels, fit a
model, compute PnL, open August/September+, or open non-BTC data.

`P2_ATTEMPT_CONSUMED=NO`.

After R13A GREEN, the next stage may build the synthetic multi-candidate
real-engine executor against the now-complete bounded dual-stream surface.
