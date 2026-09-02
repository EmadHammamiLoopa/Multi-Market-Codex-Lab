# DEV031-P0A — Frozen Corrected Raw L2 Audit Design

Experiment: `DEV031-P0A`
Design version: `event-depth-raw-l2-feasibility-v2`

This supersedes DEV031-P0 before any raw-content execution because P0's
initialization and depth-novelty gates were too weak.

Canonical input root:
`/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw/incremental_book_L2/BTCUSDT`

Exact input files are Jan-01 through Jul-01 2026 only.

Canonical output:
`/home/emadh/Multi-Market/evidence/dev031_p0a_event_depth_raw_l2_v1/DEV031_P0A_EVENT_DEPTH_RAW_L2_RESULT.json`

The auditor must stream gzip rows and may not enumerate or open any file outside
the seven exact development paths.

Atomic group key: `local_timestamp`.

Book semantics:
- snapshot group resets book;
- amount zero deletes level;
- positive amount sets level;
- valid initialized book requires nonempty bids/asks and best_bid < best_ask;
- invalidity after initialization is latched until next valid snapshot.

Novel live-depth metric:
`max_simultaneous_min_side_depth`.

Depth-novelty PASS requires:
`max_simultaneous_min_side_depth >= 11` on every day.

No labels, target outcomes, model fitting, thresholding, PnL, forward data,
downloads, ETH, trades, or Railway are allowed.
