from __future__ import annotations

from pathlib import Path
import pytest

from multimarket import dev033_g2a_materialize as mat
from multimarket import dev033_g2a_runner as runner

def test_runner_frozen_identities_and_guards():
    assert runner.EXPERIMENT_ID=="DEV033-G2A"
    assert runner.DESIGN_VERSION=="layered-raw-temporal-materialization-v1"
    assert runner.E1A_SHA256=="76e1c97e8b9a899bc27f3193316cbfc85efba8b0a7aa037d4c46fcc6a8be4a50"
    assert runner.E1A_BYTES==44689
    assert not any(runner.FORWARD_GUARDS.values())
    assert runner.REAL_OUTPUT_DIRECTORY.name=="dev033_g2a_layered_temporal_materialization_v1"
    assert runner.MANIFEST_FILENAME=="DEV033_G2A_LAYERED_TEMPORAL_MATERIALIZATION.json"

def test_registry_and_total_columns():
    assert len(mat.CANDIDATE_IDS)==24
    assert mat.TOTAL_COLUMNS==2520
    assert mat.REGISTRY[0]["candidate_id"]=="G2C01"
    assert mat.REGISTRY[-1]["candidate_id"]=="G2C24"

def test_invalid_execution_commit_fails_before_data_access(tmp_path:Path):
    with pytest.raises(runner.G2ARunnerError) as e:
        runner.run_g2a(
            workspace=tmp_path,
            execution_commit="bad",
            output_directory=tmp_path/"out",
            require_canonical_output=False,
        )
    assert e.value.reason=="execution_commit"

def test_existing_output_fails_before_data_access(tmp_path:Path):
    out=tmp_path/"out";out.mkdir()
    with pytest.raises(runner.G2ARunnerError) as e:
        runner.run_g2a(
            workspace=tmp_path,
            execution_commit="0"*40,
            output_directory=out,
            require_canonical_output=False,
        )
    assert e.value.reason=="output_directory_already_exists"
