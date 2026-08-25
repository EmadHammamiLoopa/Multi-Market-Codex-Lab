# CODEX-EXP-005-P0 Result

Status: **DATA_READY_SANDBOX**

Experiment: `CODEX-EXP-005-P0`

Frozen pre-acquisition implementation commit: `83ee71958fb6a2cf423df5e039fd42a0051496c8`

Acquisition-manifest preservation commit: `0099bf7fc6851927228bb472868ad1fe35f3fd47`

Frozen audit-result preservation commit: `64c35ca3c14745cb8d86fe0429829d9ed6f2b2df`

Audit artifact SHA-256: `b151aba2455ee237acf34da76d257b6f8d1a221166cffdbe967851315482ef52`

Audit configuration SHA-256: `26493155132bec2d2252335bb3380f0ccd84aec933acb7f8a114040d1538ba9a`

## Scope

The phase audited Tardis `binance-futures / derivative_ticker` state for only the frozen consumed sandbox dates:

- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

Symbols:

- BTCUSDT
- ETHUSDT

Exactly 14 raw files were acquired. No August data was opened. Raw files remain ignored by Git and are immutable inputs for later EXP005 phases.

## Frozen acquisition provenance

The acquisition completed successfully with 14/14 files and a committed acquisition manifest. Every downloaded file exposed the same relevant schema family:

- `timestamp`
- `local_timestamp`
- `funding_timestamp`
- `funding_rate`
- `predicted_funding_rate`
- `open_interest`
- `last_price`
- `index_price`
- `mark_price`

`local_timestamp` is the selected availability clock for causal alignment.

## Readiness result

Frozen status:

`DATA_READY_SANDBOX`

All frozen core readiness gates passed:

- all 14 files present;
- causal availability timestamp defined;
- malformed nonblank numeric values <=5% per symbol-day;
- no August access;
- open-interest decision-time coverage >=95% for both symbols;
- open-interest schema unambiguous;
- past-only as-of reconstruction supported;
- raw directory Git-ignored;
- timestamp regressions deterministically resolvable.

The premium track also passed its readiness requirement.

## Coverage

Mean one-minute decision-grid coverage with no predictive-outcome-based staleness selection:

| Track | BTCUSDT | ETHUSDT |
|---|---:|---:|
| Open interest | 99.931% | 99.931% |
| Mark-index premium | 99.931% | 99.931% |

Every symbol-day used `local_timestamp` as the causal availability clock. Across all 14 files:

- raw timestamp regressions: 0;
- exact duplicate rows: 0;
- malformed timestamps: 0;
- malformed nonblank numeric fraction: 0.000%.

## Open-interest quality

Open interest is suitable for a later causal P1:

- approximately 104k--130k finite native updates per symbol-day;
- approximately 13.5k--14.2k unique values per symbol-day;
- no non-positive values;
- no one-step relative jumps greater than 10%;
- median native update gaps are generally below one second;
- p99 update gaps are generally around two to three seconds;
- worst observed gap is under 12 seconds.

Many feed records repeat the same open-interest value, which is expected for a state stream. Later P1 construction must use past-only native state and not treat repeated values as independent information.

## Funding-rate quality

`funding_rate` is present with approximately 99.931% decision-time state coverage and hundreds to roughly one thousand distinct/changed states per symbol-day. The audit consistently identifies it as stepwise.

This means funding is usable as a causal state variable, but it should not be interpreted as a continuously independent sub-second signal merely because the feed repeats the current funding value frequently.

`predicted_funding_rate` is unusable in the frozen sample:

- finite native updates: 0;
- decision coverage: 0%;
- native missing fraction: 100%.

Therefore `predicted_funding_rate` is excluded from the next P1 hypothesis.

## Premium quality

The causally derived mark-index premium passed readiness for both symbols.

Across the frozen symbol-days:

- decision-grid coverage is 99.931%;
- median absolute premium is typically about 3.6--5.1 bp;
- p95 absolute premium is typically about 5.1--8.5 bp;
- impossible native mark/index prices observed: 0.

The premium is therefore eligible for a later P1 as a derivatives-state feature family.

## Scientifically justified P1 subset

P0 authorizes a separately preregistered P1 using only:

1. open-interest state;
2. current native funding-rate state;
3. causally derived mark-index premium state.

Not authorized for the same P1:

- predicted funding rate;
- liquidation streams;
- new exchanges;
- new symbols;
- August data;
- new model classes selected from P1 outcomes;
- L2 rescue features.

## Staleness design implication

Observed derivative-state update gaps are far shorter than 30 seconds: p99 gaps are generally around 2--3 seconds and the worst observed gap is under roughly 15 seconds even for funding updates in the audited files.

A 30-second maximum staleness limit is therefore a conservative data-quality choice for P1. It is selected from P0 update-gap evidence before predictive scoring, not from AUC, PnL, or other predictive outcomes.

## Interpretation

`DATA_READY_SANDBOX` means the new derivatives-native information family is sufficiently complete and causally alignable to justify a predictive incremental-information experiment.

It does **not** mean:

- the information predicts the 10-minute opportunity target;
- the information adds value beyond volatility/regime state;
- a direction model is justified;
- positive trading PnL exists;
- the method is prospectively validated;
- live trading is authorized.

The next scientific question is whether open interest, funding state, and premium provide **within-regime timing information beyond the existing R/regime baseline** under the already-frozen 10-minute >=24 bp opportunity target.
