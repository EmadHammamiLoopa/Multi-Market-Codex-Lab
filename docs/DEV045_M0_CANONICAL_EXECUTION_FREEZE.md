# DEV045-M0 Canonical Feasibility Execution Freeze

Status:

`DEV045_M0_GREEN_FROZEN_SINGLE_CANONICAL_RAW_FEASIBILITY_AUDIT_AUTHORIZED`

Date: 2026-09-03

## Frozen scientific execution identity

`65eacf6639ef9235cab365860917cfc2bb98c418`

This identity contains:

- DEV045 M0 raw MBP gzip scanner;
- BTC Jan-Jul no-PnL feasibility runner;
- hftbacktest API compatibility audit;
- synthetic raw scanner tests;
- feasibility contract tests;
- hftbacktest compatibility test;
- dedicated CI jobs.

Later handoff/documentation commits are not part of the scientific execution
identity.

## CI verification

GitHub Actions:

- run number: `1223`
- run id: `33784088553`
- conclusion: `success`

Dedicated jobs:

- `dev045-m0-feasibility = success`
- `dev045-m0-hftbacktest-api = success`

Supporting runs:

- #1222 raw gzip scanner = success
- #1221 hftbacktest API compatibility = success
- #1220 feasibility contracts = success
- #1215 M0 design freeze = success

## Raw scope

Exactly:

- exchange lineage: Tardis Binance Futures
- symbol: BTCUSDT
- days:
  - 2026-01-01
  - 2026-02-01
  - 2026-03-01
  - 2026-04-01
  - 2026-05-01
  - 2026-06-01
  - 2026-07-01
- raw data types:
  - incremental_book_L2
  - trades

Raw root:

`/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw`

This matches the prior DEV031/DEV032 raw lineage.

No Aug file is opened.

No Sep-01+ file is opened.

No non-BTC file is opened.

## Frozen raw headers

L2:

`exchange,symbol,timestamp,local_timestamp,is_snapshot,side,price,amount`

Trades:

`exchange,symbol,timestamp,local_timestamp,id,side,price,amount`

## Raw checks

For every authorized day:

- L2 rows > 0
- trade rows > 0
- zero parse-invalid rows
- snapshot rows > 0
- bid rows > 0
- ask rows > 0
- buy trades > 0
- sell trades > 0
- local timestamp regressions = 0
- negative local-minus-exchange feed latency = 0
- exchange/local timestamps present
- price finite positive
- quantity finite nonnegative

Also record:

- exchange timestamp regressions as diagnostic
- snapshot count
- zero-quantity L2 deletion count
- unknown trade count
- min/max/mean feed latency
- bytes and SHA256 per raw file

## Frozen simulator compatibility

Package:

`hftbacktest==2.4.4`

Verified API hooks:

- BacktestAsset.data
- initial_snapshot
- linear_asset
- constant_order_latency
- risk_adverse_queue_model
- log_prob_queue_model
- no_partial_fill_exchange
- partial_fill_exchange
- trading_value_fee_model
- tick_size
- lot_size

Primary historical queue model for future maker work:

`RISK_ADVERSE`

Diagnostic queue model:

`LOG_PROB`

Exact FIFO queue rank remains unobservable because source data is
Market-By-Price rather than Market-By-Order.

## Frozen M0 outcome semantics

If all seven raw days pass:

`DEV045_M0_CONDITIONAL_MBP_QUEUE_MODEL_ONLY`

This is deliberately not an unconditional maker execution PASS.

Reason:

- historical MBP replay is feasible;
- exact queue rank is not observed;
- conservative queue modeling and later prospective live fill calibration
  remain mandatory.

If any required raw integrity check fails:

`DEV045_M0_FAIL_MAKER_DATA_INSUFFICIENT`

## M0 no-PnL guards

M0 must not compute:

- maker PnL
- spread capture
- strategy PF
- strategy drawdown
- maker ranking
- winner

## Canonical output

Directory:

`/home/emadh/Multi-Market/evidence/dev045_m0_maker_feasibility_v1`

Manifest:

`DEV045_M0_MAKER_FEASIBILITY_RESULT.json`

The output directory must be absent before start.

## Canonical rule

Exactly one canonical raw feasibility audit is authorized.

If the canonical artifact is written successfully, M0 MUST NEVER BE RERUN to
obtain a more favorable feasibility result.

If execution stops with no artifact, perform read-only forensics before any
new attempt.

## Next if canonical M0 is conditional PASS

`DEV045-M1 MAKER REPLAY PARITY + SYNTHETIC FILL TESTS`

M1 remains pre-strategy-PnL.

It must establish event conversion and queue/fill semantics before any maker
strategy economics are opened.

## Current state

`DEV045_M0_GREEN_FROZEN_SINGLE_CANONICAL_RAW_FEASIBILITY_AUDIT_NEXT_NO_PNL`
