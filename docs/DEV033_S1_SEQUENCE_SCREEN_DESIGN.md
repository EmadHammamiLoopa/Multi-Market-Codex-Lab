# DEV033-S1 — Fixed Sequence Representation Screen Design v1

Status: `DESIGN_FROZEN_NO_SEQUENCE_MATERIALIZATION_OR_MODEL_FIT_YET`

Date: 2026-09-02

## 1. Scientific motivation

DEV032-E2B ended with:

- 10/10 adaptive refinements rejected;
- 0 adaptive refinement survivors;
- 0 advanced mechanisms;
- every refinement had negative pooled AUC delta versus its frozen parent.

Therefore the engineered-vector refinement line is closed.

DEV033-S1 asks a scientifically distinct question:

> Does retaining the causal temporal ordering of event-flow information provide
> directional value that is lost by fixed engineered summaries?

This is not DEV032-E3 and does not loosen any DEV032 threshold.

## 2. Prior justification

This sequence direction existed before DEV032 outcomes in the frozen candidate
registry:

- J02: raw stationary order-flow sequence + small MLP
- J03: raw stationary order-flow sequence + 1D CNN/TCN
- J04: event-type/intensity sequence + small GRU
- J05: compact DeepLOB-style CNN-LSTM
- J07: large Transformer sweep = EXCLUDE

The prior registry therefore supports sequence modeling as an independent
representation family.

External literature also motivates temporal LOB representations, but equally
warns against assuming that more complex architectures are automatically
better. DEV033-S1 therefore begins with only low-capacity fixed models.

## 3. Search-budget rule

DEV033-S1 contains exactly four primary hypotheses.

No architecture sweep.

No hyperparameter sweep.

No TCN, GRU, LSTM, DeepLOB, or Transformer is authorized in S1.

The four hypotheses isolate:

1. whether raw temporal ordering helps under the same linear model lineage;
2. whether one fixed low-capacity nonlinear MLP adds value beyond that linear
   sequence representation.

If all four fail, BTC Jan-Jul directional adaptive search closes.

## 4. Frozen support and target

Reuse exact frozen support only:

- BTCUSDT
- Jan-Jul 2026 consumed development sandbox
- T1 `DIRECTION_GIVEN_TOUCH`
- target A
- horizon 120 seconds
- barrier 16 bp
- causal lookback 32 seconds
- rows 1374
- LONG 684
- SHORT 690

No support shrink.

No relabeling.

No Sep-01+.

## 5. Sequence A — event-pressure sequence

Parent mechanism:
`P21 event_pressure_transition`

Information source:
exact E1A event classification semantics with dominant/raw event classes:

- BI
- BD
- BR
- BP
- AI
- AD
- AR
- AP

Time discretization:

- 32 fixed causal one-second bins;
- bin k contains events with age in `[k, k+1)` seconds before decision time;
- k=0 is newest;
- k=31 is oldest;
- no event after decision time may enter any bin.

For each bin and each of the 8 event classes, compute:

`class_qty_share = sum(abs(dq) for class) / max(sum(abs(dq) all classes in bin), eps)`

Also preserve directional sign implicitly through the class identity.

If a bin has no eligible events, all eight channels are zero.

Tensor shape:

`32 x 8`

Flattened width for non-sequence estimators:

`256`

No learned embedding.

## 6. Sequence B — stationary multilevel order-flow sequence

Parent mechanism:
`P13 multilevel_stationary_order_flow`

Time discretization:

same 32 causal one-second bins.

Depth levels:

exact top ten event ranks.

For each one-second bin and rank j=1..10:

`signed_flow_j = sum(side_signed_dq_j) / max(sum(abs(dq_j)), eps)`

The signed-flow convention is inherited exactly from the frozen E1A
stationary-order-flow lineage.

Empty bin/rank = 0.

Tensor shape:

`32 x 10`

Flattened width:

`320`

No PCA/SVD.

## 7. Four primary hypotheses

### S1H01 — EVENT_SEQUENCE_LOGISTIC

Input:
flattened 32x8 event-pressure sequence.

Model:
same train-only StandardScaler + fixed L2 LogisticRegression lineage.

C selection:
same chronological inner selection and same frozen grid
`(0.01,0.1,1.0,10.0)`.

Primary parent:
P21.

Purpose:
tests temporal representation while retaining the known low-capacity model.

### S1H02 — EVENT_SEQUENCE_MLP

Input:
same flattened 32x8 event-pressure sequence.

Fixed model:

- StandardScaler train-only
- sklearn MLPClassifier
- hidden_layer_sizes = (32,)
- activation = relu
- solver = lbfgs
- alpha = 0.01
- max_iter = 1000
- random_state = 20260902
- early_stopping = False

No architecture or alpha search.

Primary parent:
P21.

Purpose:
tests one fixed nonlinear alternative on the identical sequence information.

### S1H03 — STATIONARY_FLOW_SEQUENCE_LOGISTIC

Input:
flattened 32x10 stationary multilevel order-flow sequence.

Model:
same train-only StandardScaler + fixed L2 LogisticRegression lineage.

C selection:
same chronological inner C selection.

Primary parent:
P13.

### S1H04 — STATIONARY_FLOW_SEQUENCE_MLP

Input:
same flattened 32x10 stationary-flow sequence.

Fixed MLP exactly as S1H02.

Primary parent:
P13.

## 8. Why no TCN/GRU yet

The current labeled support is only 1374 examples and the BTC Jan-Jul
development sample has already been adaptively reused.

Opening TCN/GRU/DeepLOB/Transformer simultaneously would materially increase
researcher degrees of freedom.

A TCN/GRU stage is authorized only if at least one of the four S1 hypotheses is
a multiplicity-controlled sequence survivor.

If all S1 hypotheses fail, no deep sequence stage is opened on BTC Jan-Jul.

## 9. Stage decomposition

### DEV033-S1A — sequence materialization only

Before any S1 predictive fit:

- materialize exact 32x8 event-pressure sequences;
- materialize exact 32x10 stationary-flow sequences;
- verify exact 1374 support and 684/690 labels;
- all values finite;
- daily and campaign hashes;
- no model fit;
- no predictive metric;
- no null;
- no PnL.

### DEV033-S1B — predictive sequence screen

Only after S1A is frozen and read-only verified.

## 10. Outer folds

Exactly unchanged:

1. Jan-Mar -> Apr
2. Jan-Apr -> May
3. Jan-May -> Jun
4. Jan-Jun -> Jul

For Logistic candidates:
same chronological inner C-selection protocol.

For MLP candidates:
no hyperparameter selection; fit only on full outer-training fold.

## 11. Reproduction gate

Before S1 candidate interpretation, reproduce:

- B00
- P13
- P21

against frozen E1B-R1:

- exact prediction hashes;
- exact selected C values;
- pooled AUC/logloss/Brier within absolute tolerance 1e-15.

Any mismatch => INVALID before S1 interpretation.

## 12. Primary endpoint

Primary:
pooled OOF ROC AUC.

Primary sequence delta:

- S1H01/S1H02 versus frozen P21
- S1H03/S1H04 versus frozen P13

Also report descriptive delta versus B00.

## 13. Joint temporal null

Exactly:

- seed 20260902
- 1999 replicates
- same four within-fold circular shifts per replicate
- legal shift 10..n-10
- four primary hypotheses jointly controlled
- parent-relative delta statistic
- plus-one raw p
- single-step max-stat FWER p
- q95 using empirical higher quantile

Unlike the E2B artifact-retention deviation, S1B MUST serialize:

- all four candidate-specific null vectors;
- max-stat null vector;
- all 1999 shift tuples.

Artifact completeness must be explicitly unit-tested before canonical execution.

## 14. Sequence survivor gate

A candidate is `SEQUENCE_SURVIVOR` only if ALL:

1. pooled AUC > frozen parent AUC;
2. pooled AUC > B00 AUC;
3. pooled AUC >= 0.56;
4. >=3/4 parent-relative fold AUC deltas positive;
5. >=3/4 candidate fold AUC > 0.50;
6. all 4 LOO parent-relative pooled AUC deltas positive;
7. observed parent-relative delta > joint max-stat q95;
8. max-stat FWER p <= 0.05;
9. all provenance/support/causality/finiteness/reproduction guards pass.

`SEQUENCE_INCONCLUSIVE` requires:

- pooled delta > parent;
- >=3/4 positive fold deltas;
- all four LOO deltas positive;

but misses at least one survivor gate.

Else:

`SEQUENCE_REJECTED`.

## 15. Advancement

At most two sequence mechanisms may advance:

- at most one event-pressure mechanism;
- at most one stationary-flow mechanism.

No weak slot filling.

## 16. Stop rule

If zero `SEQUENCE_SURVIVOR`:

- BTC Jan-Jul directional adaptive search is CLOSED;
- no TCN/GRU/DeepLOB/Transformer on this development sample;
- no Sep-01+ opening;
- no PnL;
- next work must wait for or obtain an independent historical domain under a
  separately frozen acquisition/replication protocol.

If one or more sequence survivors exist:

- still exploratory only;
- no Sep-01+;
- next stage may test at most one fixed temporal architecture per surviving
  information family before independent historical replication.

## 17. Forward guards

Must remain false:

- Aug-01 opened
- Aug-30 opened
- Sep-01+ opened
- Railway opened
- market-raw-archive opened
- abundant-love opened
- acquisition/download
- PnL
- threshold optimization
- calibration rescue
- architecture sweep

Current state:

`DEV033_S1_DESIGN_FROZEN_S1A_FORMULAS_IMPLEMENTATION_NEXT_NO_MODEL_FIT`
