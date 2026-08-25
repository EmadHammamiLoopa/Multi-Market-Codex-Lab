# CODEX-EXP-004-P0 Preregistration

Status: **MODEL-FREE DESIGN FROZEN BEFORE AUDIT OUTPUT IS OPENED**

Date: 2026-08-25

Experiment ID: `CODEX-EXP-004-P0`

## Motivation

`CODEX-EXP-001`, `CODEX-EXP-002`, and `CODEX-EXP-003` are permanently closed failures. The accumulated evidence rejects further escalation of the same 10--30 second BTC/ETH public-microstructure directional family under the tested personal-system cost and latency constraints.

This phase does **not** attempt another predictor. It asks a prior economic question:

> At which fixed holding horizons, if any, do BTCUSDT and ETHUSDT exhibit enough executable move magnitude and enough opportunity density that a later causal predictor would have room to pay realistic 8--12 bp round-trip costs?

The audit intentionally uses a future-aware direction oracle as an **upper-bound descriptive diagnostic only**. Oracle results are never trading evidence and cannot be called a strategy or a backtest.

## Frozen data

- Symbols: `BTCUSDT`, `ETHUSDT`.
- Target/execution input: existing Phase-L `FEATURES250` files only.
- Days: first UTC calendar day of January through July 2026 only.
- These days are already consumed sandbox data.
- No Binance Spot, Bybit, OI, funding, liquidations, options, macro, on-chain, or new data source is used in this phase.
- No download or regeneration is permitted.
- `2026-08-01` and `2026-08-04` through `2026-08-23` remain sealed and must not be opened.

## Execution semantics

The audit preserves the Phase-L executable touch semantics:

- decision state at `t`;
- reaction/entry at `t + 250 ms`;
- long entry at target ask and fixed-horizon exit at target bid;
- short entry at target bid and fixed-horizon exit at target ask;
- no midpoint substitution;
- no passive fill assumption;
- no maker credit;
- no sizing, leverage, Kelly, or compounding.

A row is valid only if the decision, entry, and fixed exit books are valid and all required prices are finite and positive. A fixed horizon may not cross the UTC day boundary.

## Decision schedules

Two descriptive views are frozen:

1. `dense_1m`: decisions every 60 seconds. These windows may overlap and therefore measure opportunity *availability*, not independent trade count.
2. `nonoverlap`: deterministic decisions every full holding horizon starting at UTC midnight. These windows do not overlap and provide a conservative density/stability view without oracle-timed event selection.

No threshold-dependent or future-dependent decision scheduling is allowed.

## Frozen horizons

The exact fixed holding horizons are:

- 60 s
- 180 s
- 300 s
- 600 s
- 900 s
- 1800 s
- 3600 s

They correspond to 1, 3, 5, 10, 15, 30, and 60 minutes.

No horizon may be added, removed, or shifted after output is opened under this experiment ID.

## Future-aware headroom oracle

For every valid scheduled decision:

```text
long_gross_bps  = 10000 * log(bid_exit / ask_entry)
short_gross_bps = 10000 * log(bid_entry / ask_exit)
oracle_gross_bps = max(long_gross_bps, short_gross_bps)
```

The oracle therefore knows the better fixed-horizon direction after the fact. This is deliberately impossible information and is used only to answer whether sufficient move magnitude exists in principle.

The audit reports long, short, and oracle distributions separately so the oracle cannot hide a structurally one-sided sample.

## Frozen costs and headroom thresholds

Round-trip cost envelopes:

- 8 bp primary;
- 12 bp stress.

Gross executable headroom thresholds:

- 8 bp
- 12 bp
- 16 bp
- 24 bp
- 36 bp
- 40 bp
- 60 bp
- 80 bp

`24 bp` is the key model-worthiness threshold because it equals 3x the 8 bp primary cost and 2x the 12 bp stress cost. `36 bp` is the strong-headroom threshold because it equals 3x the 12 bp stress cost.

For each schedule/horizon the audit must report:

- valid decision count;
- long/short/oracle mean and q50/q75/q90/q95/q99 gross bp;
- oracle threshold counts and fractions;
- oracle net distributions after 8 and 12 bp;
- fraction of oracle decisions positive after each cost;
- long-win, short-win, and tie fractions.

## Frozen model-worthiness gate

Only the deterministic `nonoverlap` schedule determines whether a horizon is eligible for a later predictive experiment.

For the `24 bp` headroom events, a horizon must satisfy **all** of:

1. pooled event count >= 100;
2. pooled event fraction >= 1%;
3. at least 12 of 14 symbol-days contain at least one 24 bp event;
4. median 24 bp event count per symbol-day >= 3;
5. BTC contributes at least 30 events and ETH contributes at least 30 events;
6. no one symbol-day contributes more than 25% of all 24 bp events;
7. at least 40 pooled events also reach the stronger 36 bp headroom threshold.

These gates establish only that the target family has enough **economic headroom and sample density to justify attempting prediction**. They do not establish predictability or profitability.

If more than one horizon is eligible, the frozen selection rule is:

> choose the **shortest eligible horizon** for the first predictive experiment.

This favors opportunity density and limits holding risk while requiring the same economic room. No post-hoc composite score or manual horizon choice is permitted.

If no horizon is eligible, the proposed large-move fixed-horizon family is stopped before ML and a new economic hypothesis is required.

## Interpretation rules

A Phase-0 eligible horizon means only:

`MODEL_WORTHY_SANDBOX`

It does **not** mean:

- profitable;
- predictable;
- validated;
- ready for August;
- ready for live or paper trading.

A future predictive phase must be separately preregistered before any new information source, target, classifier, threshold, or validation period is opened.

## Prohibited rescue actions

After the audit output is opened, this experiment ID may not be rescued by:

- adding horizons;
- changing the 1-minute decision grid;
- changing reaction latency;
- lowering costs;
- changing headroom thresholds;
- changing eligibility gates;
- adding new markets;
- adding OI/funding/basis/liquidation data;
- using MFE, a best-exit oracle, triple barriers, or variable holding time;
- training any ML model.

Pathwise MFE/triple-barrier feasibility is a different target question and, if justified, requires a new preregistered experiment.

## Required pre-score tests

Before the audit may run, synthetic tests must establish:

1. entry occurs exactly one 250 ms step after decision;
2. fixed exit occurs exactly `H` after entry;
3. long and short executable formulas use ask/bid touches correctly;
4. oracle direction is the greater of the two executable fixed-horizon returns;
5. dense decisions are exactly 60 s apart;
6. non-overlap decisions are exactly one horizon apart;
7. day-boundary crossings are rejected;
8. invalid decision/entry/exit books are rejected;
9. sealed dates/paths are rejected before open;
10. threshold counts/fractions are deterministic;
11. eligibility uses only the `nonoverlap` schedule;
12. shortest-eligible selection is deterministic.

## Stop condition

The required action after implementation, tests, and publication of the exact pre-score commit is **STOP FOR REVIEW**.

No headroom audit output may be opened before that exact commit is frozen and the tracked worktree is clean.
