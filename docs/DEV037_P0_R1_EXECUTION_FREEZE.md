# DEV037-P0-R1 Execution Freeze

Status: `EXECUTION_FROZEN_SINGLE_COVERAGE_ONLY_CANONICAL_R1_NEXT`

Date: 2026-09-02

Scientific implementation commit:

`6f2a65423fe0b70fc82b1558ff49aa2ef87a9256`

Dedicated CI:

- workflow run = `33685557434`
- workflow conclusion = SUCCESS
- job = `dev037-p0-r1-coverage`
- pytest = SUCCESS
- harness smoke = SUCCESS

The previous failing run was caused only by a wrong synthetic test expectation
for q80 under method="higher". Production controller logic was unchanged.

## Frozen R1 controller candidates

Exactly:

- W120
- W360
- W720

No other window is permitted.

## Frozen threshold rule

At decision t:

`threshold_t = q80(prior_scores_only, method="higher")`

Rules:

- current score is never included in its own threshold;
- rolling reference uses only scores observed before t;
- warm-start uses only prior OOF training scores;
- target coverage = 0.20;
- no validation label is used.

## Frozen six policy score streams

- S0 TOUCH_ONLY_SELECTIVE
- S1 DIRECTION_CONFIDENCE_SELECTIVE
- S2 PRODUCT_JOINT_SELECTIVE
- S3 BALANCED_MIN_PERCENTILE
- S4 GEOMETRIC_BALANCED_PERCENTILE
- S5 META_CORRECTNESS_FILTER

R1 changes only threshold transport.

## Frozen operational ranking

A controller must be feasible across all 24 policy-fold combinations.

Ranking:

1. smallest mean absolute coverage deviation from 0.20;
2. smallest worst absolute coverage deviation;
3. smallest mean absolute 60-row rolling coverage error;
4. fewest rolling60 windows outside [0.10,0.30];
5. smaller window.

No correctness metric is allowed.

## Canonical R1 output reserved

Directory:

`/home/emadh/Multi-Market/evidence/dev037_p0_r1_adaptive_coverage_controller_v1`

Artifact:

`DEV037_P0_R1_ADAPTIVE_COVERAGE_CONTROLLER_RESULT.json`

From the canonical R1 start marker:

`DEV037-P0-R1 MUST NEVER BE RERUN`

even if the attempt fails.

## Strict prohibitions

R1 must not calculate or inspect:

- validation action precision;
- validation correct action count;
- validation false action count;
- challenger-vs-S0 correctness deltas;
- temporal null;
- policy survivor classification;
- PnL;
- fees;
- slippage;
- position sizing;
- leverage;
- forward holdout.

Current state:

`DEV037_P0_R1_EXECUTION_FROZEN_SINGLE_COVERAGE_ONLY_CANONICAL_RUN_NEXT`
