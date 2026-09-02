# DEV032-E1B — Broad Predictive Screen Design v1

Status: `DESIGN_FROZEN_NO_PREDICTIVE_FIT_YET`

Date: 2026-09-02

## 1. Purpose

DEV032-E1B is the first predictive screening stage over the already-frozen
DEV032-E1A representations.

It is a development-only broad historical screen. It does not validate a
trading model, does not authorize PnL, and does not authorize any Sep-01+
forward access.

The scientific question is:

> Which preregistered microstructure mechanisms add stable directional ranking
> information beyond the frozen PRICE23 baseline on the already-consumed
> BTCUSDT Jan-Jul 2026 development sandbox?

The screen is intentionally ranking-specific. This does not retroactively alter
DEV031-P1B, whose terminal status remains:

`FAIL_EVENT_DEPTH_NO_STABLE_INCREMENTAL_DIRECTION_VALUE`

## 2. Frozen parent evidence

### DEV032-E1A

Canonical artifact:

`/home/emadh/Multi-Market/evidence/dev032_e1a_wave1_materialization_v1/DEV032_E1A_WAVE1_MATERIALIZATION.json`

SHA256:

`76e1c97e8b9a899bc27f3193316cbfc85efba8b0a7aa037d4c46fcc6a8be4a50`

bytes:

`44689`

Required state:

- status = `DEV032_WAVE1_EXACT_SUPPORT_MATERIALIZED`
- pass = true
- rows = 1374
- LONG = 684
- SHORT = 690
- strategies = 36
- all materialized values finite
- all forward/activity guards false
- read-only verification PASS

DEV032-E1A MUST NEVER be rerun.

### DEV031-P1B audit control

Canonical artifact:

`/home/emadh/Multi-Market/evidence/dev031_p1b_event_depth_incremental_v1/DEV031_P1B_EVENT_DEPTH_INCREMENTAL_RESULT.json`

SHA256:

`4e55554151b8caba588ea2ffdf7c6b1454a5eabe74f833a44f3784a980ddb56b`

bytes:

`14796`

Terminal status remains:

`FAIL_EVENT_DEPTH_NO_STABLE_INCREMENTAL_DIRECTION_VALUE`

P1B is used only as a frozen regression/reproduction control.

## 3. Fixed scientific task

- symbol: BTCUSDT
- historical development period: Jan-Jul 2026 only
- task: T1 `DIRECTION_GIVEN_TOUCH`
- target: A
- horizon: 120 s
- barrier: 16 bp
- causal information window: 32 s
- exact support: 1374 rows
- LONG: 684
- SHORT: 690

Exact chronological outer folds:

1. Jan-Mar train -> Apr validation
2. Jan-Apr train -> May validation
3. Jan-May train -> Jun validation
4. Jan-Jun train -> Jul validation

No fold may be changed after predictive outcomes exist.

## 4. Candidate universe

The E1A strategy blocks S00-S35 are immutable.

### 4.1 Baseline

`B00 = S00 = PRICE23`

### 4.2 Primary incremental candidates — exactly 34

The primary test asks whether a mechanism adds information beyond PRICE23.

- `P02 = S02`
  - exact frozen `PRICE23 + EVENT_DEPTH26`
  - implementation must assert that S02 equals exact concatenation S00 then S01

For every `k = 03..35`:

- `Pk = CONCAT(S00, Sk)`

Concatenation order is always S00 first, candidate block second.

Therefore:

- one baseline model
- 34 primary incremental candidate models
- no post-hoc candidate addition or deletion

### 4.3 Standalone mechanism diagnostics

For scientific interpretation only, standalone representations may also be
evaluated for:

- S01
- S03-S35

Standalone results are diagnostics. They cannot produce a
`STRONG_SCREENING_SURVIVOR` and are not used to choose the primary winner.

### 4.4 Fixed mechanism families

- legacy event/depth: S02
- aggregated snapshot control: S03
- queue/depth imbalance: S04-S07
- microprice/fair value: S08-S10
- multi-level/stationary order flow: S11-S15
- book geometry: S16-S20
- event pressure/transitions: S21-S24
- event timing/activity: S25-S28
- excitation/Hawkes-inspired: S29-S31
- resilience/recovery: S32-S33
- temporal-shape flow/event pressure: S34-S35

No family reassignment after outcomes exist.

## 5. Model policy

Wave-1 holds the model family constant to isolate information-set value.

For baseline and every primary candidate:

- `StandardScaler`, fit on training data only
- `LogisticRegression`
- penalty: L2
- solver: `lbfgs`
- `C_GRID = (0.01, 0.1, 1.0, 10.0)`
- `fit_intercept = True`
- `class_weight = None`
- `max_iter = 1000`
- `random_state = 20260825`
- decision threshold diagnostic only: 0.5

No:

- feature subset search
- threshold optimization
- class-weight search
- calibration rescue
- alternate model family
- XGBoost/HGB/MLP/TCN/Transformer in E1B
- architecture search

Nonlinear/model-family refinement belongs to a later experiment only after E1B
survivors exist.

## 6. Inner model selection

For each outer fold and representation:

- inner validation day = last day of the outer training period
- inner fit days = all earlier outer-training days
- evaluate all four C values

Select C lexicographically by:

1. lowest binary log loss
2. lowest Brier score
3. highest ROC AUC
4. lowest C

This intentionally preserves the P1B low-capacity model-selection lineage and
does not tune C directly to the E1B primary AUC outcome.

After C is selected, refit scaler and model on the complete outer-training
period and predict the outer validation day.

## 7. Mandatory regression reproduction before broad fitting

Before any new candidate is accepted as valid:

1. verify the frozen E1A artifact SHA/bytes/status/support;
2. verify all seven E1A daily file identities;
3. verify frozen P1B artifact SHA/bytes/status;
4. reproduce the exact frozen P3 PRICE23 OOF prediction hashes;
5. using E1A S00/S02 and the P1B model machinery, reproduce frozen P1B C0 and C1
   fold prediction hashes and pooled metrics;
6. assert E1A S02 is bitwise/numerically identical to concatenated S00+S01
   under the frozen CSV representation.

If reproduction fails, E1B is INVALID and no leaderboard is scientific evidence.

## 8. Primary endpoint

Primary endpoint:

`pooled OOF ROC AUC`

Primary candidate statistic:

`delta_auc_i = pooled_auc(P_i) - pooled_auc(B00)`

The OOF pool contains exactly the four validation folds Apr-Jul.

No model is ranked by in-sample performance.

## 9. Required metrics

For baseline and every primary candidate record:

- pooled ROC AUC
- pooled binary log loss
- pooled Brier score
- balanced accuracy at 0.5
- macro F1 at 0.5
- MCC at 0.5
- four fold AUC values
- four fold log losses
- four fold Brier scores
- selected C per fold
- support/label/prediction hashes

For every candidate versus B00:

- pooled AUC delta
- fold AUC deltas
- number of positive fold AUC deltas
- four leave-one-fold-out pooled AUC deltas
- worst-fold candidate AUC
- log-loss/Brier deltas as diagnostics

Probability metrics are diagnostic in E1B; they do not override the
ranking-specific primary endpoint.

## 10. Temporal null and family-wise multiplicity control

### 10.1 Primary null: stratified circular-shift max-stat

Predictions remain fixed.

Within each of the four validation folds, labels are circularly shifted.
For a fold of size `n`, legal nonzero shifts are integers satisfying:

`10 <= shift <= n-10`

A fixed RNG seed:

`NULL_SEED = 20260902`

generates exactly:

`NULL_REPLICATES = 1999`

four-fold shift tuples.

The same shift tuple is applied to all 34 primary candidates and B00 in each
replicate so the dependence structure across candidates is preserved.

For each null replicate:

1. shift labels independently within each validation fold;
2. concatenate the four shifted validation folds;
3. calculate AUC delta versus B00 for all 34 primary candidates;
4. store every candidate null delta;
5. store the maximum candidate AUC delta.

Primary family-wise quantities for each candidate:

- raw empirical temporal-null p
- single-step max-stat FWER empirical p
- q95 of the max-stat null
- observed delta minus q95 margin

Empirical p-values use the plus-one rule:

`p = (1 + exceedances) / (1 + NULL_REPLICATES)`

### 10.2 Legacy common-shift audit

For lineage comparability with DEV031-P1B, also compute the deterministic common
shift audit using the same shift k in every fold for all legal common k values.

This is diagnostic only and does not replace the 1999-replicate primary
max-stat null.

### 10.3 Optional stepdown diagnostic

Romano-Wolf-style stepdown adjusted p-values may be computed from the same
preregistered joint null matrix as a secondary diagnostic.

Promotion does not depend on stepdown significance; the conservative
single-step max-stat FWER gate remains primary.

## 11. Strong screening-survivor gates

A primary candidate is `STRONG_SCREENING_SURVIVOR` only if ALL are true:

1. pooled candidate AUC > pooled B00 AUC;
2. pooled candidate AUC >= 0.56;
3. at least 3 of 4 fold AUC deltas versus B00 are positive;
4. at least 3 of 4 candidate fold AUC values are > 0.50;
5. all four leave-one-fold-out pooled AUC deltas versus B00 are positive;
6. observed pooled AUC delta > q95 of the 34-candidate max-stat null;
7. single-step max-stat FWER empirical p <= 0.05;
8. all provenance, causality, support, finiteness, and execution guards pass.

No gate may be changed after outcomes exist.

## 12. Other statuses

`SCREENING_INCONCLUSIVE`

Requires:

- pooled AUC > B00;
- >=3/4 positive fold AUC deltas;
- all LOO AUC deltas positive;

but misses one or more of:

- absolute AUC >= 0.56;
- max-stat q95 gate;
- max-stat FWER p <= 0.05.

`SCREENING_REJECTED`

All other valid candidates.

`INVALID`

Any provenance, reproduction, support, label, finite-value, chronology, or
execution invariant failure.

## 13. Complete leaderboard rule

The artifact must contain every preregistered primary candidate, including
failures.

No candidate may be hidden because it performs badly.

Leaderboard ordering is descriptive only:

1. status class
2. lower max-stat FWER p
3. higher pooled AUC delta
4. higher worst-fold AUC
5. lower feature count
6. strategy ID lexical order

The ordering itself is not an additional significance test.

## 14. Advancement rule

At most three mechanisms may advance from E1B.

Advancement requires `STRONG_SCREENING_SURVIVOR`.

To reduce correlated refinement:

- initially at most one survivor per fixed mechanism family may advance;
- if more than one survivor exists in a family, choose by the frozen leaderboard
  ordering above.

If fewer than three strong survivors exist, do not fill empty slots with weak
candidates.

Any advanced mechanism is still exploratory and requires independent historical
replication before Sep-01+ may be considered.

## 15. Compute policy

E1B should use the workstation efficiently without changing model semantics.

Execution design:

- process-level parallelism across independent candidate/fold jobs;
- maximum worker cap: 20;
- BLAS/OpenMP threads per worker: 1;
- deterministic result ordering independent of completion order;
- no GPU is required for E1B LogisticRegression;
- GPU remains reserved for later preregistered nonlinear/sequence experiments.

The worker count affects runtime only and must not affect hashes or predictions.

## 16. Canonical output contract

Proposed canonical directory:

`/home/emadh/Multi-Market/evidence/dev032_e1b_broad_predictive_screen_v1`

Proposed artifact:

`DEV032_E1B_BROAD_PREDICTIVE_SCREEN_RESULT.json`

Before canonical execution the directory must not exist.

After one valid canonical E1B artifact is created:

`DEV032-E1B MUST NEVER BE RERUN`

Any material change requires a new experiment/version.

## 17. Forward and activity guards

Must remain false throughout E1B:

- Aug-01 opened
- Aug-30 opened
- Sep-01+ opened
- Railway opened
- market-raw-archive opened
- abundant-love opened
- downloads/acquisition run
- raw E1A rematerialization run
- PnL run
- threshold optimization run
- calibration rescue run
- feature subset search run
- alternate model family run

E1B reads only the frozen local E1A/P1B/P3 evidence required by the protocol.

## 18. Interpretation boundary

Even a strong E1B result means only:

`BTC JAN-JUL DEVELOPMENT SCREENING SURVIVOR`

It does not mean:

- validated model
- deployable strategy
- profitability
- economic edge
- forward confirmation
- Sep-01+ authorization

Independent historical replication remains mandatory.

## 19. Literature rationale

The frozen mechanism universe is supported by distinct literature strands:

- Xu, Gould & Howison: multi-level order-flow imbalance and deeper LOB levels;
- Kolm, Turiel & Westray: stationary order-flow inputs can outperform raw book
  states;
- Zhang, Zohren & Roberts: spatial/temporal LOB representations (DeepLOB);
- Berti & Kasneci: complex architectures are not automatically necessary;
- 2026 Bitcoin multivariate Hawkes/LOB forecasting: event timing and
  cross-excitation are directly relevant to crypto LOB prediction;
- White's Reality Check and Romano-Wolf multiple testing: broad model screens
  require explicit protection against data snooping and multiplicity.

## 20. Next permitted action

After this design is committed:

1. implement E1B loader/model/null/leaderboard code;
2. write synthetic and regression tests;
3. reproduce P3/P1B exactly in tests or preflight;
4. run CI only;
5. freeze implementation commit;
6. run local preflight;
7. only then authorize the single canonical E1B predictive screen.

Current state:

`DEV032_E1B_DESIGN_FROZEN_IMPLEMENTATION_ONLY_NO_PREDICTIVE_FIT_YET`
