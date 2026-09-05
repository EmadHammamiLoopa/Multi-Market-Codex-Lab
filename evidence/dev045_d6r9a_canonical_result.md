# DEV045 D6R9A — Feb 1 Full-Day V2 Canonical Result

Status: **FROZEN PASS / NEVER RERUN**

Execution head: `d9972bf8947466d91728a61dfa39bf5c1ed1f682`.

Canonical marker SHA256: `66ffb16ae49ef37740e51a0e9b3d562ab2724762d4290ecf8e594a62b742d4c7`.
Canonical evidence SHA256: `54afd16ca610b76de0658d68764b661335fcda23e3ae3ca4ce4de93c57c199d9`.

BTCUSDT `2026-02-01` raw provenance matched exactly:

- trades: 57,631,972 bytes, SHA256 `dfd19ab53abbc90118ce3c861521ecb17dbed6ce7bcc7410c07f296460454508`;
- incremental_book_L2: 865,907,076 bytes, SHA256 `a1e9fc0fcc20d309d171ed1b6367ebe17948c84dd025a07a5d13c80f0b023cc4`.

The structurally bounded V2 converter ran with the frozen production settings: chunk rows 250,000, merge fan-in 8, hftbacktest 2.4.4, 6 GiB RSS abort guard. It produced:

- base event rows: **172,721,713**;
- final event rows: **179,584,138**;
- initial sort runs: **1,382**;
- exchange merge levels: **4**;
- local merge levels: **4**;
- final NPY bytes: **11,493,385,088**;
- output SHA256: `d757d2ac32a29b0ac587323e115779c466068c6c0eba4270226b9c4109254cbc`;
- peak RSS: **478,396,416 bytes**;
- output dtype itemsize: **64**;
- NPY version: **1.0**.

The attempt started at `2026-09-05T18:12:08.307079+00:00` and completed at `2026-09-05T18:43:21.585040+00:00` (~31m13s).

No Jan rerun, old converter, upstream converter, other Feb-Jul day, August, September+, non-BTC, policy replay, historical PnL, Railway or live-trading surface was opened.

This closes the new full-day V2 resource proof. D6R9A must never be rerun.
