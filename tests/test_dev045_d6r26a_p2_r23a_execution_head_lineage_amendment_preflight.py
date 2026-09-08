from __future__ import annotations

from types import SimpleNamespace

import pytest

from multimarket import (
    dev045_d6r26a_p2_r2_frozen_source_registry as r2,
)
from multimarket import (
    dev045_d6r26a_p2_r22_final_successor_campaign_runner_binding_preauthorization as r22,
)
from multimarket import (
    dev045_d6r26a_p2_r23_final_one_shot_readiness_authorization_preflight as r23,
)
from multimarket import (
    dev045_d6r26a_p2_r23a_execution_head_lineage_amendment_preflight as r23a,
)


EXEC_HEAD = "a" * 40


def _hooks(
    *,
    head: str = EXEC_HEAD,
    clean: bool = True,
    marker: bool = False,
):
    def source_metadata(
        expected: r2.FrozenSourceRecord,
    ) -> r23.SourceMetadata:
        return r23.SourceMetadata(
            day=expected.day,
            path=expected.path,
            bytes=expected.bytes,
        )

    return r23.ReadinessHooks(
        repo_head=lambda: head,
        worktree_clean=lambda: clean,
        attempt_marker_exists=lambda: marker,
        output_root_pristine=lambda: True,
        scratch_root_pristine=lambda: True,
        source_metadata=source_metadata,
        memory_snapshot=lambda: (
            r22.MemorySnapshot(
                mem_available_bytes=(
                    32 * 1024**3
                ),
                rss_anon_bytes=(
                    128 * 1024**2
                ),
                vm_swap_bytes=0,
            )
        ),
        engine_identity=lambda: (
            SimpleNamespace(
                version="2.4.4"
            )
        ),
    )


def test_r23a_contract_remains_fully_preauthorization():
    r23a.validate_r23a_contract()

    assert (
        r23a.EXACT_EXECUTION_HEAD_MUST_BE_SUPPLIED_BY_ONE_SHOT_WRAPPER
        is True
    )

    assert (
        r23a.HISTORICAL_PAYLOAD_READ_AUTHORIZED
        is False
    )

    assert (
        r23a.ATTEMPT_MARKER_WRITE_AUTHORIZED
        is False
    )

    assert (
        r23a.HISTORICAL_SIMULATOR_LANE_AUTHORIZED
        is False
    )

    assert (
        r23a.P2_ATTEMPT_CONSUMED
        is False
    )


def test_exact_supplied_execution_head_passes():
    report = (
        r23a.run_readiness_preflight(
            hooks=_hooks(),
            expected_execution_head=(
                EXEC_HEAD
            ),
        )
    )

    assert report.status == (
        "READY_FOR_EXPLICIT_ONE_SHOT_EXECUTION"
    )

    assert report.head == EXEC_HEAD

    assert (
        report.historical_payload_read
        is False
    )

    assert (
        report.attempt_consumed
        is False
    )


def test_wrong_live_head_fails_before_metadata():
    with pytest.raises(
        r23a.ExecutionHeadPreflightError,
        match="head:",
    ):
        r23a.run_readiness_preflight(
            hooks=_hooks(
                head="b" * 40
            ),
            expected_execution_head=(
                EXEC_HEAD
            ),
        )


@pytest.mark.parametrize(
    "value",
    (
        "",
        "abc",
        "G" * 40,
        "a" * 39,
        "a" * 41,
    ),
)
def test_invalid_expected_head_rejected(
    value,
):
    with pytest.raises(
        r23a.ExecutionHeadPreflightError,
        match="expected_execution_head",
    ):
        r23a.run_readiness_preflight(
            hooks=_hooks(),
            expected_execution_head=value,
        )


def test_dirty_tree_or_marker_still_blocks():
    with pytest.raises(
        r23a.ExecutionHeadPreflightError,
        match="worktree_dirty",
    ):
        r23a.run_readiness_preflight(
            hooks=_hooks(
                clean=False
            ),
            expected_execution_head=(
                EXEC_HEAD
            ),
        )

    with pytest.raises(
        r23a.ExecutionHeadPreflightError,
        match="attempt_marker_exists",
    ):
        r23a.run_readiness_preflight(
            hooks=_hooks(
                marker=True
            ),
            expected_execution_head=(
                EXEC_HEAD
            ),
        )
