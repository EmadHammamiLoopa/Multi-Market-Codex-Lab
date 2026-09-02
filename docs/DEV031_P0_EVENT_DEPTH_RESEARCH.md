# DEV031-P0 — Event-Time / Depth-Aware Raw L2 Feasibility Audit

Status: `PREREGISTERED_NOT_RUN`

## Motivation

DEV030-P8, P9, and P10 closed the Jan-Jul PRICE-only temporal sequence representation family.

P10 terminal result:
`FAIL_PRICE_MINIROCKET_NO_STABLE_INCREMENTAL_VALUE`

P10 artifact SHA256:
`10ff1d422d0a06cbe3a99de873ecbfab2d21a8881145ab4d7be0754a61c5c2e9`

DEV031 is a materially different information-family audit. It does not attempt
another model architecture on the same PRICE representation.

## Existing raw source

The repository already contains a Tardis acquisition path for:
- `incremental_book_L2`
- `trades`

The raw L2 schema used by the frozen acquisition/audit code is:

`exchange,symbol,timestamp,local_timestamp,is_snapshot,side,price,amount`

The current L2 reconstruction code applies every incremental price-level update
to a price-keyed book and produces a 250 ms grid with:
- best bid/ask;
- L1 quantities;
- spread;
- microprice;
- L5/L10 depth totals;
- OBI L1/L5/L10.

Therefore the raw L2 stream contains information that is not preserved in the
250 ms feature representation, including:
- event arrival timing inside each 250 ms interval;
- count of additions/updates/deletions;
- same-message groups sharing local_timestamp;
- price-level identities;
- depth beyond top 10;
- order of L2 update groups through time;
- event-time replenishment/depletion paths.

This is the candidate genuinely new information family.

## DEV031-P0 question

For BTCUSDT consumed Jan-Jul development days only, do the already-acquired
raw `incremental_book_L2` files contain sufficiently complete and causal
event-time/depth information to justify one future bounded DEV031 predictive
experiment?

P0 is availability/novelty/quality only.

It must not:
- construct predictive labels;
- inspect direction outcomes;
- fit a model;
- compute predictive metrics;
- inspect P3/P10 predictions;
- open August/September;
- access Railway/archive storage.

## Frozen scope

Symbol:
`BTCUSDT`

Development days:
- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

Raw data type:
`incremental_book_L2`

Explicitly excluded from P0:
- ETHUSDT;
- trades;
- Aug-01 sealed confirmation;
- Aug-30;
- Sep-01+;
- Railway/object archive.

## Read-only audit measurements

For each Jan-Jul raw L2 file, P0 may inspect only structural/input statistics:

1. file existence, bytes, SHA256;
2. exact header;
3. row count;
4. first/last local timestamp;
5. first/last exchange timestamp;
6. local timestamp monotonicity;
7. bad-row count;
8. snapshot count;
9. rows before first snapshot;
10. distinct local_timestamp groups;
11. fraction of rows in multi-row groups;
12. distribution of group sizes;
13. bid/ask row counts;
14. amount==0 deletion count/fraction;
15. distinct price levels touched;
16. maximum/median updates per 250 ms bucket;
17. fraction of nonempty 250 ms buckets;
18. update counts per 250 ms bucket;
19. whether valid reconstructed book can be established after snapshot;
20. causal timestamp relation diagnostics only:
    exchange timestamp vs local timestamp offset distribution.

P0 may not summarize any quantity conditional on LONG/SHORT/NONE outcomes.

## New-information novelty checks

P0 must demonstrate structural information that cannot be reconstructed from the
existing 250 ms Phase0DL features.

At least these must be nontrivial:
- more than one raw update group within some 250 ms buckets;
- nonzero level deletions (`amount==0`);
- more distinct touched price levels than the preserved top-10 aggregate view;
- event counts/group sizes vary over time;
- raw stream includes within-grid sequencing lost by 250 ms sampling.

This is an information-availability statement only, not predictive evidence.

## Feasibility gates

P0 PASS requires all:

1. all seven BTCUSDT Jan-Jul raw L2 files exist;
2. exact expected header on all seven;
3. zero malformed rows;
4. nondecreasing local timestamps on all seven;
5. at least one snapshot per day;
6. book initialization feasible after snapshot on all seven;
7. nonzero incremental events after initialization on all seven;
8. nonzero deletions on all seven;
9. multi-event/multi-group 250 ms buckets occur on all seven;
10. raw event-time structure demonstrably contains information discarded by the
    250 ms aggregate representation;
11. no forward/sealed data opened.

Terminal statuses:
- `DATA_READY_EVENT_DEPTH_RAW_L2`
- `FAIL_EVENT_DEPTH_RAW_L2_INCOMPLETE`
- `INCONCLUSIVE_EVENT_DEPTH_RAW_L2_AUDIT`

No predictive claim can be made from a P0 PASS.

## Follow-up rule

If P0 passes, DEV031-P1 design may be considered.

P1 must freeze exactly one bounded representation before any predictive outcome
inspection. Candidate mechanisms may include event counts, level-touch dynamics,
queue/depth changes, or event-time sequences, but P0 itself must not select among
them based on labels.

If P0 fails, do not acquire/open forward data to rescue it. Diagnose whether the
failure is raw-data availability, snapshot integrity, or event-time coverage.

## Prior evidence preserved

Do not collapse:
- EXP024-P1 opportunity-ranking success;
- DEV030-P3 direction baseline success;
- DEV030-P4 touch component success;
- DEV030-P8/P9/P10 PRICE-only representation failures.
