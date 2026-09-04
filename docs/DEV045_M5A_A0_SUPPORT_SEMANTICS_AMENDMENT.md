# DEV045-M5A — A0 Support Semantics Amendment

Date: 2026-09-04

Status:

PRE-EXECUTION AMENDMENT /
NO HISTORICAL PNL OPENED /
NO HISTORICAL REPLAY EXECUTED

## Reason

DEV045 M5 froze the economic arena over seven BTCUSDT development days:

- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

The frozen DEV044 A0 OOF lineage provides legitimate validation support only
for Apr-01 through Jul-01.

No legitimate A0 prediction exists for Jan-01 through Mar-01.

This amendment freezes the missing-support semantics before any DEV045 M6
historical PnL is observed.

## Frozen A0 / legacy semantics

### Jan-Mar

A0/legacy adapter support is unavailable.

Official representation:

    available = FALSE
    p_touch = NONE
    legacy_state = NONE

M06 and M07 therefore use their already-frozen M3 base behavior.

Because frozen M3 returns ABSTAIN from its legacy-direction layer when
legacy_state is None, this means:

    M06 unavailable behavior == M02
    M07 unavailable behavior == M02

No new fallback strategy is introduced.

### Apr-Jul

The directional adapter may be used only when joint support exists:

    available =
        exact A0 timestamp support
        AND
        causal legacy StrategyState available

If either component is unavailable:

    available = FALSE
    p_touch = NONE
    legacy_state = NONE

No half-valid adapter state is allowed.

## Prohibited transformations

No:

- A0 refit
- A0 retraining
- interpolation
- probability forward-fill
- backward-fill
- synthetic probability
- future information
- nearest-neighbor timestamp substitution
- cross-day probability carry
- Jan-Mar imputation

An exact-support miss remains unavailable.

## M3 compatibility boundary

Frozen M3 is not modified.

Its MarketState currently requires numeric `a0_p_touch`.

For an unavailable M5A support object, the compatibility boundary may pass:

    legacy_state = None
    a0_p_touch = 0.0

The numeric 0.0 is a NON-SEMANTIC COMPATIBILITY SENTINEL only.

It is NOT:

- a prediction
- an observation
- an imputation
- a synthetic p_touch
- an A0 diagnostic value

The authoritative M5A state remains:

    available = FALSE
    p_touch = NONE
    legacy_state = NONE

## Clock semantics

Two clocks are explicitly distinct.

### MARKET EVENT

A market event may:

- update book state
- update queue state
- process fills
- process latency
- process order lifecycle

A market event MUST NOT by itself manufacture, interpolate, carry, or
re-evaluate A0 support.

A market event is not automatically a policy-decision epoch.

### POLICY DECISION EPOCH

Only an explicitly designated policy-decision epoch may evaluate M01-M08.

For M06/M07 at that epoch:

- use the adapter only on exact valid joint support;
- otherwise use the frozen unavailable fallback semantics.

Between policy-decision epochs, an already-issued order remains subject to
the normal frozen M4 lifecycle.

That persistence is NOT forward-fill of p_touch.

No previous probability is carried into a later epoch.

## Decision-epoch cadence

M5A freezes clock separation and exact-support semantics.

M5A does NOT invent a new policy-decision cadence.

The historical event-loop contract must bind its decision cadence separately
to already-authorized causal lineage before historical execution.

Until that contract is frozen, MARKET EVENT != POLICY DECISION EPOCH.

## Frozen experiment family

Unchanged:

- M01-M08
- 8 policies
- 7 development days
- 6 UTC four-hour blocks/day
- 42 blocks/policy/scenario
- primary Q0 250/250ms
- stress Q0 500/500ms
- 20,000 centered joint max-stat bootstrap repetitions
- seed 450045
- FWER alpha 0.05
- all M5 promotion gates

M3 blob remains unchanged.

M4 blob remains unchanged.

M5 preregistration remains unchanged except for this explicit pre-execution
missing-support amendment.

## Diagnostic-only adapter increment

After historical execution, the following paired Apr-Jul quantities may be
reported:

    M06 - M02
    M07 - M02

These are frozen as:

    DIAGNOSTIC_ONLY = TRUE
    PROMOTION_GATE = FALSE
    MODEL_SELECTION = FALSE
    RESCUE_AUTHORIZATION = FALSE

They cannot change survivor eligibility, promotion, model selection, or
authorize rescue/tuning.

## Execution prohibition

M5A itself performs no:

- historical file I/O
- historical replay
- economic arena execution
- PnL computation
- canonical PnL write
- Railway access
- network acquisition
- live/testnet/paper trading
