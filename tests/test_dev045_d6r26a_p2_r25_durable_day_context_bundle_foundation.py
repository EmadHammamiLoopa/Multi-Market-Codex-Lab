from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from multimarket import (
    dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20,
)
from multimarket import (
    dev045_d6r26a_p2_r25_durable_day_context_bundle_foundation as r25,
)


def _source_identity() -> r25.DurableSourceIdentity:
    return r25.DurableSourceIdentity(
        day="2099-01-01",
        path="/synthetic/not-a-real-source.npy",
        rows=123,
        bytes=456,
        sha256="0" * 64,
    )


def _build_context(tmp_path: Path):
    data = r20.make_synthetic_dual_context_fixture()
    scratch = tmp_path / "r20"
    scratch.mkdir()
    return r20.build_once_day_context(
        data,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
        scratch_root=scratch,
    )


def test_r25_contract_is_preattempt_and_nonhistorical() -> None:
    r25.validate_r25_contract()
    assert r25.P2_ATTEMPT_CONSUMED is False
    assert r25.PREEXECUTION_ONLY is True
    assert r25.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r25.REAL_JAN_JUL_DURABLE_MATERIALIZATION_AUTHORIZED is False
    assert r25.HISTORICAL_CANDIDATE_SIMULATION_AUTHORIZED is False
    assert r25.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r25.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r25.MODEL_FIT_AUTHORIZED is False
    assert r25.PNL_AUTHORIZED is False


def test_synthetic_roundtrip_reopens_exact_r20_surface(tmp_path: Path) -> None:
    original = _build_context(tmp_path)
    bundle = tmp_path / "bundle" / "2099-01-01"
    source = _source_identity()

    try:
        r25.persist_day_context(
            context=original,
            source_identity=source,
            final_dir=bundle,
        )

        reopened = r25.open_verified_day_context(
            bundle_dir=bundle,
            expected_source_identity=source,
        )

        try:
            assert reopened.bounds == original.bounds
            assert reopened.feature_summary == original.feature_summary
            assert reopened.raw_event_pass_count == 1

            assert np.array_equal(
                reopened.feature_cache.decision_local_ns,
                original.feature_cache.decision_local_ns,
            )
            assert np.array_equal(
                reopened.feature_cache.best_bid_tick,
                original.feature_cache.best_bid_tick,
            )
            assert np.array_equal(
                reopened.feature_cache.best_ask_tick,
                original.feature_cache.best_ask_tick,
            )
            assert np.array_equal(
                reopened.feature_cache.values,
                original.feature_cache.values,
            )

            assert isinstance(
                reopened.feature_cache.decision_local_ns,
                np.memmap,
            )
            assert reopened.feature_cache.decision_local_ns.flags.writeable is False
            assert reopened.feature_cache.values.flags.writeable is False
            assert isinstance(reopened.midpoint_index.records, np.memmap)
            assert reopened.midpoint_index.records.flags.writeable is False

            assert reopened.midpoint_index.count == original.midpoint_index.count
            assert reopened.midpoint_index.bytes == original.midpoint_index.bytes
            assert reopened.midpoint_index.sha256 == original.midpoint_index.sha256
            assert np.array_equal(
                reopened.midpoint_index.records,
                original.midpoint_index.records,
            )
        finally:
            r25.close_reopened_day_context(reopened)

        assert bundle.is_dir()
        assert {path.name for path in bundle.iterdir()} == set(r25.DAY_FILES)
    finally:
        r20.close_midpoint_index(original.midpoint_index)


def test_source_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    original = _build_context(tmp_path)
    bundle = tmp_path / "bundle" / "2099-01-01"

    try:
        r25.persist_day_context(
            context=original,
            source_identity=_source_identity(),
            final_dir=bundle,
        )

        wrong = r25.DurableSourceIdentity(
            day="2099-01-01",
            path="/synthetic/not-a-real-source.npy",
            rows=123,
            bytes=456,
            sha256="1" * 64,
        )

        with pytest.raises(r25.R25DurableBundleError, match="source_identity_mismatch"):
            r25.open_verified_day_context(
                bundle_dir=bundle,
                expected_source_identity=wrong,
            )
    finally:
        r20.close_midpoint_index(original.midpoint_index)


def test_corrupt_array_is_rejected_before_reopen(tmp_path: Path) -> None:
    original = _build_context(tmp_path)
    bundle = tmp_path / "bundle" / "2099-01-01"

    try:
        r25.persist_day_context(
            context=original,
            source_identity=_source_identity(),
            final_dir=bundle,
        )

        target = bundle / r25.DECISION_FILE
        with target.open("r+b") as handle:
            handle.seek(-1, 2)
            last = handle.read(1)
            handle.seek(-1, 2)
            handle.write(bytes([last[0] ^ 0x01]))

        with pytest.raises(r25.R25DurableBundleError, match="file_sha256"):
            r25.open_verified_day_context(
                bundle_dir=bundle,
                expected_source_identity=_source_identity(),
            )
    finally:
        r20.close_midpoint_index(original.midpoint_index)


def test_missing_manifest_is_incomplete_and_rejected(tmp_path: Path) -> None:
    original = _build_context(tmp_path)
    bundle = tmp_path / "bundle" / "2099-01-01"

    try:
        r25.persist_day_context(
            context=original,
            source_identity=_source_identity(),
            final_dir=bundle,
        )
        (bundle / r25.MANIFEST_NAME).unlink()

        with pytest.raises(r25.R25DurableBundleError, match="bundle_file_set"):
            r25.open_verified_day_context(
                bundle_dir=bundle,
                expected_source_identity=_source_identity(),
            )
    finally:
        r20.close_midpoint_index(original.midpoint_index)


def test_existing_final_bundle_is_never_overwritten(tmp_path: Path) -> None:
    original = _build_context(tmp_path)
    bundle = tmp_path / "bundle" / "2099-01-01"

    try:
        r25.persist_day_context(
            context=original,
            source_identity=_source_identity(),
            final_dir=bundle,
        )

        with pytest.raises(r25.R25DurableBundleError, match="final_bundle_exists"):
            r25.persist_day_context(
                context=original,
                source_identity=_source_identity(),
                final_dir=bundle,
            )
    finally:
        r20.close_midpoint_index(original.midpoint_index)
