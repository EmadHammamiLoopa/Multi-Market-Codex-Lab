# DEV032-E1A Scientific Execution Freeze

Status: `EXECUTION_FROZEN_NO_REAL_RUN_YET`

Frozen scientific execution commit:

`d37d4b4b7e409a6f4ffe5a31cd83ad1abbc35ede`

Frozen branch:

`research/dev032-e1a-execution-frozen`

CI evidence:

- workflow run: `33631272795`
- head: `d37d4b4b7e409a6f4ffe5a31cd83ad1abbc35ede`
- conclusion: `SUCCESS`
- `dev032-e1a-feature-core`: SUCCESS
- `dev031-p0-audit`: SUCCESS
- `dev031-p0a-audit`: SUCCESS
- `dev031-p1a-materialization`: SUCCESS
- `dev031-p1b-incremental`: SUCCESS
- `p10-transform`: SUCCESS
- unit tests Python 3.10: SUCCESS
- unit tests Python 3.12: SUCCESS

## Frozen scientific files

The execution commit freezes these scientific inputs:

- `docs/DEV032_E0_CANDIDATE_CENSUS.md`
- `docs/DEV032_E0_CANDIDATE_REGISTRY.md`
- `docs/DEV032_E1_WAVE1_SCREEN_DRAFT.md`
- `docs/DEV032_E1A_STRATEGY_FORMULAS.md`
- `src/multimarket/dev032_e1a_feature_core.py`
- `src/multimarket/dev032_e1a_materialize.py`
- `tools/dev032_e1a_raw_features.cpp`
- `src/multimarket/dev032_e1a_runner.py`
- `tests/test_dev032_e1a_feature_core.py`
- `tests/test_dev032_e1a_materialize.py`
- `tests/test_dev032_e1a_raw_extractor.py`
- `tests/test_dev032_e1a_runner.py`
- `.github/workflows/test.yml`

No scientific code change is permitted after the canonical E1A materialization
run begins. Any material change requires a new experiment/version.

## Frozen task

- symbol: BTCUSDT
- historical development period: Jan-Jul 2026 only
- task: T1 DIRECTION_GIVEN_TOUCH
- target: A
- horizon: 120 s
- barrier: 16 bp
- causal information window: 32 s
- exact frozen support: 1,374 rows
- LONG: 684
- SHORT: 690
- strategies: S00-S35, exactly 36
- raw-derived S04-S35 columns: 278

## Forward guards

Must remain false:

- Aug-01 opened
- Aug-30 opened
- Sep-01+ opened
- Railway opened
- market-raw-archive opened
- abundant-love opened
- downloads/acquisition
- predictive fit
- predictive metrics
- PnL

## Canonical output

The canonical directory is:

`/home/emadh/Multi-Market/evidence/dev032_e1a_wave1_materialization_v1`

Before execution it MUST NOT exist.

After one valid canonical artifact is written, DEV032-E1A MUST NEVER be rerun.

## Required local preflight before execution

Run from the local worktree:

```bash
cd /mnt/c/Users/emadh/Downloads/market-exp026

git fetch origin
git checkout research/dev032-e1a-execution-frozen
git reset --hard d37d4b4b7e409a6f4ffe5a31cd83ad1abbc35ede

echo "HEAD=$(git rev-parse HEAD)"
echo "DIRTY_COUNT=$(git status --porcelain | wc -l)"

test "$(git rev-parse HEAD)" = "d37d4b4b7e409a6f4ffe5a31cd83ad1abbc35ede"
test -z "$(git status --porcelain)"
test ! -e /home/emadh/Multi-Market/evidence/dev032_e1a_wave1_materialization_v1

python -m pytest -q   tests/test_dev032_e1a_feature_core.py   tests/test_dev032_e1a_materialize.py   tests/test_dev032_e1a_raw_extractor.py   tests/test_dev032_e1a_runner.py

sha256sum   docs/DEV032_E1A_STRATEGY_FORMULAS.md   src/multimarket/dev032_e1a_feature_core.py   src/multimarket/dev032_e1a_materialize.py   tools/dev032_e1a_raw_features.cpp   src/multimarket/dev032_e1a_runner.py   tests/test_dev032_e1a_feature_core.py   tests/test_dev032_e1a_materialize.py   tests/test_dev032_e1a_raw_extractor.py   tests/test_dev032_e1a_runner.py
```

Do not execute the canonical materializer unless all preflight commands succeed.

## Canonical execution command

Only after a clean PASS preflight:

```bash
python - <<'PY'
from pathlib import Path
from multimarket.dev032_e1a_runner import run_e1a

result = run_e1a(
    workspace=Path("."),
    execution_commit="d37d4b4b7e409a6f4ffe5a31cd83ad1abbc35ede",
    max_workers=2,
)
print("ARTIFACT_PATH=", result.artifact_path)
print("ARTIFACT_SHA256=", result.artifact_sha256)
print("ARTIFACT_BYTES=", result.artifact_bytes)
PY
```

This command is a one-shot scientific execution.

## Current state

`DEV032_E1A_EXECUTION_FROZEN_PREFLIGHT_REQUIRED_NO_CANONICAL_RUN_YET`
