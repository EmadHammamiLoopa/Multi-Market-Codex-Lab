# CODEX-EXP-024-P1 Preregistration

Status: **PREREGISTERED BEFORE ANY EXP024-P1 PROSPECTIVE ANALYTICAL OPENING**

Date frozen: 2026-08-30

Experiment ID: `CODEX-EXP-024-P1`

Parent EXP024-P0 acquisition implementation commit:

`2eb478bb5969c6f2bb8a7eb0b72eda8baa45ec23`

This document freezes the corrected fresh prospective ranking-confirmation
protocol before the 2026-08-30 raw acquisition or future grid is opened for
analytical parsing, target construction, model scoring, or metric calculation.

## Frozen lineage

- EXP022-P1 preregistration commit:
  `73feafca0b1f901b10d2856b07c3058462f1cfff`;
- EXP022-P1 invalid frozen implementation:
  `0a86f2440d44a7969cd640ecca830b07a4350e00`;
- EXP022-P1 preserved INVALID result:
  `91ae1465a20354082e9005eff1742ac3b2b73651`;
- EXP023-P0 preregistration:
  `ee34a50950f7ad78b608611743f4ac0a2f480f63`;
- EXP023-P0 corrected implementation:
  `306446a4a215680076ad96b32781499ba4abe6b1`;
- EXP023-P0 preserved readiness:
  `3a343cef8520a5eb7f966e9ee31826a1ff85b930`;
- EXP023 readiness artifact SHA-256:
  `4eaf158b2517cf6c0be2efc2e7026a73a6b9986977d2c78499bb5785f142c1af`;
- EXP024-P0 preregistration commit:
  `2f1e200990d2d04258f941ef6a487d1642aeb0ce`;
- EXP024-P0 acquisition implementation commit:
  `2eb478bb5969c6f2bb8a7eb0b72eda8baa45ec23`;
- EXP024-P0 preregistration SHA-256:
  `1630ab4591b20a26640a45c980b28b788516434110795d5d406f0189d92a6bd2`.

EXP022-P1 remains permanently `INVALID`. The consumed 2026-08-28 raw and
grid files are forbidden inputs. EXP023-P0 makes no predictive claim; it only
validated the implementation-safety correction used here.

## Prospective state at freeze

The EXP024-P0 collector for 2026-08-30 UTC is armed and/or collecting. Neither
its raw data nor any future finalized grid has been opened, listed, sized,
hashed, copied, parsed, inspected, summarized, or scored during EXP024-P1
preregistration and implementation development.

The future EXP024-P0 audit SHA-256 and prospective grid SHA-256 are
deliberately unknown today. They must not be guessed, predeclared, or inferred.

Development and preflight use only synthetic fixtures, frozen code/document
provenance, and the already-consumed Jan-Jul historical Phase-L data.

## Scientific question

Does the frozen single causal trailing realized-volatility state variable
`rv_30m_bps` prospectively rank occurrence of the frozen 10-minute,
at-least-24 bp executable BTCUSDT opportunity on the genuinely fresh
2026-08-30 UTC day?

This is a ranking/timing confirmation only. It is not a direction, PnL,
leverage, calibration-method, feature, threshold, or model-selection
experiment.

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

Only already-consumed frozen Phase-L historical data for those days may be
used for training and preflight semantic equivalence.

Prospective validation day:

`2026-08-30 UTC`

Forbidden inputs are:

- the EXP024 prospective raw gzip JSONL;
- the consumed 2026-08-28 raw or grid;
- 2026-08-01;
- 2026-08-04 through 2026-08-23;
- every other August day;
- ETH or any other symbol;
- any network data during P1;
- funding, OI, liquidations, options, macro, news, or on-chain data.

## Frozen scientific configuration

The canonical EXP024-P1 configuration SHA-256 is:

`3a9edfa6d2c9d15591373237574eb9552f09755eff2f0265e434621508e83b88`

Relative to frozen EXP022-P1, only experiment identity, prospective day, P0
authorization provenance, and the EXP023 implementation-safety path change.
Every predictive choice remains identical.

## Frozen feature

The only legitimate predictive feature is:

`rv_30m_bps`

At decision timestamp `t`, use 31 causal mid observations at exact one-minute
spacing from `t-30m` through `t`, producing 30 log returns. The value is:

`10000 * sqrt(sum(r^2))`

Every 250 ms book state in the inclusive interval `[t-30m, t]` must be valid.
All mids must be finite and positive. There is no interpolation, future fill,
forward fill across invalid state, or prior-day fill. The implementation must
reuse the frozen EXP022/Phase-L feature helpers.

## Frozen target

Decisions occur every 60 seconds from UTC midnight on the exact 250 ms grid.

For decision `t`:

- entry is `t + 250 ms`, exactly one row;
- exit is entry plus 600 seconds, exactly 2,400 rows;
- `long_bps = 10000 * log(bid_exit / ask_entry)`;
- `short_bps = 10000 * log(bid_entry / ask_exit)`;
- `oracle = max(long_bps, short_bps)`;
- `label = 1[oracle >= 24.0]`.

Decision, entry, and exit book states must be valid. Entry and exit must remain
inside 2026-08-30 UTC. Required values must be finite. Direction exists only
inside frozen oracle construction and must never be output, analyzed, scored,
compared, or reported.

## Frozen historical model

Fit exactly once on concatenated Jan-Jul historical common support:

1. `StandardScaler` fit on the sole `rv_30m_bps` column;
2. `LogisticRegression` with:
   - `C = 1.0`;
   - `penalty = "l2"`;
   - `solver = "lbfgs"`;
   - `class_weight = None`;
   - `max_iter = 1000`;
   - `random_state = 20260825`.

No August fitting or refitting, threshold fitting, calibration fitting,
feature selection, model selection, or prospective-label-dependent fitting
decision is allowed.

## Frozen common support

A decision enters support only if all are true:

- the complete causal `rv_30m_bps` feature is valid;
- the decision book row is valid;
- exact entry and exit rows are valid and inside the UTC day;
- feature, target, score, and all required derived values are finite;
- rows are unique and ordered by ascending decision timestamp.

No imputation, interpolation, future quote use, or support change after labels
or scores are observed is permitted.

## Frozen support gate

Minimum prospective common support requires all of:

- n >= 1,200;
- positive labels >= 10;
- negative labels >= 100.

Otherwise the result is:

`INCONCLUSIVE_INSUFFICIENT_SUPPORT`

This cannot be rescued by changing any protocol choice.

## Frozen ranking and secondary metrics

Primary reporting is:

- n, positives, negatives, prevalence;
- ROC AUC;
- average precision;
- AP / prevalence;
- top-decile precision;
- top-decile lift.

The top decile contains exactly `ceil(0.10 * n)` rows, ordered by descending
model score and then ascending decision timestamp for score ties.

Secondary non-gating diagnostics are Brier score, Brier skill against the
observed prospective constant-prevalence forecast, clipped log loss, and mean
predicted probability. Log-loss clipping is `[1e-12, 1-1e-12]`. No calibrator
may be fit.

## Frozen temporal falsification

Keep chronological prospective scores fixed and circularly shift labels with:

`numpy.roll(y, k)`

Eligible shifts are every `k = 30, 60, 90, ...` below n for which
`min(k, n-k) >= 30`. No random selection and no zero shift are allowed.

Require at least 20 eligible shifts. For each shift calculate ROC AUC and
average precision. Define each null 95th percentile with:

`numpy.quantile(values, 0.95, method="higher")`

and one-sided empirical p-value with:

`(1 + count(null >= observed)) / (1 + number_of_null_shifts)`.

## Frozen primary PASS gates

With sufficient support, predictive PASS requires every gate:

1. ROC AUC >= 0.60;
2. AP / prevalence >= 1.50;
3. top-decile lift >= 1.50;
4. observed AUC strictly exceeds temporal-null AUC q95;
5. AUC empirical p <= 0.05;
6. observed AP strictly exceeds temporal-null AP q95;
7. AP empirical p <= 0.05;
8. every provenance, causality, authorization, implementation, support, and
   no-leakage invariant passes.

The frozen nonoverlap 10-minute diagnostic remains secondary and non-gating.

## Frozen status mapping

Insufficient common or temporal-null support:

`INCONCLUSIVE_INSUFFICIENT_SUPPORT`

Sufficient support and every primary gate passes:

`PASS_PROSPECTIVE_VOLATILITY_RANKING_CONFIRMED`

Sufficient support but at least one scientific gate fails:

`FAIL_PROSPECTIVE_VOLATILITY_RANKING_NOT_CONFIRMED`

Any provenance, P0 authorization, grid hash, causality, implementation,
forbidden-access, or protocol violation:

`INVALID`

No result may be rerun or rescued under this experiment ID.

## Corrected implementation safety

EXP024-P1 must use the correction validated by EXP023-P0:

- every final invariant is an exact built-in Python `bool`;
- any residual non-built-in invariant is an implementation error;
- invariant adjudication is type-safe and does not use arbitrary scalar
  identity tests;
- supported NumPy bool, integer, and float payload scalars are recursively
  normalized before writing;
- NaN and infinity are forbidden;
- the normalized payload must pass `json.dumps(..., allow_nan=False)`;
- existing final output or `.part` causes refusal before prospective access;
- first output uses exclusive `.part` creation and atomic replacement;
- PASS-, FAIL-, INCONCLUSIVE-, and INVALID-shaped synthetic payloads must all
  exercise the corrected serialization path.

## Future EXP024-P0 authorization

The prospective grid must not be opened, including for opaque hashing, until
the supplied future EXP024-P0 audit has been read and verified as integrity
metadata.

The audit SHA-256 is computed and recorded at execution but is not predeclared.
The verified audit must require at minimum:

- `experiment_id = CODEX-EXP-024-P0`;
- `status = PROSPECTIVE_BOOKTICKER_DATA_READY`;
- `scope = DATA_ACQUISITION_AND_INTEGRITY_ONLY`;
- `collection_day = 2026-08-30`;
- `symbol = BTCUSDT`;
- `frozen_implementation_commit =
  2eb478bb5969c6f2bb8a7eb0b72eda8baa45ec23`;
- `preregistration_sha256 =
  1630ab4591b20a26640a45c980b28b788516434110795d5d406f0189d92a6bd2`;
- `readiness_artifact_sha256 =
  4eaf158b2517cf6c0be2efc2e7026a73a6b9986977d2c78499bb5785f142c1af`;
- `predictive_metrics_calculated = false`;
- every P0 integrity gate has its exact expected built-in-bool value;
- every no-analysis guard is false;
- grid path has the exact EXP024/BTCUSDT/2026-08-30 artifact suffix;
- grid SHA-256 is a valid recorded digest and grid bytes are positive.

Only after the audit passes may the supplied grid be opened as opaque bytes to
verify exact size and SHA-256 against that audit. Only after opaque
authorization passes may the grid be analytically parsed.

The prospective raw path recorded in the audit is metadata only. P1 must not
open or hash the raw file and exposes no raw-input argument.

## Execution state and one-shot order

Before authorization:

- `prospective_grid_opaque_verified = false`;
- `prospective_grid_analytically_opened = false`;
- `model_fit = false`;
- `prospective_metrics_scored = false`.

Historical Jan-Jul preparation may occur before prospective parsing. The model
may be fit only in one-shot execute mode after provenance and P0/grid opaque
authorization pass. Analytical grid opening occurs only after the opaque grid
check.

Before any prospective audit/grid operation, execute mode must require that
the final output and `.part` do not exist. Any later execution failure creates
one atomic `INVALID` artifact. Once any artifact exists, rerun is forbidden.

## Modes and preflight

The implementation exposes:

- `--mode preflight`;
- `--mode execute`.

Preflight must reject prospective P0 audit, grid, output, and execute-only
arguments. It may use synthetic fixtures, code/document lineage, and consumed
Jan-Jul historical data only. It must not fit the model, open prospective
data, or calculate prospective metrics.

Before future execute authorization, preflight must establish exact scientific
configuration and model parameters, Jan-Jul-only provenance, one-feature
historical semantic equivalence, corrected bool/JSON safety, temporal-null
equivalence, one-shot protection, and synthetic P0 authorization behavior.

## Strict execution guards and forbidden outputs

All of these remain false throughout EXP024-P1:

- `direction_scored`;
- `pnl_scored`;
- `leverage_scored`;
- `older_august_holdout_opened`;
- `historical_aug1_feature_reparsed`;
- `prospective_raw_opened`;
- `network_accessed`.

No result artifact may contain long/short gross returns, winning direction,
directional labels or scores, PnL, leverage, or any path/content from the raw
prospective file.

## No-rescue rule

After prospective execution begins, do not change the 24 bp threshold, 600 s
horizon, 250 ms entry delay, 60 s decision grid, `rv_30m_bps` construction,
Jan-Jul training calendar, fixed model, support thresholds, temporal shifts,
metric definitions, or PASS gates. Do not add a model, feature, calibrator,
threshold, subset, or data source.

At preregistration creation time, no August market-data file was accessed, no
prospective target or score was constructed, no model was fit on August, no
prospective metric was calculated, and no Railway or network resource was
accessed.
