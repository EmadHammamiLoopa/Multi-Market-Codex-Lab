# DEV045 D6R26A P2 R19 — Once/day dense feature-cache builder preexecution

Parent R18 GREEN HEAD:

`e6aa3eabd3a34e4f0fff5fec0192624d1d65a941`

## Why R19 is required

R18 froze the consumer of the R17 shared dense cache, but intentionally did
not implement the production once/day cache builder.

Final R4 binding would therefore still have contained an unimplemented
callback.

R19 closes that gap without opening historical Jan-Jul data.

## Raw-pass rule

R19 performs exactly one sequential local raw-event pass for feature
extraction.

It uses:

- R13 local streaming decoder;
- R10 bounded rolling accumulator;
- R17 feed-bound requested one-second grid;
- R18 dense `[decision, 8 cases, 25 features]` cache shape.

It does not run the exchange-midpoint decoder because that stream is required
for labels, not for local feature-cache construction.

No one of the 40 lanes may rescan raw events for features.

## Important R17/R10 eligibility boundary

R17 freezes the requested one-second grid beginning at nominal
`day_start + 30s`.

P2 separately requires:

`VALID_LOCAL_BBO_AND_30S_CAUSAL_FEATURE_HISTORY_AT_DECISION_EPOCH`

Those conditions are not identical when the first actual complete book occurs
after nominal day start.

Example frozen into R19 CI:

- nominal day start = 0s;
- first complete local book = 1s;
- requested grid begins = 30s;
- 30s has only 29s actual causal history;
- first eligible epoch = 31s.

R19 does not create a 30s row and then silently drop it.

Instead:

- 30s is audited as a leading pre-candidate/preeligible requested epoch;
- cache construction begins at 31s;
- after the first eligible epoch, every remaining requested epoch must
  materialize successfully;
- any missing feature after eligibility begins is terminal failure.

This preserves P2's `MISSING_FEATURE_ROWS_DROPPED=False`.

## Dense cache

The final cache is:

- read-only NumPy;
- int64 decision timestamps;
- int64 best-bid/best-ask ticks;
- float64 values with shape `[N, 8, 25]`;
- exact R17 memory accounting;
- no raw source;
- no decoder;
- no book/flow history;
- no accumulator object.

Lane decision schedules are derived from the eligible cache itself, so a
preeligible requested epoch can never reach candidate simulation.

## Synthetic semantic parity

CI performs a single synthetic raw pass and proves all eight side × distance
feature vectors at 31s are numerically identical to the frozen R8B batch
reference.

It also proves phase-1 sequential decisions:

`31s, 36s, 41s, 46s`

remain exactly five seconds apart.

## Scope

R19 is PREEXECUTION ONLY.

It does not:

- open Jan-Jul;
- import/start the historical simulator;
- write the P2 attempt marker;
- write canonical historical labels;
- fit a model;
- calculate PnL;
- open August;
- open September+;
- open non-BTC data.

`P2_ATTEMPT_CONSUMED=False`.

After R19 GREEN, the remaining preauthorization layer is the final R4
execution binding. That layer can bind:

- R8A exact source verifier/open/close;
- R19 once/day feature-cache builder;
- lane schedules derived from the eligible shared cache;
- R15/R18 exact engine/materializer semantics;
- R16/R8A atomic partition publication;
- R4 stop-on-first-failure campaign state machine.

Historical execution remains separately unauthorized until that final binding
is also GREEN.
