from __future__ import annotations

from pathlib import Path

import pytest

from multimarket import dev032_e1b_loader as loader
from multimarket import dev032_e1b_runner as runner

def test_primary_registry_is_exact_and_ordered():
    assert loader.PRIMARY_IDS == tuple(["P02"]+[f"P{i:02d}" for i in range(3,36)])
    assert len(loader.PRIMARY_IDS)==34
    assert tuple(loader.FAMILY_BY_PRIMARY)==loader.PRIMARY_IDS

def test_runner_rejects_noncanonical_real_output(tmp_path):
    with pytest.raises(runner.E1BRunnerError,match="noncanonical_output_directory"):
        runner.run_e1b(
            execution_commit="a"*40,
            output_directory=tmp_path/"x",
            require_canonical_output=True,
        )

def test_runner_rejects_canonical_path_in_nonreal_mode():
    with pytest.raises(runner.E1BRunnerError,match="canonical_output_requires_real_mode"):
        runner.run_e1b(
            execution_commit="a"*40,
            output_directory=runner.REAL_OUTPUT_DIRECTORY,
            require_canonical_output=False,
        )

def test_runner_rejects_existing_output_before_evidence_access(tmp_path):
    out=tmp_path/"exists"
    out.mkdir()
    with pytest.raises(runner.E1BRunnerError,match="output_directory_already_exists"):
        runner.run_e1b(
            execution_commit="a"*40,
            output_directory=out,
            require_canonical_output=False,
        )

@pytest.mark.parametrize("sha",["","abc","G"*40,"a"*39,"a"*41])
def test_runner_rejects_invalid_execution_commit_before_evidence_access(tmp_path,sha):
    with pytest.raises(runner.E1BRunnerError,match="execution_commit_must_be_full_sha"):
        runner.run_e1b(
            execution_commit=sha,
            output_directory=tmp_path/"out",
            require_canonical_output=False,
        )

def test_forward_guards_are_all_false():
    assert runner.FORWARD_GUARDS
    assert not any(runner.FORWARD_GUARDS.values())
