# DEV044-T0C Flow/Toxicity Implementation Freeze

Status:

`DEV044_T0C_FLOW_TOXICITY_GREEN_FROZEN`

Date: 2026-09-03

## CI-validated implementation identity

`e70f0249a3b5e3bdfd27118ce7c778e850b9fe41`

This identity contains:

- normalized T10 flow implementation;
- T16 trade-signed VPIN implementation;
- T10 integration into the strategy-state materializer;
- synthetic/unit tests;
- dedicated CI wiring.

Subsequent commits are documentation/handoff only.

## CI verification

GitHub Actions run:

`33760207692`

Run number:

`1156`

Conclusion:

`success`

Relevant jobs:

- `dev044-t0-strategy-contract = success`
- `dev044-t0a-a0-oof = success`
- `dev044-t0b-state-materialization = success`
- `dev044-t0c-flow-toxicity = success`

Follow-up runs #1157 and #1158 also completed successfully.

## Frozen T10 semantics

Source:

`mlofi_l10_250ms`

For W in {1s,16s,32s}:

`normalized_flow_W = sum(flow_W) / sum(abs(flow_W))`

Zero denominator -> 0.

No PnL-based scaling.
No threshold search.
Frozen T10 dead-zone remains +/-0.05.

## Frozen T16 semantics

T16 toxicity state:

`TRADE-SIGNED VPIN`

- 50 equal-volume buckets;
- per-bucket imbalance = abs(buy-sell)/bucket_volume;
- toxicity = mean(last 50 completed bucket imbalances);
- toxicity is unavailable until 50 completed buckets;
- unavailable toxicity -> T16 ABSTAIN;
- frozen veto remains toxicity >=0.80 -> ABSTAIN;
- VPIN may suppress only and cannot create/reverse a signal.

Bucket-volume calibration formula:

`median(Jan-Mar non-overlapping 30m directional BTC trade volume) / 50`

This calibration is NO-PNL and must be frozen before Apr-Jul economic scoring.

## Data guards

- DEV044 PnL unopened.
- Apr-Jul economic tournament unopened.
- Sep-01+ sealed.
- all non-BTC markets sealed.

## Next stage

`DEV044-T0D VPIN BUCKET CALIBRATION`

T0D is NO-PNL and may read Jan-Mar BTC TRADE250 directional volume only.

Current state:

`DEV044_T0C_GREEN_FROZEN_T0D_VPIN_CALIBRATION_AUTHORIZED_NO_PNL`
