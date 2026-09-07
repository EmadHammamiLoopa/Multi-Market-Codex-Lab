# DEV045-D6R26A-P2-R4 — Canonical Materialization Runner Pre-Execution

## Status

Pre-execution runner implementation only. Parent R3: `49f3d4c522d5010ff1c957b70e11a2341f11dded`.

R4 freezes the orchestration state machine for Jan–Jul Gen-2 candidate-label materialization without binding any historical file reader or simulator. CI uses fake in-memory hooks only.

## Frozen execution order

1. Validate R3 authorization contract and exact authorization token.
2. Refuse immediately if an attempt marker already exists.
3. Verify all seven frozen source identities before attempt consumption.
4. Write the attempt marker.
5. Open one day only.
6. Run that day’s 40 deterministic lanes.
7. Verify every partition identity.
8. Close the day before moving to the next day.
9. Stop on the first post-consumption failure and write terminal failure evidence.
10. Write the final manifest only after all 7 days / 280 lanes / 280 partitions complete.

The attempt-consumption boundary remains exactly: `FIRST_CANONICAL_CANDIDATE_SIMULATOR_LANE_START_AFTER_EXACT_SOURCE_IDENTITY_VERIFICATION`. The marker is written immediately before that first lane can start.

## Safety semantics

Authorization failure, pre-existing attempt marker, and source identity precheck failure do not consume the attempt. Once the marker is written, any failure is terminal: no automatic retry, resume, or rerun is authorized.

R4 itself does not open or hash Jan–Jul files, import `hftbacktest`, write canonical labels, fit models, calculate PnL, access August/September+, open non-BTC data, perform network acquisition, or authorize live trading.

## Source registry

R4 consumes the corrected frozen R2 registry. June 2026 uses the D6R16 PASS witness SHA256:

`ac97ad27c9d58b3b3e249547b8ae7c74cf2ebfde07965103bd9c8c05d0df1160`

The older D6R17 contract contains a malformed June SHA transcription; R2 documents and guards that known lineage defect while preserving the original D6R16 ingestion evidence as authoritative.

## Next gate

After R4 dedicated CI is GREEN, create the real binding layer that connects the frozen runner to the verified memmap adapter and patched hftbacktest 2.4.4, first under non-historical/synthetic probes. Historical Jan–Jul opening remains forbidden until that real binding is frozen and GREEN.
