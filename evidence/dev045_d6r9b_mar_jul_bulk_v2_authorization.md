# DEV045 D6R9B — Mar–Jul Bulk V2 Materialization

Status: **EXECUTION-READY AFTER EXACT CI GREEN**

Parent D6R9A head: `d9972bf8947466d91728a61dfa39bf5c1ed1f682`. D6R9A is frozen PASS and never rerun.

Purpose: materialize the five remaining already-provenanced BTCUSDT days in fixed chronological order using only the structurally bounded V2 converter:

`2026-03-01 → 2026-04-01 → 2026-05-01 → 2026-06-01 → 2026-07-01`.

All raw byte sizes, SHA256 identities, D5B frozen row counts, and D6R8C scratch requirements were frozen before these conversions. Production settings remain chunk rows 250,000, merge fan-in 8, hftbacktest 2.4.4, and the 6 GiB current-RSS abort guard.

Each day is an independent canonical unit with its own attempt marker, evidence JSON and final NPY output. The bulk command may skip only a previously frozen PASS day. If a day has any marker/evidence/output combination that is not a complete PASS, that day is frozen non-PASS and the bulk process stops; it is never rerun. A pre-marker resource or metadata failure consumes no attempt.

D6R9B does not rerun Feb or Jan. It does not invoke the old converter or upstream Tardis converter and does not perform whole-output `np.load`/memmap. It opens no August, September+, non-BTC, policy replay, historical PnL, Railway or live-trading surface.

After all five days PASS, Jan/Feb–Jul canonical feed artifacts are available for the next ingestion-validation/economic preparation step. Risk-envelope numbers must still be frozen before historical PnL is opened.
