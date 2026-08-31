# CODEX-EXP-027-P0 Readiness

Status: **IMPLEMENTATION_READY_FOR_DEPLOYMENT**

Experiment ID: `CODEX-EXP-027-P0`

Preregistration commit:

`4737d9553981469746d32383da448c02551d2e42`

Validated implementation commit:

`89dfd73977740f4d2cb6a36d4c20de3546699bec`

Validation summary:

- focused EXP027 collector tests: 11 passed
- EXP025 + EXP027 regression: 44 passed, 9 subtests passed
- expanded EXP025/EXP027/archive/finalizer: 53 passed, 9 subtests passed
- Python compile checks: PASS
- full repository regression excluding the known unrelated optional-xgboost collection test:
  610 passed, 127 subtests passed, 3 FutureWarnings
- git diff --check: PASS
- working tree: clean

Known unrelated environment limitation:

`tests/test_v23_phase0dk_nonlinear.py` cannot collect in the current local
environment because optional dependency `xgboost` is intentionally not
installed. No EXP027 code imports or depends on that module.

Readiness adjudication:

`EXP027_P0_IMPLEMENTATION_READY_FOR_DEPLOYMENT`

Deployment constraints:

- deploy as a NEW Railway service
- do not modify or redeploy the healthy EXP025 `abundant-love` collector
- use a separate 5 GB staging volume
- connect the existing private Railway Bucket through variable references
- first deployment day is partial if deployment begins after 00:00 UTC
- do not stop EXP025 until at least one completed EXP027 hourly chunk has:
  - closed successfully
  - uploaded successfully
  - exact remote byte size verified
  - exact SHA-256 metadata verified
  - immutable hourly archive manifest created
  - local staging raw deleted only after all verification
  - no operational-failure marker

This readiness result is operational/infrastructure-only. It makes no
predictive or profitability claim.
