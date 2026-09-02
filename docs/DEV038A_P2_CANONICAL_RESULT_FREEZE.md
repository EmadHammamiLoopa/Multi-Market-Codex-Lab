# DEV038-A-P2 Canonical Result Freeze

Status: `CANONICAL_SUCCESS_CONTROLLER_SURVIVOR_C2_W720`

Date: 2026-09-03

Scientific execution commit:

`a1ac3ea806def0f38b8952295b68fab8eb18e3a1`

Canonical start UTC:

`2026-09-02T23:24:31Z`

Canonical end UTC:

`2026-09-02T23:24:45Z`

Permanent rule:

`DEV038-A-P2 MUST NEVER BE RERUN`

No second canonical attempt is permitted.

## Canonical artifact

Path:

`/home/emadh/Multi-Market/evidence/dev038a_p2_final_controller_correctness_v1/DEV038A_P2_FINAL_CONTROLLER_CORRECTNESS_RESULT.json`

SHA256:

`df32874a362cd75f646cdca483dc46956797431ac9a5861435639dfbf7f4b311`

Bytes:

`191547`

Canonical console log:

`/home/emadh/Multi-Market/evidence/dev038a_p2_canonical_console_v1.log`

Log SHA256:

`18c0357e518e2f1823a97f3bfdc9a6d2064d5f3b1d7342c94649dc904a695c4c`

Log bytes:

`715`

Canonical process:

- run RC = 0
- read-only verification RC = 0
- verification checks = 16 PASS / 0 FAIL
- git tree clean
- no staging residue

## Terminal result

`DEV038A_P2_CONTROLLER_SURVIVOR_FOUND`

Survivor ranking:

`['C2']`

Advanced controller:

`C2`

Frozen controller window:

`W720`

## Frozen integrated policy

The predictive policy frozen after DEV038-A-P2 is:

`A0 PRICE32 + BTC45 + S0 TOUCH_ONLY_SELECTIVE + W720 rolling q80 controller`

Frozen target:

- BTCUSDT
- horizon = 120 seconds
- barrier = 16 bps

Frozen controller semantics:

- score = p_touch
- prior-score-only rolling buffer
- window = 720
- quantile = 0.80
- method = higher
- current score excluded from its own threshold
- direction = frozen BTC45 sign

No further predictive search is permitted.

## C0 — W120 incumbent

- actions = 1100
- coverage = 0.19545131485429992
- correct = 112
- false = 988
- action precision = 0.10181818181818182
- correct-action rate = 0.01990049751243781
- false-action rate = 0.17555081734186212
- action-on-NONE fraction = 0.8163636363636364
- LONG = 455
- SHORT = 645

## C1 — W360

- actions = 1080
- coverage = 0.19189765458422176
- correct = 130
- false = 950
- action precision = 0.12037037037037036
- correct-action rate = 0.023098791755508174
- false-action rate = 0.16879886282871356
- action-on-NONE fraction = 0.7814814814814814
- LONG = 451
- SHORT = 629

Versus C0:

- Delta action precision = +0.018552188552188542
- Delta correct-action rate = +0.0031982942430703633
- Delta false-action rate = -0.006751954513148556
- Delta action-on-NONE fraction = -0.03488215488215496
- positive folds = 4/4
- all LOO positive = true
- joint max-stat q95 = 0.018830698287220025
- FWER p = 0.052
- survivor = false

C1 therefore failed the frozen survivor gate. In particular:

- practical DeltaPrecision threshold required >= +0.020 but observed
  +0.018552188552188542;
- observed DeltaPrecision did not exceed joint max-stat q95;
- FWER p = 0.052 > 0.05.

No post-hoc weakening is permitted.

## C2 — W720

- actions = 1104
- coverage = 0.19616204690831557
- correct = 141
- false = 963
- action precision = 0.12771739130434784
- correct-action rate = 0.025053304904051173
- false-action rate = 0.1711087420042644
- action-on-NONE fraction = 0.7635869565217391
- LONG = 472
- SHORT = 632

Versus C0:

- Delta action precision = +0.025899209486166017
- Delta correct-action rate = +0.005152807391613362
- Delta false-action rate = -0.004442075337597717
- Delta action-on-NONE fraction = -0.05277667984189727
- positive folds = 4/4
- all LOO positive = true
- joint max-stat q95 = 0.018830698287220025
- FWER p = 0.0155
- survivor = true

C2 passed the frozen survivor gates and is the only controller permitted to
advance.

Relative to W120, W720:

- increases action precision from 10.1818% to 12.7717%;
- increases correct-action rate from 1.9900% to 2.5053% of all rows;
- reduces false-action rate from 17.5551% to 17.1109%;
- reduces the fraction of actions occurring on true NONE from 81.6364% to
  76.3587%.

These are development correctness metrics, not profitability metrics.

## Joint temporal null

- seed = 20260903
- replicates = 1999
- max-stat q95 = 0.018830698287220025
- shift tuples = 1999
- max-null count = 1999
- all verification checks = PASS

## Predictive search closure

The frozen hard stop now applies.

No further:

- controller-window search;
- q-threshold search;
- opportunity representation search;
- feature search;
- model-family rescue;
- meta-filter rescue;
- BTC45 tuning;
- target-geometry tuning;
- Apr-Jul PnL optimization.

`PREDICTIVE SEARCH = CLOSED`

## Economic/forward guards

The canonical run explicitly preserved:

- PnL = not run
- fees = not run
- slippage = not run
- forward data = not opened

This result does not establish profitability.

## Mandatory next route

1. freeze untouched forward-confirmation protocol;
2. open only the predeclared untouched forward period;
3. evaluate the frozen integrated policy without tuning;
4. freeze the forward result;
5. then proceed to DEV038-B economic/execution falsification under a separately
   frozen cost/execution protocol.

Current state:

`DEV038A_P2_FROZEN_C2_W720_PREDICTIVE_SEARCH_CLOSED_FORWARD_CONFIRMATION_DESIGN_NEXT`
