from __future__ import annotations

from dataclasses import dataclass

import pytest

from multimarket import (
    dev045_d6r26a_p2_r1_canonical_label_materializer_preauth as r1,
)
from multimarket import (
    dev045_d6r26a_p2_r2_frozen_source_registry as r2,
)
from multimarket import (
    dev045_d6r26a_p2_r3_execution_authorization_contract as r3,
)
from multimarket import (
    dev045_d6r26a_p2_r4_canonical_materialization_runner_preexec as r4,
)
from multimarket import (
    dev045_d6r26a_p2_r22_final_successor_campaign_runner_binding_preauthorization as r22,
)


@dataclass
class FakePrepared:
    day: str


class SyntheticFailure(RuntimeError):
    pass


def _good_memory() -> r22.MemorySnapshot:
    return r22.MemorySnapshot(
        mem_available_bytes=(
            32 * 1024**3
        ),
        rss_anon_bytes=(
            128 * 1024**2
        ),
        vm_swap_bytes=0,
    )


def _hooks(
    *,
    events: list[str],
    attempt_exists: bool = False,
    fail_prepare_day: str | None = None,
    fail_lane_id: str | None = None,
):
    def verify_source(
        expected: r2.FrozenSourceRecord,
    ) -> r4.VerifiedSource:
        events.append(
            f"verify:{expected.day}"
        )

        return r4.VerifiedSource(
            day=expected.day,
            path=expected.path,
            rows=expected.rows,
            bytes=expected.bytes,
            sha256=expected.sha256,
        )

    def prepare_day(
        source: r4.VerifiedSource,
    ) -> FakePrepared:
        events.append(
            f"prepare:{source.day}"
        )

        if (
            source.day
            == fail_prepare_day
        ):
            raise SyntheticFailure(
                f"prepare:{source.day}"
            )

        return FakePrepared(
            day=source.day
        )

    def run_lane(
        prepared: FakePrepared,
        lane: r1.LaneSpec,
    ) -> r4.LaneArtifact:
        assert (
            prepared.day
            == lane.day
        )

        events.append(
            f"run:{lane.lane_id}"
        )

        if (
            lane.lane_id
            == fail_lane_id
        ):
            raise SyntheticFailure(
                f"lane:{lane.lane_id}"
            )

        return r4.LaneArtifact(
            lane_id=lane.lane_id,
            relpath=(
                lane.partition_relpath
            ),
            bytes=1,
            sha256="0" * 64,
            row_count=1,
        )

    return r22.SuccessorHooks(
        attempt_marker_exists=lambda: (
            attempt_exists
        ),

        assert_output_pristine=lambda: (
            events.append(
                "output-pristine"
            )
        ),

        preflight_memory=lambda: (
            events.append(
                "memory-preflight"
            )
            or _good_memory()
        ),

        capture_runtime_memory_baseline=lambda: (
            events.append(
                "memory-baseline"
            )
            or _good_memory()
        ),

        check_runtime_memory=lambda baseline: (
            events.append(
                "memory-runtime"
            )
        ),

        verify_source=verify_source,

        verify_engine_identity=lambda: (
            events.append(
                "engine-identity"
            )
        ),

        prepare_day=prepare_day,

        close_prepared_day=lambda prepared: (
            events.append(
                f"close:{prepared.day}"
            )
        ),

        write_attempt_marker=lambda payload: (
            events.append(
                "marker"
            )
        ),

        run_lane=run_lane,

        verify_partition=lambda artifact: (
            events.append(
                f"partition:{artifact.lane_id}"
            )
        ),

        write_failure_artifact=lambda payload: (
            events.append(
                "failure-artifact"
            )
        ),

        write_final_manifest=lambda payload: (
            events.append(
                "final-manifest"
            )
        ),
    )


def test_r22_contract_is_preauthorization_only():
    r22.validate_r22_contract()

    assert (
        r22.FINAL_SUCCESSOR_RUNNER_FROZEN
        is True
    )

    assert (
        r22.REAL_CALLBACK_BINDING_IMPLEMENTED
        is True
    )

    assert (
        r22.PER_LANE_ANON_BASELINE_AFTER_ENGINE_BINDING
        is True
    )

    assert (
        r22.TOTAL_RSS_ABORT_THRESHOLD_BYTES
        is None
    )

    assert (
        r22.TOTAL_RSS_IS_BOUNDEDNESS_GATE
        is False
    )

    assert (
        r22.P2_ATTEMPT_CONSUMED
        is False
    )

    assert (
        r22.HISTORICAL_SOURCE_OPEN_AUTHORIZED
        is False
    )

    assert (
        r22.ATTEMPT_MARKER_WRITE_AUTHORIZED
        is False
    )

    assert r22.PNL_AUTHORIZED is False


def test_frozen_source_dates_are_exact_utc_24h():
    for day in (
        r1.REAL_DEVELOPMENT_DAYS
    ):
        start, end = (
            r22.utc_day_bounds_ns(
                day
            )
        )

        assert (
            end - start
            == 86_400_000_000_000
        )

        assert (
            start
            % 86_400_000_000_000
            == 0
        )


def test_memory_policy_gates_anon_swap_available_not_total_rss():
    baseline = r22.MemorySnapshot(
        mem_available_bytes=(
            16 * 1024**3
        ),
        rss_anon_bytes=(
            100 * 1024**2
        ),
        vm_swap_bytes=0,
    )

    r22.validate_runtime_memory(
        baseline=baseline,
        observed=r22.MemorySnapshot(
            mem_available_bytes=(
                8 * 1024**3
            ),
            rss_anon_bytes=(
                200 * 1024**2
            ),
            vm_swap_bytes=0,
        ),
    )

    with pytest.raises(
        r22.SuccessorCampaignError,
        match="process_swap_growth",
    ):
        r22.validate_runtime_memory(
            baseline=baseline,
            observed=r22.MemorySnapshot(
                mem_available_bytes=(
                    8 * 1024**3
                ),
                rss_anon_bytes=(
                    200 * 1024**2
                ),
                vm_swap_bytes=4096,
            ),
        )

    with pytest.raises(
        r22.SuccessorCampaignError,
        match="anonymous_growth",
    ):
        r22.validate_runtime_memory(
            baseline=baseline,
            observed=r22.MemorySnapshot(
                mem_available_bytes=(
                    8 * 1024**3
                ),
                rss_anon_bytes=(
                    baseline.rss_anon_bytes
                    + r22.ANON_GROWTH_ABORT_THRESHOLD_BYTES
                    + 1
                ),
                vm_swap_bytes=0,
            ),
        )


def test_success_path_orders_marker_immediately_before_first_lane():
    events: list[str] = []

    summary = (
        r22.run_successor_campaign(
            authorization_value=(
                r3.AUTH_TOKEN
            ),
            hooks=_hooks(
                events=events
            ),
        )
    )

    assert summary.status == (
        "CANONICAL_280_PARTITIONS_COMPLETE"
    )

    assert (
        summary.verified_source_count
        == 7
    )

    assert (
        summary.prepared_day_count
        == 7
    )

    assert (
        summary.completed_day_count
        == 7
    )

    assert (
        summary.completed_lane_count
        == 280
    )

    assert (
        summary.partition_count
        == 280
    )

    assert (
        summary.attempt_consumed
        is True
    )

    verify_positions = [
        i
        for i, event in enumerate(
            events
        )
        if event.startswith(
            "verify:"
        )
    ]

    prepare_positions = [
        i
        for i, event in enumerate(
            events
        )
        if event.startswith(
            "prepare:"
        )
    ]

    assert len(
        verify_positions
    ) == 7

    assert max(
        verify_positions
    ) < min(
        prepare_positions
    )

    engine_index = events.index(
        "engine-identity"
    )

    assert max(
        verify_positions
    ) < engine_index

    assert engine_index < min(
        prepare_positions
    )

    marker_index = events.index(
        "marker"
    )

    first_run_index = next(
        i
        for i, event in enumerate(
            events
        )
        if event.startswith(
            "run:"
        )
    )

    assert (
        events.index(
            "prepare:2026-01-01"
        )
        < marker_index
    )

    assert (
        marker_index + 1
        == first_run_index
    )

    assert events.count(
        "marker"
    ) == 1

    assert len(
        [
            event
            for event in events
            if event.startswith(
                "run:"
            )
        ]
    ) == 280

    assert len(
        [
            event
            for event in events
            if event.startswith(
                "partition:"
            )
        ]
    ) == 280

    assert events[-1] == (
        "final-manifest"
    )

    assert (
        "failure-artifact"
        not in events
    )


def test_first_day_context_failure_does_not_consume_attempt():
    events: list[str] = []

    with pytest.raises(
        r22.SuccessorCampaignError,
        match="PRE_ATTEMPT_FAILURE",
    ):
        r22.run_successor_campaign(
            authorization_value=(
                r3.AUTH_TOKEN
            ),
            hooks=_hooks(
                events=events,
                fail_prepare_day=(
                    "2026-01-01"
                ),
            ),
        )

    assert "marker" not in events

    assert (
        "failure-artifact"
        not in events
    )

    assert not any(
        event.startswith(
            "run:"
        )
        for event in events
    )


def test_first_lane_failure_is_terminal_after_marker():
    events: list[str] = []

    first_lane = (
        r1.build_materialization_plan()[0]
    )

    summary = (
        r22.run_successor_campaign(
            authorization_value=(
                r3.AUTH_TOKEN
            ),
            hooks=_hooks(
                events=events,
                fail_lane_id=(
                    first_lane.lane_id
                ),
            ),
        )
    )

    assert summary.status == (
        "TERMINAL_FAILURE_AFTER_ATTEMPT_CONSUMPTION"
    )

    assert (
        summary.attempt_consumed
        is True
    )

    assert (
        summary.completed_lane_count
        == 0
    )

    marker_index = events.index(
        "marker"
    )

    run_index = events.index(
        f"run:{first_lane.lane_id}"
    )

    assert (
        marker_index + 1
        == run_index
    )

    assert events.count(
        "marker"
    ) == 1

    assert (
        "failure-artifact"
        in events
    )

    assert (
        "final-manifest"
        not in events
    )

    assert len(
        [
            event
            for event in events
            if event.startswith(
                "run:"
            )
        ]
    ) == 1


def test_existing_marker_blocks_all_callbacks():
    events: list[str] = []

    with pytest.raises(
        r22.SuccessorCampaignError,
        match="attempt_already_consumed",
    ):
        r22.run_successor_campaign(
            authorization_value=(
                r3.AUTH_TOKEN
            ),
            hooks=_hooks(
                events=events,
                attempt_exists=True,
            ),
        )

    assert events == []


def test_real_hook_builder_is_construction_only(
    tmp_path,
):
    hooks = (
        r22.build_real_successor_hooks(
            output_root=(
                tmp_path
                / "canonical"
            ),
            scratch_root=(
                tmp_path
                / "scratch"
            ),
        )
    )

    assert isinstance(
        hooks,
        r22.SuccessorHooks,
    )

    assert not (
        tmp_path
        / "canonical"
    ).exists()

    assert not (
        tmp_path
        / "scratch"
    ).exists()
