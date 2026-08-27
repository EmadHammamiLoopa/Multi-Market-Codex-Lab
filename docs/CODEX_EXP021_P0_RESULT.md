# CODEX-EXP-021-P0 Frozen Result

Status: **NO_CALIBRATION_DESIGN_READY_SANDBOX**

Date: 2026-08-27

Frozen pre-output HEAD:

`6b0b67487fa5132d23b8c913611669a8640fb17b`

Result artifact:

`evidence/codex/exp021_p0_calibration_design/CALIBRATION_DESIGN_AUDIT.json`

Result artifact SHA-256:

`39dae4bc576beef8625584eb0e45e953ca10cd7b6b7a46852ebaa15e99e63c1e`

Parent EXP020 diagnostic:

`DIAGNOSTIC_COMPLETE_VOLATILITY_FALSIFICATION_AND_CALIBRATION`

Frozen EXP019 status remains:

`FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED`

## Official adjudication

`CODEX-EXP-021-P0 = NO_CALIBRATION_DESIGN_READY_SANDBOX`

No calibration design satisfied the frozen readiness rule.

This is a valid sandbox design-audit outcome, not INVALID.

No predictive validation claim is permitted.

## Aggregate comparison

### RAW

- n = **5,596**
- aggregate Brier score = **0.11753406053809577**
- aggregate log loss = **0.3914415319475509**
- aggregate fold-normalized Brier skill = **0.03490639785859251**

### ROLLING_OOF_INTERCEPT

- aggregate Brier score = **0.1182389693187496**
- aggregate log loss = **0.3952053670662963**
- aggregate fold-normalized Brier skill = **0.029118263328161698**
- Brier improved vs RAW in **2/4** folds
- log loss improved vs RAW in **1/4** folds
- AUC preserved in **4/4** folds

### ROLLING_OOF_PLATT

- aggregate Brier score = **0.12056385766129459**
- aggregate log loss = **0.4035588749202987**
- aggregate fold-normalized Brier skill = **0.010028181229312927**
- Brier improved vs RAW in **1/4** folds
- log loss improved vs RAW in **1/4** folds
- AUC preserved in **4/4** folds
- Platt slope positive in **4/4** folds

Both calibrated candidates retained positive aggregate fold-normalized Brier skill, but both were worse than RAW on aggregate Brier and log loss and failed the frozen fold-consistency requirements.

## Candidate readiness

### ROLLING_OOF_INTERCEPT

Failed:

- aggregate Brier improves vs RAW
- aggregate log loss improves vs RAW
- Brier improves in at least 3/4 folds
- log loss improves in at least 3/4 folds

Passed:

- aggregate fold-normalized Brier skill > 0
- AUC preserved in all four folds

Official readiness: **false**

### ROLLING_OOF_PLATT

Failed:

- aggregate Brier improves vs RAW
- aggregate log loss improves vs RAW
- Brier improves in at least 3/4 folds
- log loss improves in at least 3/4 folds

Passed:

- aggregate fold-normalized Brier skill > 0
- AUC preserved in all four folds
- Platt slope positive in all four folds

Official readiness: **false**

## Fold observations

The historical calibration relation was not stable enough for either frozen method to dominate RAW causally.

Examples:

- Apr: RAW outperformed both calibration methods on Brier and log loss.
- May: intercept calibration modestly improved both Brier and log loss.
- Jun: Platt modestly improved both Brier and log loss.
- Jul: intercept marginally improved Brier but not log loss.

This lack of temporal consistency is exactly what the frozen readiness rule was designed to detect.

## Scientific interpretation

EXP020 showed that the Aug-01 calibration failure was materially associated with an extreme prevalence shift.

EXP021 now shows that this does **not** imply that a simple deployable historical calibration correction can be learned reliably from Jan-Jul.

The historical RAW VOL probabilities were already better overall than either frozen rolling calibration method on Apr-Jul.

Therefore:

1. do not deploy rolling intercept correction;
2. do not deploy rolling Platt scaling;
3. do not use the post-hoc Aug prior-shift correction from EXP020 operationally;
4. do not continue adding calibration methods merely to rescue the Aug result.

The available evidence supports a stronger distinction:

- VOL **ranking/timing alignment** has substantial evidence;
- probability calibration is regime-sensitive and currently lacks a causally selected robust correction.

## Invariants

All invariants passed:

- EXP020 artifact SHA exact
- EXP020 status exact
- EXP019 frozen FAIL unchanged
- Apr-Jul outer folds exact
- OOF history begins at Mar
- base-model training strictly earlier than each outer fold
- calibration history strictly earlier than each target fold
- Aug feature reparsed = false
- older August holdout opened = false
- direction scored = false
- PnL scored = false
- network accessed = false
- EXP019 re-adjudicated = false

## Research implication

Calibration-method search should stop here unless a materially new, independently justified calibration hypothesis exists.

The next scientifically cleaner step is not another calibration rescue audit.

A future fresh holdout experiment should explicitly separate:

1. **ranking/timing confirmation**, using a falsification control that destroys test-time feature/label alignment;
2. **probability calibration**, reported as a separate secondary property rather than allowed to obscure rank evidence;
3. direction and PnL, which remain prohibited until the new opportunity-predictability protocol passes its own preregistered ranking/timing gates.

Any fresh validation requires a new Experiment ID and must use a still-unopened holdout.
