# DEV041 — Model-Free Executable Economic Headroom Screen V2

Status:

`DESIGN_V2_FROZEN_BEFORE_ANY_DEV041_REAL_HEADROOM_OUTPUT`

Date: 2026-09-03

Supersedes before any real DEV041 output:

`docs/DEV041_MODEL_FREE_HEADROOM_DESIGN.md`

The V1 document remains preserved in Git history. No Jan-Jul DEV041 headroom
result had been observed before this V2 freeze.

## 1. Objective

Find the strongest economically plausible executable target geometry on
already-consumed BTCUSDT Jan-Jul data before spending research budget on a new
predictive family.

DEV041 is model-free and uses future first-passage information only as an
oracle headroom ceiling.

A survivor is not a trading strategy.

## 2. New-family boundary

DEV040-P1 permanently closed:

`A0 PRICE32 + BTC45 + S0 + W720 + forced-120s taker execution`

as:

`F0_NO_GROSS_EXECUTABLE_EDGE`

DEV041 does not rescue, rerun, or modify DEV040.

Its question is:

> Which predeclared executable horizon/barrier geometry contains enough robust
> realized-after-response movement headroom to justify building a completely
> new predictor?

## 3. Data seal

Allowed analytical real data:

- BTCUSDT only
- first-day Jan-Jul 2026 consumed lineage only

Forbidden throughout DEV041:

- 2026-09-01+
- ETH
- SOL
- every other collected market
- any forward-bucket analytical access

Storage-only forward integrity operations remain allowed.

## 4. Hard-frozen candidate universe

Horizons:

- 60 s
- 120 s
- 300 s
- 600 s
- 900 s
- 1800 s

Barriers:

- 8 bps
- 12 bps
- 16 bps
- 24 bps
- 32 bps

Exact Cartesian product:

`6 × 5 = 30 candidates`

IDs:

`H{seconds}_B{bps}`

This exact universe is the only DEV041 geometry universe.

After any real DEV041 result is observed:

- NO new horizon;
- NO new barrier;
- NO interpolation such as 20bp;
- NO intermediate horizon such as 450s;
- NO second grid;
- NO nearby-candidate rescue;
- NO volatility-adaptive barrier;
- NO gate weakening.

If none of the 30 passes, this target-geometry family closes.

## 5. Authoritative first-passage semantics

Reuse the existing DEV030 executable first-passage engine.

Decision grid:

- exact one-minute decisions

Entry latency:

- 250 ms

LONG:

- enter at executable ask;
- barrier is evaluated against executable bid.

SHORT:

- enter at executable bid;
- barrier is evaluated against executable ask.

The first executable barrier touch determines oracle direction.

Same-row dual touch:

- ambiguous;
- excluded.

No touch by vertical horizon:

- NONE.

Missing/broken causal path:

- invalid;
- no interpolation or filling.

## 6. Touch event is NOT an assumed fill

The first-passage touch is a diagnostic event, not a guaranteed exit fill.

For each clean touch, freeze:

`touch_timestamp = first executable opposite-side quote reaching barrier`

Then freeze market-response execution latency:

`RESPONSE_LATENCY = 250 ms`

Realized exit timestamp:

`touch_timestamp + 250 ms`

The response row must exist on the exact 250 ms grid and have a valid,
uncrossed executable book.

If that response row is unavailable or invalid:

- record `response_exit_unavailable`;
- do not invent a fill;
- exclude that opportunity from the realizable oracle trade ledger;
- retain the event in touch/support diagnostics.

No faster-than-250ms response assumption is allowed.

## 7. Per-opportunity execution decomposition

For every realizable oracle opportunity serialize:

### Nominal barrier

`nominal_barrier_bps`

### Actual executable touch return

LONG:

`10000 * ln(touch_bid / entry_ask)`

SHORT:

`10000 * ln(entry_bid / touch_ask)`

Call this:

`touch_gross_bps`

### Barrier overshoot

`barrier_overshoot_bps = touch_gross_bps - nominal_barrier_bps`

### Realized after-response return

LONG:

`10000 * ln(response_bid / entry_ask)`

SHORT:

`10000 * ln(entry_bid / response_ask)`

Call this:

`realized_gross_bps`

### Execution leakage

Signed:

`execution_leakage_bps = touch_gross_bps - realized_gross_bps`

Interpretation:

- positive = deterioration during response latency;
- zero = unchanged;
- negative = improvement after touch.

Do not floor or cap this value.

## 8. Flat-only realizable oracle ledger

Flat-only occupancy uses the REALIZED response exit, not the touch timestamp.

For each candidate/day:

1. process realizable oracle opportunities chronologically;
2. accept next opportunity only when flat;
3. remain occupied until response exit;
4. ignore opportunities whose decision occurs while occupied;
5. no pyramiding;
6. no concurrent BTC positions;
7. no cross-day position.

This ledger is still oracle because future touch direction is known.

## 9. Frozen cost envelopes

All eligibility economics use `realized_gross_bps`, not touch return.

### C0

Realized executable gross after 250ms response latency.

### C1

- realized gross
- minus 8 bps round-trip fee envelope
- minus 1 bp/side explicit slippage
- total explicit deduction = 10 bps

### C2

- realized gross
- minus 12 bps round-trip fee envelope
- minus 2 bp/side explicit slippage
- total explicit deduction = 16 bps

Touch-return economics may be reported only as diagnostic headroom and may not
determine eligibility.

## 10. Required outputs per candidate

### Support

- valid decisions
- invalid decisions
- LONG-first
- SHORT-first
- NONE
- ambiguity
- clean-touch prevalence
- response-exit-unavailable count
- realizable-opportunity fraction

### Timing

- median/p90 first-passage time
- LONG/SHORT timing
- fixed response latency = 250 ms

### Execution decomposition

Pooled and per day:

- nominal barrier
- mean/median/p90 touch gross
- mean/median/p90 barrier overshoot
- mean/median/p90 signed execution leakage
- fraction leakage > 0
- fraction leakage < 0
- mean/median/p90 realized gross

### Activity

- raw clean touches
- raw realizable opportunities
- accepted flat-only realized oracle trades
- ignored overlap opportunities
- trades/day
- LONG/SHORT accepted trades

### Realized economics

For C0/C1/C2:

- mean/median return per accepted trade
- total bps
- PF
- win rate
- positive days
- per-day totals
- max drawdown
- max losing streak
- leave-one-day-out mean
- minimum daily net
- median daily net
- minimum LOO expectancy
- positive-day concentration

## 11. Hard eligibility gates

A candidate is HEADROOM_ELIGIBLE only if ALL:

1. valid support >= 6000 pooled rows;
2. accepted flat-only realized oracle trades >= 100;
3. accepted trades exist on all seven days;
4. LONG accepted trades > 0;
5. SHORT accepted trades > 0;
6. clean-touch prevalence >= 0.02;
7. C1 realized mean net > 0;
8. C1 realized total net > 0;
9. C1 positive days >= 6/7;
10. every C1 LOO realized mean net > 0;
11. C2 realized mean net > 0;
12. C2 realized total net > 0;
13. C2 positive days >= 5/7;
14. every C2 LOO realized mean net > 0;
15. no day > 40% of positive C1 total;
16. no day > 40% of positive C2 total.

A candidate cannot qualify on touch-return metrics if realized-after-response
metrics fail.

## 12. Robustness-first ranking

Among eligible candidates, rank exactly:

1. highest minimum daily C2 realized net bps;
2. highest median daily C2 realized net bps;
3. highest total C2 realized net bps;
4. highest minimum LOO C2 realized mean net bp/trade;
5. highest accepted realized oracle trades/day;
6. lower horizon;
7. higher barrier;
8. lexical candidate ID.

Advance exactly one candidate.

If none survives:

`DEV041_NO_EXECUTABLE_HEADROOM_SURVIVOR`

and close the 30-candidate target-geometry family.

## 13. Interpretation boundary

A survivor means only:

> this geometry contains robust executable movement headroom after a frozen
> 250ms response latency and conservative cost envelopes.

It does NOT establish:

- predictability;
- deployable direction knowledge;
- forward profitability;
- passive-fill feasibility;
- live execution quality.

A survivor only authorizes design of a new predictive family.

## 14. Stage structure

### DEV041-P0

Implementation + synthetic/unit CI only.

### DEV041-P1

No-result Jan-Jul support/reproduction preflight only.

It may verify:

- exact authorized source identities;
- candidate registry exactly 30;
- path/response-row availability mechanics;
- deterministic candidate enumeration.

It must not display candidate headroom/economic rankings.

### DEV041-P2

Exactly one canonical 30-candidate headroom screen.

From canonical start:

`DEV041-P2 MUST NEVER BE RERUN`

## 15. Permanent anti-rescue rule

After DEV041-P2 begins:

`NO SECOND GRID`

`NO NEW HORIZON`

`NO NEW BARRIER`

`NO INTERPOLATION`

`NO COST ENVELOPE CHANGE`

`NO RANKING CHANGE`

`NO GATE WEAKENING`

`NO OTHER-MARKET RESCUE`

## 16. Current state

`DEV041_DESIGN_V2_FROZEN_EXECUTION_LEAKAGE_IMPLEMENTATION_NEXT_NO_REAL_OUTPUT`
