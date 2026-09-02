# DEV033-G2B — Layered Temporal Incremental Screen Design v1

Status: `DESIGN_FROZEN_BEFORE_ANY_G2B_PREDICTIVE_FIT`

Date: 2026-09-02

Permanent governance:
`docs/LAYERED_STRATEGY_SEARCH_GOVERNANCE.md`

Parent materialization:
`DEV033-G2A`

## 1. Scientific question

The frozen direction-stage success remains DEV030-P3:

`A / 120s / 16bp / 32s / PRICE / S1 / M1 LogisticRegression`

DEV033-G2B asks:

> Which, if any, of the 24 frozen raw-temporal microstructure layers adds stable
> incremental directional value on top of the already-successful P3 PRICE32
> representation?

Every G2B candidate is:

`P3 PRICE32 S1 base + one frozen G2A temporal layer`

No G2B candidate is evaluated standalone.

No DEV032 inconclusive/failure representation is used as a parent.

## 2. Frozen G2A identity

Canonical materialization:

`/home/emadh/Multi-Market/evidence/dev033_g2a_layered_temporal_materialization_v1/DEV033_G2A_LAYERED_TEMPORAL_MATERIALIZATION.json`

SHA256:

`3336c70912bd0de0928a9fded04f3d7153fcd2df46dd2ed3d1b942a2c98922c6`

bytes:

`104750`

Verified:

- 37/37 read-only checks PASS
- exact 24-candidate registry
- exact 2520 total materialized added-layer columns
- exact 1374 support rows
- exact 684 LONG / 690 SHORT
- exact E1A timestamps/labels
- all 24 campaign hashes reproduced
- raw provenance 7/7 PASS

## 3. Frozen P3 base identity

Canonical P3 artifact:

`/home/emadh/Multi-Market/evidence/dev030_p3_campaign1_v1/DEV030_P3_CAMPAIGN1_RESULT.json`

SHA256:

`f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`

bytes:

`1610856`

Selected configuration:

- target = A
- horizon = 120 s
- barrier = 16 bp
- window = 32 s
- block = PRICE
- representation = S1
- model = M1 regularized logistic regression
- base feature count = 23
- terminal label = SELECTED_FOR_NEXT_DEVELOPMENT_STAGE

Frozen P3 OOF support:

- total = 573
- LONG = 309
- SHORT = 264
- fold supports = 159 / 64 / 126 / 224

Frozen P3 pooled diagnostics:

- balanced accuracy = 0.5419424831488764
- macro F1 = 0.5113006397
- MCC = 0.0920119182
- ROC AUC diagnostic = 0.5367264882

Frozen P3 fold balanced accuracy:

- F1 = 0.5700063715
- F2 = 0.6041666667
- F3 = 0.4916666667
- F4 = 0.5307091685

Frozen P3 selected C values:

- F1 = 10.0
- F2 = 10.0
- F3 = 0.1
- F4 = 0.01

Frozen P3 prediction hashes:

- F1 = `e03d233bff936b49a0452994497f32ca5ecbe52c1f490d855fe8d06dbfa9dcf4`
- F2 = `cd2cba0a6dcf3591ec9848b78e31aef796dad15d371bbecb8517aa2507340bdd`
- F3 = `19f9acf70b0065a307c0373952cad350339768607a156c9307e5192503bb1f31`
- F4 = `b05ee6e926d6a943e1fc89828eb3801af0863fa270bc2e5db5ed7cd93e9a4b66`

## 4. Candidate universe

Exactly 24 candidates:

- G2C01..G2C24

Their identities, family IDs, windows, channel order, flattened feature names,
and matrix hashes are inherited exactly from the frozen G2A artifact.

No candidate may be added, removed, renamed, merged, or feature-selected after
predictive results are observed.

## 5. Candidate construction

For each day and candidate:

`X_candidate = concatenate([X_P3_PRICE32_S1, X_G2A_candidate])`

Order is immutable:

1. all 23 frozen P3 PRICE32 S1 features
2. all frozen G2A candidate features in exact G2A order

The base P3 matrix must be reconstructed from the same frozen P3/P2C lineage
used by prior P4/P6 reproduction code.

G2A support timestamps and labels must match the reconstructed P3 T1 rows
exactly for every day before concatenation.

No support shrink.

## 6. Outer folds

Exactly the frozen four expanding P3 folds:

1. Jan-Mar -> Apr
2. Jan-Apr -> May
3. Jan-May -> Jun
4. Jan-Jun -> Jul

Validation supports must remain:

- 159
- 64
- 126
- 224

## 7. Inner C selection

Exactly the frozen P3 chronological inner protocol.

For each outer fold:

- inner validation day = final outer-training day
- inner fit days = all earlier outer-training days

Fixed C grid:

`(0.01, 0.1, 1.0, 10.0)`

For each C:

- fit StandardScaler on inner-fit only
- transform inner validation
- fit L2 LogisticRegression
- classify at threshold 0.5
- compute balanced accuracy and macro F1

Select lexicographically:

1. maximum balanced accuracy
2. maximum macro F1
3. minimum C

No candidate-specific tuning beyond this frozen C grid.

## 8. Final outer fit

After C selection:

- fit StandardScaler on full outer-training candidate matrix only
- transform outer validation
- fit the same LogisticRegression
- output p(LONG)
- classify at 0.5

LogisticRegression remains exactly:

- solver = lbfgs
- l1_ratio = 0.0
- class_weight = None
- max_iter = 1000
- fit_intercept = True
- random_state = 20260825

## 9. Mandatory P3 reproduction gate

Before interpreting any G2B candidate, reproduce the exact frozen P3 M1 head.

Required:

- exact A/120/16/32/PRICE/S1 identity
- 23 exact feature names/order
- fold supports 159/64/126/224
- C values 10/10/0.1/0.01
- four exact frozen prediction hashes
- pooled BA = 0.5419424831488764 within 5e-10
- pooled support = 573
- pooled LONG = 309
- pooled SHORT = 264

Any mismatch makes G2B INVALID before candidate interpretation.

## 10. Primary benchmark

Primary endpoint:

`delta_BA = pooled_BA(candidate) - pooled_BA(P3)`

Balanced accuracy remains primary because P3 itself was selected under the
frozen balanced-accuracy promotion protocol.

Also store as diagnostics:

- macro F1
- MCC
- ROC AUC
- predicted LONG/SHORT counts
- predicted minority fraction
- class metrics/confusion matrix where already supported by P3 metrics code

## 11. Stability diagnostics

For every candidate:

- four fold candidate BAs
- four fold delta_BA vs P3
- count of positive fold deltas
- count of candidate folds BA > 0.50
- both-classes-predicted flag for each fold
- pooled predicted-minority fraction
- four leave-one-fold-out pooled delta_BA values
- all-LOO-positive flag
- worst fold candidate BA
- median fold delta_BA
- minimum fold delta_BA

## 12. Joint temporal max-stat null

Exactly:

- 1999 replicates
- seed = 20260902
- 24 candidates jointly controlled

For each replicate:

1. independently choose one legal circular shift within each validation fold;
2. legal shifts for fold size n are integers 10..n-10;
3. use the same four shift values for P3 and all 24 candidates;
4. keep all fitted predictions/probabilities fixed;
5. circularly shift labels inside each fold;
6. compute shifted BA(candidate) - shifted BA(P3);
7. retain all 24 candidate-specific deltas;
8. retain the maximum delta across all 24 candidates.

The artifact MUST serialize:

- all 1999 four-fold shift tuples
- all 24 candidate-specific null vectors
- max-stat null vector
- per-candidate raw plus-one empirical p
- per-candidate max-stat FWER plus-one p
- max-stat q95 using empirical higher quantile
- observed minus q95

Artifact completeness for all 24 candidate-specific null vectors is a mandatory
unit test before canonical execution.

## 13. Strong layered survivor gate

A candidate is `G2_LAYER_SURVIVOR` only if ALL:

1. pooled BA(candidate) > pooled BA(P3)
2. pooled BA(candidate) >= 0.54
3. pooled delta_BA >= +0.02
4. >=3/4 fold delta_BA vs P3 positive
5. >=3/4 candidate fold BA > 0.50
6. both classes predicted in every fold
7. pooled predicted-minority fraction >= 0.10
8. all four LOO pooled delta_BA values > 0
9. observed delta_BA > joint 24-candidate max-stat q95
10. max-stat FWER p <= 0.05
11. all support/provenance/finiteness/reproduction guards PASS

No gate may be relaxed after results are observed.

## 14. Inconclusive and rejected

`G2_LAYER_INCONCLUSIVE` only if:

- pooled delta_BA > 0
- >=3/4 fold deltas positive
- all four LOO delta_BA values > 0

but one or more strong survivor gates fail.

Otherwise:

`G2_LAYER_REJECTED`.

Only `G2_LAYER_SURVIVOR` can alter the frozen direction base.

## 15. Advancement

At most three survivors may advance.

At most one survivor per T01..T08 information family.

If multiple windows from one family survive, select within family by:

1. smaller max-stat FWER p
2. larger minimum fold delta_BA
3. larger median fold delta_BA
4. larger pooled delta_BA
5. shorter window

No weak slot filling.

Survivors are not automatically concatenated together. Any multi-survivor
composition requires a separately frozen next-layer composition experiment.

## 16. Permanent layered-search consequence

If G2B has zero true survivors:

- DEV030-P3 remains the frozen direction base unchanged
- no G2B failure/inconclusive replaces it
- move to the next scientifically distinct strategy group on top of P3

If G2B has one or more true survivors:

- only those true survivors may inform the next successful base
- any composition is separately preregistered

## 17. Guards

Must remain false:

- Sep-01+ opened
- Aug-01/Aug-30 newly opened for analysis
- Railway opened
- archive bucket opened
- abundant-love opened
- new acquisition/download
- PnL
- threshold optimization
- calibration rescue
- candidate feature subset search
- alternate model-family search

## 18. Execution discipline

Implementation, CI, execution freeze, local preflight, and single canonical
execution remain separate stages.

No real G2B predictive fit is authorized by this design freeze alone.

Current state:

`DEV033_G2B_DESIGN_FROZEN_IMPLEMENTATION_NEXT_NO_REAL_FIT`
