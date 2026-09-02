# DEV032-E2 — Wave-2 Adaptive Refinement Design v1

Status: `DESIGN_FROZEN_NO_E2_MATERIALIZATION_OR_MODEL_FIT_YET`

Date: 2026-09-02

## 1. Purpose

DEV032-E2 is an adaptive Wave-2 refinement stage over the already-consumed
BTCUSDT Jan-Jul 2026 development sandbox.

It exists because DEV032-E1B-R1 produced:

- 34 primary candidates;
- 14 `SCREENING_INCONCLUSIVE`;
- 20 `SCREENING_REJECTED`;
- 0 `STRONG_SCREENING_SURVIVOR`;
- 0 advanced mechanisms.

The authoritative E1B-R1 artifact is:

`/home/emadh/Multi-Market/evidence/dev032_e1b_r1_broad_predictive_screen_v1/DEV032_E1B_BROAD_PREDICTIVE_SCREEN_RESULT.json`

SHA256:

`af223d3f97b85ae1c929f81b3ec71e892477b9b26e719638acb05ae153578b95`

bytes:

`287823`

DEV032-E1B-R1 MUST NEVER be rerun.

E2 is explicitly adaptive/exploratory. It cannot validate a model, authorize
PnL, or authorize Sep-01+.

## 2. Why Wave-2 is refinement, not winner chasing

E1B did not produce a multiplicity-controlled strong survivor.

Therefore E2 must not:

- choose P21 alone because it ranked first;
- choose only the top three observed AUCs;
- lower the E1B family-wise threshold;
- change the E1B terminal classifications;
- reopen any E1B rejected candidate by ad-hoc rationale.

Instead E2 follows the pre-E1B Candidate Registry and Wave-1 rule:

> Wave 2 may open for families with a stable E1 survivor or a scientifically
> interesting near-survivor, remains adaptive/exploratory, and has a hard cap
> of 24 strategies.

White-style data-snooping concerns are especially relevant because BTC Jan-Jul
has already been reused for model screening. E2 therefore keeps the adaptive
search finite, publishes the full Wave-2 leaderboard, and applies a new joint
max-stat family-wise null across every new Wave-2 refinement hypothesis.

## 3. Frozen E1B inconclusive parent universe — exactly 14

These are carried forward as immutable parent anchors, not new hypotheses:

| Parent | Family | E1B pooled AUC | E1B delta vs B00 | E1B FWER p |
|---|---|---:|---:|---:|
| P21 | event_pressure_transition | 0.5870721780915955 | 0.050603118564283456 | 0.0715 |
| P35 | temporal_shape | 0.5825242718446602 | 0.046055212317348104 | 0.1080 |
| P13 | multilevel_stationary_order_flow | 0.5818010199078161 | 0.04533196038050402 | 0.1175 |
| P02 | legacy_event_depth | 0.576493086201824 | 0.04002402667451199 | 0.1850 |
| P14 | multilevel_stationary_order_flow | 0.5574065901735805 | 0.020937530646268465 | 0.6810 |
| P07 | queue_depth_imbalance | 0.554182602726292 | 0.017713543198979997 | 0.7940 |
| P32 | resilience_recovery | 0.5521844660194175 | 0.015715406492105455 | 0.8470 |
| P09 | microprice_fair_value | 0.5520863979601843 | 0.015617338432872274 | 0.8505 |
| P06 | queue_depth_imbalance | 0.5497205060311856 | 0.013251446503873554 | 0.9100 |
| P05 | queue_depth_imbalance | 0.5475630087280573 | 0.011093949200745246 | 0.9500 |
| P08 | microprice_fair_value | 0.5468274982838089 | 0.01035843875649689 | 0.9665 |
| P04 | queue_depth_imbalance | 0.5465823281357262 | 0.010113268608414105 | 0.9695 |
| P17 | book_geometry | 0.5432602726292046 | 0.006791213101892568 | 0.9860 |
| P20 | book_geometry | 0.5377439442973424 | 0.001274884770030349 | 0.9995 |

The parent values above are audit anchors only. E2 implementation must read and
verify them from the frozen E1B artifact rather than type them into scientific
calculations.

## 4. Family eligibility

A family is E2-refinable only if:

1. at least one of its E1B candidates had frozen status
   `SCREENING_INCONCLUSIVE`; and
2. the pre-E1B Candidate Registry contains at least one suitable `LATER`
   refinement that preserves the mechanism's scientific lineage.

Eight E1B families had at least one inconclusive parent:

- queue_depth_imbalance
- microprice_fair_value
- multilevel_stationary_order_flow
- book_geometry
- event_pressure_transition
- temporal_shape
- resilience_recovery
- legacy_event_depth

The legacy_event_depth family has no dedicated, clean `LATER` refinement in
the registry that can be assigned without mixing scientific families. It is
therefore retained as an anchor only and receives no new E2 refinement.

## 5. Deterministic allocation rule for the 10 new refinements

Wave-2 hard cap is 24 strategies.

Exactly 14 slots are occupied by the immutable inconclusive parent anchors.

Therefore exactly 10 slots are available for new adaptive refinements.

Allocation is frozen as follows:

1. give one refinement slot to each of the seven refinable families;
2. the remaining three slots go to families with more than one inconclusive
   parent;
3. rank those families by number of inconclusive parents descending;
4. ties are broken by the original Candidate Registry section order.

Observed family counts:

- queue_depth_imbalance = 4
- microprice_fair_value = 2
- multilevel_stationary_order_flow = 2
- book_geometry = 2
- event_pressure_transition = 1
- temporal_shape = 1
- resilience_recovery = 1
- legacy_event_depth = 1

Thus the three extra slots go to:

1. queue_depth_imbalance
2. microprice_fair_value
3. multilevel_stationary_order_flow

No E1B effect size or p-value is used to choose between alternative `LATER`
refinements inside a family. Within each family, use registry order.

## 6. New Wave-2 refinement universe — exactly 10

### E2R01 — B06 QUEUE_IMBALANCE_X_SPREAD_STATE

Registry source:
`B06 | queue-imbalance × spread-state interaction | LATER`

Family:
`queue_depth_imbalance`

Frozen parent anchor:
`P07` — best-ranked inconclusive queue/depth parent under the already-frozen
E1B leaderboard ordering.

Model:
same low-capacity L2 LogisticRegression lineage.

### E2R02 — B07 QUEUE_IMBALANCE_EVENT_PERSISTENCE

Registry source:
`B07 | queue-imbalance persistence over event time | LATER`

Family:
`queue_depth_imbalance`

Frozen parent anchor:
`P07`

Model:
same L2 LogisticRegression lineage.

### E2R03 — C04 MICROPRICE_X_QUEUE_IMBALANCE

Registry source:
`C04 | microprice displacement × queue imbalance | LATER`

Family:
`microprice_fair_value`

Frozen parent anchor:
`P09`

Model:
same L2 LogisticRegression lineage.

### E2R04 — C06 MICROPRICE_ACCELERATION_CURVATURE

Registry source:
`C06 | microprice acceleration / curvature | LATER`

Family:
`microprice_fair_value`

Frozen parent anchor:
`P09`

Model:
same L2 LogisticRegression lineage.

### E2R05 — D08 TRAIN_ONLY_PCA_MLOFI

Registry source:
`D08 | principal components of level-wise MLOFI fit train-only | LATER`

Family:
`multilevel_stationary_order_flow`

Frozen parent anchor:
`P13`

PCA is fit on training data only inside each fold.

Model after PCA:
same L2 LogisticRegression lineage.

### E2R06 — D09 TRAIN_ONLY_LOW_RANK_SVD_ORDER_FLOW

Registry source:
`D09 | low-rank SVD stationary order flow fit train-only | LATER`

Family:
`multilevel_stationary_order_flow`

Frozen parent anchor:
`P13`

SVD is fit on training data only inside each fold.

Model after SVD:
same L2 LogisticRegression lineage.

### E2R07 — E08 DEPTH_DISPERSION_WEIGHTED_VARIANCE

Registry source:
`E08 | depth dispersion / weighted variance | LATER`

Family:
`book_geometry`

Frozen parent anchor:
`P17`

Model:
same L2 LogisticRegression lineage.

### E2R08 — F09 EVENT_TYPE_RUN_LENGTH_PERSISTENCE

Registry source:
`F09 | event-type run lengths / sign persistence | LATER`

Family:
`event_pressure_transition`

Frozen parent anchor:
`P21`

Model:
same L2 LogisticRegression lineage.

### E2R09 — G12 SIGNED_EVENT_TIME_MOMENTUM

Registry source:
`G12 | signed event-time momentum | LATER`

Adaptive mapping:
temporal refinement of the E1B `temporal_shape` near-survivor family.

Frozen parent anchor:
`P35`

Model:
same L2 LogisticRegression lineage.

This mapping is frozen now before any E2 feature extraction or metric.

### E2R10 — I06 SHOCK_CONDITIONED_RECOVERY_CURVE

Registry source:
`I06 | shock-conditioned recovery curve parameters | LATER`

Family:
`resilience_recovery`

Frozen parent anchor:
`P32`

Model:
same L2 LogisticRegression lineage.

## 7. Wave-2 total strategy count

Wave-2 contains exactly:

- 14 immutable E1B inconclusive parent anchors
- 10 new E2 refinement hypotheses

Total:

`24`

This exactly meets, and does not exceed, the pre-E1B hard cap.

## 8. Fixed task and support

Unless E2A materialization fails closed:

- BTCUSDT
- Jan-Jul 2026 consumed development sandbox only
- T1 `DIRECTION_GIVEN_TOUCH`
- target A
- horizon 120 s
- barrier 16 bp
- causal information window 32 s
- exact support 1374
- LONG 684
- SHORT 690
- no support shrink
- no label changes

The exact four outer folds remain:

1. Jan-Mar -> Apr
2. Jan-Apr -> May
3. Jan-May -> Jun
4. Jan-Jun -> Jul

## 9. E2 stage decomposition

### DEV032-E2A — representation/materialization only

Before any E2 predictive fit:

- freeze exact formulas for E2R01-E2R10;
- materialize all deterministic raw-derived blocks where required;
- preserve exact E1A support and labels;
- require all values finite;
- hash every daily and campaign matrix;
- no predictive fit;
- no predictive metric;
- no null;
- no PnL.

Train-only transforms such as PCA/SVD are NOT globally materialized. Their raw
input matrices are materialized in E2A, while the transform itself is fit
inside each training fold during E2B.

### DEV032-E2B — adaptive predictive refinement screen

Only after E2A is frozen and independently verified.

## 10. E2B model policy

For every vector refinement:

- StandardScaler fit on training only;
- L2 LogisticRegression;
- solver `lbfgs`;
- `l1_ratio=0.0`;
- `C_GRID=(0.01,0.1,1.0,10.0)`;
- same chronological inner C selection as E1B;
- no threshold optimization;
- no class-weight search;
- no calibration rescue.

For E2R05/E2R06, the train-only PCA/SVD transform is part of the fold pipeline
and must be fit using training data only.

No:

- HGB/XGBoost rescue
- MLP/TCN/GRU/Transformer in E2
- architecture search
- feature deletion after outcome review

Sequence/deep refinements remain deferred to E3 only if E2 produces a genuine
adaptive refinement survivor.

## 11. Parent-relative primary endpoint

E2 asks whether a preregistered refinement improves its frozen parent mechanism.

Primary endpoint remains:

`pooled OOF ROC AUC`

Primary refinement statistic for refinement j:

`delta_parent_j = AUC(E2Rj) - AUC(parent_j)`

B00 PRICE23 remains a global reference diagnostic, but the primary E2
hypothesis is parent-relative.

## 12. Required metrics

For every new refinement:

- pooled ROC AUC
- pooled log loss
- pooled Brier
- balanced accuracy at 0.5
- macro F1 at 0.5
- MCC at 0.5
- four fold AUCs
- selected C by fold
- prediction hashes

Relative to its frozen parent:

- pooled AUC delta
- four fold AUC deltas
- number positive fold deltas
- four leave-one-fold-out pooled AUC deltas
- worst-fold candidate AUC
- log-loss/Brier changes as diagnostics

Relative to B00:

- pooled AUC delta
- descriptive only for E2 promotion

## 13. E2 joint temporal null and multiplicity control

Use exactly:

- `NULL_SEED = 20260902`
- `NULL_REPLICATES = 1999`
- within-validation-fold circular label shifts
- legal shift rule `10 <= shift <= n-10`

For every null replicate, use the same four-fold shift tuple for:

- B00
- every frozen parent anchor
- all 10 E2 refinements

For each E2 refinement calculate the shifted-label parent-relative AUC delta.

Store:

- each refinement null delta
- maximum parent-relative delta across all 10 E2 refinements

Primary multiplicity quantities:

- raw empirical p
- single-step max-stat FWER p
- q95 of the 10-refinement max-stat null
- observed delta minus q95

Use plus-one empirical p-values.

Optional Romano-Wolf-style stepdown values may be recorded as secondary
diagnostics only. They do not replace the single-step max-stat promotion gate.

## 14. Adaptive refinement survivor gates

An E2 refinement is:

`ADAPTIVE_REFINEMENT_SURVIVOR`

only if ALL are true:

1. pooled refinement AUC > pooled frozen-parent AUC;
2. pooled refinement AUC > B00 pooled AUC;
3. pooled refinement AUC >= 0.56;
4. at least 3/4 fold AUC deltas versus its parent are positive;
5. at least 3/4 refinement fold AUC values are > 0.50;
6. all four leave-one-fold-out AUC deltas versus its parent are positive;
7. observed parent-relative pooled AUC delta > q95 of the 10-refinement
   max-stat null;
8. max-stat FWER empirical p <= 0.05;
9. all support, provenance, causality, finiteness, and execution guards pass.

## 15. Other E2 statuses

`ADAPTIVE_REFINEMENT_INCONCLUSIVE`

Requires:

- pooled AUC > parent;
- >=3/4 positive fold deltas versus parent;
- all LOO parent-relative AUC deltas positive;

but misses one or more strong-survivor gates.

`ADAPTIVE_REFINEMENT_REJECTED`

All other valid refinements.

`INVALID`

Any provenance/support/label/causality/finiteness/reproduction violation.

## 16. Advancement rule

At most three E2 refinements may advance.

Advancement requires:

`ADAPTIVE_REFINEMENT_SURVIVOR`

At most one advancing refinement per mechanism family.

Do not fill empty slots with inconclusive or rejected candidates.

Even an E2 survivor is still adaptive evidence from reused BTC Jan-Jul data.

Independent historical replication remains mandatory before any Sep-01+
forward confirmation.

## 17. Complete publication/audit rule

E2B must retain:

- all 14 parent anchors
- all 10 refinements
- all failures
- full null results
- all adjusted p-values
- full leaderboard

No result may be removed because it performs badly.

## 18. Forward and activity guards

Must remain false throughout E2:

- Aug-01 opened
- Aug-30 opened
- Sep-01+ opened
- Railway opened
- market-raw-archive opened
- abundant-love opened
- forward metadata listing
- downloads/acquisition
- PnL
- threshold optimization
- calibration rescue
- unregistered model-family rescue

## 19. Stop rule

If E2 produces zero `ADAPTIVE_REFINEMENT_SURVIVOR`:

- do not create E3 by simply loosening thresholds;
- do not open Sep-01+;
- do not cherry-pick the best E2 candidate;
- close the current engineered-vector refinement line unless a separately
  preregistered, scientifically distinct representation program is justified.

If E2 produces one or more genuine survivors, E3 may refine at most 12 finalists
under a separately frozen protocol.

## 20. Next permitted action

No E2 model fit is authorized yet.

Next:

1. freeze exact formulas for E2R01-E2R10;
2. implement DEV032-E2A materialization only;
3. synthetic tests and CI;
4. freeze E2A execution;
5. local preflight;
6. single E2A canonical materialization;
7. independent read-only verification;
8. only then design/implement E2B predictive screen.

Current state:

`DEV032_E2_WAVE2_DESIGN_FROZEN_E2A_FORMULAS_NEXT_NO_MODEL_FIT`
