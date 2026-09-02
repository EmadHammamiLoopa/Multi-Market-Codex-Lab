# DEV032-E2B — Predictive Refinement Implementation Protocol v1

Status: `PROTOCOL_FROZEN_BEFORE_E2B_MODEL_FIT`

Date: 2026-09-02

Parent design:
`docs/DEV032_E2_WAVE2_ADAPTIVE_REFINEMENT_DESIGN.md`

Parent formulas:
`docs/DEV032_E2A_FORMULAS.md`

Frozen E2A artifact identity:

- path:
  `/home/emadh/Multi-Market/evidence/dev032_e2a_wave2_materialization_v1/DEV032_E2A_WAVE2_MATERIALIZATION.json`
- SHA256:
  `3c26614f576af4e52b2d52f237e2e939cd79a988238022076ddcdbf57d06b89c`
- bytes: `15261`

Frozen E1B-R1 artifact identity:

- path:
  `/home/emadh/Multi-Market/evidence/dev032_e1b_r1_broad_predictive_screen_v1/DEV032_E1B_BROAD_PREDICTIVE_SCREEN_RESULT.json`
- SHA256:
  `af223d3f97b85ae1c929f81b3ec71e892477b9b26e719638acb05ae153578b95`
- bytes: `287823`

## 1. No E2B real fit yet

This protocol is frozen before any DEV032-E2B predictive fit.

## 2. Fixed folds and model lineage

Outer folds remain exactly:

1. Jan-Mar -> Apr
2. Jan-Apr -> May
3. Jan-May -> Jun
4. Jan-Jun -> Jul

Chronological inner selection remains:

- final outer-training day = inner validation day;
- all earlier outer-training days = inner fit.

C grid remains exactly:

`(0.01, 0.1, 1.0, 10.0)`

LogisticRegression remains:

- solver = lbfgs
- l1_ratio = 0.0
- class_weight = None
- max_iter = 1000
- fit_intercept = True
- random_state = 20260825

Inner C winner remains lexicographic:

1. minimum binary log loss
2. minimum Brier
3. maximum ROC AUC
4. minimum C

## 3. Ordinary E2 refinements

For E2R01-04 and E2R07-10:

- concatenate PRICE23 B00 first;
- concatenate the frozen E2A refinement block second;
- StandardScaler is fit on inner-fit only during C selection;
- transform inner validation with that inner-fit scaler;
- after C is selected, refit StandardScaler on full outer training;
- transform outer validation;
- fit selected LogisticRegression on full outer training.

No feature deletion or interaction expansion beyond the frozen E2A block.

## 4. PCA refinement E2R05

Raw E2R05 input is the frozen 20-dimensional MLOFI block.

Inner C selection:

1. fit raw-extra StandardScaler on inner-fit E2R05 raw columns only;
2. transform inner-fit and inner-validation raw extra;
3. fit PCA on scaled inner-fit only;
4. PCA n_components = 5;
5. svd_solver = full;
6. whiten = False;
7. transform inner fit and inner validation to five scores;
8. concatenate PRICE23 + five PCA scores;
9. fit the Logistic-stage StandardScaler on the concatenated inner-fit matrix;
10. transform concatenated inner validation;
11. evaluate each fixed C.

Final outer fit after C selection:

1. fit raw-extra StandardScaler on all outer-training raw E2R05 columns;
2. fit PCA on scaled outer-training only;
3. transform outer training and outer validation;
4. concatenate PRICE23 + five PCA scores;
5. fit Logistic-stage StandardScaler on concatenated outer training;
6. transform outer validation;
7. fit selected LogisticRegression.

No transform may see its corresponding validation labels or validation feature
distribution during fitting.

## 5. SVD refinement E2R06

Identical leakage-safe staging to E2R05, except:

- raw input width = 40;
- TruncatedSVD n_components = 5;
- algorithm = randomized;
- n_iter = 7;
- random_state = 20260902.

No component-count tuning.

## 6. Frozen parent reproduction gate

Before E2 refinements can be interpreted, E2B must refit and reproduce:

- B00
- P07
- P09
- P13
- P17
- P21
- P32
- P35

using the unchanged E1B model lineage.

For each reproduced representation:

- all four prediction hashes must match the frozen E1B-R1 artifact;
- all four selected C values must match exactly;
- pooled AUC/logloss/Brier must match within absolute tolerance 1e-15.

Any mismatch invalidates E2B before refinement interpretation.

The full 14 E1B `SCREENING_INCONCLUSIVE` parent anchors must also be retained
from the frozen E1B artifact for audit, even if not all are active refinement
parents.

## 7. Active parent mapping

- E2R01 -> P07
- E2R02 -> P07
- E2R03 -> P09
- E2R04 -> P09
- E2R05 -> P13
- E2R06 -> P13
- E2R07 -> P17
- E2R08 -> P21
- E2R09 -> P35
- E2R10 -> P32

No remapping.

## 8. Parent-relative comparison

For each refinement, primary delta is:

`AUC(refinement) - AUC(frozen parent)`

Also retain descriptive comparison versus B00.

Required stability values:

- four parent-relative fold AUC deltas;
- count positive parent-relative fold deltas;
- four parent-relative leave-one-fold-out pooled AUC deltas;
- all-LOO-positive flag;
- candidate fold AUC > 0.5 count;
- worst-fold candidate AUC.

## 9. Joint temporal max-stat null

Fixed:

- seed = 20260902
- replicates = 1999
- legal within-fold circular shifts = 10..n-10
- same four shift values applied to every parent and every refinement per
  replicate.

For each refinement j and replicate r:

`delta_jr = AUC_shifted(refinement_j) - AUC_shifted(parent_j)`

The replicate maximum is the maximum of all ten parent-relative deltas.

Store:

- all 1999 shift tuples;
- all ten candidate null vectors;
- max-stat null vector;
- raw plus-one p;
- max-stat FWER plus-one p;
- q95 using higher empirical quantile;
- observed minus q95.

## 10. Frozen E2 status gates

`ADAPTIVE_REFINEMENT_SURVIVOR` only if all:

1. pooled AUC > parent pooled AUC;
2. pooled AUC > B00 pooled AUC;
3. pooled AUC >= 0.56;
4. >=3/4 fold AUC deltas vs parent positive;
5. >=3/4 candidate fold AUC > 0.50;
6. all 4 LOO parent-relative deltas > 0;
7. observed parent-relative delta > max-stat q95;
8. max-stat FWER p <= 0.05;
9. provenance/support/causality/finiteness/reproduction guards pass.

`ADAPTIVE_REFINEMENT_INCONCLUSIVE` if:

- pooled AUC > parent;
- >=3/4 positive fold deltas vs parent;
- all 4 LOO parent-relative deltas > 0;

but at least one survivor gate fails.

Otherwise:

`ADAPTIVE_REFINEMENT_REJECTED`

## 11. Advancement

At most three survivors.
At most one survivor per mechanism family.
Never fill an empty slot with an inconclusive refinement.

Even an E2 survivor remains adaptive evidence from reused BTC Jan-Jul and must
undergo independent historical replication before Sep-01+.

## 12. Process execution

- ProcessPoolExecutor allowed;
- max process workers = 10 because there are exactly ten refinement fits;
- BLAS/OpenMP threads = 1 per worker;
- deterministic preregistered result order;
- real execution must use an importable module harness with
  `if __name__ == "__main__"`;
- no stdin/heredoc process-pool execution.

## 13. Prohibitions

No:

- Sep-01+
- Railway/archive/abundant-love
- PnL
- threshold optimization
- calibration rescue
- class-weight search
- alternate model family
- feature subset search
- component-count tuning
- formula modification
- E1A/E1B/E2A rerun

Current state:

`DEV032_E2B_PROTOCOL_FROZEN_IMPLEMENTATION_ONLY_NO_REAL_FIT`
