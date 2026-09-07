from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from multimarket import dev045_d6r26a_p2_r2_frozen_source_registry as r2
from multimarket import dev045_d6r26a_p2_r6_historical_source_identity_preflight as r6


def _fixture_record(tmp_path: Path, *, day: str = "2026-01-01") -> r2.FrozenSourceRecord:
    dtype = np.dtype([("payload", "V64")])
    a = np.zeros(4, dtype=dtype)
    path = tmp_path / f"BTCUSDT_{day}.npy"
    np.save(path, a, allow_pickle=False)
    payload = path.read_bytes()
    return r2.FrozenSourceRecord(
        day=day,
        path=str(path),
        rows=4,
        bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        ingestion_witness="TEST",
        witness_head="0" * 40,
    )


def test_r6_contract_opens_only_readonly_historical_identity_surface():
    r6.validate_r6_contract()
    assert r6.HISTORICAL_FILE_IO_AUTHORIZED is True
    assert r6.HISTORICAL_SOURCE_OPEN_AUTHORIZED is True
    assert r6.HISTORICAL_SOURCE_REHASH_AUTHORIZED is True
    assert r6.SIMULATOR_IMPORT_AUTHORIZED is False
    assert r6.CANDIDATE_SIMULATION_AUTHORIZED is False
    assert r6.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r6.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r6.P2_ATTEMPT_CONSUMED_BY_R6 is False
    assert r6.MODEL_FIT_AUTHORIZED is False
    assert r6.PNL_AUTHORIZED is False


def test_authorization_is_exact():
    with pytest.raises(r6.SourceIdentityPreflightError, match="authorization_denied"):
        r6.require_authorization(None)
    with pytest.raises(r6.SourceIdentityPreflightError, match="authorization_denied"):
        r6.require_authorization("YES")
    r6.require_authorization(r6.AUTH_TOKEN)


def test_verify_source_file_fixture_passes(tmp_path: Path):
    expected = _fixture_record(tmp_path)
    observed = r6.verify_source_file(expected)
    assert observed.day == expected.day
    assert observed.path == expected.path
    assert observed.rows == expected.rows
    assert observed.bytes == expected.bytes
    assert observed.sha256 == expected.sha256
    assert observed.ndim == 1
    assert observed.itemsize == 64


def test_verify_source_file_fails_closed_on_bytes_drift(tmp_path: Path):
    expected = _fixture_record(tmp_path)
    bad = r2.FrozenSourceRecord(
        day=expected.day,
        path=expected.path,
        rows=expected.rows,
        bytes=expected.bytes + 1,
        sha256=expected.sha256,
        ingestion_witness=expected.ingestion_witness,
        witness_head=expected.witness_head,
    )
    with pytest.raises(r6.SourceIdentityPreflightError, match="source_bytes_mismatch"):
        r6.verify_source_file(bad)


def test_verify_source_file_fails_closed_on_rows_drift(tmp_path: Path):
    expected = _fixture_record(tmp_path)
    bad = r2.FrozenSourceRecord(
        day=expected.day,
        path=expected.path,
        rows=expected.rows + 1,
        bytes=expected.bytes,
        sha256=expected.sha256,
        ingestion_witness=expected.ingestion_witness,
        witness_head=expected.witness_head,
    )
    with pytest.raises(r6.SourceIdentityPreflightError, match="source_rows_mismatch"):
        r6.verify_source_file(bad)


def test_verify_source_file_fails_closed_on_sha_drift(tmp_path: Path):
    expected = _fixture_record(tmp_path)
    bad = r2.FrozenSourceRecord(
        day=expected.day,
        path=expected.path,
        rows=expected.rows,
        bytes=expected.bytes,
        sha256="f" * 64,
        ingestion_witness=expected.ingestion_witness,
        witness_head=expected.witness_head,
    )
    with pytest.raises(r6.SourceIdentityPreflightError, match="source_sha256_mismatch"):
        r6.verify_source_file(bad)


def test_result_serialization_is_deterministic():
    result = r6.SourceIdentityPreflightResult(
        experiment_id=r6.EXPERIMENT_ID,
        design_version=r6.DESIGN_VERSION,
        status="SOURCE_IDENTITY_PREFLIGHT_PASS",
        data_role=r6.DATA_ROLE,
        source_registry_sha256=r6.SOURCE_REGISTRY_SHA256,
        verified_source_count=0,
        sources=(),
        historical_source_opened=True,
        simulator_imported=False,
        candidate_simulation_started=False,
        attempt_marker_written=False,
        p2_attempt_consumed=False,
        model_fit=False,
        pnl=False,
        live_trading=False,
    )
    assert r6.canonical_result_bytes(result) == r6.canonical_result_bytes(result)


def test_write_result_once_refuses_overwrite(tmp_path: Path):
    result = r6.SourceIdentityPreflightResult(
        experiment_id=r6.EXPERIMENT_ID,
        design_version=r6.DESIGN_VERSION,
        status="SOURCE_IDENTITY_PREFLIGHT_PASS",
        data_role=r6.DATA_ROLE,
        source_registry_sha256=r6.SOURCE_REGISTRY_SHA256,
        verified_source_count=0,
        sources=(),
        historical_source_opened=True,
        simulator_imported=False,
        candidate_simulation_started=False,
        attempt_marker_written=False,
        p2_attempt_consumed=False,
        model_fit=False,
        pnl=False,
        live_trading=False,
    )
    out = tmp_path / "result.json"
    digest = r6.write_result_once(result, out)
    assert len(digest) == 64
    with pytest.raises(r6.SourceIdentityPreflightError, match="result_already_exists"):
        r6.write_result_once(result, out)
