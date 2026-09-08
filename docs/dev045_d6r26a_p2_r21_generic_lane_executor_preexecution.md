# DEV045 D6R26A P2 R21 — Generic lane executor preexecution

Parent R20 GREEN HEAD:

`eded22d1df87c3f5c3ef8b31c769052b61b377c6`

## Purpose

R20 froze the complete once/day shared context:

- eligible dense feature cache;
- exact exchange-time file-backed midpoint index.

R21 freezes the missing generic lane executor.

The complete per-lane path is now:

`shared R20 context`
→ `fresh exact hftbacktest engine`
→ `one phase-isolated candidate sequence`
→ `fills / cancels / placement outcomes`
→ `R20 midpoint-index markouts`
→ `R18 canonical rows`
→ `R16 Parquet`
→ `R8A atomic LaneArtifact`

R21 remains synthetic-only preexecution.

## Engine isolation

Each of the 40 hypothetical lanes requires a fresh engine.

Within one lane, every candidate runs sequentially on the same engine.

Candidates remain at least five seconds apart.

No two candidate orders in a lane may overlap.

This preserves R15's same-engine boundary while preventing state from one
side/distance/phase lane from contaminating another hypothetical lane.

## Partial-fill safety

R21 deliberately does not accumulate `order.exec_qty`.

Instead each execution response is converted into a fill by:

`previous_remaining_qty - current_order.leaves_qty`

This makes fill accounting independent of any ambiguity about whether a
wrapper exposes per-response or cumulative executed quantity.

The resulting `FillObservation` retains:

- exchange execution timestamp;
- local response timestamp;
- exact execution price;
- response-level fill delta.

Fill quantities remain bounded by the frozen candidate quantity.

## Placement outcomes

The executor preserves all frozen P1 states:

- `POST_ONLY_ACCEPTED`;
- `POST_ONLY_REJECTED_AT_ARRIVAL`;
- `CENSORED_BEFORE_PLACEMENT_OUTCOME`.

Accepted working orders are canceled at the exact five-second boundary when
they have not fully filled.

The corrected R11 cancel-latency semantics remain binding:

the first latency field is the original NEW-order local request timestamp.

## Natural EOF

No fixed event count or wakeup count exists.

If raw feed reaches natural EOF before a candidate's five-second terminal
boundary, that is not itself a failure.

The engine may still complete the frozen order latency/cancel lifecycle.

Labels then use the exact source-observed exchange horizon:

- observable horizons remain no-fill/fill as appropriate;
- unobservable horizons become `CENSORED`.

The synthetic no-fill CI probe deliberately includes the 46-second candidate
whose terminal boundary lies beyond the final synthetic feed event.

## Markouts

R21 does not reconstruct a full Python midpoint history.

For each included fill and markout horizon it queries the R20 file-backed
index using exactly:

`LAST_BBO_MID_WITH_EXCHANGE_TS_LE_TARGET`

CI compares the first exact-engine fill candidate against the already-frozen
R14 `LabelBundle` and requires identical fill states and markout values.

## Scope

R21 does not:

- open Jan-Jul;
- run a historical candidate lane;
- write the P2 attempt marker;
- write canonical Jan-Jul partitions;
- fit models;
- calculate PnL;
- open August;
- open September+;
- open non-BTC data.

`P2_ATTEMPT_CONSUMED=False`.

## Next

After R21 GREEN, the remaining layer is the final successor campaign runner
and binding.

That successor must preserve R3 exactly:

`FIRST_CANONICAL_CANDIDATE_SIMULATOR_LANE_START_AFTER_EXACT_SOURCE_IDENTITY_VERIFICATION`

The attempt marker therefore must be written immediately before the first
historical simulator lane starts — not before source identity verification and
not merely before construction of the first day context.

The final binding will combine:

- all-seven source identity precheck;
- one read-only source open per day;
- one R20 context build per day;
- 40 fresh R8A engines per day;
- R21 lane executor;
- R18/R8A partition verification;
- stop on first failure;
- no resume/rerun after attempt consumption.

Historical execution remains separately unauthorized after R21.
