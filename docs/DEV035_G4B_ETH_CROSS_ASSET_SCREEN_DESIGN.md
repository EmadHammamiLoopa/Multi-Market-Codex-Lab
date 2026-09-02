# DEV035-G4B — ETH Cross-Asset Microstructure Incremental Screen v1

Status: `DESIGN_FROZEN_BEFORE_ANY_G4B_PREDICTIVE_FIT`

Date: 2026-09-02

## 1. Scientific question

Does already-available causal ETHUSDT microstructure context add stable
incremental information for the BTCUSDT direction-given-touch task beyond the
promoted 45-feature historical-development base?

Promoted base:

`DEV030-P3 + G3C16 FULL_FROZEN_R_CONTEXT`

This experiment does not assume ETH leads BTC structurally. It tests whether
causal ETH state available at the BTC decision timestamp adds incremental
predictive information.

## 2. Parent base identity

The inherited base is frozen at:

- 23 exact DEV030-P3 PRICE32/S1 features
- 22 exact G3C16 full frozen R-context features
- total = 45 features

Common support:

- rows = 1341
- LONG = 665
- SHORT = 676

Support SHA256:

`caa61e84281061d00e4244e4f9b30ed2096e5acb95df9906aa7de0f28750ab75`

Label SHA256:

`fcb1b8f6c5f7994ca8c611cb3381146f401be7623ef36ae316a9a2e477a83385`

## 3. G4A support audit result

DEV035-G4A established:

- exact ETH 250 ms timestamp alignment for all 1341 BTC rows;
- zero support loss for ETH L0, L1, and L2;
- exact same support SHA for all three blocks;
- all four outer validation folds retain both classes;
- no support recovery is required.

Therefore comparator and all G4B candidates use the exact same 1341 rows.

## 4. Existing ETH source identity

Use only existing Jan-Jul 2026 ETHUSDT Phase0DL FEATURES250 files.

Frozen file SHA256:

- 2026-01-01:
  `036f300bbe31f1ccbe4ec52362060870cf6c644a44c8f8b5fd30e79749a39359`
- 2026-02-01:
  `cbac5c6b624930774bd60f3a50383f2551303e3ba5de3648275a362b69e5a643`
- 2026-03-01:
  `006aaa3879fb3051bb241f73cd8b1e1af6e647ea95577e5f2d004fb7cce05187`
- 2026-04-01:
  `54dfa0cf9cb45e869c531db6e082bbb09fa0d819973fd29642be1b68c5691256`
- 2026-05-01:
  `a7e96f52a91f303296ff579d8f72ec206aedb1b1d5227c7472db641b5a5c9fa5`
- 2026-06-01:
  `7753c43fed7574520ac8583e413a57116779aa636ca6fb71026ddf8d86420c1c`
- 2026-07-01:
  `38e8853ba2a777293fa0cd645af5c709cdf9b4faeeaa57941cd37021d675b57d`

No new acquisition is allowed.

## 5. Frozen ETH candidate universe

Exactly three nested candidates:

### G4C01 — ETH_L0_STATIC_STATE

Add the 11 frozen ETH L0 features:

- spread_bps
- microprice_minus_mid_bps
- obi_l1
- obi_l5
- obi_l10
- log_bid_qty_l1
- log_ask_qty_l1
- log_bid_depth_l5
- log_ask_depth_l5
- log_bid_depth_l10
- log_ask_depth_l10

Total model width:

`45 + 11 = 56`

### G4C02 — ETH_L1_EVENT_FLOW

Add the complete frozen ETH L1 block:

- all 11 L0 features
- plus all 15 frozen L1 event-flow features

Added feature count:

`26`

Total model width:

`45 + 26 = 71`

### G4C03 — ETH_L2_FULL_MICROSTRUCTURE

Add the complete frozen ETH L2 block:

- all 11 L0 features
- all 15 L1 features
- all 17 L2 features

Added feature count:

`43`

Total model width:

`45 + 43 = 88`

Candidate order is immutable:

`G4C01, G4C02, G4C03`

No post-result feature subset selection is permitted.

## 6. Timing semantics

Primary G4B candidates use ETH state sampled at the exact same causal
250 ms timestamp as the BTC decision support row.

This means:

- ETH information timestamp <= BTC decision timestamp;
- no future ETH sample is used;
- no interpolation is used;
- no forward fill is used;
- no attempt is made to infer a structural ETH-leads-BTC mechanism.

A separate lagged-ETH experiment would require a separate preregistration.

## 7. Comparator

Comparator identity:

`BTC45_PROMOTED_BASE_REFIT`

It uses exactly the promoted 45-feature BTC base on the same 1341 support.

Every G4 candidate is:

`BTC45_PROMOTED_BASE + one frozen ETH nested block`

The frozen G3B-R1 G3C16 prediction vector is not reused as the direct comparator
because G4B performs a fresh matched-protocol comparison.

## 8. Chronological folds

Use the exact same matched support and outer partitions inherited from G3B-R1.

### Fold 1
- outer train Jan-Mar = 782 rows
- validation Apr = 156 rows = 85 LONG / 71 SHORT
- inner fit Jan-Feb = 426 rows
- inner validation Mar = 356 rows

### Fold 2
- outer train Jan-Apr = 938 rows
- validation May = 64 rows = 40 LONG / 24 SHORT
- inner fit Jan-Mar = 782 rows
- inner validation Apr = 156 rows

### Fold 3
- outer train Jan-May = 1002 rows
- validation Jun = 121 rows = 55 LONG / 66 SHORT
- inner fit Jan-Apr = 938 rows
- inner validation May = 64 rows

### Fold 4
- outer train Jan-Jun = 1123 rows
- validation Jul = 218 rows = 122 LONG / 96 SHORT
- inner fit Jan-May = 1002 rows
- inner validation Jun = 121 rows

Pooled validation:

- rows = 559
- LONG = 302
- SHORT = 257

## 9. Model lineage

Comparator and all three candidates use exactly:

- StandardScaler fit on training rows only
- L2 LogisticRegression
- solver = lbfgs
- class_weight = None
- fit_intercept = True
- max_iter = 1000
- random_state = 20260825
- threshold = 0.5

Frozen C grid:

`(0.01, 0.1, 1.0, 10.0)`

No alternate model family is allowed.

## 10. Inner C selection

Representation-specific C selection follows the frozen G3B-R1 protocol:

1. maximize inner balanced accuracy;
2. then maximize inner macro F1;
3. then choose smaller C.

The comparator and each candidate select C independently under the same
chronological protocol.

## 11. Primary endpoint

For candidate c:

`delta_BA(c) = pooled_BA(c) - pooled_BA(BTC45_PROMOTED_BASE_REFIT)`

Balanced accuracy is primary.

Also serialize:

- macro F1
- MCC
- ROC AUC diagnostic
- confusion matrix
- per-class precision/recall/F1/support
- predicted class counts
- predicted minority fraction
- all fold metrics
- all selected C values
- all inner-C ledgers
- deterministic prediction hashes

## 12. Stability diagnostics

For every candidate store:

- four fold BAs
- four comparator fold BAs
- four fold delta BAs
- positive fold-delta count
- candidate fold BA > 0.50 count
- both-classes-predicted-all-folds
- pooled predicted-minority fraction
- four leave-one-fold-out pooled delta BAs
- all-LOO-positive flag
- worst fold BA
- median fold delta BA
- minimum fold delta BA

## 13. Joint 3-candidate temporal max-stat null

Exactly:

- seed = 20260902
- replicates = 1999
- candidates = exactly G4C01..G4C03

Legal circular validation-label shifts remain:

- Fold 1 n=156: 10..146
- Fold 2 n=64: 10..54
- Fold 3 n=121: 10..111
- Fold 4 n=218: 10..208

For each replicate:

1. draw one legal shift independently for each fold;
2. use the same shifts for comparator and all three candidates;
3. keep predictions fixed;
4. shift labels within validation fold only;
5. compute candidate BA minus comparator BA;
6. retain all three candidate deltas;
7. retain the maximum across all three.

Serialize all shift tuples, all candidate null vectors, max-stat null, raw
plus-one p, max-stat FWER plus-one p, q95, and observed-minus-q95.

## 14. Strong G4 survivor gate

A candidate is `G4_LAYER_SURVIVOR` only if ALL:

1. pooled BA(candidate) > comparator BA;
2. pooled BA(candidate) >= 0.59;
3. pooled delta BA >= +0.015;
4. at least 3/4 fold delta BA values positive;
5. at least 3/4 candidate fold BA values > 0.50;
6. both classes predicted in every fold;
7. pooled predicted-minority fraction >= 0.10;
8. all four LOO pooled delta BAs > 0;
9. observed delta BA > joint 3-candidate max-stat q95;
10. max-stat FWER p <= 0.05;
11. all provenance/support/finiteness/alignment guards pass.

The absolute BA gate is deliberately raised to 0.59 because the inherited G3C16
base already achieved 0.5920001546112814 in the prior matched screen. G4 must
demonstrate useful incremental value above that stronger inherited base.

No gate may be relaxed after results are observed.

## 15. Inconclusive and rejected

`G4_LAYER_INCONCLUSIVE` only if:

- pooled delta BA > 0;
- at least 3/4 fold deltas positive;
- all four LOO deltas > 0;

but one or more strong-survivor gates fail.

Otherwise:

`G4_LAYER_REJECTED`.

## 16. Ranking and advancement

At most one G4 survivor advances because the three candidates are strictly
nested views of one ETH information family.

If more than one candidate passes every survivor gate, rank by:

1. smaller max-stat FWER p;
2. larger minimum fold delta BA;
3. larger median fold delta BA;
4. larger pooled delta BA;
5. fewer added features;
6. lexicographically smaller candidate ID.

Advance only rank 1.

This prevents automatically promoting redundant nested ETH blocks.

## 17. Stop rule

If zero true G4 survivors:

- retain the promoted BTC45 base unchanged;
- close the ETH cross-asset microstructure group;
- do not refine the best G4 failure;
- move to the next scientifically distinct group.

If one or more true survivors:

- advance only the deterministic rank-1 survivor;
- do not open forward holdout yet;
- do not run PnL;
- any new layered group requires separate preregistration.

## 18. Guards

Must remain false through design/implementation/CI/preflight:

- Sep-01+ analytical access
- Aug-30 reuse
- new acquisition/download
- Railway analytical access
- archive bucket analytical access
- abundant-love analytical access
- PnL
- threshold optimization
- calibration rescue
- feature subset search
- PCA/SVD
- interaction search
- candidate-specific support shrink
- candidate addition/removal after results

## 19. Execution discipline

Stages:

1. design freeze
2. implementation only
3. unit/synthetic CI
4. execution freeze
5. local real-data preflight with no fit
6. one canonical predictive execution
7. deep read-only verification

No real G4B fit is authorized by this design freeze.

Current state:

`DEV035_G4B_DESIGN_FROZEN_IMPLEMENTATION_NEXT_NO_REAL_FIT`
