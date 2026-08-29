# CODEX-EXP-022-P1 Frozen Result

Status: **INVALID**

Date: 2026-08-29

Experiment ID:

`CODEX-EXP-022-P1`

Preregistration commit:

`73feafca0b1f901b10d2856b07c3058462f1cfff`

Frozen implementation commit:

`0a86f2440d44a7969cd640ecca830b07a4350e00`

Prospective grid SHA-256:

`cf3a7291bc54a819e6b619badfcd01db10d4330566d0c3d8d3f16f204b7988ad`

## Official adjudication

`CODEX-EXP-022-P1 = INVALID`

No prospective ranking PASS or FAIL claim is permitted from this
experiment.

## Failure

The frozen one-shot implementation completed the analytical execution
path but failed while serializing the final result payload.

Observed exception:

`TypeError`

The failing payload field was:

`invariants.common_support_unique_and_chronological`

The invariant expression propagated a NumPy boolean scalar from
`numpy.all(...)`.

This had two implementation consequences:

1. the NumPy boolean was not JSON serializable under the frozen runtime;
2. the frozen invariant aggregation used identity checks of the form
   `value is True`, so a true NumPy boolean would not satisfy that check.

Therefore the defect affected both result serialization and frozen
status adjudication.

## Analytical-opening state

The traceback occurred in `_write_once()` after `_execute_once()` had
returned its payload.

Therefore, before the failure:

- P0 audit verification had completed;
- prospective grid opaque authorization had completed;
- Jan-Jul historical preparation had completed;
- the fixed historical model had been fit;
- the prospective Aug-28 grid had been analytically parsed;
- the prospective target had been constructed;
- prospective model probabilities had been calculated;
- ranking metrics and the temporal-shift procedure had been calculated;
- a final payload had been constructed in memory.

No final result artifact was successfully serialized.

## Researcher observation state

No prospective AUC, AP, lift, temporal-null result, or other scientific
metric was displayed or observed before the failure.

Therefore no outcome-dependent model, feature, threshold, support, or
protocol modification occurred.

Nevertheless, 2026-08-28 is analytically consumed and may never again be
described or used as an independent prospective holdout.

## Attempt history

Attempt 1 terminated because the interactive terminal closed before a
result artifact existed.

Attempt 2 used the exact frozen implementation and protocol in detached
execution. It reached the result-serialization stage and exposed the
implementation defect documented above.

No third execution of CODEX-EXP-022-P1 is permitted.

## Scientific consequence

EXP022-P1 provides no evidence for or against the prospective volatility
ranking hypothesis.

The next independent confirmation requires:

- an implementation-only correction frozen before new prospective data;
- a new Experiment ID;
- a genuinely fresh prospective validation day.

Any later use of the consumed 2026-08-28 data is diagnostic only and
cannot establish prospective confirmation.
