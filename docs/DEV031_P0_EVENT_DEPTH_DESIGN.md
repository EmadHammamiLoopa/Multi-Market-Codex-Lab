# DEV031-P0 — Frozen Raw L2 Event-Time/Depth Feasibility Design

Status: `DESIGN_FROZEN_AUDIT_NOT_RUN`

## Experiment identity

- Experiment: `DEV031-P0`
- Design version: `event-depth-raw-l2-feasibility-v1`
- Type: read-only structural feasibility audit
- Predictive fitting: forbidden
- Labels/outcomes: forbidden

## Input root

Expected local development root:

`data/v23_phase0dl_l2_raw/incremental_book_L2/BTCUSDT`

Expected files:

- `2026-01-01.csv.gz`
- `2026-02-01.csv.gz`
- `2026-03-01.csv.gz`
- `2026-04-01.csv.gz`
- `2026-05-01.csv.gz`
- `2026-06-01.csv.gz`
- `2026-07-01.csv.gz`

The auditor must not enumerate, open, hash, stat, or read Aug-01 or later.

## Expected schema

`exchange,symbol,timestamp,local_timestamp,is_snapshot,side,price,amount`

Required constants:
- exchange = `binance-futures`
- symbol = `BTCUSDT`
- side in {bid, ask}
- price > 0
- amount >= 0
- is_snapshot in {true,false}

## Time boundary

Each file must contain only local timestamps within its UTC calendar day.

No file outside the seven frozen dates may be opened.

## Audit algorithm

The implementation must stream gzip rows; it must not materialize the full file
in memory.

Per day it records:
- bytes;
- SHA256;
- rows;
- bad rows;
- snapshots;
- rows before first snapshot;
- first/last timestamps;
- distinct local timestamp groups;
- group-size statistics;
- bid/ask counts;
- deletions amount==0;
- distinct touched prices;
- 250 ms bucket occupancy and update-count statistics;
- number of 250 ms buckets with >1 local timestamp group;
- number of 250 ms buckets with >1 raw row;
- exchange/local timestamp offset quantiles;
- post-snapshot incremental update count.

No prices, quantities, or timestamps from individual rows are persisted in the
canonical result beyond first/last day boundary diagnostics.

## Canonical P0 artifact

Proposed output:

`/home/emadh/Multi-Market/evidence/dev031_p0_event_depth_raw_l2_v1/DEV031_P0_EVENT_DEPTH_RAW_L2_RESULT.json`

One-shot write semantics:
- output directory must be absent before run;
- write once atomically;
- if artifact is created, no rerun under the same experiment ID.

## Gates

PASS only if every frozen gate in the research preregistration passes.

No gate may depend on direction labels, first-passage outcomes, model metrics,
PnL, or future data.

## Prohibited

- label construction;
- P3/P10 prediction inspection;
- model fitting;
- feature selection using outcomes;
- target tuning;
- Aug-01;
- Aug-30;
- Sep-01+;
- ETHUSDT;
- trades;
- Railway;
- archive bucket;
- abundant-love;
- downloads/acquisition;
- mutation of any raw file.

## Scientific interpretation

A PASS means only:
`raw event-time/depth information exists and is structurally auditable`.

A PASS does not mean:
- directional predictability;
- economic value;
- tradability;
- improvement over P3.
