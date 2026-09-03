# DEV044-T0 — Directional Strategy Contract and Execution-Parity Design

Status:

`DESIGN_FROZEN_BEFORE_REAL_DEV044_PNL`

Date: 2026-09-03

## 1. Purpose

DEV044 is a personal-profit strategy arena.

T0 freezes the directional/taker candidate contracts before any DEV044
historical PnL comparison is opened.

T0 does not run PnL.

T0 does not open Sep-01+.

T0 does not open another market.

## 2. Arena identity

Market:

`BTCUSDT`

Core mechanisms:

`T01 ... T16`

Candidate variants:

- `U` = ungated;
- `A` = exact same strategy plus the frozen A0 TOUCH gate.

Exact candidate count:

`32`

Exact candidate order:

`T01U,T01A,T02U,T02A,...,T16U,T16A`

The 32 candidates are one selection/multiplicity family.

## 3. A0 opportunity gate

Frozen Stage-A parent:

`DEV043_A_TOUCH_SURVIVOR_A0_TOUCH_PRICE_LOGIT`

Scientific execution identity:

`342547b45f1fecd361a17daad5c7450a755c6330`

Frozen artifact:

`/home/emadh/Multi-Market/evidence/dev043_a_touch_screen_v1/DEV043_A_TOUCH_SCREEN_RESULT.json`

Bytes:

`89918`

SHA256:

`38ee159618a1ed13727eb6a86df83b93c92c2aad50251fcfb1618d890efd2eb7`

DEV044 gate:

`A0 p_touch >= 0.50`

No A0 threshold search is permitted in DEV044-T1.

No q70/q80/q90 controller is permitted.

No A0 calibration layer is permitted.

No A0 model tuning is permitted.

### A0 score materialization clarification

The frozen DEV043-A artifact stores metrics and survivor identity but does not
store every OOF p_touch value.

Therefore DEV044 may materialize the exact frozen A0 OOF score stream for
Apr-Jul by replaying only the frozen A0 estimator and frozen chronological
fold definitions.

This is NOT a DEV043-A rerun because DEV044 must not:

- re-evaluate A1 or A2;
- recompute the DEV043-A joint null;
- re-run survivor selection;
- write to DEV043-A output paths;
- alter DEV043-A status.

Before DEV044 uses the score stream, the replay must exactly reproduce frozen
A0 pooled/per-fold metrics within strict numerical tolerance. If identity
reproduction fails, DEV044 A-variants fail closed.

Official paired U/A economic evaluation is Apr-Jul only because those are the
frozen OOF validation folds for A0.

Jan-Mar may be used for causal feature warm-up / implementation support but not
for an official A0 paired-economic claim.

## 4. U/A parity invariant

For every core Txx and timestamp t:

`U_action(t) = core_Txx(t)`

`A_action(t) = core_Txx(t)` if `A0_p_touch(t) >= 0.50`

otherwise:

`A_action(t) = ABSTAIN`

U and A must have identical:

- core signal;
- direction logic;
- decision timestamp;
- execution shell;
- entry rule;
- exit rule;
- latency;
- fee/slippage scenario;
- overlap handling;
- risk unit;
- cooldown semantics.

The A0 gate may only remove an action. It may never reverse or create one.

## 5. Common T1 execution shell

T1 intentionally standardizes execution so the first arena compares directional
mechanisms rather than exit optimization.

Frozen geometry:

- horizon = 1800 seconds
- barrier = 32 bps
- decision cadence = 60 seconds
- entry latency = +250 ms
- response latency = +250 ms
- LONG executable entry = ask
- SHORT executable entry = bid
- same-direction first barrier = TP
- opposite-direction first barrier = SL
- NONE = forced-horizon exit
- LONG executable exit = bid
- SHORT executable exit = ask
- FLAT_ONLY
- no overlapping BTC positions
- no pyramiding
- no reversal while open
- normalized fixed notional
- no leverage
- no martingale
- no dynamic sizing
- no confidence sizing

The authoritative executable mechanics should reuse the DEV042-P3 / DEV030
first-passage lineage rather than create a second execution interpretation.

## 6. Discovery cost envelopes

T1 must serialize gross executable return separately from costs.

Primary discovery cost envelope:

`C_PRIMARY = 10 bps round-trip`

Stress:

`C_STRESS = 16 bps round-trip`

These envelopes preserve comparability with prior project economic work and do
not claim to be the user's final personal fee tier.

Before live deployment, the surviving policy must be remapped to the user's
verified account fee schedule without changing the strategy signal.

No strategy may win because it is evaluated under a cheaper cost envelope than
another candidate.

## 7. Exact core rules

Implementation authority:

`src/multimarket/dev044_t0_strategy_contract.py`

All inputs must be causal and finite.

### T01 — multi-scale momentum

LONG if 8s and 32s trailing returns are both >0.

SHORT if both <0.

Otherwise ABSTAIN.

### T02 — EMA trend

Use causal fast-minus-slow EMA displacement.

- LONG if > +0.5 bp
- SHORT if < -0.5 bp
- otherwise ABSTAIN

The materializer must use one fixed EMA definition. No span grid is permitted.

### T03 — local breakout

- LONG if prior-high breakout distance >=1.0 bp and downward breakout is <1.0
  bp;
- SHORT symmetrically;
- simultaneous two-sided condition -> ABSTAIN.

The rolling range must exclude future values and be defined before T1 data
access.

### T04 — volatility-expansion momentum

Require:

`RV_8 / RV_32 >= 1.25`

Then:

- LONG if 32s return > +1 bp;
- SHORT if < -1 bp;
- otherwise ABSTAIN.

### T05 — short-term overreaction reversal

Causal standardized 32s price displacement:

- z <= -1.5 -> LONG
- z >= +1.5 -> SHORT
- otherwise ABSTAIN

The z-score history must use past-only statistics.

### T06 — microprice fair-value follow

Generalized microprice displacement:

- > +0.5 bp -> LONG
- < -0.5 bp -> SHORT
- otherwise ABSTAIN

### T07 — fair-value overshoot reversion

Let price_minus_fair be current price relative to generalized fair value.

- >= +1 bp AND L1 OBI <=0 -> SHORT
- <= -1 bp AND L1 OBI >=0 -> LONG
- otherwise ABSTAIN

### T08 — L1 queue imbalance

- OBI_L1 > +0.20 -> LONG
- OBI_L1 < -0.20 -> SHORT
- otherwise ABSTAIN

### T09 — multi-depth weighted imbalance

Require sign agreement among:

- OBI_L5 with +/-0.05 dead-zone
- OBI_L20 with +/-0.05 dead-zone
- distance-weighted OBI with +/-0.05 dead-zone

All positive -> LONG.

All negative -> SHORT.

Else ABSTAIN.

### T10 — OFI/MLOFI persistence

Require sign agreement among causal normalized:

- 1s flow
- 16s flow
- 32s flow

Each uses +/-0.05 dead-zone.

All positive -> LONG.

All negative -> SHORT.

Else ABSTAIN.

### T11 — aggressive trade-flow persistence

Require 1s and 16s aggressive trade imbalance agreement with +/-0.10 dead-zone.

Both positive -> LONG.

Both negative -> SHORT.

Else ABSTAIN.

### T12 — cancellation/depletion pressure

Require agreement between:

- directional depletion pressure
- directional cancellation pressure

Each uses +/-0.10 dead-zone.

Positive agreement -> LONG.

Negative agreement -> SHORT.

Else ABSTAIN.

### T13 — Hawkes-lite event intensity

No fitted Hawkes model.

Use fixed exponential-decay directional event-intensity contrasts:

- short decay state
- medium decay state

Both must exceed +/-0.05 with the same sign.

Positive -> LONG.

Negative -> SHORT.

Else ABSTAIN.

Recommended causal source semantics reuse DEV032 fixed exponential event
intensity definitions.

### T14 — liquidity-shock continuation

A causal shock detector supplies direction in {-1,0,+1}.

Trade shock direction only when current recovery fraction <0.50.

Otherwise ABSTAIN.

T1 tests continuation only. Recovery/reversal mode is deferred to T2 to prevent
a hidden second policy inside T14.

### T15 — round-number pressure

Nearest BTC round level is fixed to the nearest $100 increment.

Require absolute round-level distance <=5 bp.

Below the round level:

- aggressive 16s trade imbalance >=+0.10 -> LONG.

Above the round level:

- aggressive 16s trade imbalance <=-0.10 -> SHORT.

Else ABSTAIN.

No $50/$100/$500 round-number grid is permitted in T1.

### T16 — regime-filtered consensus

Three votes:

1. 32s price return with +/-1 bp dead-zone;
2. weighted OBI with +/-0.05 dead-zone;
3. 16s aggressive trade imbalance with +/-0.10 dead-zone.

At least 2/3 same-direction votes are required.

Fixed veto:

- toxicity >=0.80 -> ABSTAIN;
- spread >=5 bp -> ABSTAIN.

The veto may suppress but never reverse the consensus.

No toxicity/spread threshold search is permitted in T1.

## 8. Feature provenance

Where possible, DEV044 should reuse already-audited causal building blocks from
DEV032/DEV042 rather than invent duplicate feature semantics.

Relevant reusable families include:

- cumulative queue imbalance;
- distance-weighted OBI;
- generalized microprice;
- level-wise/order-flow persistence;
- event pressure;
- exponential event intensities;
- depth/liquidity recovery;
- price/momentum histories.

If a DEV044 materializer needs a transform not already present, it must be
implemented and synthetic-tested before T1.

## 9. Support and missing-feature rule

No strategy may silently delete hard timestamps because its signal is
inconvenient.

For the official Apr-Jul paired arena:

- all 32 candidates share the same base decision timestamp universe;
- an unavailable/invalid causal feature produces ABSTAIN for that candidate and
  is counted as feature-invalid/abstain diagnostics;
- execution support for an emitted action must be exact and valid;
- no matched-subset winner comparison is allowed.

## 10. Eligibility before ranking

T1 will use an explicit viability/robustness gate before ranking.

Final numeric gates are to be frozen after a no-PnL T0 support/activity audit,
because H1800/FLAT_ONLY mechanically limits accepted trade count.

The gate categories are already frozen:

- zero execution-integrity failures;
- sufficient accepted trades;
- presence across all four Apr-Jul OOF days;
- both LONG and SHORT accepted trades unless a strategy is explicitly
  one-sided by contract (none are);
- positive gross expectancy;
- positive primary net expectancy;
- profit factor above 1;
- positive majority of days;
- positive leave-one-day-out aggregate;
- bounded single-day PnL concentration;
- acceptable drawdown;
- positive/acceptable latency-stress behavior.

The numeric thresholds may not be chosen after T1 PnL is visible.

## 11. Multiplicity / anti-overfit control

All 32 T1 candidates form one family.

Primary control:

`BLOCK MAX-STAT BOOTSTRAP`

The statistic will be based on a common aligned economic return series.

Temporal dependence must be preserved with chronological blocks.

Provisional block duration:

`4 hours`

T0 support audit may change this only for a pre-PnL mechanical reason, such as
insufficient block count. It may not be selected based on candidate PnL.

Diagnostics, not simultaneous hard gates:

- Hansen SPA;
- White Reality Check;
- Deflated Sharpe Ratio;
- PBO/CSCV only if sample geometry is adequate.

## 12. Paired A0 analysis

In addition to the 32-candidate family screen, report exactly 16 paired effects:

`T01A - T01U ... T16A - T16U`

Required paired diagnostics:

- action count removed by A0;
- accepted trade count change;
- gross bps/trade delta;
- primary net bps/trade delta;
- total net delta;
- PF delta;
- drawdown delta;
- positive-day delta;
- paired block-bootstrap uncertainty.

This analysis answers whether A0 is economically useful as an opportunity gate
across distinct directional mechanisms.

It does not create 16 extra selectable candidates.

## 13. Ranking after eligibility

Only eligible candidates are ranked.

Priority:

1. minimum leave-one-day-out primary net expectancy;
2. median daily primary net;
3. pooled primary net expectancy;
4. stressed-cost net expectancy;
5. profit factor;
6. lower max drawdown;
7. lower positive-day concentration;
8. higher independent trade support;
9. lexical candidate ID.

Raw total PnL alone never determines the winner.

PnL/max-drawdown is a diagnostic/ranking metric after eligibility, not a pass
gate by itself.

## 14. T1 -> T2 promotion

T1 common execution is a fair signal-mechanism tournament.

At most four distinct core mechanisms may advance.

Paired U/A variants of the same core do not count as distinct mechanisms for
the four-core cap.

DEV044-T2 may then give finalists one separately frozen strategy-native exit
contract each.

T2 may not become a TP/SL/horizon grid search.

## 15. Replication / forward policy

Jan-Jul remains the development laboratory.

Apr-Jul is the official A0 OOF paired arena.

Before Sep-01+:

- obtain/identify an independent unused historical BTC block;
- replicate only a small frozen finalist set;
- freeze one champion or one fixed low-correlation portfolio.

Only then open Sep-01+.

Sep-01+ is confirmation only:

`CONFIRMED` or `NOT CONFIRMED`.

No champion selection is allowed after viewing Sep-01+.

## 16. Maker separation

Maker strategies are removed from DEV044.

They belong to a separate future family:

`DEV045-M`

DEV045-M requires a maker-feasibility audit covering:

- L2/L3 suitability;
- queue-position semantics;
- partial fills;
- order-entry/cancel latency;
- fill model;
- adverse selection;
- hftbacktest or equivalent replay validation.

No maker result may enter the DEV044 taker leaderboard.

## 17. T0 implementation requirements

Required code:

- deterministic strategy contract;
- 32-candidate registry;
- inclusive A0 threshold at 0.50;
- U/A parity wrapper;
- invalid-input fail-closed behavior;
- synthetic unit tests.

Before real T1 PnL:

1. T0 contract CI green;
2. A0 score replay/materialization implemented;
3. A0 metric identity test passes;
4. exact strategy feature materialization implemented;
5. no-PnL support/activity audit completed;
6. final numeric eligibility thresholds frozen;
7. block-bootstrap implementation synthetic-tested.

## 18. Current state

`DEV044_T0_CONTRACT_IMPLEMENTED_CI_PENDING_NO_REAL_DEV044_PNL`
