# DEV044-T0B State Materialization Freeze

Status:

`DEV044_T0B_STATE_MATERIALIZATION_GREEN_FROZEN`

Date: 2026-09-03

## CI-validated implementation identity

`bb3f36d53d5ad98c7eb494d29ee486886d4ecc02`

This identity contains:

- causal strategy-state materializer;
- DEV032 raw-event adapter;
- synthetic/unit tests;
- dedicated CI wiring.

Subsequent commits on the branch are documentation/handoff only.

## CI verification

GitHub Actions run:

`33758413848`

Run number:

`1147`

Conclusion:

`success`

Relevant jobs:

- `dev044-t0-strategy-contract = success`
- `dev044-t0a-a0-oof = success`
- `dev044-t0b-state-materialization = success`

Follow-up runs #1148 and #1149 also completed successfully.

## Frozen T0B implementation

State materializer:

`src/multimarket/dev044_t0b_state_materializer.py`

Raw adapter:

`src/multimarket/dev044_t0b_raw_adapter.py`

Tests:

- `tests/test_dev044_t0b_state_materializer.py`
- `tests/test_dev044_t0b_raw_adapter.py`

## Frozen implementation semantics

- 250 ms causal grid.
- 32 s history.
- 4 s fast EMA tau.
- 32 s slow EMA tau.
- nearest-$100 BTC round-number state.
- prior-only 32 s state window excludes current row and has exactly 128 rows.
- inclusive 32 s return/RV window includes current row and has exactly 129 rows.
- no future state access.

DEV032 raw semantics are reused through the exact existing C++ extractor rather
than reimplemented.

Frozen mapped blocks:

- T09: S05/S06
- T12: S21
- T13: S30/S31
- T14: S32

## Remaining blockers

T10 remains fail-closed pending a frozen causal normalized-flow transform that
preserves the existing +/-0.05 strategy thresholds.

T16 remains fail-closed pending a canonical causal toxicity/VPIN lineage.

No T1 PnL is authorized while either blocker remains unresolved.

## Data guards

- DEV044 PnL unopened.
- Sep-01+ sealed.
- all non-BTC markets sealed.
- maker family remains separate.

## Next stage

`DEV044-T0C T10 NORMALIZED FLOW + T16 TOXICITY FEASIBILITY`

T0C remains NO-PNL.

Current state:

`DEV044_T0B_GREEN_FROZEN_T0C_BLOCKER_RESOLUTION_AUTHORIZED_NO_PNL`
