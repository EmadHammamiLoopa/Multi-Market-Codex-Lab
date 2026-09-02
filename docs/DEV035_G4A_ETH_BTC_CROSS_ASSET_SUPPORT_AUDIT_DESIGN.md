# DEV035-G4A — ETH→BTC Cross-Asset Causal Support Audit v1

Status: `DESIGN_FROZEN_BEFORE_ANY_G4_PREDICTIVE_FIT`

Date: 2026-09-02

## 1. Purpose

Before defining any G4 predictive candidate universe, determine whether existing
historical ETHUSDT Phase0DL 250 ms feature files can be aligned causally and
exactly to the promoted BTC layered-development base without opening new data,
shrinking support silently, or fitting any model.

This is a support/provenance audit only.

## 2. Promoted BTC base

Inherited base:

`DEV030-P3 + G3C16 FULL_FROZEN_R_CONTEXT`

Feature count:

- 23 P3 PRICE32/S1 features
- 22 G3C16 R-context features
- total = 45

Frozen BTC common support:

- rows = 1341
- LONG = 665
- SHORT = 676

Support SHA256:

`caa61e84281061d00e4244e4f9b30ed2096e5acb95df9906aa7de0f28750ab75`

## 3. Cross-asset hypothesis family

Potential G4 family:

`ETHUSDT causal microstructure state → BTCUSDT direction-given-touch`

This is distinct from:

- EXP003 same-asset cross-venue information;
- V2.1 coarse 5-minute cross-market context;
- G3 BTC-only opportunity/volatility context.

No claim of ETH leadership is assumed.

## 4. Existing historical source only

Use only already-consumed Jan-Jul 2026 ETHUSDT Phase0DL feature250 files
produced under the same frozen 250 ms causal semantics as BTCUSDT.

No download, Tardis acquisition, Railway, bucket, abundant-love, Sep-01+, or
Aug-30 access is allowed.

Expected days:

- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

## 5. Audit questions

For every frozen BTC G3A-R1 common-support timestamp:

1. does the ETH feature250 day exist?
2. is the ETH timestamp grid exact 250 ms?
3. is the exact BTC timestamp present in ETH?
4. is ETH book state causal and valid at that timestamp?
5. which frozen ETH blocks are finite/valid:
   - L0 static microstructure
   - L1 event-flow
   - L2 changes/replenishment/interactions
6. how many BTC rows retain exact ETH L0/L1/L2 support?
7. are exclusions label-independent?
8. do all four outer validation folds retain both classes?

## 6. No predictive use

G4A must not call:

- StandardScaler fit
- LogisticRegression fit
- any predictive metric
- any temporal null
- any feature selection
- any threshold tuning
- any PnL/economic calculation

## 7. Support policy

No candidate-specific support may be created during this audit.

The audit may report three deterministic potential common supports:

- BTC45 + ETH-L0
- BTC45 + ETH-L1
- BTC45 + ETH-L2

These are descriptive feasibility objects only.

No one is selected for prediction until a later G4B design is frozen.

If a future G4B chooses one block or a nested candidate family, its comparator
must be refit on the exact same chosen common support.

## 8. Required audit output

Read-only console diagnostic first.

Report per day and campaign:

- BTC promoted-base rows
- ETH exact-grid matches
- ETH L0 valid rows
- ETH L1 valid rows
- ETH L2 valid rows
- LONG/SHORT counts for each support
- exclusion reasons
- outer-fold class counts
- exact support hashes for each potential common support

No canonical G4 artifact is authorized yet.

## 9. Stop rule

If ETH exact alignment or support is materially inadequate, close the
cross-asset G4 family without predictive fitting and move to another distinct
family.

If support is adequate, freeze a separate DEV035-G4B predictive design before
any model fit.

Current state:

`DEV035_G4A_CROSS_ASSET_SUPPORT_AUDIT_DESIGN_FROZEN_DIAGNOSTIC_NEXT_NO_FIT`
