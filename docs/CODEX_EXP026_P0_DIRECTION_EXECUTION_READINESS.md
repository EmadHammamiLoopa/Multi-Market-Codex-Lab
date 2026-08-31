# CODEX-EXP-026-P0 Direction + Execution Readiness Design

Status: **PREREGISTERED DEVELOPMENT / READINESS PHASE — NO FRESH HOLDOUT OPENED**

Experiment ID: `CODEX-EXP-026-P0`

Parent preserved prospective confirmation commit:

`4669be4234b808286108c288f7a6eb7b3742f268`

EXP024-P1 official result artifact SHA-256:

`0fda20d127e51e8ad792c6b949889f88b59e75ab98b437fd04ead285970e5c10`

EXP024-P1 status:

`PASS_PROSPECTIVE_VOLATILITY_RANKING_CONFIRMED`

## Purpose

EXP026-P0 converts the now-confirmed non-directional opportunity-ranking signal
into a deployable, causal, execution-aware trading decision pipeline.

This phase is **not** a fresh prospective profitability confirmation. It is a
development/readiness phase. It may use only:

- the already-consumed Jan-Jul 2026 historical sandbox;
- the already-consumed 2026-08-30 BTCUSDT prospective day for bounded
  diagnostics/implementation checks;
- synthetic fixtures.

It must not open or inspect any future EXP025 full-day partition that could be
used for confirmatory validation. In particular, 2026-09-01 and later EXP025
full-day candidates remain sealed for a later experiment until a final
direction/execution rule is frozen.

## Why this phase is required

EXP024 proved ranking, not trading profitability.

The confirmed `rv_30m_bps` model answers:

> Is a >=24 bp executable 10-minute opportunity more likely around this
> timestamp?

It does **not** answer:

- long or short;
- whether a trade is profitable after fees/slippage;
- how to turn an ex-post daily top-decile ranking into a causal online trigger;
- how overlapping 60-second signals should be executed;
- how much capital or leverage should be used.

EXP026-P0 addresses those gaps without consuming the next fresh holdout.

## Frozen parent signal

The parent opportunity model remains unchanged:

- symbol: BTCUSDT;
- sole opportunity feature: `rv_30m_bps`;
- decision interval: 60 s;
- entry delay: 250 ms;
- horizon: 600 s;
- opportunity threshold: 24 bp;
- historical model training: Jan-Jul 2026 first-day files;
- StandardScaler + LogisticRegression;
- C=1.0, L2, lbfgs, max_iter=1000, random_state=20260825.

No EXP024 rerun or rescue is permitted.

## Online opportunity trigger

The prospective EXP024 top-decile metric was an ex-post ranking statistic and
cannot itself be used as a live trigger because the future day's complete
score distribution is unknown in real time.

EXP026-P0 therefore defines an ex-ante deployable trigger:

1. fit the frozen opportunity model on the authorized Jan-Jul historical
   common support only;
2. calculate model probabilities on that same authorized historical common
   support;
3. freeze the opportunity trigger at the historical 90th percentile of those
   probabilities using NumPy `quantile(..., 0.90, method="higher")`;
4. in future live/prospective use, a timestamp is eligible when its causal
   opportunity probability is >= that fixed scalar threshold.

This threshold is not tuned to future PnL and must be recorded exactly before
fresh validation.

## Direction candidates

Direction development is deliberately small and pre-specified.

Candidate A — signed-return logistic direction model:

Features available causally at decision time:

- `ret_1m_bps`
- `ret_3m_bps`
- `ret_5m_bps`
- `ret_10m_bps`
- `ret_30m_bps`
- `rv_30m_bps`
- current `spread_bps`

All values must use only state at or before decision time.

Direction training label:

`long_preferred = 1[long_executable_bps > short_executable_bps]`

where the 600-second executable long/short returns use the same frozen
entry/exit convention as EXP024.

Model:

- StandardScaler;
- LogisticRegression;
- C=1.0;
- penalty="l2";
- solver="lbfgs";
- class_weight=None;
- max_iter=1000;
- random_state=20260825.

At inference:

- probability >=0.5 -> LONG;
- probability <0.5 -> SHORT.

No confidence threshold is allowed in P0.

Candidate B — 10-minute momentum rule:

- `ret_10m_bps >= 0` -> LONG;
- otherwise -> SHORT.

Candidate C — 10-minute mean-reversion rule:

- `ret_10m_bps >= 0` -> SHORT;
- otherwise -> LONG.

No additional candidate may be added after results are observed under this ID.

## Historical model-selection protocol

Candidate selection uses only the already-consumed Jan-Jul sandbox.

Use expanding chronological folds:

- train Jan-Mar, validate Apr;
- train Jan-Apr, validate May;
- train Jan-May, validate Jun;
- train Jan-Jun, validate Jul.

For every fold:

- build the opportunity trigger from training data only;
- fit the logistic direction candidate from training data only;
- execute all three candidates on the validation day only;
- never tune a threshold on a validation day.

Primary selection statistic:

`median validation-fold net_bps_per_trade`

Tie-breaks, in order:

1. higher number of folds with positive total net bps;
2. higher pooled profit factor;
3. lower pooled maximum drawdown in bps;
4. simpler candidate in this order: B, C, A.

The selected candidate is then refit, if applicable, on the full authorized
Jan-Jul historical sandbox and frozen for future validation.

## Execution convention

At every eligible decision timestamp:

1. compute opportunity probability causally;
2. require probability >= the fixed historical trigger;
3. if flat, choose direction with the selected frozen direction rule;
4. enter at t+250 ms using the executable side of the book;
5. hold exactly 600 seconds;
6. exit using the executable side of the book;
7. while a position is open, ignore all new signals;
8. no pyramiding;
9. no leverage;
10. no stop-loss;
11. no take-profit;
12. no position-size optimization.

This single-position rule avoids counting highly overlapping 60-second
predictions as independent trades.

## Cost model

Quoted bid/ask execution already includes spread crossing.

Primary incremental execution-cost assumption:

- 10 bp round-trip trading fees;
- 2 bp additional slippage per side;
- total incremental cost = 14 bp per completed round trip.

Primary net trade result:

`net_bps = executable_gross_bps - 14.0`

Stress diagnostic:

`stress_net_bps = executable_gross_bps - 20.0`

The 20 bp stress case is secondary and non-gating in P0.

No funding, maker rebate, leverage, liquidation, borrow cost, or tax model is
included in this first readiness phase.

## P0 metrics

For each historical validation fold and candidate record:

- trigger threshold;
- number of eligible signals;
- number of executed non-overlapping trades;
- long/short trade counts;
- gross total bps;
- net total bps at 14 bp cost;
- mean net bps/trade;
- median net bps/trade;
- win rate;
- profit factor;
- maximum drawdown in cumulative net bps;
- exposure fraction;
- ignored signals while a position is open;
- stress total bps at 20 bp incremental cost.

Also report the selected candidate and the frozen full-Jan-Jul opportunity
trigger.

## Consumed 2026-08-30 diagnostic

After historical candidate selection is frozen inside P0, the already-consumed
2026-08-30 grid may be used once as a **diagnostic only** to verify:

- the online fixed trigger behaves sensibly under the observed distribution;
- direction inference executes causally;
- non-overlap execution mechanics are correct;
- cost accounting is correct.

The 2026-08-30 diagnostic:

- cannot establish prospective profitability;
- cannot change candidate selection;
- cannot change the opportunity threshold;
- cannot change costs;
- cannot add filters;
- cannot rescue a weak result.

It is an implementation/economic diagnostic because the day has already been
analytically consumed by EXP024-P1.

## P0 readiness status

PASS readiness:

`DIRECTION_EXECUTION_PIPELINE_READY_FOR_FRESH_PROSPECTIVE_VALIDATION`

requires:

- all historical folds complete causally;
- exactly one candidate selected by the frozen rule;
- final Jan-Jul parameters/trigger recorded;
- finite metrics;
- non-overlap execution verified;
- 2026-08-30 diagnostic, if executed, cannot alter the selected rule;
- no future EXP025 full-day holdout opened;
- no leverage/PnL optimization beyond this preregistration.

FAIL readiness:

`FAIL_DIRECTION_EXECUTION_PIPELINE_NOT_READY`

for a clean implementation whose historical selection cannot produce a valid
frozen candidate or required support.

INVALID:

for provenance, causality, future-data, serialization, one-shot, or protocol
violations.

P0 PASS is an engineering/research-readiness result only. It is not proof of
future profitability.

## Next fresh confirmation

Only after P0 freezes the selected rule may a new experiment ID consume future
EXP025 full-day data.

The preferred next experiment is:

`CODEX-EXP-026-P1`

or a successor ID if P0 materially changes.

Its holdout must be one or more EXP025 full-day partitions that were not
opened during P0. The exact holdout set and profitability PASS gates must be
preregistered before analytical opening.

## Non-negotiable guards

Throughout P0:

- 2026-08-30 is consumed diagnostic data, never fresh holdout;
- 2026-09-01 and later future EXP025 full-day candidates remain unopened;
- no network acquisition is performed by the research script;
- no backfill;
- no post-hoc session/subset rescue;
- no leverage optimization;
- no threshold sweep beyond the three frozen direction candidates and the
  single historical 90th-percentile opportunity trigger;
- all outputs are one-shot and immutable;
- failure/inconclusive outcomes are preserved.
