# DEV044-T0F — Viability Gates and Block-Max-Stat Design Freeze

Status:

`NO_PNL_DESIGN_IMPLEMENTED_CI_PENDING`

Date: 2026-09-03

## 1. Purpose

Freeze every DEV044-T1 selection/eligibility rule that can reasonably be fixed
before viewing economic results.

T0F is strictly NO-PNL.

The next stage may compute economics only after this design is frozen green.

## 2. Frozen parent

DEV044-T0E canonical manifest:

- bytes = `23401`
- SHA256 =
  `66864b5e90f3c5ca7d53b5a149cdcb65223eac04c04e68511fc998a0efcb84e8`
- support rows = `5516`
- A0 gate pass rows = `2250`
- VPIN bucket volume = `45.56983`

T0E MUST NEVER BE RERUN.

## 3. Candidate family

The original selection family remains exactly:

`32 candidates`

in frozen order:

`T01U,T01A,...,T16U,T16A`

Mechanical ineligibility does NOT remove a candidate from the multiplicity
family.

All 32 remain in the primary joint max-stat calculation.

## 4. Mechanical pre-eligibility gate

A candidate is mechanically eligible for economic survivor consideration only
if:

1. pooled active decisions >= `100`; and
2. active decisions >= `1` on every one of the four Apr-Jul days.

These values are frozen from support geometry only, before any PnL.

### Mechanically ineligible from frozen T0E support

- T03U: pooled active 23
- T03A: pooled active 13
- T06U: 0
- T06A: 0
- T07U: 0
- T07A: 0
- T12A: pooled active 91
- T13U: 0
- T13A: 0

These nine candidates may be included in family-wide statistical calculations
but cannot be promoted, ranked or rescued in T1.

### Mechanically eligible

Exactly 23 candidates:

- T01U
- T01A
- T02U
- T02A
- T04U
- T04A
- T05U
- T05A
- T08U
- T08A
- T09U
- T09A
- T10U
- T10A
- T11U
- T11A
- T12U
- T14U
- T14A
- T15U
- T15A
- T16U
- T16A

No post-PnL change to this list is allowed.

## 5. T1 execution shell

Frozen from T0:

- BTCUSDT
- H = 1800 s
- barrier = +/-32 bp
- decision cadence = 60 s
- entry latency = +250 ms
- response latency = +250 ms
- LONG entry at ask
- SHORT entry at bid
- executable exits at opposite side
- first TP/SL barrier or forced H1800 exit
- FLAT_ONLY
- no overlap
- no pyramiding
- fixed normalized notional
- no leverage
- no dynamic sizing

## 6. Cost and latency scenarios

Primary economics:

`10 bp round-trip cost`

Cost stress:

`16 bp round-trip cost`

Latency stress:

- entry latency = `500 ms`
- response latency = `500 ms`
- primary 10 bp round-trip cost
- same frozen action stream

No candidate receives a unique fee or latency assumption.

## 7. Accepted-trade support gates

A mechanically eligible candidate must also satisfy all of:

- accepted trades pooled >= `40`
- accepted trades on every day >= `5`
- accepted LONG trades pooled >= `10`
- accepted SHORT trades pooled >= `10`
- execution-integrity failures = `0`

These thresholds are frozen before accepted-trade counts or PnL are viewed.

A candidate failing any one is economically ineligible.

## 8. Primary economic definitions

For every accepted trade:

`net_bps = gross_executable_bps - round_trip_cost_bps`

Primary expectancy:

`mean(primary net_bps across accepted trades)`

Primary profit factor:

`sum(max(net_bps,0)) / max(abs(sum(min(net_bps,0))), 1e-12)`

Daily primary net:

`sum(primary net_bps for accepted trades assigned to that calendar day)`

Trade/day assignment for daily metrics:

`entry decision timestamp day`

Leave-one-day-out expectancy:

for each one of Apr/May/Jun/Jul, remove all trades whose decision timestamp is
on that day and recompute mean primary net bps/trade on the remaining days.

Max drawdown:

- order accepted trades chronologically by executable exit timestamp;
- equity starts at 0 bp;
- add primary net_bps at each realized exit;
- max drawdown is largest peak-to-subsequent-trough decline in cumulative bp.

Positive-day concentration:

if at least one day has positive daily primary net:

`max(positive daily net) / sum(positive daily nets)`

otherwise concentration = 1.

## 9. Frozen economic eligibility gates

Every mechanically eligible candidate must satisfy all of:

1. execution-integrity failures = 0
2. accepted trades pooled >= 40
3. accepted trades each day >= 5
4. accepted LONG >= 10
5. accepted SHORT >= 10
6. pooled primary net expectancy > 0 bp/trade
7. primary PF >= `1.10`
8. at least `3 of 4` days have positive primary daily net
9. all four LOO primary net expectancies > 0
10. positive-day concentration <= `0.60`
11. max drawdown <= `320 bp` (= 10 × 32bp barrier risk units)
12. 16bp cost-stress expectancy > 0 bp/trade
13. 500ms/500ms latency-stress expectancy > 0 bp/trade

No threshold may be relaxed after T1 results are visible.

## 10. Primary multiplicity control

Primary anti-selection control:

`JOINT CHRONOLOGICAL BLOCK MAX-STAT BOOTSTRAP`

Family:

all 32 frozen candidates.

Primary cost basis:

10 bp round-trip.

### Aligned block construction

For each candidate:

1. create its realized primary net trade PnL;
2. assign each accepted trade's full realized primary net_bps to its frozen
   decision/entry timestamp;
3. aggregate candidate net_bps into fixed UTC calendar blocks:
   - 00:00-04:00
   - 04:00-08:00
   - 08:00-12:00
   - 12:00-16:00
   - 16:00-20:00
   - 20:00-24:00
4. do this separately for Apr, May, Jun and Jul.

Thus each candidate has exactly:

`24 aligned 4-hour block totals`

The full block matrix is:

`24 × 32`

Candidate columns are resampled JOINTLY so cross-strategy correlation is
preserved.

The 4h block length is > 8× the maximum H1800 holding horizon and was frozen
before PnL.

### Test statistic

For candidate j:

`T_j = sqrt(24) * mean(block_pnl_j) / sd(block_pnl_j)`

using sample standard deviation.

If block variance is zero:

`T_j = 0`

The observed family statistic is:

`max_j T_j`

### Null bootstrap

Center each candidate's 24 block totals by its own observed block mean.

Use:

- bootstrap repetitions = `20,000`
- RNG = NumPy PCG64 via `default_rng`
- seed = `440044`
- resample exactly 24 block rows with replacement
- use the same sampled row indices for all 32 candidates in each replicate
- compute the maximum studentized statistic across all 32 each replicate.

Candidate FWER p-value:

`(1 + number(max_bootstrap >= observed_T_j)) / (1 + 20000)`

Family alpha:

`0.05`

A candidate cannot survive T1 unless:

`FWER p <= 0.05`

Mechanical/economic gates do not remove candidates from this 32-family null.

## 11. Diagnostics, not extra hard gates

Report but do not require simultaneous PASS for:

- Hansen SPA
- White Reality Check
- Deflated Sharpe Ratio
- PBO/CSCV only if geometry is interpretable

The primary hard multiplicity control remains block max-stat only.

## 12. Paired A-vs-U analysis

Exactly 16 frozen pairs:

`T01A-T01U ... T16A-T16U`

For each pair report:

- active decisions removed by A0
- accepted-trade count delta
- gross bp/trade delta
- primary net bp/trade delta
- total primary net delta
- PF delta
- max-drawdown delta
- positive-day delta
- 4h block paired delta distribution

Paired block bootstrap:

- same 24 aligned 4h blocks
- delta = A block primary net - U block primary net
- 20,000 resamples
- seed = `440045`
- percentile 95% CI for mean block delta

Paired analysis is diagnostic of A0 economic value.

It does not create extra selectable candidates and is not itself a hard
survivor gate.

## 13. Eligibility pipeline

Exact order:

`32 frozen candidates`

-> mechanical pre-eligibility

-> common execution

-> economic gates

-> 32-family block max-stat FWER

-> survivors only

-> ranking

A candidate failing an earlier eligibility stage cannot be rescued by a strong
ranking metric.

## 14. Ranking survivors

Only candidates passing:

- mechanical gate;
- every economic gate;
- FWER p <= 0.05

are ranked.

Descending priority:

1. minimum of four LOO primary net expectancies
2. median daily primary net
3. pooled primary net expectancy
4. 16bp stress-cost expectancy
5. primary PF
6. lower max drawdown
7. lower positive-day concentration
8. higher accepted-trade count
9. lexical candidate ID as deterministic final tie-break

Raw total PnL is never the sole winner criterion.

## 15. Promotion cap

At most:

`4 distinct core mechanisms`

may advance from T1.

U/A variants of the same core count as one core mechanism for this cap.

If both U and A from one core survive, the higher-ranked variant is the
default representative unless T2 explicitly freezes both for a paired
mechanistic reason before further economics.

## 16. No rescue

After T1 is opened:

- no threshold change
- no minimum-trade change
- no PF change
- no drawdown-limit change
- no block-size change
- no bootstrap seed/repetition change
- no family reduction
- no cost change
- no latency-stress change
- no post-hoc inclusion of mechanically ineligible candidates
- no T17 rescue

A materially different rule belongs to a separately named future experiment.

## 17. Implementation authority

`src/multimarket/dev044_t0f_gate_bootstrap.py`

Tests:

`tests/test_dev044_t0f_gate_bootstrap.py`

## 18. Current state

`DEV044_T0F_GATE_BOOTSTRAP_DESIGN_IMPLEMENTED_CI_PENDING_NO_PNL`
