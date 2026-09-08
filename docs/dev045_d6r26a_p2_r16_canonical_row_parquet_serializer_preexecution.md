# DEV045 D6R26A P2 R16 — Canonical row and Parquet serializer preexecution

Parent R15 GREEN HEAD:

`3df193741befc801d07da1e732d80366fcb29b73`

R15 closed the sequential same-engine candidate-lifecycle gap.

A final review before wiring the canonical R4 runner exposed one remaining
surface:

- R8A already freezes the atomic partition publisher;
- that publisher requires already-produced valid Parquet bytes;
- R1 freezes the exact canonical row schema;
- R8B freezes features and labels;
- but no canonical row builder / Parquet serialization contract had yet been
  frozen.

R16 closes that gap before historical execution authorization.

## Canonical row

R16 builds rows in the exact `R1.ROW_SCHEMA_FIELDS` order and delegates final
semantic validation back to `R1.validate_row_contract`.

The builder carries through:

- exact frozen source identity;
- lane identity and phase;
- candidate identity and price;
- all 25 feature values;
- all feature observability timestamps;
- all fill-horizon states;
- partial-fill fields;
- markout states and values;
- EOF censoring without collapse to no-fill.

## Parquet serialization

The frozen serializer is:

- PyArrow `25.0.1`;
- Parquet format `2.6`;
- data page `1.0`;
- ZSTD level 9;
- dictionary encoding disabled;
- statistics enabled;
- explicit Arrow schema in exact R1 column order;
- 1024-row bounded Python batches.

The serializer consumes an iterable incrementally. It does not construct a
full-day Python row collection.

Only one compressed partition payload is retained at once because the
already-frozen R8A atomic writer accepts bytes.

CI proves:

- exact R1 schema;
- deterministic byte output for identical rows;
- Parquet `PAR1` magic;
- round-trip row equality;
- censoring preservation;
- >2 row-group streaming/batching;
- empty partitions fail closed.

## Scope

R16 is PREEXECUTION ONLY.

It does not open Jan-Jul, start hftbacktest against historical data, write an
attempt marker, write a canonical historical partition, fit models, or
compute PnL.

`P2_ATTEMPT_CONSUMED=NO`.

After R16 GREEN, the next stage is the generic real-lane materializer
preexecution. That layer can finally combine R13A streaming state, R15
same-engine lifecycle, R16 canonical rows, and R8A atomic writer shape.

Only after that generic lane is GREEN should the final R4 one-shot binding be
constructed.
