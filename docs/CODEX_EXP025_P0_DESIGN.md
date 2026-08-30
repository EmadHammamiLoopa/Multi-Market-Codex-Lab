# CODEX-EXP-025-P0 Continuous Multi-Market Acquisition Design

Status: **LOCAL INFRASTRUCTURE DESIGN — NOT DEPLOYED**

Experiment identifier: `CODEX-EXP-025-P0`

Starting implementation parent:

`a017aebf51119e426c3c8978da67ab068e5af0de`

EXP025-P0 is private quantitative-system infrastructure. It is not a
predictive experiment, academic-paper experiment, model evaluation, or trading
system. It acquires and seals prospective quote data without constructing any
feature, target, label, forecast, direction, PnL, leverage, or performance
metric.

Development of this version is local and synthetic only. It does not inspect
any August prospective artifact, access Railway, access a network resource,
or modify the frozen EXP024 pipeline.

## Scope and initial markets

The exact initial symbol set is:

1. `BTCUSDT`
2. `ETHUSDT`
3. `SOLUSDT`

The initial adapter uses the same public Binance USD-M Futures `bookTicker`
WebSocket source family as EXP024. One asynchronous process consumes one
combined multi-stream connection. Every accepted quote retains its exact
symbol and is routed only to that symbol's state and daily file.

The collector has no REST client and no backfill, resume, repair, or merge
interface. Missing time remains missing.

## Two consumers, one acquisition boundary

The long-term system has two logically separate consumers:

```text
                         normalized causal quote events
                                      |
                 +--------------------+--------------------+
                 |                                         |
      research data-bank path                    future live path
                 |                                         |
       immutable daily raw files                online feature engine
                 |                              (not EXP025-P0)
       deterministic 250 ms grids                        |
                 |                              ranking/risk/execution
       audits + sealed inventory                (not EXP025-P0)
```

EXP025-P0 implements only the left path and the shared normalized-event
boundary. The future live consumer must be a separate module and deployment.
It must never consume sealed holdouts automatically.

## Feed-adapter boundary

A future feed adapter should implement this conceptual asynchronous interface:

```python
class QuoteFeedAdapter(Protocol):
    async def connect(self) -> AsyncContextManager[QuoteEventStream]: ...
    def normalize(self, native_event: object, receive_clock: ReceiveClock) \
            -> NormalizedQuote | RejectedEvent: ...
```

Every accepted native event normalizes to the common internal quote schema:

| Field | Meaning |
|---|---|
| `market` | Stable market family identifier |
| `symbol` | Exact canonical instrument symbol |
| `venue` | Source venue |
| `asset_class` | Stable asset-class identifier |
| `receive_timestamp_utc` | Local causal receive timestamp |
| `bid` | Best bid price |
| `ask` | Best ask price |
| `bid_size` | Best bid quantity |
| `ask_size` | Best ask quantity |
| `source_timestamp_if_available` | Native source timestamp, never the causal clock |
| `connection_epoch` | Locally assigned connection epoch |

Planned adapter families are:

- crypto: Binance initially;
- FX: a future provider adapter;
- listed futures: a future provider adapter;
- gold: a future spot or futures provider adapter;
- equity-index futures: a future provider adapter.

No paid provider is selected or implemented here. A later implementation may
evaluate Databento or another provider without changing the normalized schema.

## Concurrency and isolation

The combined WebSocket supplies all three Binance streams through one
connection. Routing occurs by the payload's exact canonical `s` field.

Each symbol owns:

- independent validation clocks;
- independent accepted/rejected counters;
- independent latest quote state;
- an independent bounded asynchronous write queue;
- an independent gzip writer task.

An inactive symbol does not delay active symbols. A slow writer does not block
feed routing until its own bounded queue is exhausted. Queue exhaustion is a
hard, symbol-identified collection error; the collector never drops data
silently. The affected symbol/day receives an immutable
`.operational-failure.json` marker, and finalization refuses that partition.
Unsupported symbols are rejected and cannot mutate any supported-symbol
state.

Writer shutdown is bounded to 30 seconds in production. That single timeout
covers enqueueing the stop sentinel, draining all previously accepted records,
closing gzip, flushing, and fsync. Timeout raises a symbol-specific operational
failure and writes the same immutable failure marker. The worker is not
silently cancelled and queued records are not declared durable. A rollover
with any writer-close failure stops before next-day files are opened.

A new connection increments one shared connection epoch. Connection attempt,
close, error, and process-stop events invalidate every symbol's latest state.
After `connection_opened`, each symbol independently requires a fresh quote.

## Daily immutable partitions

Raw layout under an output root is:

```text
multimarket/bookticker/<SYMBOL>/<YYYY-MM-DD>.jsonl.gz
```

Files are created with exclusive creation. Existing files—including empty or
interrupted files—are never opened for append and never overwritten.

The collector stores a process identity containing:

- random collector run ID;
- operating-system process ID;
- full frozen implementation commit;
- collector start wall-clock nanoseconds and UTC rendering.

Every symbol/day starts with one `day_started` metadata record containing the
process identity, exact symbol set, source, venue, asset class, day bounds, and
whether the process was armed before that day's UTC midnight.

At rollover the collector:

1. queues `day_rollover` into every completed-day file;
2. drains and closes all symbol writers concurrently;
3. finishes gzip streams and fsyncs their underlying files;
4. exclusively creates the three next-day files;
5. records new `day_started` metadata;
6. records `connection_carried` when the WebSocket remains connected;
7. requires a fresh same-day quote before grid state becomes valid.

The process never carries a prior-day quote into the next day's grid.

If the process begins during a UTC day, all three initial files are classified
`PARTIAL_START_DAY`. The first potentially full day is the next UTC day after
an observed rollover, because only then was the process armed before midnight.

## Quote acceptance and transport semantics

For each symbol independently, accept a quote only when:

- the symbol is in the exact initial set and matches its route;
- bid, ask, bid size, and ask size parse as finite numbers;
- bid and ask are positive;
- ask is strictly greater than bid;
- quantities are non-negative;
- local wall receive time does not reverse relative to the prior accepted
  quote for that symbol;
- local monotonic receive time does not reverse relative to the prior accepted
  quote for that symbol.

Rejected events never update quote state. Local receive time is the causal
clock. Native timestamps are provenance only and cannot backdate a quote.

Connection attempt, close, transport error, rollover, and collector stop
invalidate state. A new or carried epoch requires a fresh quote in the current
daily partition. There is no REST reconstruction or silent gap fill.

## Deterministic daily finalization

Finalization is per symbol/day and sequential in raw-file order, with a
bounded-memory SQLite external-sort fallback if transport ordering is found to
be inconsistent. It creates:

```text
multimarket/evidence/<SYMBOL>/<DAY>_BOOKTICKER250.csv
multimarket/audits/<SYMBOL>/<DAY>_AUDIT.json
multimarket/inventory/<SYMBOL>/<DAY>.json
```

A full-day grid has exactly 345,600 rows at 250,000 microsecond spacing:

```text
00:00:00.000
00:00:00.250
...
23:59:59.750 UTC
```

The CSV schema is exactly the EXP024 grid schema:

1. `local_timestamp_us`
2. `best_bid`
3. `best_ask`
4. `mid`
5. `book_valid`
6. `quote_age_ms`
7. `connection_epoch`
8. `source_update_id`
9. `exchange_event_time_ms`
10. `exchange_transaction_time_ms`

At grid timestamp `t`, use only the latest accepted quote with local receive
time at or before `t`. There is no interpolation, future use, prior-day fill,
or backfill. A quote is valid through exactly 2,000 ms of age and becomes stale
after that. Epoch invalidation and fresh-quote requirements are identical to
EXP024.

Finalization records coverage, transport/reconnect diagnostics, rejections,
accepted quote bounds, raw/grid bytes, and raw/grid SHA-256 values. Grid,
audit, inventory, and `.part` paths are one-shot and immutable.
Finalization also rejects any raw partition carrying an operational-failure
marker, even if its gzip stream later becomes readable; such a partition can
never be advertised as `FULL_DAY_DATA_READY`.

## Daily status mapping

`FULL_DAY_DATA_READY` requires:

- exactly one exact `day_started` record;
- collector start strictly before day start;
- exact day, symbol, process, source, and commit metadata;
- an observed next-day rollover at or after day end;
- at least one connection epoch;
- exactly 345,600 grid rows and exact timestamps;
- at least 99% valid coverage;
- no accepted invalid price, negative quantity, wrong symbol, clock reversal,
  out-of-day quote, future quote, or malformed transport record;
- recorded raw/grid hashes and byte sizes;
- all no-analysis guards false.

`PARTIAL_START_DAY` identifies an otherwise well-formed partition whose
collector process started at or after that day's midnight. It is never a full
prospective holdout.

`FAIL_DATA_INTEGRITY` applies when a non-partial day fails one or more data
integrity conditions. `INVALID` applies to implementation, provenance, input,
or one-shot execution errors.

These are acquisition statuses, not predictive results.

## Sealed holdout inventory

Each immutable inventory entry contains metadata only:

- experiment, market, venue, and asset class;
- symbol and day;
- acquisition status;
- raw/grid paths, SHA-256 values, and byte sizes;
- valid-grid coverage;
- frozen collector commit and collector run ID;
- creation time.

It contains no feature, target, label, AUC, AP, future return, direction, PnL,
leverage, model probability, or strategy score. Counting
`FULL_DAY_DATA_READY` entries, minus symbol/day keys present in a separate
append-only analytical-opening ledger, answers questions such as how many
untouched full ETH days exist without opening a grid or evaluating outcomes.
That ledger also contains metadata only (symbol, day, consuming protocol ID,
frozen protocol commit, and opening time). EXP025-P0 never creates an opening
record because it never opens a holdout analytically; a later authorized
protocol is responsible for recording its opening.

Continuous acquisition does not make every day an independent confirmation
for every hypothesis. A future protocol may designate a sealed day only when
that protocol and its implementation were frozen before that day was opened
analytically for the hypothesis. EXP025 performs no automatic scoring.

## Future deployment architecture — not executed

A future deployment should use one dedicated acquisition service with:

- a frozen image/commit and persistent `/data` volume;
- one long-running process and one combined Binance WebSocket connection;
- health checks based only on process/queue/transport metadata;
- restart policy that preserves interrupted files and refuses append;
- a separate offline finalizer job after each observed UTC rollover;
- immutable audit and inventory storage with independent backup;
- no credentials or trading permissions for the acquisition service.

The future live stream should be a separate service consuming a fan-out of the
same normalized event boundary. It must have separate credentials, risk
controls, and release governance. None of that service is implemented or
deployed by EXP025-P0.
