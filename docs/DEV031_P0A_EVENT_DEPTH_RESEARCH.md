# DEV031-P0A — Corrected Event-Time / Depth-Aware Raw L2 Feasibility Audit

Status: `PREREGISTERED_NOT_RUN`

## Why P0A exists

DEV031-P0 was preregistered and synthetic-tested, but before any raw L2 content
was opened two audit-semantic weaknesses were identified:

1. `book_initialization_feasible` only checked snapshot presence plus later
   updates; it did not reconstruct and validate a live bid/ask book.
2. `distinct_prices_touched > 10` did not prove simultaneous live depth beyond
   the top-10 aggregate representation.

No DEV031-P0 canonical artifact was created and no raw L2 content was consumed
under DEV031-P0. Therefore DEV031-P0 is preserved as
`PRE_RUN_DESIGN_INVALIDATED`, not PASS/FAIL.

DEV031-P0A changes only these audit semantics. Scope, dates, symbol, source,
no-label rule, no-model rule, and forward-data prohibitions remain unchanged.

## Frozen scope

- BTCUSDT only
- raw Tardis `incremental_book_L2`
- Jan-01 through Jul-01 2026 consumed development days only
- no ETH
- no trades
- no Aug-01
- no Aug-30
- no Sep-01+
- no Railway/archive/bucket
- no labels
- no model
- no predictive metrics

Canonical raw root:

`/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw/incremental_book_L2/BTCUSDT`

## Corrected book-integrity audit

Rows sharing the same `local_timestamp` are treated as one atomic update group.

For each group:
- if any row has `is_snapshot=true`, clear both sides before applying the group;
- amount > 0 sets that side/price quantity;
- amount == 0 deletes that side/price level;
- after a snapshot group, the book is initialized only if:
  - bid side nonempty;
  - ask side nonempty;
  - best bid < best ask;
- after initialization, any crossed/empty state invalidates the book until a
  later valid snapshot group.

P0A records:
- snapshot groups;
- valid-book groups after snapshot;
- integrity invalidations;
- maximum simultaneous live bid levels;
- maximum simultaneous live ask levels;
- maximum simultaneous minimum-side depth = min(bid_levels, ask_levels).

## Corrected novelty gate

Depth beyond the preserved top-10 view is established only if, on every day,
there is at least one valid reconstructed book state with:

`bid_levels >= 11 AND ask_levels >= 11`

Historical distinct touched prices may still be recorded descriptively but do
not satisfy this gate.

Within-grid event-time novelty still requires on every day:
- at least one 250 ms bucket with >1 raw row;
- at least one 250 ms bucket with >1 distinct local_timestamp group;
- nonzero amount==0 deletions.

## PASS gates

All seven days must satisfy:
1. exact file/schema/scope;
2. zero malformed rows;
3. nondecreasing local timestamps;
4. at least one snapshot group;
5. at least one valid reconstructed book after snapshot;
6. nonzero incremental rows after a valid initialization;
7. nonzero deletions;
8. multirow 250 ms buckets;
9. multigroup 250 ms buckets;
10. simultaneous valid depth >=11 levels on both sides at least once;
11. all forward/storage guards false.

Terminal statuses:
- `DATA_READY_EVENT_DEPTH_RAW_L2`
- `FAIL_EVENT_DEPTH_RAW_L2_INCOMPLETE`
- `INCONCLUSIVE_EVENT_DEPTH_RAW_L2_AUDIT`

PASS means structural availability only, not predictability or economic value.
