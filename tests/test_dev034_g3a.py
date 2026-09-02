from __future__ import annotations

from types import SimpleNamespace
from datetime import date

import numpy as np
import pytest

from multimarket import dev034_g3a_core as core
from multimarket import dev034_g3a_runner as runner

def test_registry_exact_contract():
    core.validate_registry_contract()
    assert len(core.R_FEATURE_NAMES)==22
    assert core.CANDIDATE_IDS==tuple(f"G3C{i:02d}" for i in range(1,17))
    assert core.BY_ID["G3C01"]["feature_names"]==("rv_30m_bps",)
    assert core.BY_ID["G3C16"]["feature_names"]==core.R_FEATURE_NAMES
    assert core.BY_ID["G3C15"]["feature_count"]==17

def test_candidate_matrix_exact_subset_order():
    x=np.arange(44,dtype=float).reshape(2,22)
    c1=core.candidate_matrix(x,"G3C01")
    assert c1.shape==(2,1)
    assert np.array_equal(c1[:,0],x[:,core.R_POS["rv_30m_bps"]])

    c13=core.candidate_matrix(x,"G3C13")
    expected=["rv_30m_bps","abs_ret_30m_bps","range_30m_bps","spread_mean_5m_bps"]
    assert c13.shape==(2,4)
    assert np.array_equal(c13,x[:,[core.R_POS[n] for n in expected]])

def test_candidate_matrix_hash_is_namespace_sensitive():
    x=np.arange(12,dtype=float).reshape(3,4)
    assert core.matrix_sha256("A",x)!=core.matrix_sha256("B",x)

def test_exact_grid_alignment():
    ts=np.arange(0,1000,250,dtype=np.int64)
    day=SimpleNamespace(ts=ts)
    target=np.asarray([0,250,500],dtype=np.int64)
    # 60-second minute grid contract is stricter than this tiny synthetic array,
    # so only zero can be valid when DECISION_STEP_ROWS=240.
    with pytest.raises(core.G3AError) as e:
        core._decision_row_indices(day,target)
    assert e.value.reason=="timestamp_not_exact_minute_grid"

def test_extract_full_r_uses_frozen_helper(monkeypatch):
    n=241
    ts=np.arange(n,dtype=np.int64)*250_000
    day=SimpleNamespace(
        day=date(2026,1,1),
        ts=ts,
        bid=np.ones(n),
        ask=np.ones(n)*1.0001,
        mid=np.ones(n),
        book_valid=np.ones(n,dtype=bool),
    )
    monkeypatch.setattr(core.exp004,"_spread",lambda d:np.zeros(n,dtype=float))
    monkeypatch.setattr(
        core.exp004,"_r_features",
        lambda d,current,spread: np.arange(22,dtype=float) if current==240 else None,
    )
    out=core.extract_full_r(day,np.asarray([ts[240]],dtype=np.int64))
    assert out.shape==(1,22)
    assert np.array_equal(out[0],np.arange(22,dtype=float))

def test_extract_full_r_fails_closed_on_invalid_context(monkeypatch):
    n=241
    ts=np.arange(n,dtype=np.int64)*250_000
    day=SimpleNamespace(
        day=date(2026,1,1),
        ts=ts,
        bid=np.ones(n),
        ask=np.ones(n)*1.0001,
        mid=np.ones(n),
        book_valid=np.ones(n,dtype=bool),
    )
    monkeypatch.setattr(core.exp004,"_spread",lambda d:np.zeros(n,dtype=float))
    monkeypatch.setattr(core.exp004,"_r_features",lambda d,current,spread:None)
    with pytest.raises(core.G3AError) as e:
        core.extract_full_r(day,np.asarray([ts[240]],dtype=np.int64))
    assert e.value.reason=="r_context_invalid_on_p3_support"

def test_runner_all_seven_input_hashes_frozen():
    assert set(runner.EXPECTED_INPUT_SHA256)=={
        "2026-01-01","2026-02-01","2026-03-01","2026-04-01",
        "2026-05-01","2026-06-01","2026-07-01",
    }
    assert all(len(v)==64 for v in runner.EXPECTED_INPUT_SHA256.values())

def test_forward_guards_all_false():
    assert not any(core.FORWARD_GUARDS.values())

def test_canonical_identity():
    assert runner.EXPERIMENT_ID=="DEV034-G3A"
    assert runner.REAL_OUTPUT_DIRECTORY.name=="dev034_g3a_opportunity_volatility_context_v1"
    assert runner.ARTIFACT_FILENAME=="DEV034_G3A_OPPORTUNITY_VOLATILITY_CONTEXT.json"
