# DEV036-C1 — Frozen-Touch × Promoted-Direction Composition Confirmation v1

Status: `DESIGN_FROZEN_BEFORE_ANY_C1_MODEL_FIT`

Date: 2026-09-02

## 1. Scientific question

Does replacing the old P3 conditional-direction component with the promoted
BTC45 / G3C16 direction component make the previously unsuccessful P4
two-head composition genuinely better, when every compared model is evaluated
on the exact same R-valid T2 support?

This is a composition-confirmation experiment, not a new feature search.

## 2. Why C1 is scientifically justified

Two upstream components are already independently established:

### Frozen touch/opportunity component

DEV030-P4 T2 TOUCH_VS_NONE:

- historical pooled validation = 5748 rows
- pooled AP = 0.2942831079
- pooled ROC AUC = 0.7317547276
- AP lift over prevalence = 2.9520755744x
- temporal-null empirical AP p = 0.0007047216
- eligible_for_composition = true

The original P4 composition nevertheless failed because its conditional
direction component was the earlier P3 direction head.

### Promoted direction component

DEV034-G3C16:

- matched comparator P3-common BA = 0.5365784523410725
- G3C16 BA = 0.5920001546112814
- delta BA = +0.05542170227020893
- 16-way max-stat FWER p = 0.0075
- true survivor = G3C16

DEV036-C1 tests whether that independently validated direction improvement
translates into a better three-class composition.

## 3. Frozen support from DEV036-C0

Use exactly:

`P4_T2 ∩ G3C16_R_CONTEXT_VALID`

Full Jan-Jul support:

- rows = 9849
- TOUCH = 1341
- NONE = 8508

Support SHA256:

`dc89f3012341bd771591693b03af00b86f64f95aa4f7db4e9dc65b7e0e7f7b3f`

T2 label SHA256:

`4a98955aab14f5d18019cecfc3ac74d443d47ee41cacc1482407746bc2193769`

Pooled outer validation:

- rows = 5628
- TOUCH = 559
- NONE = 5069

Validation-day support:

- Apr = 1407 / TOUCH 156 / NONE 1251
- May = 1407 / TOUCH 64 / NONE 1343
- Jun = 1407 / TOUCH 121 / NONE 1286
- Jul = 1407 / TOUCH 218 / NONE 1189

The 1341 directional TOUCH rows are exactly the frozen G3C16 support.

No further support shrink is allowed.

## 4. Important refit distinction

The P4 touch model cannot be required to reproduce the old P4 prediction hashes,
because C1 uses the R-valid common support and therefore removes 30 T2 rows per
day before touch-model training/evaluation.

Therefore C1 will REFIT the P4 S1 touch model under the exact frozen P4 model
lineage on the exact C0 common support.

This is a support-matched refit, not a new touch-model search.

By contrast, the conditional-direction support remains exactly the frozen 1341
G3B-R1 common support. Therefore C1 must reproduce, fold by fold:

1. the G3B-R1 `P3_COMMON_SUPPORT_REFIT` predictions;
2. the G3B-R1 `G3C16` predictions.

If either direction prediction hash does not reproduce, composition must stop
before any C1 result is produced.

## 5. Frozen three-class target

For every retained T2 row:

- NONE = class 0
- SHORT_FIRST = class 1
- LONG_FIRST = class 2

Use the exact P4 first-passage target:

- target A
- horizon = 120 s
- barrier = 16 bp
- window = 32 s

## 6. Four fixed composition systems

Exactly four systems are evaluated.

### C0 — THREE_CLASS_TRAIN_PREVALENCE

Training-fold three-class prevalence only.

No learned probability beyond prevalence.

### C1 — TOUCH_PLUS_DIRECTIONAL_PRIOR

Use the support-matched P4 S1 touch probability:

`p_touch(x)`

and the training-fold directional prevalence among TOUCH rows:

`p_long_prior`

Compose:

- P(NONE) = 1 - p_touch
- P(SHORT_FIRST) = p_touch × (1 - p_long_prior)
- P(LONG_FIRST) = p_touch × p_long_prior

This is the touch-only composition comparator.

### C2 — TOUCH_PLUS_P3_COMMON_DIRECTION

Use the same support-matched touch probability plus the exact reproduced
G3B-R1 P3-common conditional-direction probability:

`p_long_p3(x)`

This is the fair old-direction composition comparator.

### C3 — TOUCH_PLUS_BTC45_PROMOTED_DIRECTION

Use the same support-matched touch probability plus the exact reproduced
G3C16 / BTC45 conditional-direction probability:

`p_long_btc45(x)`

This is the promoted-direction composition under test.

No fifth system is allowed.

## 7. Touch-model lineage

For the C1 support-matched touch refit, preserve exact DEV030-P4 S1 lineage:

- exact P4 PRICE/S1 feature order
- StandardScaler fit on training rows only
- LogisticRegression
- L2
- solver = lbfgs
- class_weight = None
- fit_intercept = True
- max_iter = 1000
- threshold only for diagnostics; probability metrics are primary
- fixed C grid = 0.01 / 0.1 / 1.0 / 10.0
- chronological inner-fold C selection inherited from P4
- no threshold optimization
- no calibration rescue

The touch model is trained on all retained T2 rows in the outer training period.

## 8. Direction-model lineage

Both C2 and C3 are fit only on retained TOUCH rows with directional labels.

Because retained TOUCH support is exactly the frozen G3B-R1 common support,
model lineage must match G3B-R1 exactly.

### C2 P3-common direction

- 23 exact P3 PRICE32/S1 features
- exact G3B-R1 P3-common C-selection protocol
- exact G3B-R1 fold prediction hashes must reproduce

### C3 BTC45 promoted direction

- same 23 P3 features
- plus exact 22 G3C16 R-context features
- total = 45
- exact G3B-R1 G3C16 C-selection protocol
- exact G3B-R1 fold prediction hashes must reproduce

No refitting variation is allowed beyond deterministic reproduction of the
frozen protocol.

## 9. Outer folds

Use the existing chronological folds.

Fold 1:

- train Jan-Mar
- validate Apr

Fold 2:

- train Jan-Apr
- validate May

Fold 3:

- train Jan-May
- validate Jun

Fold 4:

- train Jan-Jun
- validate Jul

All systems C0-C3 use identical retained validation rows within each fold.

## 10. Primary comparison

Primary scientific comparison:

`C3 promoted BTC45 composition vs C2 P3-common composition`

Primary endpoint:

`Delta_LL_32 = multiclass_log_loss(C2) - multiclass_log_loss(C3)`

Positive values favor promoted BTC45 composition.

This directly asks whether the independently promoted direction model adds
composition value beyond the old P3 direction model.

## 11. Secondary composition comparisons

Also evaluate C3 against C1 touch-plus-directional-prior.

Required secondary endpoints:

- multiclass log loss
- multiclass Brier
- macro one-vs-rest Average Precision

Diagnostics only:

- macro one-vs-rest ROC AUC
- argmax macro F1
- argmax balanced accuracy
- three-class confusion matrix
- per-class AP/AUC

## 12. Fold and leave-one-fold-out stability

Serialize for both C3-vs-C2 and C3-vs-C1:

- four fold log-loss improvements
- positive fold-improvement count
- pooled log-loss improvement
- pooled Brier improvement
- pooled macro-AP improvement
- four leave-one-fold-out pooled log-loss improvements
- all-LOO-positive flag
- minimum fold log-loss improvement
- median fold log-loss improvement

## 13. Temporal falsification for promoted-direction increment

Run a single preregistered null only for the primary C3-vs-C2 question.

The touch/NONE process must remain fixed.

Within each validation fold:

1. retain all NONE positions unchanged;
2. take the chronological sequence of directional labels on TOUCH rows only;
3. circularly shift SHORT/LONG labels within the TOUCH-row sequence;
4. use the same shifted labels when scoring C2 and C3;
5. keep all C2/C3 predicted probabilities fixed;
6. compute:
   `Delta_LL_32_null = LL(C2) - LL(C3)`.

Legal shifts on TOUCH sequences:

- Fold 1 n=156: 10..146
- Fold 2 n=64: 10..54
- Fold 3 n=121: 10..111
- Fold 4 n=218: 10..208

Null parameters:

- seed = 20260902
- replicates = 1999

Serialize:

- all four-shift tuples
- all null Delta_LL_32 values
- null q95 using method = higher
- plus-one empirical p-value
- observed minus q95

This null preserves touch occurrence and tests only whether the promoted
direction probabilities are aligned with directional outcomes better than P3.

## 14. Strong C1 promotion gate

DEV036-C1 is:

`ELIGIBLE_FOR_POLICY_COMPOSITION_DEVELOPMENT`

only if ALL conditions pass.

### Provenance/reproduction gates

1. P4 canonical parent SHA passes.
2. G3B-R1 canonical parent SHA passes.
3. C0 common-support SHA/label SHA pass.
4. P3-common direction prediction hashes reproduce all four folds.
5. G3C16 direction prediction hashes reproduce all four folds.

### Primary C3 vs C2 gates

6. pooled C3 log loss < pooled C2 log loss.
7. pooled C3 Brier < pooled C2 Brier.
8. pooled C3 macro AP > pooled C2 macro AP.
9. at least 3/4 fold log-loss improvements C2-C3 > 0.
10. all four LOO pooled log-loss improvements C2-C3 > 0.
11. observed Delta_LL_32 > temporal-null q95.
12. temporal-null plus-one empirical p <= 0.05.

### Overall composition-value gates vs C1

13. pooled C3 log loss < pooled C1 log loss.
14. pooled C3 Brier < pooled C1 Brier.
15. pooled C3 macro AP > pooled C1 macro AP.
16. at least 3/4 fold log-loss improvements C1-C3 > 0.
17. all four LOO pooled log-loss improvements C1-C3 > 0.

Every gate was fixed before C1 fitting.

No gate may be relaxed after results are seen.

## 15. Terminal outcomes

If every gate passes:

`ELIGIBLE_FOR_POLICY_COMPOSITION_DEVELOPMENT`

This still does not authorize PnL or forward holdout.

If the primary C3-vs-C2 direction-improvement gates fail:

`FAIL_PROMOTED_DIRECTION_NO_COMPOSITION_INCREMENT`

If C3 improves over C2 but fails overall composition-value gates vs C1:

`FAIL_PROMOTED_DIRECTION_IMPROVES_P3_BUT_COMPOSITION_NOT_USEFUL`

If provenance/reproduction fails:

`PREEXECUTION_REPRODUCTION_FAILURE_NO_RESULT`

No result may be rescued post hoc.

## 16. EXP024 remains separate

EXP024 opportunity ranking is not used in DEV036-C1.

This is deliberate.

C1 asks whether:

`touch probability × promoted direction probability`

is a valid three-class composition.

Only if C1 succeeds may a later separately preregistered experiment consider
combining this architecture with EXP024 opportunity ranking.

## 17. Strict prohibitions

DEV036-C1 must not:

- reuse Aug-30 as fresh data;
- open Sep-01+ data;
- use Railway/archive/abundant-love;
- run PnL;
- optimize trade threshold;
- optimize confidence threshold;
- tune composition weights;
- calibrate after result;
- search alternative touch models;
- search alternative direction models;
- add ETH/G4 features;
- select a subset of G3C16 features;
- add interaction terms;
- change support after seeing results.

## 18. Execution discipline

Stages:

1. C1 design freeze
2. implementation only
3. synthetic/unit CI
4. execution freeze
5. real-data preflight without fit
6. one canonical C1 execution
7. deep read-only verification

No real DEV036-C1 fit is authorized by this design freeze.

## 19. Permanent upstream rules

`DEV034-G3A-R1 MUST NEVER BE RERUN`

`DEV034-G3B-R1 MUST NEVER BE RERUN`

`DEV035-G4B MUST NEVER BE RERUN`

## 20. Current state

`DEV036_C1_DESIGN_FROZEN_IMPLEMENTATION_NEXT_NO_REAL_FIT`
