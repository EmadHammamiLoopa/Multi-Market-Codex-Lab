# DEV044-T1 — Economic Arena Execution Design

Status:

`IMPLEMENTED_SYNTHETIC_CI_PENDING_NO_CANONICAL_T1_PNL`

Date: 2026-09-03

## 1. Purpose

Run the first common-execution economic tournament for the 32 frozen DEV044
directional candidates.

No strategy rule, A0 threshold, support rule, cost assumption, latency
assumption, viability gate, ranking rule, or multiplicity family may change
after this stage is opened.

## 2. Frozen parents

T0E canonical action artifact:

- path:
  `/home/emadh/Multi-Market/evidence/dev044_t0e_support_audit_v1/DEV044_T0E_SUPPORT_AUDIT_RESULT.json`
- bytes: `23401`
- SHA256:
  `66864b5e90f3c5ca7d53b5a149cdcb65223eac04c04e68511fc998a0efcb84e8`

T0F frozen implementation identity:

`9100411e773b105f2d410e5bab08194313a387d3`

Final T0F freeze document:

`docs/DEV044_T0F_FINAL_FREEZE.md`

## 3. Candidate family

Exactly 32:

`T01U,T01A,...,T16U,T16A`

All 32 are executed.

Mechanical eligibility controls promotion only; it does not remove a candidate
from execution or from the max-stat family.

## 4. Primary directed execution

Decision timestamp:

the exact frozen T0E action timestamp.

Primary entry:

`decision + 250 ms`

LONG entry:

`ask(entry)`

SHORT entry:

`bid(entry)`

For each active action construct the same-direction executable PnL path from
entry through:

`entry + 1800 s`

LONG executable path:

`10000 * log(bid_t / entry_ask)`

SHORT executable path:

`10000 * log(entry_bid / ask_t)`

First same-direction executable path value >= +32 bp:

`TP touch`

First same-direction executable path value <= -32 bp:

`SL touch`

If TP and SL are both absent:

`HORIZON`

## 5. Response latency

Primary response latency:

`250 ms`

Barrier completion:

- observe TP/SL touch at t;
- executable exit at `t + 250ms`.

Forced horizon:

- horizon observation at `entry + 1800s`;
- executable forced exit at
  `entry + 1800s + 250ms`.

Thus response latency is applied consistently to both barrier and forced
horizon exits.

LONG exit:

`bid(exit)`

SHORT exit:

`ask(exit)`

Realized gross is always computed from the actual executable response quote,
not from the nominal +/-32bp touch.

## 6. Full-path validity

DEV030/DEV041 lineage is retained conservatively.

An emitted action is executable only when:

- exact 250ms timestamps exist from entry through horizon;
- every required quote on that path is book-valid;
- bid/ask are positive finite and uncrossed;
- the response exit timestamp exists;
- the response quote is valid.

Any violation is recorded as an execution-integrity failure.

No forward fill.

No interpolation.

No quote substitution.

No matched-subset deletion.

## 7. FLAT_ONLY

Each candidate is executed independently.

After accepting one trade, any later action with:

`decision_timestamp < current_trade_exit_timestamp`

is ignored as overlap.

At:

`decision_timestamp == current_trade_exit_timestamp`

the candidate is flat and may enter again.

No pyramiding.

No reversal while open.

No shared position state across candidates.

## 8. Scenarios

Primary:

- entry latency = 250ms
- response latency = 250ms
- cost = 10bp RT

Cost stress:

- same accepted primary trades
- cost = 16bp RT

Latency stress:

- rerun exact same frozen action stream
- entry latency = 500ms
- response latency = 500ms
- cost = 10bp RT

No strategy-specific costs.

No strategy-specific latency.

## 9. Economic metrics

For primary/cost stress/latency stress report:

- accepted trades
- LONG/SHORT accepted counts
- mean gross bp/trade
- mean net bp/trade
- total net bp
- PF
- positive days
- per-day net
- leave-one-day-out mean net
- positive-day concentration
- max drawdown
- median daily net

Primary max drawdown orders realized net trades by executable exit timestamp.

## 10. T0F gates

The runner imports the frozen T0F implementation directly.

No gate is duplicated with an alternate value.

Order:

1. T0F mechanical eligibility
2. T1 common execution
3. T0F economic eligibility
4. 32-family FWER max-stat
5. survivor ranking
6. maximum four distinct core representatives

## 11. Max-stat input

For every candidate:

- assign each accepted primary trade's full 10bp-net realized PnL to the UTC
  4-hour block containing its decision timestamp;
- aggregate into six aligned blocks/day;
- four days -> exactly 24 blocks.

Matrix:

`24 x 32`

The frozen T0F max-stat implementation is used without modification.

## 12. Paired A0 diagnostics

For each core T01-T16 compare A minus U using the aligned 24 block vectors.

Report:

- active decisions removed
- accepted trade delta
- gross bp/trade delta
- primary net bp/trade delta
- total primary net delta
- PF delta
- drawdown delta
- positive-day delta
- paired 4h block bootstrap 95% CI

This is diagnostic only.

## 13. Evidence files

Canonical T1 output, once separately authorized, will contain:

- `DEV044_T1_ECONOMIC_ARENA_RESULT.json`
- `DEV044_T1_PRIMARY_TRADES.csv`
- `DEV044_T1_LATENCY_STRESS_TRADES.csv`
- `DEV044_T1_PRIMARY_4H_BLOCKS.csv`

## 14. Forward guards

During T1:

- Sep-01+ stays sealed
- all non-BTC markets stay sealed
- no maker execution
- no strategy threshold change
- no family reduction
- no post-PnL rescue

## 15. Implementation

Core:

`src/multimarket/dev044_t1_execution.py`

Runner:

`src/multimarket/dev044_t1_runner.py`

Tests:

- `tests/test_dev044_t1_execution.py`
- `tests/test_dev044_t1_runner.py`

## 16. Authorization

No canonical T1 run is authorized until:

1. dedicated T1 CI is green;
2. full DEV044 regression chain is green;
3. this implementation is inspected for parity with T0/T0F;
4. a separate scientific execution identity is frozen.

## Current state

`DEV044_T1_IMPLEMENTED_SYNTHETIC_CI_PENDING_NO_CANONICAL_T1_PNL`
