# CODEX-EXP-024-P1 Result

Official status:

`PASS_PROSPECTIVE_VOLATILITY_RANKING_CONFIRMED`

## Frozen execution provenance

Frozen implementation commit:

`cdffc6d7556a2258e59f3a63e0e11419b47e5e5c`

Preregistration SHA-256:

`dc835423dc516a14a1e5b79a43b364bf8d8180f8288670aeac9e679db778caf3`

Scientific configuration SHA-256:

`3a9edfa6d2c9d15591373237574eb9552f09755eff2f0265e434621508e83b88`

Executed at UTC:

`2026-08-31T00:45:02.535058+00:00`

Result artifact SHA-256:

`0fda20d127e51e8ad792c6b949889f88b59e75ab98b437fd04ead285970e5c10`

Deterministic score-records SHA-256:

`c29027e0395716eb26ba37be87e2c5cfd5723aa2542592e2c7a123e81321a78d`

## EXP024-P0 authorization

P0 status:

`PROSPECTIVE_BOOKTICKER_DATA_READY`

P0 audit SHA-256:

`70e8861b844c88e394741edde9ba17b9a25544b45728ae8e64d868a3faff4acd`

P0 frozen implementation:

`2eb478bb5969c6f2bb8a7eb0b72eda8baa45ec23`

Prospective grid:

- bytes: `33451762`
- SHA-256: `a74bd9e040561f3bf6f4eb9c42b81f7c76681e6b4b918b636cf97e95a0bd273b`

The P0 authorization and exact opaque grid size/SHA-256 verification passed
before prospective analytical opening.

## Prospective support

- n: `1399`
- positives: `93`
- negatives: `1306`
- prevalence: `0.06647605432451752`
- minimum support gate: `PASS`

## Primary prospective ranking metrics

- ROC AUC: `0.799436842365262`
- Average precision: `0.29797522298065926`
- AP / prevalence: `4.482444483332713`
- Top-decile precision: `0.19285714285714287`
- Top-decile lift: `2.9011520737327188`

## Frozen temporal falsification

Number of eligible circular shifts:

`45`

AUC temporal-null q95:

`0.6849363566006357`

Observed AUC empirical p-value:

`0.043478260869565216`

AP temporal-null q95:

`0.11539756109511043`

Observed AP empirical p-value:

`0.021739130434782608`

The observed AUC and AP both exceeded their frozen temporal-null q95 values
and both empirical p-values satisfied the preregistered <= 0.05 gates.

## Primary gates

All preregistered primary gates passed:

- prospective AUC >= 0.60
- AP / prevalence >= 1.50
- top-decile lift >= 1.50
- observed AUC > temporal-null AUC q95
- AUC empirical p <= 0.05
- observed AP > temporal-null AP q95
- AP empirical p <= 0.05
- all provenance, causality, and protocol invariants passed

## Secondary calibration diagnostics

- Brier score: `0.0557284567449185`
- Brier skill score: `0.10197935690023519`
- log loss: `0.21906029084236775`
- mean predicted probability: `0.09718807595248448`

These diagnostics were secondary and non-gating.

## Secondary non-overlapping 10-minute diagnostic

- n: `139`
- positives: `4`
- negatives: `135`
- prevalence: `0.02877697841726619`
- ROC AUC: `0.5981481481481481`
- Average precision: `0.04627976190476191`
- AP / prevalence: `1.608221726190476`
- top-decile precision: `0.0`
- top-decile lift: `0.0`

This diagnostic was explicitly preregistered as secondary and non-gating.
Its small positive count and weaker performance do not alter the official
prospective PASS, but they should constrain interpretation and motivate
independent execution/PnL validation rather than overclaiming event-level
independence.

## Execution and causality invariants

All final invariants passed, including:

- common support unique and chronological
- decision step exactly 60 seconds
- entry delay exactly 250 ms
- historical training exactly January-July
- historical adapter semantics exact
- no August fit or refit
- one legitimate feature only: `rv_30m_bps`
- P0 audit authorized
- prospective grid SHA-256 and byte size exact
- prospective day exactly 2026-08-30
- target horizon exactly 600 seconds
- target threshold exactly 24 bp
- all execution guards false

The prospective grid was analytically opened only during the authorized
one-shot execution.

The prospective raw file was not opened by P1.

No network access occurred during P1.

No direction, PnL, or leverage was scored.

## Scientific adjudication

The frozen single causal trailing realized-volatility feature
`rv_30m_bps` prospectively confirmed its ability to rank occurrence of the
frozen 10-minute, at-least-24 bp executable BTCUSDT opportunity on the fresh
2026-08-30 UTC prospective day.

The result is a ranking/timing confirmation only. It is not yet evidence of a
profitable directional trading strategy after fees, spread, slippage,
execution uncertainty, or risk constraints.

2026-08-30 is now a consumed prospective validation day and must not be reused
as a fresh holdout for this hypothesis.

No rerun, rescue, threshold change, subset rescue, or alternative
adjudication is permitted under CODEX-EXP-024-P1.
