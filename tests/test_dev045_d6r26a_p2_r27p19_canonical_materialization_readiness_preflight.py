from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from multimarket import dev045_d6r26a_p2_r2_frozen_source_registry as r2
from multimarket import dev045_d6r26a_p2_r26p1_real_durable_materializer_preexecution as r26p1
from multimarket import dev045_d6r26a_p2_r27p19_canonical_materialization_readiness_preflight as r27p19


def test_r27p19_contract_freezes_old_semantics_and_blocks_execution():
    r27p19.validate_r27p19_contract()
    assert r27p19.SOURCE_COUNT == 7
    assert r27p19.EXPECTED_LANES_PER_DAY == 40
    assert r27p19.EXPECTED_TOTAL_PARTITIONS == 280
    assert r27p19.CORRECTED_ENGINE_IDENTITY == (
        "R27P6A_PLUS_R27P9_L5_PLUS_R27P16_R10_VOLATILITY"
    )
    assert r27p19.P2_ATTEMPT_CONSUMED is False
    assert r27p19.CANONICAL_EXECUTION_READY is False
    assert r27p19.DIRECT_FULL_DAY_ACCELERATED_MATERIALIZATION_AUTHORIZED is False
    assert r27p19.READINESS_BLOCKER == "FULL_DAY_BOUNDED_MEMORY_NOT_PROVEN"


def test_static_full_day_capacity_audit_is_exact_and_not_claimed_as_rss():
    assert r27p19.FUSED_RAW_CAPACITY_BYTES_PER_EVENT == 265
    assert r27p19.LARGEST_SOURCE_DAY == "2026-07-01"
    assert r27p19.LARGEST_SOURCE_ROWS == 181_084_390
    assert r27p19.LARGEST_FUSED_RAW_CAPACITY_BYTES == 47_987_363_350
    assert r27p19.FULL_DAY_BOUNDED_MEMORY_PROVEN is False


def test_partial_residue_policy_preserves_without_reuse_or_delete():
    assert r27p19.PARTIAL_DURABLE_BUILD_IS_NOT_COMPLETE is True
    assert r27p19.PARTIAL_DURABLE_BUILD_REUSE_AUTHORIZED is False
    assert r27p19.PARTIAL_DURABLE_BUILD_AUTO_DELETE_AUTHORIZED is False
    assert r27p19.PARTIAL_DURABLE_BUILD_PRESERVE_FOR_FORENSICS is True
    assert r27p19.COMPLETED_DURABLE_BUNDLE_REUSE_REQUIRES_R25_VERIFICATION is True


def _install_synthetic_sources(monkeypatch, root_path: Path):
    source_root = root_path / "sources"
    source_root.mkdir()
    records = []
    for index, item in enumerate(r2.FROZEN_SOURCE_REGISTRY):
        path = source_root / f"{index}.npy"
        path.write_bytes(b"x" * (index + 1))
        records.append((item, path, index + 1))
    synthetic_registry = tuple(
        type(item)(
            day=item.day,
            path=str(path),
            rows=item.rows,
            bytes=size,
            sha256=item.sha256,
            ingestion_witness=item.ingestion_witness,
            witness_head=item.witness_head,
        )
        for item, path, size in records
    )
    monkeypatch.setattr(r2, "FROZEN_SOURCE_REGISTRY", synthetic_registry)


def _install_synthetic_paths(monkeypatch, root_path: Path, canonical: Path, durable: Path):
    monkeypatch.setattr(r27p19, "CANONICAL_OUTPUT_ROOT", canonical)
    monkeypatch.setattr(
        r27p19,
        "ATTEMPT_MARKER_PATH",
        canonical / "DEV045_D6R26A_P2_ATTEMPT_CONSUMED.json",
    )
    monkeypatch.setattr(
        r27p19,
        "FAILURE_ARTIFACT_PATH",
        canonical / "DEV045_D6R26A_P2_FAILURE.json",
    )
    monkeypatch.setattr(
        r27p19,
        "FINAL_MANIFEST_PATH",
        canonical / "DEV045_D6R26A_P2_CANONICAL_MANIFEST.json",
    )
    monkeypatch.setattr(r27p19, "DURABLE_ROOT", durable)
    monkeypatch.setattr(r27p19, "DURABLE_BUILD_ROOT", durable / r26p1.BUILD_ROOT_NAME)
    monkeypatch.setattr(
        r27p19,
        "DURABLE_COMPLETION_MANIFEST_PATH",
        durable / r26p1.COMPLETION_MANIFEST_NAME,
    )


def test_metadata_preflight_allows_forensic_build_residue_but_never_execution(monkeypatch):
    with TemporaryDirectory(prefix="dev045_r27p19_") as root:
        root_path = Path(root)
        _install_synthetic_sources(monkeypatch, root_path)
        canonical = root_path / "canonical"
        durable = root_path / "durable"
        build = durable / r26p1.BUILD_ROOT_NAME
        build.mkdir(parents=True)
        (build / "historical-residue").mkdir()
        _install_synthetic_paths(monkeypatch, root_path, canonical, durable)

        observed = r27p19.inspect_local_metadata_only()
        assert observed.source_stat_match_count == 7
        assert observed.durable_partial_build_names == ("historical-residue",)
        assert observed.canonical_execution_ready is False
        assert observed.readiness_blocker == "FULL_DAY_BOUNDED_MEMORY_NOT_PROVEN"


def test_metadata_preflight_fails_closed_on_canonical_collision(monkeypatch):
    with TemporaryDirectory(prefix="dev045_r27p19_collision_") as root:
        root_path = Path(root)
        _install_synthetic_sources(monkeypatch, root_path)
        canonical = root_path / "canonical"
        canonical.mkdir()
        (canonical / "unexpected.txt").write_text("collision", encoding="utf-8")
        durable = root_path / "durable"
        _install_synthetic_paths(monkeypatch, root_path, canonical, durable)

        with pytest.raises(r27p19.R27P19Error, match="canonical_output_not_pristine"):
            r27p19.inspect_local_metadata_only()
