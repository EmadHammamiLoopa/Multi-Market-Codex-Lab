# DEV045-M5B — Multi-Rate Decision Clock Amendment

Date: 2026-09-04

Status:

PRE-EXECUTION CLOCK SEMANTICS /
NO HISTORICAL REPLAY /
NO HISTORICAL PNL

## Discovery

DEV045-M2 explicitly froze:

    Decision cadence = 1 second

and:

    At each 1-second decision:
      maintain / keep / cancel / replace quotes.

Separately, frozen DEV030/DEV042/DEV043 A0 lineage uses exact-minute
decision support:

    DECISION_STEP_US = 60_000_000

and DEV042 materialization explicitly selects:

    exact_minute_decision_indices(...)

Therefore frozen A0 probability support is not a continuous one-second state.

It is an exact-minute support stream.

This mismatch was identified before any DEV045 historical maker PnL.

## Problem

The naive combination:

    maker decision every 1 second
    +
    A0 exact-support-only

would produce:

    minute boundary:
        adapter may act

    next second:
        no A0 row
        fallback M02

This would turn a sparse minute-level legacy predictor into a one-second pulse
and could manufacture quote churn not present in the source predictor lineage.

M5B forbids that interpretation before historical execution.

## Frozen clocks

Three clocks are distinct.

### 1. MARKET EVENT CLOCK

Driven by replay events.

It may:

- update order book;
- update queue;
- process trades/fills;
- process latency;
- process order responses.

A market event does not automatically evaluate a policy.

### 2. BASE MAKER / RISK CLOCK

Frozen M2 authority:

    cadence = 1 second

M5B resolves the deterministic phase as exact UTC second boundaries:

    timestamp_us % 1_000_000 == 0

This clock governs normal maker maintenance and risk controls.

The 60-second unresolved-inventory timeout remains authoritative and is checked
through this base/risk clock.

### 3. LEGACY ADAPTER CLOCK

For M06/M07 only.

The source A0 lineage is exact-minute.

Adapter candidate epochs are therefore exact UTC minute boundaries:

    timestamp_us % 60_000_000 == 0

on Apr-Jul only.

This is a strict subset of the one-second maker clock.

## Jan-Mar

There is no legitimate A0 OOF support.

Therefore:

    adapter enabled = FALSE

for the entire day.

M06/M07 remain their frozen M02-equivalent base behavior.

## Apr-Jul adapter semantics

At an exact adapter candidate minute:

    exact A0 support
    AND
    causal legacy state
        -> APPLY_ADAPTER

If the exact minute is an adapter candidate but either component is missing:

        -> FALLBACK_TO_M02

At a one-second maker epoch that is NOT an adapter candidate minute:

        -> NO_ALPHA_UPDATE

NO_ALPHA_UPDATE is not the same as unavailable A0.

It does not:

- call A0;
- invent p_touch;
- forward-fill p_touch;
- interpolate p_touch;
- clear the adapter solely because no A0 row exists at that second.

An already-issued order may remain through its normal M4 lifecycle unless
ordinary maker/risk/safety maintenance requires another action.

Order persistence is not probability persistence.

## No probability carry

No previous p_touch value may be stored as the probability for a later second.

Between adapter epochs:

    p_touch = NONE

for the support layer.

The system may retain only ordinary execution/policy lifecycle state such as
the already-issued working order.

## Exact support failure at a minute epoch

If an Apr-Jul exact-minute adapter candidate epoch has no legitimate A0 score
or no causal legacy state:

    FALLBACK_TO_M02

The prior adapter must not be rescued by carrying the previous probability.

## M5A relationship

M5A remains frozen.

M5B resolves only the clock-rate ambiguity discovered after M5A:

- M5A exact joint-support semantics remain authoritative;
- M5A no-refit/no-interpolation/no-forward-fill rules remain authoritative;
- M5B defines when exact joint support is supposed to be queried.

## Unchanged experiment family

No change to:

- M01-M08;
- eight-policy multiplicity family;
- seven development days;
- 42 blocks/policy/scenario;
- primary/stress latency;
- fees;
- bootstrap repetitions;
- seed;
- FWER alpha;
- promotion gates.

M3 remains unchanged.

M4 remains unchanged.

M5 remains unchanged except for explicit pre-execution M5A/M5B semantics.

## Diagnostic-only rule

Apr-Jul:

    M06 - M02
    M07 - M02

remains diagnostic only.

It cannot promote, rescue, rank, or retune a policy.

## Execution prohibition

M5B itself performs no:

- historical data read;
- A0 replay/refit;
- historical strategy replay;
- economic arena execution;
- PnL computation;
- canonical result write;
- Railway access;
- network acquisition;
- live/testnet/paper trading.
