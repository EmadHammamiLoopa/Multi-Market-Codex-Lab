# CODEX-EXP-028-P0 Abstention-Aware Direction Readiness

Status: PREREGISTERED DEVELOPMENT / READINESS PHASE — NO FRESH HOLDOUT OPENED

## Motivation

CODEX-EXP-026-P0 ended as the frozen result:

FAIL_DIRECTION_EXECUTION_PIPELINE_NOT_READY

because at least one validation fold produced zero executable trades under the
frozen opportunity gate.

EXP028-P0 does not rescue or modify EXP026. It defines a new experiment ID
before any new scoring is performed.

## Authorized data

Only the already-consumed Jan-Jul 2026 BTCUSDT historical sandbox may be used.

2026-08-30 remains consumed diagnostic data and is not opened in P0.

2026-09-01 and later remain unopened prospective candidates.

No network acquisition or backfill is permitted.

## Frozen upstream opportunity gate

The opportunity mechanism remains unchanged from EXP026:

- sole opportunity feature: rv_30m_bps
- decision interval: 60 seconds
- entry latency: 250 ms
- execution horizon: 600 seconds
- opportunity label threshold: 24 bp
- StandardScaler + LogisticRegression
- C=1
- L2
- lbfgs
- max_iter=1000
- random_state=20260825
- fold trigger = training-set opportunity probabilities only
- trigger = np.quantile(probabilities, 0.90, method="higher")

The opportunity threshold must not be reduced, swept, tuned, or rescued.

## Direction candidates

Exactly three candidates are permitted:

A. Logistic direction model using:
ret_1m_bps
ret_3m_bps
ret_5m_bps
ret_10m_bps
ret_30m_bps
rv_30m_bps
spread_bps

B. 10-minute momentum:
ret_10m_bps >= 0 -> LONG
otherwise SHORT

C. 10-minute mean reversion:
ret_10m_bps >= 0 -> SHORT
otherwise LONG

No additional candidate may be introduced under this experiment ID.

## Historical folds

Use the same expanding chronological folds:

1. Jan-Mar train -> Apr validation
2. Jan-Apr train -> May validation
3. Jan-May train -> Jun validation
4. Jan-Jun train -> Jul validation

All models and opportunity thresholds are training-only.

## Abstention-aware fold rule

Opportunity eligibility is common to A, B, and C.

A validation fold is ACTIVE when the frozen opportunity gate produces at least
one executed non-overlapping trade.

A validation fold is ABSTENTION when it produces zero executed trades.

An ABSTENTION fold:

- is recorded explicitly;
- has zero realized PnL;
- has zero exposure;
- has no defined net_bps_per_trade;
- is not converted to a synthetic zero-bps-per-trade observation;
- cannot alter the opportunity trigger;
- cannot alter candidate definitions.

Because opportunity eligibility is shared across A/B/C, ACTIVE versus
ABSTENTION status must be identical for all candidates within a fold.

## Selection feasibility

Historical direction selection is feasible only if at least 3 of the 4
validation folds are ACTIVE.

If fewer than 3 validation folds are ACTIVE:

FAIL_ABSTENTION_AWARE_DIRECTION_PIPELINE_NOT_READY

No alternate threshold, session filter, subset, or rescue is permitted.

## Candidate selection

Among ACTIVE folds only, the primary statistic is:

median validation-fold net_bps_per_trade

Tie-breaks, in order:

1. more ACTIVE folds with positive total net bps;
2. higher pooled profit factor across executed ACTIVE-fold trades;
3. lower pooled maximum drawdown in bps;
4. simpler candidate in the order B, C, A.

ABSTENTION folds are reported but excluded from per-trade direction ranking
because net_bps_per_trade is undefined when no trade exists.

## Execution

Unchanged from EXP026:

- flat-only execution;
- entry at decision t + 250 ms;
- hold exactly 600 seconds;
- ignore signals while a position remains open;
- spread crossing included in executable gross return;
- primary incremental round-trip cost = 14 bp;
- stress incremental round-trip cost = 20 bp;
- no leverage;
- no pyramiding;
- no stop loss;
- no take profit;
- no position-sizing optimization;
- no post-hoc filtering.

## P0 status

PASS:

ABSTENTION_AWARE_DIRECTION_PIPELINE_READY_FOR_FRESH_PROSPECTIVE_VALIDATION

requires:

- provenance verified;
- all four historical folds processed causally;
- at least three ACTIVE validation folds;
- ACTIVE/ABSTENTION pattern identical across A/B/C;
- exactly one candidate selected by the frozen rule;
- final Jan-Jul parameters recorded;
- non-overlap and timing invariants verified;
- no fresh future holdout opened.

FAIL:

FAIL_ABSTENTION_AWARE_DIRECTION_PIPELINE_NOT_READY

for a clean implementation that does not satisfy the frozen historical
selection-feasibility rule.

INVALID:

for provenance, causality, future-data, serialization, one-shot, or protocol
violations.

P0 PASS is a readiness result only. It does not establish prospective
profitability.

## Non-negotiable guards

- EXP026 remains frozen and is never rerun.
- No opportunity-threshold reduction or sweep.
- No added direction candidate.
- No session/subset rescue.
- No leverage optimization.
- No Aug-30 analytical opening in EXP028-P0.
- No Sep-01-or-later opening.
- No network acquisition.
- All experimental outputs are one-shot and immutable.

## Frozen Candidate A model specification

Candidate A uses exactly the EXP026 direction-model specification:

- StandardScaler
- LogisticRegression
- C = 1.0
- penalty = l2
- solver = lbfgs
- class_weight = None
- max_iter = 1000
- random_state = 20260825

The direction label is:

long_preferred = 1[long_executable_bps > short_executable_bps]

Candidate A predicts LONG when:

P(long_preferred = 1) >= 0.5

and SHORT otherwise.

No confidence threshold, probability calibration, class weighting, threshold
sweep, or alternative classifier is permitted.

If an authorized Candidate A training set contains valid exact-binary labels
but only one observed class, this is a clean readiness failure, not a protocol
violation.

Malformed, non-finite, non-binary, provenance-invalid, or causally invalid
inputs remain protocol violations and therefore INVALID.

## Final Jan-Jul freeze after historical selection

If historical selection is feasible and exactly one candidate is selected:

1. refit the frozen opportunity model on the full authorized Jan-Jul common
   support;
2. compute opportunity probabilities on that same authorized Jan-Jul training
   support;
3. freeze the final opportunity trigger as:

   np.quantile(training_probabilities, 0.90, method="higher")

4. if Candidate A is selected, refit Candidate A on the full authorized
   Jan-Jul direction-training support using the exact frozen model
   specification above;
5. if Candidate B or C is selected, record its deterministic rule unchanged;
6. record the selected candidate, final opportunity trigger, model
   hyperparameters, training support, and provenance in the immutable P0
   artifact.

No Aug-30 or Sep-01-or-later data may participate in this final refit or
trigger calculation.

The final Jan-Jul frozen rule may be used only by a separately preregistered
future prospective-validation experiment.
