# DEV041-P2 Canonical Execution Freeze

Status: `EXECUTION_FROZEN_SINGLE_CANONICAL_30_CANDIDATE_SCREEN_NEXT`

Date: 2026-09-03

Scientific execution commit:

`85678f10df3a720ea08c55bfa361d38e5cb8b8b4`

Execution branch:

`research/dev041-p2-execution-frozen`

The later documentation/handoff commits are excluded from scientific execution
identity.

Frozen V2 design:

`docs/DEV041_MODEL_FREE_HEADROOM_DESIGN_V2.md`

Design commit:

`88c2c17a1f370fadc9435c02dc7b0432c0bd6098`

P1 no-result preflight:

`DEV041_P1_NO_RESULT_PREFLIGHT_PASS`

P1 freeze:

`docs/DEV041_P1_NO_RESULT_PREFLIGHT_RESULT_FREEZE.md`

P1 freeze commit:

`8f0b78490ec95c5f0172b646e168fdbd495cc763`

## Canonical candidate universe

Exactly 30:

Horizons:
- 60
- 120
- 300
- 600
- 900
- 1800 seconds

Barriers:
- 8
- 12
- 16
- 24
- 32 bps

No second grid is permitted.

## Frozen executable semantics

Entry:

- exact minute decision
- +250 ms entry latency
- LONG enters ask
- SHORT enters bid

Touch:

- LONG barrier evaluated against bid
- SHORT barrier evaluated against ask
- first executable touch defines oracle direction
- same-row dual touch = ambiguous/excluded
- no touch by horizon = NONE

Response:

- touch event is not a fill
- response latency = +250 ms
- realized exit quote is opposite-side executable quote at touch +250 ms
- missing/invalid response row = response_exit_unavailable
- such opportunity remains in support diagnostics but is excluded from
  realizable oracle trades

Execution decomposition:

- nominal barrier
- executable touch gross
- barrier overshoot
- realized gross after response latency
- signed execution leakage

Eligibility uses realized-after-response economics only.

## Frozen cost envelopes

C0:
- realized executable gross
- zero explicit cost deduction

C1:
- 10 bps total explicit deduction
- 8 bps fee envelope
- 1 bp/side slippage

C2:
- 16 bps total explicit deduction
- 12 bps fee envelope
- 2 bp/side slippage

## Frozen eligibility

All 16 V2 eligibility gates are immutable.

## Frozen ranking

Among eligible candidates:

1. highest minimum daily C2 realized net bps
2. highest median daily C2 realized net bps
3. highest total C2 realized net bps
4. highest minimum LOO C2 realized mean net bp/trade
5. highest accepted realized oracle trades/day
6. lower horizon
7. higher barrier
8. lexical candidate ID

Advance exactly one candidate.

If no candidate qualifies:

`DEV041_NO_EXECUTABLE_HEADROOM_SURVIVOR`

and close this target-geometry family.

## Permanent anti-rescue

From canonical start:

`DEV041-P2 MUST NEVER BE RERUN`

No second attempt is permitted even on failure after the start marker.

After results:

- NO new horizon
- NO new barrier
- NO interpolation
- NO second grid
- NO cost-envelope change
- NO eligibility weakening
- NO ranking change
- NO other-market rescue

## Forward reserve

No analytical access to:

`2026-09-01 UTC onward`

for BTC or any other market.

## Current state

`DEV041_P2_EXECUTION_FROZEN_SINGLE_CANONICAL_SCREEN_NEXT`
