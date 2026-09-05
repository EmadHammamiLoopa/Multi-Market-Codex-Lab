# DEV045 D6R8EG — Canonical Result

Status: **FROZEN PASS / NEVER RERUN**

Execution head: `e8d87ed29998e1af5a037ff2290c72cdfe967344`.

Canonical marker SHA256: `ccbf010be8a0493da30e22a8c51bbc98961bd5d11635eadd2a8403f4d7ada95f`.
Canonical evidence SHA256: `c912e7a8233995aed3abfd4d911e35b10097f46e434f56502f09dbb41a5806b9`.

The exact Jan 10-minute real slice passed raw identity and semantic identity. Upstream hftbacktest 2.4.4, the frozen old converter, and V2 each produced exactly 503,934 64-byte events with identical output SHA256 `60ebc2aec273976c12526f7c49159d005368388a0f9d5993af269cc9753ffaf7`.

Pairwise exact fieldwise NaN-equal parity passed for upstream-vs-old, upstream-vs-V2, and old-vs-V2. V2 reported base rows 496,224, final rows 503,934, chunk rows 250,000, four initial sort runs, one exchange merge level, one local merge level, and peak RSS 457,990,144 bytes.

D6R8EF remains permanently frozen FAIL and was not rerun. Jan full-day was not rerun. Feb-Jul, August, September+, non-BTC, policy replay, historical PnL, Railway and live trading remained closed during D6R8EG.

This closes the real 10-minute converter-parity question. No further old/upstream full-day parity run is required before the separately bounded V2 full-day resource proof.
