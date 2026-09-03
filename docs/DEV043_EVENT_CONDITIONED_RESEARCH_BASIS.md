# DEV043 — Event-Conditioned Decomposition Research Basis

Status:

`FROZEN_RESEARCH_BASIS_BEFORE_ANY_DEV043_REAL_RESULT`

Date: 2026-09-03

## Motivation from frozen internal evidence

DEV041 established strong executable oracle headroom for:

`H1800_B32`

DEV042 then showed that a direct three-class predictor:

- LONG_FIRST
- SHORT_FIRST
- NONE

did not recover that headroom predictively.

DEV042 common OOF target prevalence was:

- NONE = 0.5135968092820885
- LONG_FIRST = 0.2496374184191443
- SHORT_FIRST = 0.23676577229876722

The strongest DEV042 economic representation was:

`C2_PRESSURE_CAPACITY_LOGIT`

with:

- mean gross = +2.5357003777301026 bps/trade
- C1 mean net = -7.4642996222698965
- C2 mean net = -13.464299622269898
- C2 positive folds = 0/4
- FWER p = 0.274

Thus the direct three-class formulation failed to convert oracle headroom into
deployable economic value.

Earlier project evidence also showed that separating touch/opportunity from
direction can add predictive value:

- a dedicated touch/opportunity stage was previously retained;
- BTC45 direction added genuine conditional composition value over the older
  direction layer;
- selective touch gating improved correctness operationally even when full
  economic viability later failed.

DEV043 therefore tests a genuinely different factorization:

`P(TOUCH, DIRECTION) = P(TOUCH) * P(DIRECTION | TOUCH)`

rather than fitting one three-class decision boundary.

## External research rationale

Recent research on financial prediction increasingly separates:

- whether a meaningful movement/event occurs;
- which direction follows conditional on that event.

This is closely related to hurdle/two-stage classification and competing-risk
or first-passage formulations.

The practical rationale is that movement occurrence can depend strongly on
liquidity state, volatility, pressure, and fragility, while conditional
direction may depend on a different information set.

Order-flow and order-book studies also support separating directional pressure
from liquidity/absorption state rather than assuming one feature family solves
both questions.

## DEV043 research question

Primary question:

> Does decomposing H1800/B32 into event occurrence and conditional direction
> recover predictive-economic alignment that the direct three-class DEV042
> formulation did not?

Secondary diagnostic questions:

1. Is TOUCH/NONE materially predictable OOF?
2. Is LONG/SHORT materially predictable conditional on actual TOUCH rows?
3. If both components survive independently, does their frozen composition
   retain positive executable C2 economics?

## Non-rescue boundary

DEV043 is not permitted to:

- reuse failed DEV042 three-class scores and retune thresholds;
- add a sixth DEV042 model;
- tune DEV042 HGB;
- weaken DEV042 cost assumptions;
- change H1800/B32;
- reinterpret DEV042 failure.

DEV042 remains permanently closed.

DEV043 is a separately preregistered factorized probability model.

## Forward reserve

Sep-01+ remains sealed.

All non-BTC markets remain sealed.
