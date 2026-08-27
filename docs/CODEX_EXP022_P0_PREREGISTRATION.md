# CODEX-EXP-022-P0 Preregistration

Status: **PREREGISTERED BEFORE PROSPECTIVE COLLECTION**

Date frozen: 2026-08-27

Experiment ID: `CODEX-EXP-022-P0`

Parent preserved commit:

`2b827a0df9d8e1bebe37df3445e1173fe4cb37e0`

Parent scientific state:

- `CODEX-EXP-019-P1 = FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED`
- `CODEX-EXP-020-P0 = DIAGNOSTIC_COMPLETE_VOLATILITY_FALSIFICATION_AND_CALIBRATION`
- `CODEX-EXP-021-P0 = NO_CALIBRATION_DESIGN_READY_SANDBOX`

## Purpose

EXP022-P0 creates a genuinely prospective, previously unseen BTCUSDT holdout for a later ranking-confirmation experiment.

This phase is **data acquisition and integrity only**.

It performs no target construction, no prediction, no AUC/AP, no direction scoring, and no PnL.

## Why a new prospective day is required

The historical Phase 0D-L preregistration explicitly states that the older Phase J/K holdout:

`2026-08-04..2026-08-23`

remains untouched and is not repurposed for Phase L.

EXP022 preserves that separation.

The existing Tardis Phase-L downloader provides free first-of-month samples only and therefore does not provide a new full unseen late-August day.

EXP022 instead collects a new prospective day after the present protocol is frozen.

## Frozen prospective day

Symbol:

`BTCUSDT`

Venue:

`Binance USD-M Futures`

UTC collection day:

`2026-08-28`

Day bounds:

- start: 2026-08-28 00:00:00 UTC inclusive
- end: 2026-08-29 00:00:00 UTC exclusive

No other symbol or day may be substituted after collection begins.

## Frozen source

Primary stream:

`BTCUSDT @bookTicker`

Binance USD-M WebSocket endpoint family:

`fstream.binance.com`

Only public market data is used.

No authentication and no trading endpoint.

## Why bookTicker is sufficient

The later frozen opportunity-ranking hypothesis uses only:

1. trailing `rv_30m_bps`, derived from causal mid prices;
2. best bid / best ask for the frozen 250 ms delayed-entry and 600 s executable opportunity target.

Full L2 depth, OFI, trades, options, derivatives, direction, and PnL are not needed for this hypothesis.

EXP022 therefore deliberately collects the minimum prospective information set required for the ranking hypothesis.

## Raw event record

Every accepted bookTicker update must preserve:

- local receive timestamp in wall-clock nanoseconds;
- local monotonic receive timestamp in nanoseconds;
- connection epoch;
- exchange event time `E` when present;
- exchange transaction time `T` when present;
- update id `u`;
- symbol `s`;
- best bid price `b`;
- best bid quantity `B`;
- best ask price `a`;
- best ask quantity `A`.

Transport lifecycle records must preserve:

- connection opened;
- connection closed / transport error;
- connection epoch;
- local wall-clock and monotonic timestamps.

Raw records are append-only gzip JSONL.

## Causality

A quote arriving at local receive time `r` may influence only grid timestamps `t >= r`.

No exchange event is backdated to exchange timestamp.

The prospective causal clock is the local receive clock, matching the historical Phase-L use of local timestamps as the decision clock.

## Frozen 250 ms grid

After the UTC day is complete, finalize into exactly:

`345600`

rows at:

`00:00:00.000, 00:00:00.250, ..., 23:59:59.750 UTC`

Columns:

- `local_timestamp_us`
- `best_bid`
- `best_ask`
- `mid`
- `book_valid`
- `quote_age_ms`
- `connection_epoch`
- `source_update_id`
- `exchange_event_time_ms`
- `exchange_transaction_time_ms`

For each grid timestamp, use the latest accepted quote whose **local receive timestamp is <= the grid timestamp**.

## Frozen quote validity rules

A grid quote is valid only if all are true:

1. at least one accepted quote has arrived at or before the grid time;
2. best bid > 0;
3. best ask > best bid;
4. bid and ask quantities are non-negative;
5. source symbol is exactly BTCUSDT;
6. raw local receive wall-clock timestamps have not moved backwards;
7. raw monotonic receive timestamps have not moved backwards;
8. the quote belongs to a currently connected epoch;
9. quote age at the grid timestamp is <= **2000 ms**.

If any condition fails, the row remains on the exact grid but:

- price columns are `nan`;
- `book_valid = 0`.

No interpolation.

No future quote fill.

No midpoint reconstruction across invalid intervals.

## Reconnection rule

A disconnect or transport error invalidates the quote state immediately.

After reconnection, no grid row becomes valid until a new valid BTCUSDT bookTicker quote is received in the new connection epoch.

## Raw acceptance rules

Reject a bookTicker update if:

- symbol is not exactly BTCUSDT;
- best bid/ask is non-finite or non-positive;
- best ask <= best bid;
- quantities are non-finite or negative;
- local wall-clock time decreases relative to the previous accepted raw record;
- monotonic receive time decreases.

Rejected updates are counted and recorded in the final audit; they are never used for grid state.

## Frozen P0 integrity gate

P0 status is:

`PROSPECTIVE_BOOKTICKER_DATA_READY`

only if all are true:

1. raw file exists and is non-empty;
2. finalized grid has exactly 345600 rows;
3. grid timestamps are exactly 250000 us apart;
4. first timestamp = 2026-08-28 00:00:00 UTC;
5. last timestamp = 2026-08-28 23:59:59.750 UTC;
6. valid grid coverage >= 99.0%;
7. no accepted quote has invalid/crossed prices;
8. no accepted quote has negative quantities;
9. no accepted raw wall-clock timestamp reversal;
10. no accepted raw monotonic timestamp reversal;
11. no quote from another symbol is accepted;
12. no future quote is used for any grid row;
13. raw SHA-256 and grid SHA-256 are recorded;
14. older Phase J/K holdout remains unopened;
15. Aug-01 historical feature file is not reparsed;
16. target is not scored;
17. model is not fit;
18. AUC/AP are not scored;
19. direction is not scored;
20. PnL is not scored.

If acquisition completes but any integrity gate fails:

`FAIL_PROSPECTIVE_BOOKTICKER_DATA_INTEGRITY`

If execution/provenance logic is violated:

`INVALID`

## P0 output

Expected raw path:

`/home/emadh/Multi-Market/data/codex_exp022/bookticker/BTCUSDT/2026-08-28.jsonl.gz`

Expected grid path:

`/home/emadh/Multi-Market/evidence/codex/exp022_prospective_bookticker/BTCUSDT/2026-08-28_BOOKTICKER250.csv`

Expected audit artifact:

`evidence/codex/exp022_p0_prospective_bookticker/PROSPECTIVE_BOOKTICKER_AUDIT.json`

## P0 no-analysis guards

Throughout EXP022-P0:

- `target_scored = false`
- `model_fit = false`
- `auc_scored = false`
- `direction_scored = false`
- `pnl_scored = false`
- `historical_aug1_feature_reparsed = false`
- `older_august_holdout_opened = false`

Network access is expected **only for acquisition**.

Network access is not permitted during later frozen scoring except where explicitly preregistered.

## Relationship to future EXP022-P1

P0 success does not authorize direction or PnL.

If and only if P0 passes, a separate frozen P1 may use this exact grid artifact and SHA-256 for a new opportunity-ranking confirmation.

P1 scientific choices must be preregistered before the grid is analytically opened for target/model scoring.

## No-rescue rule

After prospective collection begins:

- do not change the day;
- do not change symbol;
- do not add streams;
- do not change 250 ms grid;
- do not change 2000 ms staleness threshold;
- do not interpolate missing quotes;
- do not use Aug4-23;
- do not reopen Aug-01 features;
- do not score target/model/AUC/direction/PnL in P0.

Any material correction after output requires a new Experiment ID.
