# DEV044-T0C — T10 Normalized Flow and T16 VPIN Toxicity Design

Status:

`IMPLEMENTED_CI_PENDING_NO_PNL`

Date: 2026-09-03

## Purpose

Resolve the final two DEV044-T1 blockers before any economic scoring:

- T10 normalized multi-level flow persistence.
- T16 toxicity veto.

T0C remains strictly NO-PNL.

## T10 frozen normalization

Source:

`mlofi_l10_250ms`

For each W in {1s,16s,32s}:

`normalized_flow_W = sum(flow_250ms over W) / sum(abs(flow_250ms over W))`

Zero denominator -> 0.

Properties:

- causal;
- dimensionless;
- bounded to [-1,1];
- preserves the already frozen T10 dead-zone threshold +/-0.05;
- no train fit;
- no full-history scale estimate;
- no PnL-based calibration.

T10 therefore no longer requires a raw S15 magnitude interpretation.

## T16 frozen toxicity method

Primary toxicity state:

`TRADE-SIGNED VPIN`

Existing project raw trade data already classifies Tardis trades causally by
local timestamp into buy/sell/unknown.

Unknown trades contribute to neither directional side.

### Equal-volume buckets

Use actual buy/sell directional quantity.

A 250ms bin may span multiple volume buckets; its buy/sell composition is
allocated proportionally when a bucket boundary is crossed.

Per completed bucket:

`imbalance = abs(buy_volume - sell_volume) / bucket_volume`

Thus each bucket imbalance is in [0,1].

### VPIN state

Use exactly:

`50 completed equal-volume buckets`

`toxicity = mean(last 50 bucket imbalances)`

The score is bounded [0,1].

The already frozen T16 veto remains unchanged:

`toxicity >= 0.80 -> ABSTAIN`

No threshold search.

### Bucket-volume calibration

The bucket-volume constant is calibrated without PnL using Jan-Mar BTC trade
volume only.

Frozen formula:

1. partition Jan-Mar TRADE250 directional volume into non-overlapping 30-minute
   calendar blocks;
2. compute buy+sell directional quantity in each positive-volume block;
3. take the median 30-minute volume;
4. divide by 50.

Therefore:

`VPIN_BUCKET_VOLUME = median(Jan-Mar 30m directional volume) / 50`

Rationale:

- no future Apr-Jul information;
- no PnL information;
- approximately aligns a 50-bucket toxicity window to the H1800 regime;
- fixed once before T1.

The numeric bucket value must be materialized/frozen in a no-PnL audit before
T1.

### Warm-up

Until 50 completed buckets exist in a day:

`toxicity = unavailable`

T16 must ABSTAIN on those timestamps.

Do not fill toxicity with zero.

The volume clock resets at each isolated project day because the project
development days are separated by large calendar gaps.

## Implementation

`src/multimarket/dev044_t0c_flow_toxicity.py`

T10 is integrated into:

`src/multimarket/dev044_t0b_state_materializer.py`

Tests:

`tests/test_dev044_t0c_flow_toxicity.py`

## Literature/implementation note

VPIN uses equal-volume buckets and normalized absolute buy/sell imbalance as an
order-flow-toxicity state. Recent Bitcoin work also reports economically
relevant links between VPIN and subsequent price jumps.

DEV044 uses directly trade-signed buy/sell volume because the project already
has causally classified Binance trade data. It does not use a bulk-volume
classification approximation.

T16 is a veto only. VPIN never creates or reverses a directional action.

## T1 readiness

After this implementation:

- T10 logic is resolved.
- T16 logic is resolved.
- T16 still needs one no-PnL numeric bucket-volume calibration artifact on
  Jan-Mar before full T1 readiness.

No strategy PnL is authorized yet.

## Forward guards

- DEV044 PnL: unopened
- Sep-01+: sealed
- non-BTC markets: sealed
- maker family: separate

## Current state

`DEV044_T0C_IMPLEMENTED_CI_PENDING_VPIN_CALIBRATION_NEXT_NO_PNL`
