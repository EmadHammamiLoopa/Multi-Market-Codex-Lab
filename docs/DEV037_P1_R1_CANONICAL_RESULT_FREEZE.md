# DEV037-P1-R1 Canonical Result Freeze

Status: `CANONICAL_SUCCESS_NO_CHALLENGER_SURVIVOR_RETAIN_S0`

Date: 2026-09-02

Scientific execution commit:

`25221269bee4681916af663b668cf1f4446a3294`

Canonical artifact:

`/home/emadh/Multi-Market/evidence/dev037_p1_r1_four_policy_w120_correctness_v1/DEV037_P1_R1_FOUR_POLICY_W120_CORRECTNESS_RESULT.json`

Artifact SHA256:

`9a9ade5fbc9e564f192786e75551277174907afad26c76a927099e7d859f0cee`

Artifact bytes:

`236045`

Canonical console:

`/home/emadh/Multi-Market/evidence/dev037_p1_r1_canonical_console_v1.log`

Canonical contract:

- 14 PASS
- 0 FAIL
- process exit = 0
- read-only verification = PASS
- staging residue = none
- git tree clean

Permanent rule:

`DEV037-P1-R1 MUST NEVER BE RERUN`

## Terminal result

`DEV037_P1_R1_NO_CHALLENGER_SURVIVOR_RETAIN_S0`

Advanced policy:

`S0 TOUCH_ONLY_SELECTIVE`

Controller:

`W120`

Survivor ranking:

`[]`

No challenger advanced.

## Pooled policy results

### S0 — TOUCH_ONLY_SELECTIVE

- actions = 1100
- coverage = 0.19545131485429992
- correct actions = 112
- false actions = 988
- action precision = 0.10181818181818182
- correct actions / all rows = 0.01990049751243781
- false actions / all rows = 0.17555081734186212
- LONG actions = 455
- SHORT actions = 645
- LONG precision = 0.13626373626373625
- SHORT precision = 0.07751937984496124
- direction accuracy among acted true-TOUCH rows = 0.5544554455445545
- fraction actions on true NONE = 0.8163636363636364

Fold action precision:

- Apr = 0.0875
- May = 0.056910569105691054
- Jun = 0.08191126279863481
- Jul = 0.16510903426791276

### S1 — DIRECTION_CONFIDENCE_SELECTIVE

- actions = 1124
- coverage = 0.19971570717839374
- correct = 83
- false = 1041
- action precision = 0.07384341637010676
- correct action rate = 0.014747690120824448

Vs S0:

- DeltaPrecision = -0.027974765448075062
- DeltaCorrectRate = -0.005152807391613362
- positive folds = 0/4
- all LOO positive = false
- FWER p = 1.0
- survivor = false

### S2 — PRODUCT_JOINT_SELECTIVE

- actions = 1085
- coverage = 0.1927860696517413
- correct = 106
- false = 979
- action precision = 0.09769585253456221
- correct action rate = 0.018834399431414357

Vs S0:

- DeltaPrecision = -0.004122329283619608
- DeltaCorrectRate = -0.0010660980810234533
- positive folds = 2/4
- all LOO positive = false
- FWER p = 0.953
- survivor = false

### S5 — META_CORRECTNESS_FILTER

- actions = 1090
- coverage = 0.19367448471926083
- correct = 108
- false = 982
- action precision = 0.09908256880733946
- correct action rate = 0.019189765458422176

Vs S0:

- DeltaPrecision = -0.0027356130108423665
- DeltaCorrectRate = -0.0007107320540156344
- positive folds = 1/4
- all LOO positive = false
- FWER p = 0.88
- survivor = false

## Joint temporal null

- seed = 20260902
- replicates = 1999
- joint max-stat q95 = 0.013283726949207375
- all null contract checks = PASS

No challenger exceeded the frozen joint null threshold while also satisfying
the practical and fold-stability gates.

## Interpretation

The result does not invalidate the upstream forecasting components.

It establishes that, under the frozen W120 live-compatible selective controller,
none of S1, S2, or S5 improves action correctness over S0 robustly enough to be
promoted.

S0 is retained because it is the simplest operational policy and the frozen
terminal contract explicitly advances S0 when no challenger survives.

This is not yet evidence of economic profitability.

The low exact first-passage action precision and high action-on-NONE fraction
make DEV038 an economic falsification stage, not a presumed-profit stage.

## Forbidden activities remained false

- no fees
- no slippage
- no PnL
- no leverage
- no position sizing
- no forward data
- no W360/W720 correctness
- no S3/S4 correctness

## Next stage

DEV038 must be a separately frozen economic/execution protocol for S0 + W120
only.

The protocol must define before any PnL is observed:

- entry timestamp / execution delay;
- executable entry price;
- take-profit / stop-loss / horizon exit;
- treatment of NONE events;
- overlap / concurrent-signal handling;
- transaction-cost model;
- slippage model;
- gross and net return calculation;
- risk metrics;
- position sizing used for evaluation;
- promotion/failure gates.

No final forward holdout should be opened until the economic protocol is frozen.

Current state:

`DEV037_P1_R1_FROZEN_RETAIN_S0_DEV038_ECONOMIC_PROTOCOL_DESIGN_NEXT`
