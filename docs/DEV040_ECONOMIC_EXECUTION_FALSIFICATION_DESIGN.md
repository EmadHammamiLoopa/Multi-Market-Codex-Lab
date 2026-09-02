# DEV040 — Economic / Execution Falsification Design

Status: `DESIGN_FROZEN_BEFORE_ANY_DEV040_PNL`

Date: 2026-09-03

## 1. Project objective

This is a personal investment/profitability project.

DEV040 asks whether the fully frozen predictive policy produces executable
economic value on already-consumed Jan-Jul development data under explicit,
conservative execution assumptions.

DEV040 is NOT a new predictive search.

## 2. Frozen predictive policy

Exactly:

`A0 PRICE32 + BTC45 + S0 TOUCH_ONLY_SELECTIVE + W720 rolling q80`

Frozen target:

- symbol = BTCUSDT
- horizon = 120 seconds
- barrier = 16 bps

Frozen controller:

- score = p_touch
- window = 720 prior scores
- quantile = 0.80
- numpy method = higher
- current score excluded from its own threshold
- LONG iff BTC45 p_long >= 0.5
- SHORT otherwise

Predictive search remains permanently CLOSED.

## 3. Frozen canonical parent

DEV038-A-P2 canonical artifact:

`/home/emadh/Multi-Market/evidence/dev038a_p2_final_controller_correctness_v1/DEV038A_P2_FINAL_CONTROLLER_CORRECTNESS_RESULT.json`

SHA256:

`df32874a362cd75f646cdca483dc46956797431ac9a5861435639dfbf7f4b311`

Bytes:

`191547`

Scientific execution commit:

`a1ac3ea806def0f38b8952295b68fab8eb18e3a1`

Advanced controller:

`C2 / W720`

Permanent rule:

`DEV038-A-P2 MUST NEVER BE RERUN`

## 4. Forward reserve remains sealed

DEV040 may not open any data from:

`2026-09-01 UTC onward`

for any market.

This includes BTC, ETH, SOL, and every other collected market.

No forward features, predictions, coverage, labels, PnL, market statistics, or
execution simulation are permitted.

Storage-only integrity operations remain allowed.

## 5. Economic evaluation support

DEV040 economic scoring uses only the already-consumed frozen Apr-Jul OOF
validation action streams from the final C2/W720 policy.

Exactly four economic days:

- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

Jan-Mar may only participate in the frozen training/warm-start lineage that
generated those OOF actions.

No economic PnL may be scored on in-sample Jan-Mar predictions.

Expected pooled C2 action count from the frozen parent:

`1104`

The DEV040 implementation must reproduce the exact action stream before any
economic metric is accepted.

## 6. Economic baseline philosophy

DEV040-P1 is a single fixed baseline, not a parameter grid.

It must answer:

> Does the frozen predictive action stream have enough gross executable edge
> and enough net edge under conservative taker execution to justify further
> economic engineering?

No exit search, cost search, latency rescue, or sizing search occurs in P1.

## 7. Frozen execution clock

The existing DEV030 first-passage lineage is authoritative for entry causality.

Primary entry latency:

`250 ms`

Decision at time t.

Executable entry occurs at the first exact 250 ms grid row:

`t + 250 ms`

Entry price:

- LONG: best ask at entry row
- SHORT: best bid at entry row

This already includes crossing the observed spread.

No mid-price entry is permitted.

## 8. Frozen baseline exit

Primary DEV040-P1 uses one forced-horizon taker exit only.

No TP and no stop-loss in the primary baseline.

Holding horizon:

`120 seconds after executable entry`

Exit decision time:

`entry_time + 120 s`

Primary exit response latency:

`250 ms`

Therefore executable primary exit is the first exact causal valid book row at:

`entry_time + 120 s + 250 ms`

Exit price:

- LONG: best bid
- SHORT: best ask

If the exact primary exit row is missing/invalid, the trade is an integrity
failure and DEV040-P1 fails rather than silently dropping the trade.

This forced-horizon baseline is intentionally simpler than barrier-exit logic
and avoids choosing exits based on the already-observed 16 bp target outcome.

## 9. Latency sensitivity

Primary:

- entry = 250 ms
- exit response = 250 ms

Frozen stress-only sensitivity:

- entry = 500 ms
- exit response = 500 ms

Frozen severe sensitivity:

- entry = 1000 ms
- exit response = 1000 ms

Primary promotion/failure status is determined by the 250 ms baseline.

500 ms and 1000 ms cannot rescue a failed primary.

They are diagnostics for decay and robustness.

No faster-than-250 ms latency is evaluated.

## 10. Spread accounting

Spread is not represented as a separate arbitrary constant in gross return.

It is paid mechanically through executable quotes:

- LONG buy at ask, sell at bid
- SHORT sell at bid, buy back at ask

For reporting, serialize:

- entry spread bps
- exit spread bps
- median/p90 spread
- gross executable return already after bid/ask crossing

No double-counting of spread is permitted.

## 11. Fees

Primary round-trip taker fee envelope:

`8 bps total`

implemented as:

- 4 bps entry
- 4 bps exit

Stress fee envelope:

`12 bps total`

implemented as:

- 6 bps entry
- 6 bps exit

Zero-fee, rebate, VIP, and maker-credit scenarios are not promotion cases.

Fee break-even is reported directly from gross executable expectancy.

If verified personal live fee rates are later available, they require a
separate frozen deployment-cost mapping; they do not alter DEV040-P1.

## 12. Slippage

Primary DEV040-P1 slippage assumption:

`0 bps explicit extra slippage`

Reason:

The executable bid/ask crossing is directly observed, while exact
size-dependent market-impact reconstruction is not yet proven available for
the frozen action support.

To prevent optimism, explicit slippage stress scenarios are mandatory:

- +1 bp per side = 2 bps round trip
- +2 bp per side = 4 bps round trip

These are subtractive stress costs on top of executable bid/ask returns and
fees.

Primary pass may not rely on a positive zero-slippage result alone; the
conservative +1 bp/side stress is a mandatory gate below.

No negative slippage / price improvement is allowed.

## 13. Position and overlap semantics

Primary evaluation is:

`FLAT_ONLY`

Rules:

1. process action timestamps chronologically within each day;
2. when flat, accept the next frozen LONG/SHORT action;
3. once entered, ignore every subsequent action until executable exit;
4. no pyramiding;
5. no concurrent BTC positions;
6. no reversal while a position is open;
7. reset flat at UTC day start;
8. no trade may cross UTC day boundary.

This converts dense action rows into executable non-overlapping trades.

Also report raw action count and ignored-overlap action count.

## 14. Sizing and leverage

Evaluation unit:

`1.0 normalized notional`

Returns are measured in basis points.

No leverage.

No compounding.

No Kelly.

No dynamic sizing.

No confidence sizing.

No martingale.

Capital-return figures, if shown, must be simple normalized translations of
the exact bps ledger, not a sizing optimization.

## 15. Primary trade return

For each accepted trade:

LONG gross executable bps:

`10000 * ln(exit_bid / entry_ask)`

SHORT gross executable bps:

`10000 * ln(entry_bid / exit_ask)`

Primary net bps:

`gross_executable_bps - 8`

Primary conservative-slippage net bps:

`gross_executable_bps - 8 - 2`

Stress-fee net bps:

`gross_executable_bps - 12`

Severe cost diagnostic:

`gross_executable_bps - 12 - 4`

No fee/spread/slippage term may be hidden inside another metric.

## 16. Required outputs

DEV040-P1 must serialize pooled and per-day:

### Activity

- raw actions
- accepted flat-only trades
- ignored overlap actions
- trades/day
- LONG trades
- SHORT trades
- exposure seconds
- exposure fraction

### Execution

- entry timestamps
- exit timestamps
- holding seconds
- entry spread bps
- exit spread bps
- latency scenario

### Gross economics

- gross bp/trade mean
- gross bp/trade median
- total gross bps
- gross win rate
- gross profit factor

### Net economics

For each frozen cost scenario:

- net bp/trade mean
- net bp/trade median
- total net bps
- net win rate
- profit factor
- max drawdown in cumulative bps
- max consecutive losing trades
- positive days
- net return/day
- cumulative net return

### Break-even

- round-trip cost break-even bps
- fee break-even after observed spread crossing
- maximum extra slippage per side before mean expectancy reaches zero

### Robustness

- results at 250/500/1000 ms
- results at primary/stress fee envelopes
- results at 0/+1/+2 bp per-side explicit slippage

## 17. Profit factor definition

On the sequential flat-only trade ledger:

`PF = sum(positive net bps) / abs(sum(negative net bps))`

If no negative trades exist, PF = +infinity and must be serialized explicitly.

If no positive trades exist, PF = 0.

## 18. Max drawdown definition

For cumulative net bps ordered chronologically:

- prepend equity 0;
- cumulative sum trade net bps;
- running peak;
- drawdown = running peak - cumulative equity;
- max drawdown = maximum drawdown in bps.

No percentage capital drawdown is required in P1 because sizing/leverage are
not part of the experiment.

## 19. Net return/day definition

For each Apr-Jul UTC day:

`day_net_bps = sum(net bps of accepted trades entered that day)`

Report:

- mean day net bps
- median day net bps
- minimum day net bps
- maximum day net bps
- positive-day count / 4

## 20. Cost break-even definition

Pooled break-even round-trip cost:

`mean gross executable bps per accepted trade`

This is the total additional round-trip cost that would reduce mean expectancy
to zero.

Maximum extra slippage per side under a fee envelope F:

`max(0, (mean_gross_bps - F) / 2)`

If mean gross <= F, extra-slippage break-even is zero.

## 21. Mandatory primary falsification gates

The baseline economic case is:

- 250 ms entry
- 250 ms exit response
- observed bid/ask execution
- 8 bps total fees
- +1 bp per side explicit slippage
- flat-only
- forced 120 s exit
- normalized notional
- no leverage

DEV040-P1 is `ECONOMIC_BASELINE_PASS` only if ALL hold:

1. accepted trades >= 100;
2. accepted trades present on all four Apr-Jul days;
3. LONG trades > 0 and SHORT trades > 0;
4. mean gross executable bp/trade > 0;
5. mean net bp/trade under 8 bp + 2 bp slippage > 0;
6. pooled net profit factor > 1.05;
7. positive days >= 3/4;
8. total net bps > 0;
9. max drawdown < total positive-gross-profit magnitude;
10. 500 ms diagnostic mean gross bp/trade > 0;
11. no single day contributes > 60% of positive primary net bps.

If any fails:

`DEV040_P1_ECONOMIC_BASELINE_FAIL`

## 22. Failure taxonomy

This taxonomy is frozen before P1.

### F0 — No gross executable edge

If:

`mean gross executable bp/trade <= 0`

then the frozen predictive/execution family is economically falsified at the
most basic level.

No fee, maker, slippage, risk, sizing, or leverage rescue is authorized.

### F1 — Gross edge positive but below conservative costs

If gross > 0 but primary net <= 0:

Economic mechanism may exist but cannot pay the frozen taker envelope.

A later separately named economic experiment MAY test one materially different
execution mechanism, such as passive entry, only if:

- mechanism is preregistered;
- no Sep-01+ data is opened;
- no predictive component changes;
- it is not a parameter sweep around the failed taker baseline.

Historical EXP002 passive-entry failure must be considered before authorizing
such a mechanism.

### F2 — Net edge positive but unstable

If primary mean net > 0 but stability/risk gates fail:

A separately named risk-protocol experiment MAY be considered on consumed data
only.

It may change risk/overlap/capital rules but may not alter predictive scores,
controller, target, features, or model.

### PASS

If all primary gates pass:

The baseline execution policy becomes eligible for a separate frozen risk
protocol/finalization stage before the final sealed forward test.

## 23. No rescue inside DEV040-P1

After P1 begins there is no:

- alternate holding-period search;
- TP grid;
- stop-loss grid;
- trailing-stop grid;
- maker/taker switch;
- fee optimization;
- slippage optimization;
- latency optimization;
- leverage;
- sizing search;
- confidence sizing;
- controller reopening;
- predictive threshold reopening;
- target reopening.

Any materially new economic mechanism requires a new experiment ID and must
remain on consumed data.

## 24. Historical lessons explicitly incorporated

DEV040 acknowledges earlier frozen failures:

### CODEX-EXP-001

High-activity short-horizon taker cells could not pay 8-12 bp costs.

Therefore DEV040 reports gross headroom before interpreting net failure.

### CODEX-EXP-002

Conservative passive-entry simulation generated real fills but gross expectancy
was negative before fees; optimistic queue assumptions did not rescue it.

Therefore passive execution is not assumed to be a free solution and is not
part of DEV040-P1.

### CODEX-EXP-003

Faster 250 ms diagnostics did not rescue the failed cross-venue family, and
slower latency deteriorated results.

Therefore DEV040 does not permit a faster-than-250 ms latency rescue.

## 25. Stage structure

### DEV040-P0 — Economic support / executable-price audit

P0 only verifies:

- exact frozen C2 action reproduction;
- Apr-Jul OOF action timestamps;
- executable bid/ask availability at 250/500/1000 ms;
- forced 120 s exit availability;
- overlap/flat-only deterministic trade count;
- spread finite/positive;
- no Sep-01+ access.

P0 must NOT calculate gross/net PnL, PF, drawdown, win rate, or cost break-even.

### DEV040-P1 — Single frozen economic baseline

Only after P0 PASS.

P1 calculates the economic metrics and frozen gates above exactly once.

From P1 canonical start:

`DEV040-P1 MUST NEVER BE RERUN`

## 26. Current prohibitions

- NO Sep-01+ analytical access
- NO ETH/SOL/other-market analytical access
- NO predictive tuning
- NO economic PnL before P0 PASS
- NO personal-live capital deployment
- NO leverage
- NO new data acquisition for P1

## 27. Current state

`DEV040_ECONOMIC_EXECUTION_DESIGN_FROZEN_P0_SUPPORT_AUDIT_IMPLEMENTATION_NEXT`
