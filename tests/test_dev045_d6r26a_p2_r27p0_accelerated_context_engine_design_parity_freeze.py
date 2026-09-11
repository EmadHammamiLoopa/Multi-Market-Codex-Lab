from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from multimarket import (
    dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20,
)
from multimarket import (
    dev045_d6r26a_p2_r27p0_accelerated_context_engine_design_parity_freeze as r27p0,
)


def _build_pair(tmp_path: Path):
    events = r20.make_synthetic_dual_context_fixture()
    left = r20.build_once_day_context(
        events,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
        scratch_root=tmp_path / "reference",
    )
    right = r20.build_once_day_context(
        events,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
        scratch_root=tmp_path / "candidate",
    )
    return events, left, right


def test_r27p0_contract_is_strictly_preattempt() -> None:
    r27p0.validate_r27p0_contract()

    assert r27p0.P2_ATTEMPT_CONSUMED is False
    assert r27p0.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r27p0.HISTORICAL_SOURCE_REHASH_AUTHORIZED is False
    assert r27p0.SIMULATOR_LANE_AUTHORIZED is False
    assert r27p0.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r27p0.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r27p0.MODEL_FIT_AUTHORIZED is False
    assert r27p0.PNL_AUTHORIZED is False
    assert r27p0.FULL_JAN_JUL_RERUN_FORBIDDEN_IN_R27P0 is True
    assert r27p0.R26P1_PARTIAL_RESIDUE_PRESERVE_REQUIRED is True
    assert r27p0.R26P1_PARTIAL_RESIDUE_REUSE_FORBIDDEN is True


def test_acceleration_candidates_and_speed_gate_are_frozen() -> None:
    assert r27p0.ACCELERATION_CANDIDATES == ("NUMBA_JIT", "RUST_PYO3")
    assert r27p0.MIN_ACCEPTED_SPEEDUP == 10.0
    assert r27p0.EXACT_OUTPUT_PARITY_REQUIRED is True
    assert r27p0.ONE_CAUSAL_RAW_EVENT_PASS_REQUIRED is True


def test_exact_context_parity_accepts_identical_reference_builds(
    tmp_path: Path,
) -> None:
    _, left, right = _build_pair(tmp_path)
    try:
        r27p0.assert_exact_context_parity(left, right)
        assert r27p0.digest_day_context(left) == r27p0.digest_day_context(right)
    finally:
        r20.close_midpoint_index(left.midpoint_index)
        r20.close_midpoint_index(right.midpoint_index)


def test_exact_context_parity_rejects_feature_difference(
    tmp_path: Path,
) -> None:
    _, left, right = _build_pair(tmp_path)
    try:
        changed = np.array(right.feature_cache.values, copy=True)
        changed[0, 0, 0] += 1.0
        changed.setflags(write=False)
        mutated_cache = type(right.feature_cache)(
            decision_local_ns=right.feature_cache.decision_local_ns,
            best_bid_tick=right.feature_cache.best_bid_tick,
            best_ask_tick=right.feature_cache.best_ask_tick,
            values=changed,
        )
        mutated = r20.DayContextBuildResult(
            bounds=right.bounds,
            feature_cache=mutated_cache,
            feature_summary=right.feature_summary,
            midpoint_index=right.midpoint_index,
            raw_event_pass_count=right.raw_event_pass_count,
        )
        with pytest.raises(r27p0.R27P0ParityError, match="feature_values_values"):
            r27p0.assert_exact_context_parity(left, mutated)
    finally:
        r20.close_midpoint_index(left.midpoint_index)
        r20.close_midpoint_index(right.midpoint_index)


def test_speedup_gate_accepts_ten_x_and_rejects_less() -> None:
    reference = r27p0.BenchmarkObservation(
        implementation="R20_PYTHON_REFERENCE",
        event_count=1_000_000,
        elapsed_seconds=100.0,
    )
    accepted = r27p0.BenchmarkObservation(
        implementation="RUST_PYO3",
        event_count=1_000_000,
        elapsed_seconds=10.0,
    )
    rejected = r27p0.BenchmarkObservation(
        implementation="NUMBA_JIT",
        event_count=1_000_000,
        elapsed_seconds=20.0,
    )

    assert r27p0.require_speedup_gate(
        reference=reference,
        candidate=accepted,
    ) == pytest.approx(10.0)

    with pytest.raises(r27p0.R27P0ParityError, match="speedup_gate"):
        r27p0.require_speedup_gate(
            reference=reference,
            candidate=rejected,
        )


def test_bounded_synthetic_benchmark_wrapper_never_requires_historical_io(
    tmp_path: Path,
) -> None:
    events = r20.make_synthetic_dual_context_fixture()
    observation, context = r27p0.benchmark_builder_once(
        implementation="R20_PYTHON_REFERENCE",
        builder=r20.build_once_day_context,
        events=events,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
        scratch_root=tmp_path / "benchmark",
    )
    try:
        assert observation.event_count == int(events.size)
        assert observation.elapsed_seconds > 0.0
        assert observation.events_per_second > 0.0
        assert context.raw_event_pass_count == 1
    finally:
        r20.close_midpoint_index(context.midpoint_index)
