# DEV044-T0A A0 OOF Replay Freeze

Status:

`DEV044_T0A_A0_REPLAY_GREEN_FROZEN`

Date: 2026-09-03

## Implementation identity

CI-validated implementation commit:

`d6d7a95ac4c6edb5fd9f6a9d5d75f0698f6e726e`

Core implementation:

`src/multimarket/dev044_t0a_a0_oof.py`

Tests:

`tests/test_dev044_t0a_a0_oof.py`

## CI

GitHub Actions run:

`33757255274`

Run number:

`1136`

Conclusion:

`success`

Dedicated job:

`dev044-t0a-a0-oof = success`

Subsequent documentation-only runs through #1138 also completed successfully.

## Frozen replay contract

The DEV044 A0 replay:

- verifies the frozen DEV043-A artifact identity;
- replays A0_TOUCH_PRICE_LOGIT only;
- uses the frozen Apr-Jul OOF folds;
- performs no A1/A2 fit;
- performs no DEV043-A joint null;
- performs no survivor selection;
- writes no DEV043 artifact;
- requires exact frozen A0 metric reproduction at absolute tolerance 1e-12;
- emits a deterministic support hash and score hash for DEV044 use.

A0 gate remains:

`p_touch >= 0.50`

No threshold search is authorized.

## Data/economic state

No DEV044 PnL has been run.

Sep-01+ remains sealed.

All non-BTC markets remain sealed.

## Next authorized stage

`DEV044-T0B CAUSAL STRATEGY-STATE MATERIALIZATION + DEV032 RAW ADAPTER`

T0B remains NO-PNL.

Current state:

`DEV044_T0A_GREEN_FROZEN_T0B_STATE_MATERIALIZATION_AUTHORIZED_NO_PNL`
