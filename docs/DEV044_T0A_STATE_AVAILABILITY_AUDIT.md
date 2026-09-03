# DEV044-T0A — Strategy-State Availability and Materialization Audit

Status:

`NO_PNL_FEASIBILITY_AUDIT_DESIGN`

Date: 2026-09-03

## 1. Purpose

T0A determines which frozen DEV044 strategy-state variables can be reproduced
causally from existing audited sources before any DEV044 economic comparison.

No PnL is authorized in this stage.

## 2. Primary sources reviewed

Existing causal/project sources:

1. `FEATURES250` through DEV030 / Phase0DL lineage.
2. DEV042 price/OFI/pressure materialization.
3. DEV032 audited raw-event feature definitions.
4. DEV043-A frozen A0 survivor and OOF fold geometry.

The objective is to reuse existing definitions wherever possible.

## 3. Directly available or mechanically derivable states

The following T0 states are available from existing `FEATURES250` plus
strictly backward-looking transforms:

### Price / trend

- `ret_8_bps`: exact mid log return t vs t-8s.
- `ret_32_bps`: exact mid log return t vs t-32s.
- `ema_fast_minus_slow_bps`: fixed causal EWM difference.
- `breakout_up_bps` / `breakout_down_bps`: current mid relative to prior
  trailing range excluding future observations.
- `rv_ratio_8_to_32`: causal realized-volatility ratio from 250ms log returns.
- `price_z_32`: current log-mid displacement relative to prior 32s causal
  mean/std.

These support T01-T05 after exact formulas are frozen in the materializer.

### Fair value / book

Direct `FEATURES250` fields:

- `microprice_minus_mid_bps`
- `obi_l1`
- `obi_l5`
- `obi_l10`
- `spread_bps`

Therefore:

- `microprice_disp_bps` is direct.
- `price_minus_fair_bps = -microprice_disp_bps`.
- T06 and T07 are directly supportable.
- T08 is directly supportable.

### Aggressive flow

Direct source:

- `trade_qty_imbalance_1s`

Longer causal persistence can be derived from historical trailing values of
this source without future access.

This supports T11 after the exact 16s aggregation rule is frozen.

### Depletion / replenishment pressure

Direct fields include:

- `bid_replenish_l5_1s`
- `ask_replenish_l5_1s`
- `bid_deplete_l5_1s`
- `ask_deplete_l5_1s`

These provide a causal depletion-pressure component.

However, an exact separate cancellation-pressure state is not directly stored
in `FEATURES250`.

T12 therefore requires raw-event lineage or an already-audited DEV032 event
feature replay before T1.

### Round-number state

From causal current mid:

- nearest $100 BTC level is deterministic;
- round distance in bp is deterministic.

Together with 16s aggressive-trade persistence, T15 is supportable.

## 4. States requiring DEV032/raw-event replay

### T09 multi-depth weighted imbalance

Frozen T09 requires:

- OBI_L5
- OBI_L20
- distance-weighted OBI

`FEATURES250` supplies OBI_L5 but not OBI_L20 or distance-weighted OBI.

DEV032 already defines:

- S05 multi-depth OBI including L20;
- S06 distance-weighted OBI.

Therefore T09 should reuse/replay DEV032 causal extraction on DEV044 Apr-Jul
decision support.

No approximation from OBI_L10 is allowed.

### T10 OFI/MLOFI persistence

`FEATURES250` has short-window OFI/MLOFI fields, but the frozen T10 contract
expects causal 1s/16s/32s normalized flow persistence.

DEV032 contains stronger audited raw-flow definitions:

- S11/S12 MLOFI;
- S15 stationary standardized order flow;
- S34 temporal flow shape.

T10 should use an exact raw-flow replay rather than silently treat a trailing
average of a 1s indicator as equivalent to true 16s/32s flow.

### T12 cancellation/depletion pressure

DEV032 raw event taxonomy explicitly separates:

- insert;
- delete;
- replenish;
- deplete.

Therefore cancellation pressure should be reproduced from the DEV032
delete/deplete event lineage.

No synthetic cancellation proxy is allowed.

### T13 Hawkes-lite event intensity

Not directly present in `FEATURES250`.

DEV032 S29-S31 already define fixed exponential event intensities with:

- tau = 1s
- tau = 8s

This is exactly aligned with T13's intended fixed Hawkes-lite structure.

T13 must reuse those semantics.

### T14 liquidity shock / recovery

DEV032 S32/S33 already define:

- depletion shocks;
- depth recovery;
- spread/queue resilience.

T14 should reuse those semantics on DEV044 support.

No new post-hoc shock threshold is allowed.

## 5. T16 toxicity blocker

The frozen T16 contract includes a toxicity veto:

`toxicity >= 0.80 -> ABSTAIN`

A true VPIN/toxicity state is not present in the reviewed `FEATURES250`
schema, and DEV032's frozen feature set does not expose a canonical VPIN stream.

Therefore T16 is currently:

`MATERIALIZATION_BLOCKED_PENDING_TOXICITY_LINEAGE`

Do NOT silently set toxicity to zero.

Do NOT replace toxicity with spread, OFI, or another proxy after T0 freeze.

Before T1, choose one of two clean paths:

1. implement a separately specified causal VPIN/toxicity materializer from an
   authorized raw trade source; or
2. move T16 to a later separately versioned family and reduce the T1 candidate
   universe before any PnL is opened.

The choice must be made before T1 results exist.

## 6. Strategy readiness matrix

Current no-PnL status:

- T01: READY_AFTER_FORMULA_MATERIALIZER
- T02: READY_AFTER_FORMULA_MATERIALIZER
- T03: READY_AFTER_FORMULA_MATERIALIZER
- T04: READY_AFTER_FORMULA_MATERIALIZER
- T05: READY_AFTER_FORMULA_MATERIALIZER
- T06: READY_DIRECT
- T07: READY_DIRECT
- T08: READY_DIRECT
- T09: NEEDS_DEV032_RAW_REPLAY
- T10: NEEDS_DEV032_RAW_REPLAY
- T11: READY_AFTER_AGGREGATION_FORMULA
- T12: NEEDS_DEV032_RAW_REPLAY
- T13: NEEDS_DEV032_RAW_REPLAY
- T14: NEEDS_DEV032_RAW_REPLAY
- T15: READY_AFTER_FORMULA_MATERIALIZER
- T16: BLOCKED_PENDING_TOXICITY_LINEAGE

No T1 PnL is authorized until this matrix is resolved into an exact executable
materializer registry.

## 7. A0 OOF materialization

Implementation:

`src/multimarket/dev044_t0a_a0_oof.py`

The replay:

- uses A0 only;
- uses the frozen DEV043-A folds;
- uses the frozen A0 estimator definition;
- verifies the frozen DEV043-A artifact identity;
- refuses A1/A2 selection activity;
- computes no DEV043 null;
- writes no DEV043 artifact;
- verifies frozen pooled/per-fold/LOO metric identity before DEV044 can use the
  score stream.

Frozen identity tolerance:

`absolute tolerance = 1e-12`

Official A0 paired-economic support remains Apr-Jul only.

## 8. Next T0A implementation steps

1. wait for A0 replay CI to be green;
2. freeze exact mechanical formulas for T01-T05, T11 and T15;
3. implement DEV032 raw-event replay adapter for T09/T10/T12/T13/T14;
4. resolve T16 toxicity before PnL;
5. build a single Apr-Jul strategy-state table;
6. run a NO-PNL activity/support audit;
7. freeze numeric eligibility gates;
8. only then authorize T1.

## 9. Forward guards

- DEV044 real PnL: NOT OPENED
- Sep-01+: SEALED
- non-BTC markets: SEALED
- maker arena: OUTSIDE DEV044

## 10. Current state

`DEV044_T0A_A0_REPLAY_IMPLEMENTED_STATE_AVAILABILITY_AUDIT_COMPLETE_CI_PENDING_NO_PNL`
