from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from multimarket import dev045_d6r26a_p2_r1_canonical_label_materializer_preauth as r1
from multimarket import dev045_d6r26a_p2_r2_frozen_source_registry as r2
from multimarket import dev045_d6r26a_p2_r3_execution_authorization_contract as r3
from multimarket import dev045_d6r26a_p2_r4_canonical_materialization_runner_preexec as r4
from multimarket import dev045_d6r26a_p2_r6_historical_source_identity_preflight as r6
from multimarket import dev045_d6r26a_p2_r8a_real_hooks_writer_preexecution as r8a


def test_r8a_contract_is_implementation_only_and_execution_remains_closed():
    r8a.validate_r8a_contract()

    assert r8a.PARENT_R7_HEAD == (
        "a167f39dd6bf50e43d8f2bc67feab0a60729248a"
    )
    assert r8a.DATA_ROLE == "CONSUMED_DEVELOPMENT"
    assert r8a.SOURCE_REGISTRY_SHA256 == (
        "97c631d621118d5cd4d294825dec545c92d85c62456403a6974ca38a70ece3f4"
    )

    assert r8a.REAL_SOURCE_VERIFIER_IMPLEMENTED is True
    assert r8a.READ_ONLY_MMAP_OPEN_IMPLEMENTED is True
    assert r8a.REAL_ENGINE_FACTORY_IMPLEMENTED is True
    assert r8a.ATOMIC_WRITER_IMPLEMENTED is True
    assert r8a.SEALED_RUNNER_HOOKS_IMPLEMENTED is True

    assert r8a.FEATURE_LABEL_EXECUTOR_FROZEN is False
    assert r8a.EXECUTION_AUTHORIZATION_CREATED is False
    assert r8a.HISTORICAL_FILE_IO_AUTHORIZED is False
    assert r8a.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r8a.SIMULATOR_IMPORT_AUTHORIZED is False
    assert r8a.CANDIDATE_SIMULATION_AUTHORIZED is False
    assert r8a.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r8a.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r8a.MODEL_FIT_AUTHORIZED is False
    assert r8a.PNL_AUTHORIZED is False


def test_real_source_verifier_adapter_preserves_exact_identity(monkeypatch):
    expected = r2.FROZEN_SOURCE_REGISTRY[0]

    observed = r6.ObservedSourceIdentity(
        day=expected.day,
        path=expected.path,
        rows=expected.rows,
        bytes=expected.bytes,
        sha256=expected.sha256,
        ndim=1,
        itemsize=64,
    )

    monkeypatch.setattr(
        r8a.r6,
        "verify_source_file",
        lambda source: observed,
    )

    result = r8a.verify_source_impl(
        expected
    )

    assert result == r4.VerifiedSource(
        day=expected.day,
        path=expected.path,
        rows=expected.rows,
        bytes=expected.bytes,
        sha256=expected.sha256,
    )


def test_shared_npy_opener_is_read_only_and_bounded_memory(tmp_path):
    dtype = np.dtype(
        [("payload", "V64")]
    )

    data = np.zeros(
        5,
        dtype=dtype,
    )

    path = tmp_path / "probe.npy"

    np.save(
        path,
        data,
        allow_pickle=False,
    )

    mapped = r8a._open_npy_memmap(
        path,
        expected_rows=5,
        expected_bytes=path.stat().st_size,
        expected_itemsize=64,
    )

    try:
        assert isinstance(
            mapped,
            np.memmap,
        )
        assert mapped.ndim == 1
        assert mapped.shape == (5,)
        assert mapped.dtype.itemsize == 64
        assert mapped.flags.writeable is False
    finally:
        mm = getattr(
            mapped,
            "_mmap",
            None,
        )

        if mm is not None:
            mm.close()


def test_atomic_partition_writer_is_write_once_and_hash_verified(tmp_path):
    lane = r1.build_materialization_plan()[0]

    payload = (
        b"PAR1"
        + b"R8A-SYNTHETIC-WRITER-PROBE"
        + b"PAR1"
    )

    artifact = r8a.write_partition_bytes_impl(
        root=tmp_path,
        lane=lane,
        payload=payload,
        row_count=7,
    )

    assert artifact.lane_id == lane.lane_id
    assert artifact.relpath == lane.partition_relpath
    assert artifact.bytes == len(payload)
    assert artifact.row_count == 7
    assert len(artifact.sha256) == 64

    r8a.verify_partition_impl(
        root=tmp_path,
        artifact=artifact,
    )

    with pytest.raises(
        r8a.RealHooksPreexecutionError,
        match="artifact_already_exists",
    ):
        r8a.write_partition_bytes_impl(
            root=tmp_path,
            lane=lane,
            payload=payload,
            row_count=7,
        )


def test_lazy_engine_factory_has_no_import_until_called_and_validates_once(
    monkeypatch,
):
    source = r4.VerifiedSource(
        day="2026-01-01",
        path="/synthetic/probe.npy",
        rows=1,
        bytes=64,
        sha256="0" * 64,
    )

    events = np.zeros(
        1,
        dtype=np.dtype(
            [("payload", "V64")]
        ),
    )

    handle = r8a.DaySourceHandle(
        source=source,
        events=events,
    )

    calls = {
        "identity": 0,
        "validation": 0,
        "asset": 0,
        "import": 0,
    }

    monkeypatch.setattr(
        r8a,
        "_expected_frozen_source",
        lambda observed: r2.FROZEN_SOURCE_REGISTRY[0],
    )

    def fake_identity():
        calls["identity"] += 1
        return object()

    def fake_validate(data):
        assert data is events
        calls["validation"] += 1

    def fake_asset(data, **kwargs):
        assert data is events
        assert kwargs["queue_model"] == "risk_adverse"
        assert kwargs["maker_fee"] == 0.0
        assert kwargs["taker_fee"] == 0.0
        calls["asset"] += 1
        return "ASSET"

    class FakeBacktest:
        def __init__(self, assets):
            assert assets == ["ASSET"]
            self.closed = False

        def close(self):
            self.closed = True
            return 0

    fake_hft = SimpleNamespace(
        HashMapMarketDepthBacktest=FakeBacktest
    )

    def fake_import(name):
        assert name == "hftbacktest"
        calls["import"] += 1
        return fake_hft

    monkeypatch.setattr(
        r8a.r5,
        "verify_engine_identity",
        fake_identity,
    )
    monkeypatch.setattr(
        r8a.m4,
        "validate_events",
        fake_validate,
    )
    monkeypatch.setattr(
        r8a.m4,
        "build_asset",
        fake_asset,
    )
    monkeypatch.setattr(
        r8a.importlib,
        "import_module",
        fake_import,
    )

    engine1 = r8a.new_engine_impl(
        handle
    )
    r8a.close_engine_impl(
        engine1
    )

    engine2 = r8a.new_engine_impl(
        handle
    )
    r8a.close_engine_impl(
        engine2
    )

    assert calls["identity"] == 1
    assert calls["validation"] == 1
    assert calls["asset"] == 2
    assert calls["import"] == 2


def test_sealed_runner_hooks_cannot_consume_attempt_even_with_valid_r3_token(
    tmp_path,
):
    hooks = r8a.build_sealed_runner_hooks(
        output_root=tmp_path,
    )

    marker = (
        tmp_path
        / r8a.ATTEMPT_MARKER_RELPATH
    )

    assert marker.exists() is False

    with pytest.raises(
        r8a.RealHooksPreexecutionError,
        match="execution_surface_sealed:verify_source",
    ):
        r4.run_canonical_materialization(
            authorization_value=r3.AUTH_TOKEN,
            hooks=hooks,
        )

    assert marker.exists() is False


def test_control_writer_rejects_noncanonical_control_path(tmp_path):
    with pytest.raises(
        r8a.RealHooksPreexecutionError,
        match="control_relpath",
    ):
        r8a.write_control_json_impl(
            root=tmp_path,
            relpath="NOT_CANONICAL.json",
            payload={"status": "NO"},
        )
