# CODEX-EXP-008-P0 Execution Status

Status: `ABORTED_INCOMPLETE_CONNECTIVITY`

Date: 2026-08-26

Frozen experiment head:

`2b7132b9cd902df631afb42dd12bdd057a2ec12b`

## Reason

The frozen EXP008-P0 options-surface acquisition did not complete under an unstable network connection that had become unsuitable for multi-gigabyte historical options-chain acquisition while the user was on metered mobile data.

The provider client had repeatedly restarted the first frozen daily file (`2026-03-01`) after network stalls. When a manual SIGINT was subsequently attempted, the recorded EXP008 process no longer existed, and the experiment directory contained no completed raw daily file, acquisition manifest, or audit artifact. Therefore the exact final client-side termination path is not inferred beyond the observed incomplete network/acquisition state.

No complete March raw artifact had been promoted from staging.

## Scientific adjudication

This is **not** a `FAIL_OPTIONS_SURFACE_DATA_NOT_READY` result and is **not** evidence against the options-surface hypothesis.

The experiment did not complete its frozen acquisition protocol and therefore produced no valid P0 readiness adjudication.

It must not be interpreted as predictive failure, data-readiness failure, or invalidation of the surface family.

## Guards at termination

- sealed August opened: false
- target scored: false
- future return inspected: false
- model fit: false
- AUC scored: false
- direction scored: false
- PnL scored: false

## Future use

Do not resume or restart CODEX-EXP-008-P0 as though it were the same one-shot execution.

A future return to the options-surface question requires either:

1. a separately preregistered acquisition-replication experiment with a robust acquisition protocol, or
2. another venue/source under a new Experiment ID.

Any incomplete staging bytes from the aborted run are non-scientific partial downloads and must never be treated as frozen raw source artifacts.
