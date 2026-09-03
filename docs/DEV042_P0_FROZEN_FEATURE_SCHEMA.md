# DEV042-P0 Frozen Feature Schema

Status:

`FEATURE_SCHEMA_FROZEN_BEFORE_ANY_DEV042_REAL_FEATURE_AUDIT_OUTPUT`

Date: 2026-09-03

Target parent:

`H1800_B32`

This document freezes exact causal feature construction before any DEV042
real-data feature/support audit output, label construction, or model fit.

## 1. Source

Authorized source is the existing frozen BTCUSDT Phase0DL FEATURE250 lineage.

Exact source columns are already frozen by DEV030:

- local_timestamp_us
- best_bid / best_ask / mid
- book_valid / l0_valid / l1_valid / l2_valid
- the exact 43 stored L0/L1/L2 feature columns

No new raw market source is introduced.

## 2. Decision grid

Features are emitted only at exact minute decisions:

`timestamp_us % 60_000_000 == 0`

All historical summaries end at the decision timestamp.

No feature uses any row after the decision timestamp.

## 3. Minute-endpoint summary policy

Long-horizon summaries use exact minute endpoints rather than every 250 ms bin.

Reason:

- target horizon is 30 minutes;
- model actions occur only once per minute;
- source OFI/L2 variables at each endpoint are already causal 250ms/1s/3s
  microstructure summaries;
- requiring every 250ms bin across 30 minutes would turn isolated source-mask
  events into very long support deletions.

No interpolation or imputation is allowed.

Every required endpoint must exist, have the required validity mask, and be
finite.

## 4. F0 PRICE_MOMENTUM exact order

Price return lags:

- price_ret_bps_60s
- price_ret_bps_180s
- price_ret_bps_300s
- price_ret_bps_600s
- price_ret_bps_900s
- price_ret_bps_1800s

Definition:

`10000 * ln(mid_t / mid_{t-lag})`

Realized-volatility features from exact one-minute log returns:

- price_rv_bps_300s
- price_rv_bps_900s
- price_rv_bps_1800s

Definition:

population standard deviation of one-minute log-return bps within the inclusive
causal window.

Range features:

- price_range_bps_300s
- price_range_bps_900s
- price_range_bps_1800s

Definition:

`10000 * ln(max(mid_window) / min(mid_window))`

Momentum contrasts:

- price_momentum_contrast_60_300
- price_momentum_contrast_300_900
- price_momentum_contrast_900_1800

Definitions:

- ret_60 - ret_300
- ret_300 - ret_900
- ret_900 - ret_1800

F0 count:

`15`

## 5. F1 PRICE_PLUS_OFI

F1 contains all F0 features plus exactly five source flow series:

- ofi_l1_1s
- mlofi_l5_1s
- mlofi_l10_1s
- trade_qty_imbalance_1s
- trade_count_imbalance_1s

For each series serialize:

### Current endpoint

- <name>__last

### Exact minute-endpoint windows

Windows:

- 60 s
- 300 s
- 900 s
- 1800 s

For each window:

- <name>__mean_<window>s
- <name>__std_<window>s

No sum is used because source OFI variables already encode short-window flow
magnitudes and window lengths differ.

F1 OFI additions:

`5 * (1 + 4*2) = 45`

F1 total count:

`60`

## 6. F2 PRESSURE_CAPACITY

F2 is an independent microstructure representation and does NOT automatically
contain F0.

Source depth columns are confirmed by the frozen C++ materializer to equal:

`log1p(actual depth quantity)`

so exact capacity is reconstructed with:

`expm1(log_depth)`

### F2 snapshot-derived exact order

1. spread_bps
2. microprice_minus_mid_bps
3. obi_l1
4. obi_l5
5. obi_l10
6. depth_log_imbalance_l5
7. depth_log_imbalance_l10
8. bid_depth_concentration_log
9. ask_depth_concentration_log
10. pressure_capacity_l5
11. pressure_capacity_l10
12. replenish_support_norm_l5
13. replenishment_imbalance
14. depletion_imbalance
15. liquidity_fragility_l5

Definitions:

`depth_log_imbalance_l5 = log_bid_depth_l5 - log_ask_depth_l5`

`depth_log_imbalance_l10 = log_bid_depth_l10 - log_ask_depth_l10`

`bid_depth_concentration_log = log_bid_depth_l5 - log_bid_depth_l10`

`ask_depth_concentration_log = log_ask_depth_l5 - log_ask_depth_l10`

Let:

- B5 = expm1(log_bid_depth_l5)
- A5 = expm1(log_ask_depth_l5)
- B10 = expm1(log_bid_depth_l10)
- A10 = expm1(log_ask_depth_l10)
- O = ofi_l1_1s
- eps = 1e-12

Then:

`pressure_capacity_l5 = max(O,0)/(A5+eps) - max(-O,0)/(B5+eps)`

`pressure_capacity_l10 = max(O,0)/(A10+eps) - max(-O,0)/(B10+eps)`

Let BR/AR/BD/AD be the frozen 1-second bid/ask replenish/deplete values.

`replenish_support_norm_l5 = (BR + AD - AR - BD)/(B5 + A5 + eps)`

`replenishment_imbalance = (BR - AR)/(BR + AR + eps)`

`depletion_imbalance = (AD - BD)/(AD + BD + eps)`

`liquidity_fragility_l5 = spread_bps/(1 + log1p(B5 + A5))`

### F2 temporal summaries

For exactly these six derived/source series:

- spread_bps
- microprice_minus_mid_bps
- depth_log_imbalance_l5
- pressure_capacity_l5
- replenish_support_norm_l5
- liquidity_fragility_l5

use exact minute-endpoint windows:

- 60 s
- 300 s
- 900 s

and statistics:

- mean
- std

F2 temporal additions:

`6 * 3 * 2 = 36`

F2 total count:

`15 + 36 = 51`

## 7. F3 / F4 common combined order

C3_COMBINED_LOGIT and C4_COMBINED_HGB use the exact same combined feature
matrix.

Combined order:

1. all 15 F0 features;
2. the 45 OFI additions from F1, excluding duplicated F0;
3. all 51 F2 features.

Combined count:

`111`

No feature appears twice.

## 8. Frozen family dimensions

- C0_PRICE_LOGIT: 15
- C1_OFI_LOGIT: 60
- C2_PRESSURE_CAPACITY_LOGIT: 51
- C3_COMBINED_LOGIT: 111
- C4_COMBINED_HGB: 111

## 9. Exact causal lookback bounds

F0 maximum explicit lookback:

`1800 s`

F1 maximum minute-endpoint summary lookback:

`1800 s`

The longest F1 source feature used is a 1-second source aggregate, so maximum
raw-source history is:

`1801 s`

F2 maximum temporal window:

`900 s`

The L2 source variables used have <=1 second internal lookback, so maximum raw
F2 source history is:

`901 s`

Global maximum raw lookback:

`1801 s`

No feature may read earlier than decision -1801s or later than decision.

## 10. Validity contracts

F0 requires:

- all needed minute mids finite and >0;
- book_valid at every required price endpoint.

F1 OFI additions require:

- l1_valid at every exact minute endpoint used by the corresponding summary;
- all five source flow values finite.

F2 requires:

- l2_valid at every exact minute endpoint used;
- all required L0/L1/L2 source values finite;
- reconstructed depths finite and >=0;
- derived features finite.

No NaN imputation.

No forward fill.

No missing-endpoint substitution.

## 11. Common feature support

For each day:

`COMMON_FEATURE_SUPPORT = F0_VALID & F1_VALID & F2_VALID`

The same common timestamp sequence will later be used by C0-C4.

P0 must serialize:

- exact ordered feature names/hashes;
- native F0/F1/F2 support counts;
- common support count;
- common-support retention vs 1440 minute decisions;
- common support timestamp SHA256;
- first/last common timestamp;
- invalid reason counts.

P0 must NOT construct labels.

## 12. P0 pass contract

P0 passes only if:

1. source manifest identities match frozen Jan-Jul hashes;
2. exact seven-day BTC calendar;
3. every day has 1440 exact minute decisions;
4. feature-family dimensions equal 15/60/51/111/111;
5. feature names/order are identical to this document;
6. all common-support feature matrices are finite;
7. common support is non-empty every day;
8. pooled common-support retention >= 0.90;
9. common-support timestamp order is strict and unique;
10. no label function is invoked;
11. no estimator is fit;
12. no economic output is calculated;
13. Sep-01+ and other markets remain sealed.

If retention <0.90:

`DEV042_P0_COMMON_SUPPORT_RETENTION_FAIL`

and no model stage is authorized.

## 13. Current state

`DEV042_P0_FEATURE_SCHEMA_FROZEN_IMPLEMENTATION_AND_SYNTHETIC_CI_NEXT`
