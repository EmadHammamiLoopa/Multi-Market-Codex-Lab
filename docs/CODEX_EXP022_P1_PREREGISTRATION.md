# CODEX-EXP-022-P1 Preregistration

Status: **PREREGISTERED BEFORE ANY EXP022-P1 ANALYTICAL OPENING**

Date frozen: 2026-08-29

Experiment ID: `CODEX-EXP-022-P1`

Parent preserved commit:

`54153407a5b8995b921923a48d21cb6ba00568b3`

Parent P0 status:

`PROSPECTIVE_BOOKTICKER_DATA_READY`

This document freezes the EXP022-P1 scientific protocol before the prospective 2026-08-28 grid is opened for analytical parsing, target construction, model scoring, or metric calculation.

## Identity and frozen provenance

P0 audit artifact:

`evidence/codex/exp022_p0_prospective_bookticker/PROSPECTIVE_BOOKTICKER_AUDIT.json`

Required P0 audit artifact SHA-256:

`d1d2a90844260e88ab2fae4e20456960c2491512b91372147f3810c16c71d779`

Required prospective raw SHA-256 as recorded in the P0 audit:

`c0a11173f8f03dbad787f18e3a7db31af1b1d8abb113f1171772ef9c6460f5a0`

Required prospective 250 ms grid SHA-256:

`cf3a7291bc54a819e6b619badfcd01db10d4330566d0c3d8d3f16f204b7988ad`

Required prospective grid byte size:

`33390476`

The P1 implementation must verify the exact prospective grid byte size and raw-byte SHA-256 before parsing the grid. Hashing for this authorization step is opaque-byte integrity verification, not analytical parsing.

The prospective raw gzip JSONL is not an EXP022-P1 analytical input. P1 must not open it, including for hash recomputation. The frozen raw digest may be checked only as a field in the already-frozen P0 audit.

## Scientific question

Does the already-frozen single causal trailing realized-volatility state variable `rv_30m_bps` prospectively rank occurrence of the already-frozen 10-minute, at-least-24 bp executable BTCUSDT opportunity on the genuinely unseen 2026-08-28 UTC day?

This is a ranking/timing confirmation experiment only.

It is not:

- a direction experiment;
- a trading-PnL experiment;
- a leverage experiment;
- a calibration-method search;
- a feature search;
- a threshold search;
- a model search.

## Relationship to prior frozen results

EXP019 tested the same one-feature volatility hypothesis on the already-consumed 2026-08-01 holdout and remains permanently:

`FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED`

EXP020 showed diagnostically that the old within-training-day label permutation did not destroy the one-feature prospective ranking and that the Aug-01 result exhibited severe prevalence/calibration shift. EXP020 did not rescue EXP019.

EXP021 found no historically selected calibration design ready for prospective use and remains:

`NO_CALIBRATION_DESIGN_READY_SANDBOX`

EXP022-P1 therefore tests only the ranking/timing hypothesis on new prospective data. Calibration diagnostics are secondary and non-gating. The old training-label placebo and future canary are not P1 gates.

## Frozen data scope

Symbol:

`BTCUSDT`

Historical model-training days are exactly:

- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

Only the already-consumed frozen Phase-L historical data for those BTCUSDT days may be used for training and pre-open implementation validation.

Prospective validation day:

`2026-08-28`

The prospective analytical input is only the exact finalized 250 ms grid whose byte size and SHA-256 are frozen above.

Forbidden analytical inputs are:

- 2026-08-01;
- 2026-08-04 through 2026-08-23;
- every other August day;
- ETH;
- any new network data;
- options;
- funding;
- open interest;
- liquidations;
- macro data;
- news;
- on-chain data;
- the prospective raw gzip JSONL.

Aug-01 must not be added to training even though it has already been consumed by earlier experiments. The historical model remains exactly the Jan-Jul model so EXP022-P1 is a clean prospective confirmation of the already-developed hypothesis.

## Required pre-open authorization order

Before the prospective grid is parsed analytically, the later P1 implementation must perform all of the following:

1. verify the frozen parent/protocol provenance;
2. hash the P0 audit artifact as opaque bytes and require the exact frozen P0 audit SHA-256;
3. parse that verified audit and require:
   - `experiment_id = CODEX-EXP-022-P0`;
   - `status = PROSPECTIVE_BOOKTICKER_DATA_READY`;
   - the recorded raw SHA-256 equals the frozen raw digest;
   - the recorded grid SHA-256 equals the frozen grid digest;
   - the recorded grid byte size equals `33390476`;
   - all P0 integrity gates have their frozen PASS/false-guard values;
4. require the prospective grid file byte size to equal `33390476` without parsing it;
5. hash the prospective grid as opaque bytes and require the exact frozen grid SHA-256;
6. verify the frozen Jan-Jul historical input provenance;
7. verify that no forbidden August, raw prospective, direction, PnL, leverage, or network access has occurred;
8. complete the pre-open implementation validation defined below.

Any failure in these checks must abort before prospective analytical parsing and produce `INVALID` if a one-shot P1 artifact is being created.

## Frozen primary feature

The only legitimate predictive feature is:

`rv_30m_bps`

No other legitimate feature is allowed.

EXP022-P1 inherits the exact Phase-L / EXP004 / EXP019 realized-volatility construction. It must reuse the existing frozen helper semantics where appropriate rather than inventing a new feature.

For an eligible decision timestamp `t` on the 250 ms grid:

- one minute is exactly 240 grid rows;
- use 31 causal mid observations at exactly `t-30m, t-29m, ..., t-1m, t`;
- those observations define 30 consecutive one-minute log returns;
- if the sampled mids are `m_0, ..., m_30`, then `r_j = log(m_j / m_{j-1})` for `j = 1, ..., 30`;
- `rv_30m_bps = 10000 * sqrt(sum(r_j^2, j=1..30))`.

The exact inherited validity semantics are:

- every 250 ms book state in the inclusive interval `[t-30m, t]` must have `book_valid = 1`;
- all required mids must be finite and strictly positive;
- only grid information at or before `t` may be used;
- no midpoint may be interpolated;
- no future feature fill is permitted;
- no forward fill is permitted across an invalid book interval;
- no prior-day state may fill the beginning of 2026-08-28;
- if the complete causal interval is unavailable or invalid, the feature is invalid.

This full-interval rule reproduces the existing `_r_features` / `_rv` semantics: the numerical realized volatility uses 31 one-minute samples, while feature validity requires uninterrupted causal 250 ms book validity across the complete 30-minute lookback.

## Frozen target

The target is inherited exactly from EXP004 and EXP019.

Decision grid:

Every 60 seconds from 2026-08-28 00:00:00 UTC. On the 250 ms grid this is every 240 rows.

At an eligible decision time `t`:

- `entry = t + 250 ms`, exactly one 250 ms grid step after the decision;
- `exit = entry + 600 s`, exactly 2,400 grid steps after entry;
- `long_gross_bps = 10000 * log(bid_exit / ask_entry)`;
- `short_gross_bps = 10000 * log(bid_entry / ask_exit)`;
- `oracle_gross_bps = max(long_gross_bps, short_gross_bps)`;
- `label = 1[oracle_gross_bps >= 24.0]`.

The exact grid rows must be used. There is no interpolation or as-of substitution for entry or exit.

The decision, entry, and exit book rows must be valid under the inherited target helper. The decision-row requirement is also implied by the complete valid feature window. Entry and exit bid/ask values must be finite and strictly positive. Entry and exit must remain inside 2026-08-28 UTC. Labels whose required rows cross the UTC day boundary are invalid.

Direction is used only internally to take the maximum executable opportunity magnitude. P1 must not output, analyze, rank, report, or evaluate which direction won. There is no direction scoring and no PnL calculation.

## Frozen prospective common support

A prospective decision enters EXP022-P1 scientific support only if all are true:

1. its `rv_30m_bps` feature is causally valid under the complete inherited lookback rule;
2. its decision book row is valid;
3. its exact entry quote is valid;
4. its exact exit quote is valid;
5. entry and exit remain inside 2026-08-28 UTC;
6. the feature, target inputs, model score, and all required derived values are finite.

The common-support rows must be unique and ordered by ascending decision timestamp before any metric or temporal-shift calculation.

No imputation, interpolation, future feature fill, future quote use, or forward fill through invalid state is allowed. Support may not be changed after labels or scores are observed.

## Frozen historical training set and model

The training rows are the already-consumed frozen BTCUSDT Jan-Jul Phase-L rows on the inherited valid scientific support and frozen target. Do not reparse Aug-01 and do not add any August training row.

Fit one model once on the concatenated Jan-Jul training data:

1. `StandardScaler`, fit only on the one-column Jan-Jul historical `rv_30m_bps` training matrix;
2. `LogisticRegression` with exactly:
   - `C = 1.0`;
   - `penalty = "l2"`;
   - `solver = "lbfgs"`;
   - `class_weight = None`;
   - `max_iter = 1000`;
   - `random_state = 20260825`.

No hyperparameter search, Aug-28 fitting, Aug-28 refitting, probability-threshold fitting, calibration fitting, feature selection, model selection, or prospective-label-dependent fitting decision is permitted.

## Pre-open implementation validation

Before the prospective grid is opened analytically, validate the implementation using only:

- synthetic fixtures; and
- already-consumed Jan-Jul historical data.

Synthetic fixtures must establish at minimum:

- exact 60-second decision alignment from UTC midnight;
- exact one-step 250 ms entry delay;
- exact entry-plus-600-second exit;
- exact 31-sample / 30-return `rv_30m_bps` calculation;
- invalidation by any invalid book state in the complete 30-minute feature interval;
- no future feature or quote use;
- no interpolation or forward fill;
- day-boundary label invalidation;
- common-support construction;
- deterministic score/timestamp ordering;
- deterministic temporal circular shifts and null calculations.

Where technically possible, the prospective grid-to-`rv_30m_bps` adapter must reproduce the frozen historical `_r_features` / `_rv` output on already-consumed Jan-Jul decision timestamps. The target adapter must reproduce `executable_fixed_horizon` on already-consumed Jan-Jul decision timestamps.

Any material feature, target, timing, support, or model mismatch must abort before prospective scoring. It is an implementation/provenance failure and must not be repaired after seeing Aug-28 results under this experiment ID.

## Frozen minimum-support gate

Before scientific PASS/FAIL adjudication, prospective common support must satisfy all of:

- total eligible decisions >= 1,200;
- positive labels >= 10;
- negative labels >= 100.

If any condition fails, the result is:

`INCONCLUSIVE_INSUFFICIENT_SUPPORT`

This is not a scientific FAIL. It must not be rescued by changing the target threshold, horizon, feature, model, day, support definition, or any support threshold.

## Frozen primary ranking metrics

On the full prospective common support report:

- `n`;
- positives;
- negatives;
- prevalence;
- ROC AUC;
- average precision;
- AP / prevalence;
- top-decile precision;
- top-decile lift.

Use the existing metric semantics based on `roc_auc_score` and `average_precision_score`.

For the top decile:

- `k = ceil(0.10 * n)`;
- order first by descending model score;
- resolve equal-score ties by ascending decision timestamp;
- select exactly the first `k` rows;
- top-decile precision is the mean label in those rows;
- top-decile lift is top-decile precision divided by full-support prevalence.

## Secondary non-gating calibration diagnostics

Also report:

- Brier score;
- Brier skill versus the prospective constant-prevalence forecast;
- log loss;
- mean predicted probability.

The prospective constant-prevalence forecast is the observed prospective common-support prevalence. Thus:

- `Brier = mean((y-p)^2)`;
- `Brier_baseline = mean((y-prevalence)^2)`;
- `Brier_skill = 1 - Brier / Brier_baseline`.

Use the existing frozen score-helper convention of clipping probabilities to `[1e-12, 1-1e-12]` for log loss only.

These are descriptive calibration diagnostics. They are not PASS/FAIL gates and cannot veto or rescue the ranking result. No calibrator may be fit.

## Frozen prospective temporal falsification null

The primary falsification control is a deterministic temporal circular shift on the chronologically ordered prospective common-support rows.

Keep the fitted model scores and decision timestamps fixed. Let the original binary label vector be `y` of length `n`.

Eligible shifts are every integer `k` in:

`30, 60, 90, ...`

strictly below `n` for which:

`min(k, n-k) >= 30`

Do not use `k = 0`. Do not randomly select or subsample shifts.

For exact deterministic orientation, the shifted vector for shift `k` is:

`y_shifted = numpy.roll(y, k)`

That is, original label position `i` moves to position `(i+k) mod n`. Scores remain at their original timestamps.

Because common-support decisions are on the frozen 60-second grid, the minimum circular displacement is approximately 30 minutes, exceeding the frozen 10-minute target horizon.

For every eligible shift compute:

- ROC AUC between `y_shifted` and the fixed observed scores;
- average precision between `y_shifted` and the fixed observed scores.

Require at least 20 eligible shifts. If fewer than 20 exist despite the support rule, classify:

`INCONCLUSIVE_INSUFFICIENT_SUPPORT`

For each metric, define the null 95th percentile exactly as:

`numpy.quantile(null_values, 0.95, method="higher")`

For observed value `v`, define the one-sided empirical p-value exactly as:

`(1 + count(null_values >= v)) / (1 + len(null_values))`

The temporal-shift null is the primary falsification control.

Do not use the old within-day training-label permutation as a P1 gate. Do not use the old future-canary `+0.10` delta gate.

## Frozen primary PASS gates

If minimum support is adequate, EXP022-P1 is a predictive PASS only if all are true:

1. prospective ROC AUC >= 0.60;
2. prospective AP / prevalence >= 1.50;
3. prospective top-decile lift >= 1.50;
4. observed ROC AUC is strictly greater than the temporal-shift AUC 95th percentile;
5. one-sided empirical temporal-shift AUC p-value <= 0.05;
6. observed average precision is strictly greater than the temporal-shift AP 95th percentile;
7. one-sided empirical temporal-shift AP p-value <= 0.05;
8. every provenance, causality, input-hash, support, implementation, and no-leakage invariant passes.

Calibration diagnostics and the nonoverlap diagnostic are not gates. No gate may be relaxed after the prospective result is seen.

## Frozen nonoverlap diagnostic

Also report a deterministic `nonoverlap_10m` diagnostic.

It consists of prospective common-support decision timestamps aligned every 10 minutes from UTC midnight, equivalent to UTC minute offsets satisfying `minute_from_midnight % 10 == 0`.

Where both label classes are present, report:

- n;
- positives;
- negatives;
- prevalence;
- ROC AUC;
- average precision;
- AP / prevalence;
- top-decile precision;
- top-decile lift.

Use the same deterministic score/timestamp tie rule for its top decile.

If both classes are not present, report the subset counts and class insufficiency without manufacturing a metric.

This subset is diagnostic only and is not a PASS/FAIL gate because one prospective day may contain too few independent positive events.

## Frozen status mapping

If prospective common support or temporal-null support is insufficient:

`INCONCLUSIVE_INSUFFICIENT_SUPPORT`

If support is sufficient and every primary ranking/falsification gate passes:

`PASS_PROSPECTIVE_VOLATILITY_RANKING_CONFIRMED`

If support is sufficient but one or more scientific ranking or falsification gates fail:

`FAIL_PROSPECTIVE_VOLATILITY_RANKING_NOT_CONFIRMED`

If any provenance, hash, causality, implementation, forbidden-data-access, one-shot, or protocol invariant is violated:

`INVALID`

`FAIL_PROSPECTIVE_VOLATILITY_RANKING_NOT_CONFIRMED` and `INCONCLUSIVE_INSUFFICIENT_SUPPORT` are frozen outcomes. Neither may be rerun or rescued under `CODEX-EXP-022-P1`.

## Strict prohibitions and execution guards

Throughout EXP022-P1, all of the following must remain false:

- `direction_scored`;
- `pnl_scored`;
- `leverage_scored`;
- `older_august_holdout_opened`;
- `historical_aug1_feature_reparsed`;
- `network_accessed`.

The P0 raw prospective JSONL must never be analytically opened in P1. Only the exact finalized prospective grid with the frozen byte size and SHA-256 may be used.

Target construction, historical model fitting, prospective scoring, and AUC/AP calculation are authorized only in the later one-shot P1 execution after every pre-open validation and input-authorization check passes. They are not authorized during preregistration or implementation development.

No direction winner, directional label, directional score, trade, PnL, return series, leverage result, or economic performance estimate may be emitted.

## No-rescue rule

After prospective analytical scoring begins, do not change:

- the 24 bp threshold;
- the 600 s horizon;
- the 250 ms entry delay;
- the 60 s decision grid;
- the `rv_30m_bps` definition or validity rule;
- the Jan-Jul training calendar;
- the fixed logistic model or scaler;
- support thresholds;
- temporal-shift construction or orientation;
- metric definitions or thresholds;
- PASS gates.

Do not add another model, feature, calibrator, threshold, subset, or data source to rescue a failure or inconclusive result.

A materially new hypothesis requires a new experiment ID and genuinely fresh validation data.

## Output and one-shot rule

The later P1 implementation must produce exactly one immutable result artifact.

Before creating that artifact, it must verify:

- the exact P0 audit SHA-256;
- the exact P0 PASS status and integrity state;
- the exact prospective grid byte size and SHA-256 before parsing;
- historical Jan-Jul input provenance;
- no forbidden August access;
- no prospective raw JSONL access;
- no direction, PnL, leverage, or network access;
- all causality, support, implementation, and protocol invariants.

Once any P1 result artifact is created, do not rerun P1 under the same experiment ID regardless of whether the artifact records PASS, FAIL, INCONCLUSIVE, or INVALID.

The result artifact must preserve enough provenance, counts, metrics, null-distribution summaries, empirical p-values, gate values, and execution guards to reproduce the frozen adjudication without reporting direction or PnL.

## Preregistration-time state

At creation of this preregistration:

- the prospective grid was not opened, read, copied, parsed, inspected, summarized, or scored;
- the prospective raw JSONL was not opened;
- no target was constructed;
- no model was fit;
- no AUC or AP was calculated;
- no direction was scored;
- no PnL or leverage was scored;
- no older August holdout or Aug-01 feature was opened;
- no Railway or network resource was accessed.
