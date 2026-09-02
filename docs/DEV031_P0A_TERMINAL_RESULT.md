# DEV031-P0A Terminal Result

Experiment: `DEV031-P0A`

Design version: `event-depth-raw-l2-feasibility-v2`

Official terminal status:

`DATA_READY_EVENT_DEPTH_RAW_L2`

Pass: `True`

## Canonical artifact

`/home/emadh/Multi-Market/evidence/dev031_p0a_event_depth_raw_l2_v1/DEV031_P0A_EVENT_DEPTH_RAW_L2_RESULT.json`

SHA256:

`97f43dccd6a119867aced5de372121a87bc912c20b26b6f032333b761c82cc01`

Bytes:

`11461`

Scientific execution commit:

`fa3b6e50b13191c4a9d31a7c2a5909da84fe08f0`

## Result summary

Seven exact BTCUSDT Jan-Jul 2026 raw `incremental_book_L2` development
files were audited read-only.

Across all seven days:
- 922,305,070 raw L2 rows were audited;
- 119,709,360 amount-zero deletion rows were observed;
- 45 snapshot groups were reconstructed;
- 14,703,433 valid reconstructed book groups were observed after snapshot;
- zero malformed rows on every day;
- zero local timestamp regressions on every day;
- zero book-integrity invalidations on every day;
- no failed preregistered gate.

Every day showed:
- raw within-250ms multi-event structure;
- multiple distinct event-time groups inside 250ms buckets;
- deletions;
- valid snapshot reconstruction;
- live simultaneous depth beyond top-10.

Daily maximum simultaneous minimum-side depth:
- Jan-01: 17,499
- Feb-01: 19,755
- Mar-01: 24,694
- Apr-01: 20,511
- May-01: 22,700
- Jun-01: 20,437
- Jul-01: 14,847

The weakest day still exceeded the preregistered >=11-level requirement by a
very large margin.

## Scientific interpretation

This result establishes that the raw event-time/depth-aware L2 family contains
substantial structural information that was discarded by the earlier frozen
250ms PRICE/top-depth representation.

It does not establish:
- directional predictability;
- opportunity-ranking improvement;
- calibration;
- economic value;
- profitability;
- forward generalization.

The result therefore authorizes a separately preregistered development-stage
event-time/depth representation experiment. It does not authorize opening
Aug-01, Aug-30, Sep-01+, Railway archive data, or any forward confirmation set.

## Permanence

`DEV031-P0A MUST NEVER BE RERUN`

The canonical artifact must not be modified, regenerated, overwritten, deleted,
or replaced.

Historical bookkeeping:
- DEV031-P0 = `PRE_RUN_DESIGN_INVALIDATED`
- first P0A single-process attempt = `ABORTED_THROUGHPUT_NO_ARTIFACT`
- canonical P0A parallel run = frozen PASS
