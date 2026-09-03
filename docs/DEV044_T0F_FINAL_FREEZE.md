# DEV044-T0F Final Gate/Bootstrap Freeze

Status:

`DEV044_T0F_GREEN_FROZEN_T1_IMPLEMENTATION_AUTHORIZED`

Date: 2026-09-03

## Frozen implementation identity

`9100411e773b105f2d410e5bab08194313a387d3`

This commit contains:

- frozen mechanical viability gates;
- frozen accepted-trade support gates;
- frozen economic eligibility gates;
- frozen ranking order;
- frozen 32-candidate family identity;
- frozen 4h aligned block max-stat bootstrap;
- frozen bootstrap repetitions/seed/alpha;
- regression tests;
- fixture-only correction preserving count invariants.

The final correction changed tests only. No scientific threshold, gate, family,
cost, latency, block geometry, ranking rule, or bootstrap parameter changed.

## CI verification

GitHub Actions:

- run number: `1199`
- run id: `33780730827`
- conclusion: `success`

Relevant jobs:

- dev044-t0-strategy-contract = success
- dev044-t0a-a0-oof = success
- dev044-t0b-state-materialization = success
- dev044-t0c-flow-toxicity = success
- dev044-t0d-vpin-calibration = success
- dev044-t0e-support-audit = success
- dev044-t0f-gate-bootstrap = success

## Frozen mechanical gate

A candidate may be promoted only if:

- pooled active >= 100
- active >= 1 on each Apr-Jul day

Mechanically ineligible:

- T03U
- T03A
- T06U
- T06A
- T07U
- T07A
- T12A
- T13U
- T13A

Exactly 23 candidates are mechanically eligible for survivor consideration.

All 32 remain in the multiplicity family.

## Frozen accepted-trade gates

- pooled accepted trades >= 40
- accepted trades each day >= 5
- accepted LONG >= 10
- accepted SHORT >= 10
- execution-integrity failures = 0

## Frozen primary/stress economics

Primary round-trip cost:

`10 bp`

Cost stress:

`16 bp`

Primary latency:

- entry = 250 ms
- response = 250 ms

Latency stress:

- entry = 500 ms
- response = 500 ms

Required economic gates:

- primary net expectancy > 0
- primary PF >= 1.10
- >= 3/4 positive days
- all four leave-one-day-out primary expectancies > 0
- positive-day concentration <= 0.60
- max drawdown <= 320 bp
- 16bp cost-stress expectancy > 0
- 500/500ms latency-stress expectancy > 0

## Frozen multiplicity control

Primary family:

`all 32 candidates`

Aligned geometry:

- 4h UTC blocks
- 6 blocks/day
- 4 days
- 24 aligned blocks/candidate
- 24 x 32 joint block matrix

Bootstrap:

- centered null
- joint candidate resampling
- studentized mean block PnL
- 20,000 repetitions
- seed = 440044
- FWER alpha = 0.05

Candidate survivor requirement:

`FWER p <= 0.05`

## Frozen ranking

Only full survivors are ranked.

Priority:

1. minimum LOO primary net expectancy
2. median daily primary net
3. pooled primary net expectancy
4. 16bp stress-cost expectancy
5. primary PF
6. lower max drawdown
7. lower positive-day concentration
8. accepted-trade count
9. lexical candidate ID

Promotion cap:

`maximum 4 distinct core mechanisms`

## Permanent no-rescue rule

After T1 economics are opened, no post-hoc changes are allowed to:

- mechanical thresholds
- accepted-trade thresholds
- economic gates
- cost assumptions
- latency assumptions
- block length
- bootstrap repetitions
- bootstrap seed
- FWER alpha
- family membership
- ranking order

## Authorization

DEV044-T1 implementation and synthetic/unit CI are authorized.

No canonical T1 economic execution is authorized until:

1. T1 execution implementation is complete;
2. execution semantics are reconciled to prior H1800/B32 lineage;
3. synthetic/unit CI is green;
4. a separate T1 scientific execution identity is frozen.

Sep-01+ and non-BTC remain sealed.

## Current state

`DEV044_T0F_GREEN_FROZEN_T1_IMPLEMENTATION_AUTHORIZED_NO_T1_PNL_YET`
