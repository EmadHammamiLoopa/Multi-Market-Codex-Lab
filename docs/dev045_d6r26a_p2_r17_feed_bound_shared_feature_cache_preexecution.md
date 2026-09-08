# DEV045 D6R26A P2 R17 — Feed-bound scheduling and shared feature cache

Parent R16 GREEN HEAD:

`6c37c3b7486c5cbd306bcb6b17583cde4e48175e`

## Why R17 exists

Before building the generic real-lane materializer, two historical lessons
must be frozen into its architecture.

### 1. D6R13/D6R14/D6R15 EOF lesson

The earlier full-day ingestion failure proved that a fixed wakeup target must
not define success.

The frozen rule is:

`NATURAL_END_OF_DATA`

R17 therefore derives the candidate scheduling bound from the final observed
local feed timestamp.

The exclusive scheduling bound is:

`last_observed_local_ns + 1`

This retains a candidate whose decision timestamp is exactly the final feed
timestamp, while forbidding all decisions after actual EOF.

Nominal day end remains only a validity envelope. It is not the runtime stop
condition.

Candidates retained near EOF continue to use the existing horizon-level
censoring rules.

### 2. Full-day performance lesson

The canonical Feb source contains approximately 179.6 million rows.

It would be structurally incorrect to perform Python raw-feature decoding
again for each of 40 simulator lanes.

R17 therefore freezes:

- exactly one raw feature-extraction pass per opened day;
- no per-lane Python raw-feature rescan;
- one shared feature cache reused by all 40 lanes;
- dense NumPy storage rather than Python object graphs.

The cache is indexed by the one-second canonical decision grid and contains
the eight side × distance feature cases.

A full 24h grid after the 30-second warmup contains only 86,370 decision
epochs. Eight × 25 float64 values plus decision timestamps and BBO ticks stay
below 150 MiB and well below the frozen 256 MiB limit.

This bounded cache scales with canonical decision epochs, not with the
~180-million-row raw source.

## Scope

R17 is PREEXECUTION ONLY.

It does not:

- open Jan-Jul;
- start hftbacktest on historical data;
- write the attempt marker;
- write canonical labels;
- fit models;
- compute PnL;
- touch August, September+, or non-BTC data.

`P2_ATTEMPT_CONSUMED=NO`.

After R17 GREEN, R18 may implement the generic real-lane materializer using:

- R8A source/engine/writer primitives;
- the shared once/day feature cache required here;
- R15 sequential same-engine candidate lifecycle;
- R16 canonical row + Parquet serializer;
- feed-bound EOF/censor semantics frozen here.

Only after that generic lane is GREEN should the final R4 one-shot campaign
binding be frozen.
