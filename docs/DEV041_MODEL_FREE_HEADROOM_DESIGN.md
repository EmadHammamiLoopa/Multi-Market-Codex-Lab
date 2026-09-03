# DEV041 — Model-Free Executable Economic Headroom Screen

Status: `DESIGN_FROZEN_BEFORE_ANY_DEV041_REAL_HEADROOM_OUTPUT`

Date: 2026-09-03

## 1. Objective

Find the strongest economically plausible executable target geometry on
already-consumed BTCUSDT Jan-Jul data before spending research budget on a new
predictive family.

DEV041 is deliberately model-free.

It uses future path information only as an ORACLE HEADROOM CEILING.

A survivor is not a trading strategy.

## 2. Why DEV041 is a new family

DEV040-P1 permanently closed:

`A0 PRICE32 + BTC45 + S0 + W720 + forced-120s taker execution`

as:

`F0_NO_GROSS_EXECUTABLE_EDGE`

DEV041 does not change that result and does not rerun it.

It changes the research question from:

"Can the frozen 120-second predictive family make money?"

to:

"At which predeclared executable horizon/barrier geometries does enough market
movement exist to justify training a new predictor at all?"

## 3. Data seal

Allowed real data:

- BTCUSDT only
- 2026-01-01 through 2026-07-01 first-day lineage
- already-consumed data only

Forbidden:

- 2026-09-01+
- ETH
- SOL
- any other collected market
- any forward-bucket analytical access

Storage-only forward integrity operations remain allowed.

## 4. Candidate group

The complete candidate group is frozen before any DEV041 real output.

Horizons:

- 60 s
- 120 s
- 300 s
- 600 s
- 900 s
- 1800 s

Executable barriers:

- 8 bps
- 12 bps
- 16 bps
- 24 bps
- 32 bps

Cartesian product:

`6 horizons × 5 barriers = 30 candidates`

Candidate IDs use:

`H{seconds}_B{bps}`

Examples:

- H60_B8
- H120_B16
- H300_B24
- H900_B32
- H1800_B32

The group intentionally contains the historical DEV030 geometries:

- D = H60_B8
- A = H120_B16
- C = H300_B12
- B = H300_B24

so old anchors are visible but receive no special ranking privilege.

No candidate may be added after real results are observed.

## 5. Why this grid

The horizons span one minute through thirty minutes while remaining intraday.

The barrier grid spans:

- below the prior conservative economic envelope (8);
- near the economic envelope (12);
- the frozen historical target (16);
- materially above costs (24, 32).

This is a headroom screen, so lower barriers are retained as density controls
even though they cannot automatically satisfy higher cost envelopes.

No square-root-of-time assumption is used to generate the barrier values.

## 6. Authoritative path engine

Use the existing DEV030 executable first-passage semantics, generalized only to
the frozen DEV041 horizon/barrier set.

Decision grid:

- exact one-minute decisions

Entry latency:

- 250 ms

LONG executable path:

- enter at ask
- liquidate at bid

SHORT executable path:

- enter at bid
- cover at ask

The first barrier reached determines the oracle side.

If both sides first reach on the same row:

- mark ambiguous
- exclude from clean oracle opportunities

If neither side reaches before the vertical horizon:

- NONE

Missing/broken path:

- invalid
- never silently filled or interpolated

## 7. Oracle headroom semantics

For a clean first-passage event:

- oracle direction = direction that reaches the barrier first;
- oracle entry = causal executable entry quote at decision + 250 ms;
- oracle exit = executable opposite quote at first barrier timestamp;
- gross oracle bps = actual executable log-return at that exit.

This deliberately uses future information.

It is a ceiling diagnostic, not deployable PnL.

## 8. Flat-only oracle ledger

For each candidate/day:

1. process decision timestamps chronologically;
2. accept a clean oracle opportunity only when flat;
3. remain occupied until its first-passage exit;
4. ignore overlapping opportunities;
5. no pyramiding;
6. no same-symbol concurrent position;
7. no cross-day position.

This yields a non-overlapping oracle ledger.

## 9. Frozen cost envelopes

Report oracle economics under:

### C0 gross
- executable bid/ask only
- no additional fee/slippage subtraction

### C1 primary conservative
- 8 bps round-trip fees
- +1 bp/side explicit slippage
- total explicit deduction = 10 bps

### C2 severe
- 12 bps round-trip fees
- +2 bp/side explicit slippage
- total explicit deduction = 16 bps

Costs are used only to measure headroom.

No cost optimization is allowed.

## 10. Required candidate outputs

For each of 30 candidates, pooled and per day:

### Support
- valid decisions
- invalid decisions
- clean LONG-first count
- clean SHORT-first count
- NONE count
- ambiguity count
- clean-touch prevalence

### Timing
- median first-passage time
- p90 first-passage time
- LONG/SHORT first-passage timing

### Flat-only opportunity density
- raw clean opportunities
- accepted non-overlapping oracle trades
- ignored overlap opportunities
- oracle trades/day
- LONG oracle trades
- SHORT oracle trades

### Gross headroom
- mean gross executable bp/oracle trade
- median gross executable bp/oracle trade
- total gross bps
- gross PF
- gross win rate

### Cost headroom
Under C1 and C2:
- mean net bp/oracle trade
- total net bps
- PF
- positive days
- per-day net bps
- max drawdown
- max losing streak

### Stability
- leave-one-day-out mean C1 net
- leave-one-day-out mean C2 net
- minimum daily C1 net
- minimum daily C2 net
- maximum positive-day concentration

## 11. Hard headroom eligibility gates

A candidate is `HEADROOM_ELIGIBLE` only if ALL:

1. valid support >= 6000 pooled rows;
2. accepted flat-only oracle trades >= 100;
3. accepted oracle trades exist on all seven days;
4. LONG oracle trades > 0;
5. SHORT oracle trades > 0;
6. clean-touch prevalence >= 0.02;
7. C1 mean net bp/oracle trade > 0;
8. C1 total net bps > 0;
9. C1 positive days >= 6/7;
10. every C1 leave-one-day-out mean net > 0;
11. C2 mean net bp/oracle trade > 0;
12. C2 total net bps > 0;
13. C2 positive days >= 5/7;
14. every C2 leave-one-day-out mean net > 0;
15. no single day contributes > 40% of positive C1 total net bps;
16. no single day contributes > 40% of positive C2 total net bps.

These are intentionally demanding because oracle headroom should be clearly
positive before a new predictor is worth building.

## 12. Ranking

Among HEADROOM_ELIGIBLE candidates, rank exactly by:

1. highest minimum daily C2 net bps;
2. highest median daily C2 net bps;
3. highest C2 total net bps;
4. highest accepted oracle trades/day;
5. highest minimum LOO C2 mean net bp/trade;
6. lower horizon;
7. higher barrier;
8. lexical candidate ID.

Advance exactly one candidate:

`DEV041_HEADROOM_SURVIVOR_<candidate>`

If no candidate is eligible:

`DEV041_NO_EXECUTABLE_HEADROOM_SURVIVOR`

## 13. Important interpretation

Because oracle direction uses future path information, the winning candidate is
NOT evidence of a profitable strategy.

It only answers:

"Does this geometry have enough executable movement magnitude and density that
a future predictor could plausibly have room to pay realistic costs?"

The next stage, if a survivor exists, must create a new predictive family from
scratch and test whether the oracle opportunities are actually learnable.

## 14. No post-result rescue

After DEV041 canonical output begins:

- no new horizon;
- no new barrier;
- no cost-envelope change;
- no gate weakening;
- no ranking change;
- no volatility-adaptive barrier added;
- no TP/SL grid;
- no passive-execution rescue;
- no other-market rescue.

Any materially different headroom concept requires a new experiment ID.

## 15. Stage structure

### DEV041-P0
Implementation + synthetic/unit CI only.

### DEV041-P1
No-result real-data reproduction/support preflight:
- Jan-Jul authorized data identities;
- candidate count 30;
- causal path availability;
- no economic result display.

### DEV041-P2
Exactly one canonical model-free headroom screen.

From canonical P2 start:

`DEV041-P2 MUST NEVER BE RERUN`

## 16. Forward protection

All Sep-01+ data and all non-BTC markets remain analytically sealed throughout
DEV041.

## 17. Current state

`DEV041_MODEL_FREE_HEADROOM_DESIGN_FROZEN_IMPLEMENTATION_NEXT`
