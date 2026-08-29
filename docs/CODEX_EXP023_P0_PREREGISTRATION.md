# CODEX-EXP-023-P0 Preregistration

Status: **PREREGISTERED BEFORE ANY EXP023-P0 READINESS EXECUTION**

Date frozen: 2026-08-29

Experiment ID: `CODEX-EXP-023-P0`

Parent preserved commit:

`91ae1465a20354082e9005eff1742ac3b2b73651`

Invalid parent experiment:

`CODEX-EXP-022-P1 = INVALID`

Invalid frozen implementation commit:

`0a86f2440d44a7969cd640ecca830b07a4350e00`

This is an implementation-only correction and readiness audit. It cannot
change the frozen `INVALID` status of CODEX-EXP-022-P1 and cannot make a
predictive claim.

## Frozen parent evidence

The correction is grounded in these frozen parent files:

- `docs/CODEX_EXP022_P1_PREREGISTRATION.md`, SHA-256
  `e4c9ca4075834de29d01613c695b534081a01b506e7f233ca6fa9542419e3f5b`;
- `docs/CODEX_EXP022_P1_RESULT.md`, SHA-256
  `a007d0f1249e7ad480f1bfeabfbf58c5d9d3896ed3630f1e5081c3ffaa69dd80`;
- `src/multimarket/codex_exp022_p1.py`, SHA-256
  `79300d16e7cb9790c43b082c0788cb88a622cce622a3b15c6027bb072c1fb831`;
- `tests/test_codex_exp022_p1.py`, SHA-256
  `ccc76bb8e827c679b06ee7078725cb1d9a861ec05cf1180d18b7664af313385d`;
- `evidence/codex/exp022_p1_invalid_execution/ATTEMPT2_EXECUTE.log`,
  SHA-256
  `ead250b412305756b1a25139e8c1a3c59240c91c388360b2f6fb9b29dcd1ea84`.

The frozen result establishes that the parent analytical path completed in
memory but failed before its result artifact could be serialized. The
2026-08-28 prospective day is consequently consumed. It is not eligible for
reuse as a prospective holdout and must not be opened by EXP023-P0.

## Purpose and non-claim scope

EXP023-P0 has one purpose: eliminate and regression-test the implementation
defect that prevented safe invariant adjudication and final-payload JSON
serialization in the frozen EXP022-P1 implementation.

EXP023-P0 is not:

- a rerun or rescue of EXP022-P1;
- a predictive validation;
- a direction experiment;
- a PnL or leverage experiment;
- a feature, model, threshold, calibration, support, or null search;
- authorization to inspect any August market data.

No ROC AUC, average precision, lift, calibration diagnostic, target result,
model score, direction, return, PnL, or leverage result may be calculated on
2026-08-28 in EXP023-P0.

## Observed frozen implementation defect

The parent implementation constructed
`invariants.common_support_unique_and_chronological` using an expression that
could return `numpy.bool_` from `numpy.all(...)`.

It then aggregated invariants with identity tests such as `value is True` and
`value is False`. A true NumPy boolean therefore had two consequences:

1. it was not serializable by the frozen JSON payload path;
2. it did not satisfy `value is True`, so it could corrupt invariant
   adjudication.

This defect, and only this implementation defect, is in correction scope.

## Required correction

The corrected implementation must establish all of the following:

1. Every invariant expression is converted to an exact built-in Python
   `bool` before adjudication or serialization. Expressions involving
   `numpy.all(...)` must be explicitly normalized with `bool(...)`.
2. Invariant aggregation accepts only values for which `type(value) is bool`.
   Any residual NumPy boolean or other scalar type is an implementation error,
   not a false scientific gate.
3. Invariant expectations are compared type-safely; arbitrary scalar identity
   checks are forbidden.
4. A recursive JSON-safety layer deterministically converts NumPy scalar
   `bool`, integer, and floating values to built-in JSON types.
5. The JSON-safety layer rejects every non-finite built-in or NumPy floating
   value. NaN and infinity must never be emitted or converted to a misleading
   finite/null value.
6. The final normalized payload must serialize under
   `json.dumps(..., allow_nan=False)`.
7. Full synthetic PASS-, FAIL-, INCONCLUSIVE-, and INVALID-shaped result
   payloads must exercise the serialization path.
8. One-shot output safety remains exact: an existing final artifact or
   existing `.part` marker is never overwritten or reused, and a first write
   is created as `.part` then atomically moved to the final path.

The regression suite must reproduce the old `numpy.bool_(True)` failure and
then demonstrate that the corrected common-support invariant is a built-in
`True`, adjudicates correctly, and serializes safely. A separate strict test
must prove that an unnormalized non-built-in invariant is rejected.

## Frozen scientific configuration

No scientific parameter changes in EXP023-P0. The corrected implementation
must retain an exact canonical copy of the frozen EXP022-P1 configuration,
whose canonical SHA-256 is:

`5592bd41fa4cfc48dd418f0f1920762d8d760ab6bb39ce2000e0114d9603f348`

The inherited configuration remains:

- symbol: `BTCUSDT` only;
- historical training days: 2026-01-01, 2026-02-01, 2026-03-01,
  2026-04-01, 2026-05-01, 2026-06-01, and 2026-07-01 only;
- feature: `rv_30m_bps` only;
- grid interval: 250 ms;
- decision interval: 60 seconds;
- entry delay: 250 ms;
- horizon: 600 seconds;
- label: executable oracle opportunity at least 24.0 bp;
- scaler: `StandardScaler` fit on frozen Jan-Jul historical training only;
- model: `LogisticRegression(C=1.0, penalty="l2", solver="lbfgs",
  class_weight=None, max_iter=1000, random_state=20260825)`;
- minimum support: n at least 1,200, positives at least 10, negatives at
  least 100;
- ranking gates: exactly those frozen in EXP022-P1;
- temporal circular shifts: multiples of 30 rows, `numpy.roll(y, k)`, frozen
  eligibility rule, `quantile(..., 0.95, method="higher")`, and frozen
  one-sided empirical p-value;
- no calibration fitting, model search, feature search, threshold search,
  direction scoring, PnL, or leverage.

Scientific helpers for feature construction, target construction, support,
model, and temporal-null semantics must be inherited from the frozen EXP022-P1
implementation rather than scientifically redefined.

## Authorized validation inputs

EXP023-P0 may use only:

- synthetic in-memory or temporary fixtures;
- code and documentation provenance;
- already-consumed BTCUSDT Jan-Jul frozen Phase-L historical files during a
  later explicit semantic-equivalence preflight.

The development and unit-test task that creates this implementation uses only
synthetic fixtures and does not run the Jan-Jul preflight.

Forbidden inputs and access include:

- the consumed 2026-08-28 prospective grid, including opaque hashing;
- the prospective raw gzip JSONL;
- 2026-08-01;
- 2026-08-04 through 2026-08-23;
- every other August market-data file;
- ETH or any other symbol;
- Railway or any network resource;
- options, funding, open interest, liquidations, macro, news, or on-chain
  data.

## Preflight-only architecture

EXP023-P0 must expose only a correction/readiness preflight. It must not expose
an execute mode, grid argument, raw-input argument, or any code path that
analytically opens or scores 2026-08-28.

The later preflight may verify the frozen code/document provenance and run
exact feature/target/support semantic equivalence on the already-consumed
Jan-Jul historical Phase-L data. It must not fit the prospective model or
produce predictive metrics.

Synthetic tests may exercise the frozen feature, target, and temporal-null
helpers using synthetic values solely to prove semantic identity.

## Frozen execution guards

Every readiness payload must explicitly record all of these as false:

- `direction_scored`;
- `pnl_scored`;
- `leverage_scored`;
- `older_august_holdout_opened`;
- `historical_aug1_feature_reparsed`;
- `network_accessed`;
- `prospective_raw_opened`.

It must additionally record that the prospective grid was not opened, the
model was not fit, and predictive metrics were not produced.

## Readiness adjudication

EXP023-P0 may receive:

`IMPLEMENTATION_CORRECTION_READY_FOR_FRESH_PROSPECTIVE_VALIDATION`

only if all of the following are true:

- the frozen NumPy-boolean defect is reproduced by regression evidence;
- the corrected common-support invariant is exactly a built-in bool;
- every final invariant is exactly a built-in bool;
- strict invariant type validation and type-safe adjudication pass;
- recursive JSON-safety and non-finite rejection tests pass;
- complete synthetic PASS, FAIL, INCONCLUSIVE, and INVALID payloads serialize;
- the scientific configuration exactly equals frozen EXP022-P1;
- synthetic feature and target semantics exactly match frozen helpers;
- synthetic temporal-null semantics remain exact;
- the later Jan-Jul preflight reports exact semantic equivalence on every
  frozen day;
- one-shot output protection passes;
- no August data is accessed;
- no predictive metrics are produced;
- every focused EXP023-P0 test passes.

If the correction is not ready, the status is:

`FAIL_IMPLEMENTATION_CORRECTION_NOT_READY`

If provenance, forbidden-access, implementation, or protocol invariants are
violated, the status is:

`INVALID`

None of these statuses is a predictive result. A genuinely fresh future
prospective experiment requires a new experiment ID and a new unconsumed
validation day after this implementation correction is frozen ready.

## One-shot readiness artifact

A later readiness preflight may create at most one immutable EXP023-P0 result
artifact. Before any preflight work, an existing final output or `.part` path
must cause refusal without modification. The first write must use exclusive
`.part` creation and an atomic move.

The readiness artifact must include frozen parent provenance, the exact frozen
scientific configuration and its hash, historical Jan-Jul provenance and
semantic-equivalence summaries, correction checks, exact built-in invariants,
the frozen guards, and an explicit statement that it contains no predictive
claim or metric.

## No-rescue rule

EXP023-P0 cannot rescue or reinterpret EXP022-P1. No consumed Aug-28 quantity
may inform this correction. No feature, target, model, threshold, support
condition, temporal-null definition, ranking gate, or scientific status may be
changed under this experiment ID.

At preregistration creation time, no August market-data file was opened, no
prospective or historical model was fit, no target or predictive metric was
calculated, no direction/PnL/leverage was scored, and no network resource was
accessed.
