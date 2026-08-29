# CODEX-EXP-022-P0 Frozen Result

Status: **PROSPECTIVE_BOOKTICKER_DATA_READY**

Date: 2026-08-29

Frozen pre-output implementation HEAD:

`b000667d4bbd5f6c7614c4e81c3cd9b0d1cca99e`

Result artifact:

`evidence/codex/exp022_p0_prospective_bookticker/PROSPECTIVE_BOOKTICKER_AUDIT.json`

Result artifact SHA-256:

`d1d2a90844260e88ab2fae4e20456960c2491512b91372147f3810c16c71d779`

Prospective raw SHA-256:

`c0a11173f8f03dbad787f18e3a7db31af1b1d8abb113f1171772ef9c6460f5a0`

Prospective 250 ms grid SHA-256:

`cf3a7291bc54a819e6b619badfcd01db10d4330566d0c3d8d3f16f204b7988ad`

## Official adjudication

`CODEX-EXP-022-P0 = PROSPECTIVE_BOOKTICKER_DATA_READY`

The preregistered prospective BTCUSDT bookTicker acquisition and integrity phase passed all frozen integrity gates.

This is a data-readiness result only.

No predictive validation claim, direction claim, or PnL claim is permitted from P0.

## Acquisition result

- symbol: BTCUSDT
- venue: Binance USD-M Futures
- UTC day: 2026-08-28
- accepted quotes: 38,799,998
- rejected records: 0
- transport records: 4
- accepted wall-clock reversals: 0
- accepted monotonic-clock reversals: 0
- accepted invalid/crossed prices: 0
- accepted negative quantities: 0
- accepted wrong-symbol quotes: 0

Raw bytes:

`1,837,104,146`

## Finalized grid

- rows: 345,600
- expected rows: 345,600
- grid step: 250,000 us
- valid rows: 345,596
- valid coverage: 0.999988425925926
- future quote violations: 0
- stale or unavailable rows: 0
- reconnect-invalid rows: 0
- first timestamp exact: PASS
- last timestamp exact: PASS

Grid bytes:

`33,390,476`

## Frozen integrity state

All required P0 integrity gates passed.

In particular:

- raw file non-empty = true
- exact grid row count = true
- exact 250 ms step = true
- coverage >= 99% = true
- no future quote use = true
- no invalid accepted quote = true
- no accepted clock reversal = true
- no other symbol accepted = true
- raw SHA recorded = true
- grid SHA recorded = true

## No-analysis guards

At P0 completion:

- target_scored = false
- model_fit = false
- auc_scored = false
- direction_scored = false
- pnl_scored = false
- historical_aug1_feature_reparsed = false
- older_august_holdout_opened = false

Network access occurred only for the preregistered prospective acquisition.

## Scientific interpretation

EXP022-P0 establishes a genuinely prospective and causally finalized BTCUSDT holdout artifact suitable for a separately preregistered ranking-confirmation experiment.

It does not test whether the volatility-ranking hypothesis predicts opportunity.

That question belongs exclusively to CODEX-EXP-022-P1.

No EXP022-P1 target, model, AUC, AP, direction, or PnL may be evaluated until the P1 protocol and implementation are frozen.
