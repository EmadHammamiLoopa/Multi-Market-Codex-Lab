# DEV045-M5A A0 Support Semantics Handoff

Date: 2026-09-04

## Status

PRE-EXECUTION SUPPORT SEMANTICS FROZEN

Local contract verification:

- 222 M5A tests passed
- 18 frozen M3 regression tests passed
- M3 blob unchanged
- M4 blob unchanged
- M5 preregistration blob unchanged
- M5 fee amendment blob unchanged
- historical data not opened
- historical replay not executed
- historical PnL not computed

## Parent

`4a6c4226d35856b6a1c8d6214813799feed7ccb2`

## Problem closed by M5A

The frozen M5 arena contains 7 BTCUSDT development days, Jan-Jul.

The legitimate frozen DEV044 A0 OOF validation support exists only on:

- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

No legitimate A0 OOF probability exists for Jan-Mar.

M5A freezes the missing-support semantics before any M6 historical PnL.

## Jan-Mar semantics

For Jan-Mar:

    available = FALSE
    p_touch = NONE
    legacy_state = NONE

M06 and M07 therefore use their already-existing frozen M3 base behavior.

Contract tests establish field-wise behavioral identity:

    M06(unavailable) == M02
    M07(unavailable) == M02

across inventories from -0.003 to +0.003, multiple depth states,
inventory-age states below and at/above the 60-second flatten threshold,
and terminal forced-flatten behavior.

## Apr-Jul joint support

The adapter is available only when BOTH are true:

1. an exact legitimate A0 timestamp exists;
2. a causal legacy StrategyState exists.

Otherwise the entire adapter support object is unavailable.

No half-valid state is permitted.

## Probability semantics

Forbidden:

- refit
- retraining
- interpolation
- forward-fill
- backward-fill
- nearest-neighbor substitution
- synthetic probability
- future data
- cross-day carry

Frozen M3 still requires numeric `a0_p_touch`.

At the compatibility boundary only:

    legacy_state = None
    a0_p_touch = 0.0

The `0.0` value is a non-semantic sentinel.

It is not an A0 prediction, observation, imputation, or diagnostic value.

## Clock semantics

MARKET EVENT and POLICY DECISION EPOCH are separate clocks.

A market event may update:

- order book
- queue state
- fills
- latency
- order lifecycle

A market event does NOT automatically trigger policy reevaluation and
does NOT manufacture A0 support.

Only a designated POLICY DECISION EPOCH may evaluate M01-M08.

For M06/M07:

- exact joint support -> adapter may act;
- no exact joint support -> frozen M02-equivalent base behavior.

An order created at a decision epoch may persist naturally through the
frozen M4 lifecycle until a later maintenance epoch.

Order persistence is not probability forward-fill.

No previous p_touch value may be carried into a later decision epoch.

## Decision cadence

M5A freezes clock separation.

It does NOT invent a new decision cadence.

The upcoming historical event-loop contract must bind the decision cadence
to authorized causal lineage before historical execution.

## Frozen M5 family remains unchanged

- 8 policies
- 7 development days
- 6 four-hour UTC blocks/day
- 42 blocks/policy/scenario
- primary Q0 250/250ms
- stress Q0 500/500ms
- 20,000 centered joint max-stat bootstrap repetitions
- seed 450045
- FWER alpha 0.05
- original promotion gates

## Diagnostic-only comparison

After historical execution, paired Apr-Jul differences may be reported:

    M06 - M02
    M07 - M02

Frozen semantics:

    DIAGNOSTIC_ONLY = TRUE
    PROMOTION_GATE = FALSE
    MODEL_SELECTION = FALSE
    RESCUE_AUTHORIZATION = FALSE

These diagnostics cannot change survivor selection.

## Next gate

After dedicated M5A CI is green:

1. freeze historical policy-decision cadence;
2. implement actual historical event-loop driver;
3. structural and synthetic validation only;
4. verify immutable Jan-Jul raw provenance;
5. reread M5/M5A/M6 preregistration and handoffs;
6. only then execute the first one-shot M6 historical arena.

The first historical output is evidence and cannot authorize tuning or rerun.
