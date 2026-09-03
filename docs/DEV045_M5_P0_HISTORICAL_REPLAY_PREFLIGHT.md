# DEV045 M5-P0 Historical Replay Preflight

Status: DESIGN_ONLY

Parent scientific identity: `cbffd48a9eea77a7ace843f9c830ac96bd39a071`

## Purpose

Establish a fail-closed historical replay readiness gate before DEV045-M6 economics are authorized.

This gate is strictly non-economic. It may validate data availability, schema integrity, chronology, frozen policy-state availability, adapter compatibility, passive-target invariants, and replay-engine initialization. It MUST NOT expose, compute, persist, rank, or compare maker fills, fill rates, realized PnL, gross spread capture, fees, markouts, policy economics, or winners.

## Frozen authorized historical days

- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

BTCUSDT / Binance Futures only. SEP01_PLUS_SEALED and NON_BTC_SEALED remain in force.

## Allowed checks

1. Required Tardis incremental_book_L2 and trades inputs exist for every authorized day.
2. Input files are non-empty and parseable under the frozen M1 conversion path.
3. Event timestamps are valid and chronological after conversion.
4. Best bid/ask state is valid whenever policy evaluation is attempted.
5. Frozen DEV044 state required by M06/M07 (T10/T05 plus A0 gate state) is resolvable without changing any frozen threshold or decision rule.
6. M3 policies M01..M08 can be instantiated exactly as frozen.
7. M4 adapter rejects marketable/crossed/inside-spread targets and preserves one-bid/one-ask lifecycle constraints.
8. The safety-patched exact hftbacktest 2.4.4 source can initialize and consume the converted event stream.
9. Primary/stress/diagnostic latencies remain exactly 250/250 ms, 500/500 ms, and 100/100 ms respectively.
10. Any missing input, malformed event, unavailable frozen state, simulator mismatch, or invariant breach fails closed.

## Explicitly forbidden before the personal fee freeze

- submitting strategy orders against the historical seven-day replay for economic measurement;
- reporting or persisting maker fills, partial fills, fill ratio, cancel outcomes, queue wait, or forced-liquidation frequency by policy;
- computing gross or net PnL, spread capture, fees, taker liquidation cost, expectancy, profit factor, drawdown, daily economics, markouts, bootstrap statistics, p-values, eligibility, rankings, or a survivor;
- changing M01..M08, queue model hierarchy, latency, size, inventory cap, timeout, A0, T05, T10, terminal liquidation, flat-to-flat accounting, bootstrap, or M5 eligibility gates;
- opening SEP01_PLUS or NON_BTC data.

## Output contract

The preflight output may contain only gate-level booleans and identity metadata required to prove readiness. It must not contain per-policy economic counts or any economic scalar that could reveal comparative performance.

Successful completion means only `HISTORICAL_REPLAY_PIPELINE_READY_NO_ECONOMICS`. It does not authorize M6. M6 remains blocked until the actual personal venue fee schedule is independently verified and frozen under the M5 fee gate.
