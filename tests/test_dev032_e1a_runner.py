from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest

from multimarket import dev032_e1a_feature_core as fc
from multimarket import dev032_e1a_runner as r


def test_runner_frozen_identity_and_registry():
    assert r.EXPERIMENT_ID=="DEV032-E1A"
    assert r.DESIGN_VERSION=="wave1-full-materialization-v1"
    assert r.STATUS_PASS=="DEV032_WAVE1_EXACT_SUPPORT_MATERIALIZED"
    assert len(fc.strategy_feature_counts())==36
    assert sum(fc.strategy_feature_counts()[f"S{i:02d}"] for i in range(4,36))==278
    assert fc.strategy_feature_counts()["S03"]==12
    assert not any(r.FORWARD_GUARDS.values())


def test_noncanonical_output_rejected_before_data(tmp_path: Path):
    with pytest.raises(r.E1ARunnerError) as e:
        r.run_e1a(
            workspace=tmp_path,
            execution_commit="0"*40,
            output_directory=tmp_path/"wrong",
            require_canonical_output=True,
        )
    assert e.value.reason=="noncanonical_output_directory"


def test_invalid_execution_commit_rejected_before_data(tmp_path: Path):
    with pytest.raises(r.E1ARunnerError) as e:
        r.run_e1a(
            workspace=tmp_path,
            execution_commit="short",
            output_directory=tmp_path/"synthetic",
            require_canonical_output=False,
        )
    assert e.value.reason=="execution_commit_must_be_full_sha"


def test_full_campaign_count_constants_match_frozen_support():
    assert r.mat.EXPECTED_TOTAL_ROWS==1374
    assert r.mat.EXPECTED_LONG==684
    assert r.mat.EXPECTED_SHORT==690


def test_s03_shape_contract_via_fake_candidate(monkeypatch):
    class FakeEntry:
        path=Path("/tmp/fake.csv")
    class FakeDay:
        pass
    class FakeTarget:
        target_id="A"; horizon_seconds=120; barrier_bps=16
    class FakeCandidate:
        decision_timestamps_us=np.array([10,20,30],dtype=np.int64)
        s0_valid=np.array([True,True,True])
        s0_values=np.arange(36,dtype=float).reshape(3,12)

    monkeypatch.setattr(r.dd,"verify_input_manifest",lambda:[type("E",(),{"day":r.dd.HISTORICAL_DAYS[0],"path":Path("/tmp/fake")})()])
    monkeypatch.setattr(r,"_load_day",lambda path,day:FakeDay())
    monkeypatch.setattr(r.dd,"FROZEN_TARGETS",(FakeTarget(),))
    monkeypatch.setattr(r.dd,"build_candidate_day",lambda *a,**k:FakeCandidate())

    x=r._s03_for_day(r.dd.HISTORICAL_DAYS[0],np.array([10,30],dtype=np.int64))
    assert x.shape==(2,12)
    assert np.array_equal(x[0],np.arange(12,dtype=float))
    assert np.array_equal(x[1],np.arange(24,36,dtype=float))
