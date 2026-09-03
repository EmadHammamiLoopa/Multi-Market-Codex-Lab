# DEV045-M0 Canonical Feasibility Result Freeze

Status:

`DEV045_M0_CONDITIONAL_MBP_QUEUE_MODEL_ONLY`

Date: 2026-09-03

## Canonical execution identity

`65eacf6639ef9235cab365860917cfc2bb98c418`

DEV045-M0 MUST NEVER BE RERUN.

## Canonical artifact

Path:

`/home/emadh/Multi-Market/evidence/dev045_m0_maker_feasibility_v1/DEV045_M0_MAKER_FEASIBILITY_RESULT.json`

Bytes:

`15490`

SHA256:

`9a950ba7f4421cc06815f58ce559d3365081f7c8d6ce360225f65154a70138f3`

Status:

`DEV045_M0_CONDITIONAL_MBP_QUEUE_MODEL_ONLY`

## Frozen aggregate audit

Authorized days:

`7`

All days pass:

`true`

Total incremental L2 rows:

`922305070`

Total trade rows:

`30712432`

Total snapshot rows:

`156405`

Total zero-quantity L2 rows:

`119709360`

Total unknown trade rows:

`0`

Maximum observed L2 local-minus-exchange latency:

`5878256 us`

Maximum observed trade local-minus-exchange latency:

`3047500 us`

Every authorized day passed:

- exact raw header
- positive row support
- zero bad rows
- snapshot presence
- bid/ask presence
- buy/sell trade presence
- local timestamp monotonicity
- zero negative local-minus-exchange latency
- exchange/local timestamp presence

No Aug data was opened.

No Sep-01+ data was opened.

No non-BTC data was opened.

## Per-day raw identities

### 2026-01-01

L2:
- bytes = `347513061`
- SHA256 =
  `0488a2204c9070b1e6a8769af48d54fb36e6a5658613267e2615cd3228002ded`
- rows = `62609291`
- snapshots = `2002`
- zero-qty rows = `7667372`

Trades:
- bytes = `9691108`
- SHA256 =
  `e4aaee2b9f85016a5198e0cace5755dbd789c0f6f47ac0fc802c8f4b533833f6`
- rows = `1056983`

### 2026-02-01

L2:
- bytes = `865907076`
- SHA256 =
  `a1e9fc0fcc20d309d171ed1b6367ebe17948c84dd025a07a5d13c80f0b023cc4`
- rows = `165962192`
- snapshots = `7085`
- zero-qty rows = `27573999`

Trades:
- bytes = `57631972`
- SHA256 =
  `dfd19ab53abbc90118ce3c861521ecb17dbed6ce7bcc7410c07f296460454508`
- rows = `6759515`

### 2026-03-01

L2:
- bytes = `737199360`
- SHA256 =
  `a5468fb97f161b05a89f8dcc39d8c88a58fb6dc60caeb69aa783facff66c27e1`
- rows = `139795935`
- snapshots = `2434`
- zero-qty rows = `21396807`

Trades:
- bytes = `50842755`
- SHA256 =
  `50d3762a883f3f1cddc6869bbc2dbaaacf5bb52637ac0b51b85ae4dfcafdcb50`
- rows = `5961363`

### 2026-04-01

L2:
- bytes = `675132621`
- SHA256 =
  `d1d08211ebcc8b576c4b9d50158ff39971f66dd463cffe1929dacd3d17223cfd`
- rows = `124963429`
- snapshots = `22194`
- zero-qty rows = `16859336`

Trades:
- bytes = `33823287`
- SHA256 =
  `31959ff7bcf8aae71fe4826987a6cbafc7897c6e881a2d555b89b99ac4def804`
- rows = `4104211`

### 2026-05-01

L2:
- bytes = `557562555`
- SHA256 =
  `284b95a8d84d1fdda10f73d80ba8cfb5f1f2ee60db9bd00937f3701e5948faf4`
- rows = `101067739`
- snapshots = `29023`
- zero-qty rows = `10622246`

Trades:
- bytes = `26110327`
- SHA256 =
  `272f6d8ac29d14098c27d9fdaf95795ac5ed371024a000f279feaa38cf5605e1`
- rows = `3166686`

### 2026-06-01

L2:
- bytes = `893502369`
- SHA256 =
  `581361873d3a692362257217e27961332ee25786dca27f280048be2ed150837d`
- rows = `161057093`
- snapshots = `47781`
- zero-qty rows = `17311007`

Trades:
- bytes = `34960370`
- SHA256 =
  `f1f695bf6ef198f209a115250d1b99194bb21dfa4693cab2dcb4a10a969be53e`
- rows = `4445372`

### 2026-07-01

L2:
- bytes = `923475379`
- SHA256 =
  `b2e8bbed3db89695f055dc3010a0fff074732d82ae18117a1602b5593c90d1f1`
- rows = `166849391`
- snapshots = `45886`
- zero-qty rows = `18278593`

Trades:
- bytes = `41982532`
- SHA256 =
  `eefc51c11e55b6d0224e760479bff87fc1f052773ae3c8ae08700395fa229a87`
- rows = `5218302`

## Interpretation

Historical passive execution research is feasible with the current source only
under queue-model uncertainty.

The source is:

`MARKET_BY_PRICE_L2`

not Market-By-Order.

Therefore:

- exact individual-order FIFO rank is not observed;
- touch=fill is forbidden;
- queue advancement cannot be treated as directly observed;
- queue assumptions must remain explicit and conservative;
- later prospective live fill calibration is mandatory before deployment.

## Frozen queue policy for next stage

Primary:

`RISK_ADVERSE`

Diagnostic:

`LOG_PROB`

Pinned simulator compatibility:

`hftbacktest==2.4.4`

M0 already verified API support for:

- initial snapshot
- constant order latency
- risk-adverse queue model
- log probability queue model
- partial fill exchange
- no-partial-fill exchange
- trading-value fee model
- price/lot configuration

## No-PnL confirmation

M0 computed no:

- maker PnL
- spread capture
- PF
- drawdown
- strategy leaderboard
- winner

## Next authorized stage

`DEV045-M1 MAKER REPLAY PARITY + SYNTHETIC FILL TESTS`

M1 remains pre-strategy-PnL.

M1 must prove:

1. Tardis MBP/trade event conversion into the pinned simulator;
2. snapshot initialization and continuity;
3. deterministic submit/cancel lifecycle latency;
4. risk-adverse queue behavior on controlled synthetic cases;
5. probabilistic queue model behavior as diagnostic only;
6. partial-fill and no-partial-fill semantics;
7. no touch=fill;
8. fee hooks;
9. maker/taker fill flags;
10. post-fill markout plumbing without strategy PnL.

Only after M1 is green may a finite maker policy family be designed.

## Current state

`DEV045_M0_CANONICAL_CONDITIONAL_PASS_FROZEN_M1_REPLAY_PARITY_NEXT_NO_STRATEGY_PNL`
