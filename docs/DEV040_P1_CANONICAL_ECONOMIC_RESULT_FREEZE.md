# DEV040-P1 Canonical Economic Result Freeze

Status:

`DEV040_P1_ECONOMIC_BASELINE_FAIL`

Failure taxonomy:

`F0_NO_GROSS_EXECUTABLE_EDGE`

Date: 2026-09-03

Scientific execution commit:

`ec69319ad77f34880ce85e1245ec0054e49b78a5`

Permanent rule:

`DEV040-P1 MUST NEVER BE RERUN`

No second canonical attempt is permitted.

## Canonical artifact

Path:

`/home/emadh/Multi-Market/evidence/dev040_p1_economic_baseline_v1/DEV040_P1_ECONOMIC_BASELINE_RESULT.json`

SHA256:

`935740f4dce6f8260cd22d6ead2f1aa2833c1b99bf5380e6faa184b01bdaf3ee`

Bytes:

`702431`

Canonical console log:

`/home/emadh/Multi-Market/evidence/dev040_p1_canonical_console_v1.log`

Log SHA256:

`2a1c3a7c22ee1510ee3fd499cd5ac5957498becd1ae3f35325c1f58ba4ab08cb`

Log bytes:

`934`

Canonical process:

- run RC = 0
- read-only verification RC = 0
- verification = 13 PASS / 0 FAIL
- git tree clean
- no staging residue

## Frozen support

- raw C2/W720 actions = 1104
- FLAT_ONLY accepted trades = 570
- LONG trades = 243
- SHORT trades = 327
- trades/day mean = 142.5
- Apr-Jul only
- all forward reserves remained sealed

## Primary economic scenario

Frozen primary:

- entry latency = 250 ms
- forced hold = 120 s
- exit response latency = 250 ms
- executable bid/ask crossing
- fees = 8 bps round trip
- explicit slippage = +1 bp per side
- FLAT_ONLY
- normalized notional
- no leverage

Primary results:

- mean gross executable bp/trade = -0.19759324074309276
- median gross executable bp/trade = -0.5367673975103269
- total gross bps = -112.62814722356288
- gross win rate = 0.4842105263157895
- gross profit factor = 0.9484919923509775

- mean net bp/trade = -10.197593240743092
- median net bp/trade = -10.536767397510328
- total net bps = -5812.628147223562
- net win rate = 0.11929824561403508
- net profit factor = 0.09230457556327486
- max drawdown = 5812.628147223564 bps
- max consecutive losing trades = 60
- positive days = 0/4

Primary day net bps:

- 2026-04-01: -1058.3577979247805
- 2026-05-01: -1187.791072358016
- 2026-06-01: -1745.4480793230427
- 2026-07-01: -1821.031197617724

Cost break-even:

- gross round-trip cost break-even = -0.19759324074309276 bps
- extra-slippage-per-side break-even = 0.0 bps

Because gross expectancy is already negative, there is no positive cost budget.

## Latency diagnostics

500 ms:

- mean gross bp/trade = -0.24125859573579297
- gross PF = 0.9374386475348062
- mean net bp/trade = -10.241258595735793

1000 ms:

- mean gross bp/trade = -0.2576799291678627
- gross PF = 0.9327081691247161
- mean net bp/trade = -10.257679929167862

Slower latency does not rescue the strategy.

## Spread observations

Observed median spreads were approximately 0.0145 bps at entry and exit, with
p90 approximately 0.0170 bps.

The economic failure is therefore not explained by a large quoted-spread
assumption. Gross executable returns are negative even before fee/slippage
deductions.

## Exposure

250 ms:

- accepted trades = 570
- total exposure = 68542.5 seconds
- exposure fraction of four days = 0.19832899305555557

500 ms:

- exposure fraction = 0.19874131944444445

1000 ms:

- exposure fraction = 0.19956597222222222

## Frozen gate result

Passed:

- accepted trades >= 100
- all four days present
- LONG and SHORT positive

Failed:

- mean gross > 0
- mean net > 0
- PF > 1.05
- positive days >= 3
- total net > 0
- drawdown gate
- 500 ms gross > 0
- positive-day concentration gate

## Frozen interpretation

The strategy is classified as:

`F0_NO_GROSS_EXECUTABLE_EDGE`

This means the frozen predictive/execution family is economically falsified at
the most basic executable-return level.

Under the preregistered DEV040 taxonomy, F0 does NOT authorize:

- fee rescue
- maker/passive rescue
- slippage rescue
- latency rescue
- risk/sizing rescue
- leverage
- TP/SL search
- alternate holding-period search
- predictive reopening
- controller reopening
- threshold reopening
- target reopening

No post-hoc weakening of this rule is permitted.

## Forward reserve

No analytical access occurred to:

`2026-09-01 UTC onward`

for BTCUSDT or any other collected market.

The forward reserve remains untouched and should NOT be spent confirming a
strategy that already failed gross executable economics on consumed OOF data.

## Project-level conclusion

The specific frozen family:

`A0 PRICE32 + BTC45 + S0 + W720 + forced-120s taker execution`

is closed as an investment candidate.

This does not imply that no profitable strategy can exist in the collected
markets. It means this specific discovered family failed its frozen economic
falsification.

Any future strategy research must be a genuinely new experiment family rather
than a rescue of DEV040-P1, and must continue to preserve Sep-01+ as sealed
forward reserve until that new family is fully frozen.

Current state:

`DEV040_P1_FROZEN_F0_NO_GROSS_EDGE_FAMILY_CLOSED_FORWARD_RESERVE_PRESERVED`
