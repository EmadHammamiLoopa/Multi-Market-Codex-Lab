from __future__ import annotations

from types import SimpleNamespace

import pytest

from multimarket import (
    dev045_d6r26a_p2_r2_frozen_source_registry as r2,
)
from multimarket import (
    dev045_d6r26a_p2_r23_final_one_shot_readiness_authorization_preflight as r23,
)


def _good_memory():
    return (
        __import__(
            "multimarket."
            "dev045_d6r26a_p2_r22_final_successor_campaign_runner_binding_preauthorization",
            fromlist=["MemorySnapshot"],
        )
        .MemorySnapshot(
            mem_available_bytes=(
                32 * 1024**3
            ),
            rss_anon_bytes=(
                128 * 1024**2
            ),
            vm_swap_bytes=0,
        )
    )


def _hooks(
    *,
    head: str = r23.PARENT_R22_HEAD,
    clean: bool = True,
    marker: bool = False,
    output_pristine: bool = True,
    scratch_pristine: bool = True,
    size_delta_day: str | None = None,
    events: list[str] | None = None,
):
    events = (
        events
        if events is not None
        else []
    )

    def source_metadata(
        expected: r2.FrozenSourceRecord,
    ) -> r23.SourceMetadata:
        events.append(
            f"stat:{expected.day}"
        )

        delta = (
            1
            if expected.day
            == size_delta_day
            else 0
        )

        return r23.SourceMetadata(
            day=expected.day,
            path=expected.path,
            bytes=(
                expected.bytes
                + delta
            ),
        )

    return r23.ReadinessHooks(
        repo_head=lambda: (
            events.append(
                "head"
            )
            or head
        ),

        worktree_clean=lambda: (
            events.append(
                "worktree"
            )
            or clean
        ),

        attempt_marker_exists=lambda: (
            events.append(
                "marker-check"
            )
            or marker
        ),

        output_root_pristine=lambda: (
            events.append(
                "output-check"
            )
            or output_pristine
        ),

        scratch_root_pristine=lambda: (
            events.append(
                "scratch-check"
            )
            or scratch_pristine
        ),

        source_metadata=source_metadata,

        memory_snapshot=lambda: (
            events.append(
                "memory"
            )
            or _good_memory()
        ),

        engine_identity=lambda: (
            events.append(
                "engine"
            )
            or SimpleNamespace(
                version="2.4.4"
            )
        ),
    )


def test_r23_contract_is_strictly_preexecution():
    r23.validate_r23_contract()

    assert (
        r23.SOURCE_METADATA_STAT_AUTHORIZED
        is True
    )

    assert (
        r23.HISTORICAL_PAYLOAD_READ_AUTHORIZED
        is False
    )

    assert (
        r23.SOURCE_NPY_LOAD_AUTHORIZED
        is False
    )

    assert (
        r23.SOURCE_MMAP_AUTHORIZED
        is False
    )

    assert (
        r23.SOURCE_REHASH_AUTHORIZED
        is False
    )

    assert (
        r23.SOURCE_ROW_SCAN_AUTHORIZED
        is False
    )

    assert (
        r23.EXECUTION_START_FUNCTION_IMPLEMENTED
        is False
    )

    assert (
        r23.P2_ATTEMPT_CONSUMED
        is False
    )

    assert r23.PNL_AUTHORIZED is False


def test_ready_report_checks_exact_seven_metadata_records_without_payload_read(
    tmp_path,
):
    events: list[str] = []

    report = (
        r23.run_readiness_preflight(
            hooks=_hooks(
                events=events
            ),
            output_root=(
                tmp_path
                / "output"
            ),
            scratch_root=(
                tmp_path
                / "scratch"
            ),
        )
    )

    assert report.status == (
        "READY_FOR_EXPLICIT_ONE_SHOT_EXECUTION"
    )

    assert report.head == (
        r23.PARENT_R22_HEAD
    )

    assert report.source_count == 7

    assert (
        report.total_source_bytes
        == sum(
            item.bytes
            for item in (
                r2.FROZEN_SOURCE_REGISTRY
            )
        )
    )

    assert (
        report.engine_version
        == "2.4.4"
    )

    assert (
        report.historical_payload_read
        is False
    )

    assert (
        report.attempt_consumed
        is False
    )

    assert len(
        [
            event
            for event in events
            if event.startswith(
                "stat:"
            )
        ]
    ) == 7

    assert "engine" in events
    assert "memory" in events


def test_wrong_head_fails_before_source_metadata(
    tmp_path,
):
    events: list[str] = []

    with pytest.raises(
        r23.ReadinessPreflightError,
        match="head:",
    ):
        r23.run_readiness_preflight(
            hooks=_hooks(
                head="0" * 40,
                events=events,
            ),
            output_root=(
                tmp_path
                / "output"
            ),
            scratch_root=(
                tmp_path
                / "scratch"
            ),
        )

    assert not any(
        event.startswith(
            "stat:"
        )
        for event in events
    )


def test_dirty_worktree_fails_before_source_metadata(
    tmp_path,
):
    events: list[str] = []

    with pytest.raises(
        r23.ReadinessPreflightError,
        match="worktree_dirty",
    ):
        r23.run_readiness_preflight(
            hooks=_hooks(
                clean=False,
                events=events,
            ),
            output_root=(
                tmp_path
                / "output"
            ),
            scratch_root=(
                tmp_path
                / "scratch"
            ),
        )

    assert not any(
        event.startswith(
            "stat:"
        )
        for event in events
    )


def test_existing_attempt_marker_blocks_preflight(
    tmp_path,
):
    with pytest.raises(
        r23.ReadinessPreflightError,
        match="attempt_marker_exists",
    ):
        r23.run_readiness_preflight(
            hooks=_hooks(
                marker=True
            ),
            output_root=(
                tmp_path
                / "output"
            ),
            scratch_root=(
                tmp_path
                / "scratch"
            ),
        )


def test_nonpristine_output_or_scratch_blocks_preflight(
    tmp_path,
):
    with pytest.raises(
        r23.ReadinessPreflightError,
        match="output_root_not_pristine",
    ):
        r23.run_readiness_preflight(
            hooks=_hooks(
                output_pristine=False
            ),
            output_root=(
                tmp_path
                / "output"
            ),
            scratch_root=(
                tmp_path
                / "scratch"
            ),
        )

    with pytest.raises(
        r23.ReadinessPreflightError,
        match="scratch_root_not_pristine",
    ):
        r23.run_readiness_preflight(
            hooks=_hooks(
                scratch_pristine=False
            ),
            output_root=(
                tmp_path
                / "output"
            ),
            scratch_root=(
                tmp_path
                / "scratch"
            ),
        )


def test_source_size_mismatch_fails_closed(
    tmp_path,
):
    with pytest.raises(
        r23.ReadinessPreflightError,
        match="source_metadata_mismatch",
    ):
        r23.run_readiness_preflight(
            hooks=_hooks(
                size_delta_day=(
                    "2026-06-01"
                )
            ),
            output_root=(
                tmp_path
                / "output"
            ),
            scratch_root=(
                tmp_path
                / "scratch"
            ),
        )


def test_real_hook_builder_is_construction_only(
    tmp_path,
):
    hooks = (
        r23.build_real_readiness_hooks(
            repo_root=tmp_path,
            output_root=(
                tmp_path
                / "output"
            ),
            scratch_root=(
                tmp_path
                / "scratch"
            ),
        )
    )

    assert isinstance(
        hooks,
        r23.ReadinessHooks,
    )

    assert not (
        tmp_path
        / "output"
    ).exists()

    assert not (
        tmp_path
        / "scratch"
    ).exists()
