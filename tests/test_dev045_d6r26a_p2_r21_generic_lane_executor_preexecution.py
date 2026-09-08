from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
import pytest

from multimarket import (
    dev045_d6r26a_p1_synthetic_candidate_labeler as p1,
)
from multimarket import (
    dev045_d6r26a_p2_r14_synthetic_candidate_grid_real_engine_preexecution as r14,
)
from multimarket import (
    dev045_d6r26a_p2_r21_generic_lane_executor_preexecution as r21,
)


def _read(
    root: Path,
    artifact,
):
    path = (
        Path(root)
        / artifact.relpath
    )

    assert path.is_file()

    return (
        pq.ParquetFile(
            path
        )
        .read()
        .to_pydict()
    )


def test_r21_contract_is_strictly_preauthorization():
    r21.validate_r21_contract()

    assert (
        r21.FRESH_ENGINE_PER_LANE_REQUIRED
        is True
    )

    assert (
        r21.ONE_ENGINE_FOR_ALL_CANDIDATES_IN_LANE
        is True
    )

    assert (
        r21.FILL_QTY_FROM_REMAINING_LEAVES_DELTA
        is True
    )

    assert (
        r21.DIRECT_EXEC_QTY_ACCUMULATION_FORBIDDEN
        is True
    )

    assert (
        r21.MARKOUTS_USE_R20_FILE_BACKED_INDEX
        is True
    )

    assert (
        r21.P2_ATTEMPT_CONSUMED
        is False
    )

    assert (
        r21.HISTORICAL_SOURCE_OPEN_AUTHORIZED
        is False
    )

    assert (
        r21.ATTEMPT_MARKER_WRITE_AUTHORIZED
        is False
    )


def test_no_fill_lane_runs_four_sequential_candidates_in_one_exact_engine(
    tmp_path: Path,
):
    root = (
        tmp_path
        / "no_fill_output"
    )

    scratch = (
        tmp_path
        / "no_fill_scratch"
    )

    summary = (
        r21.run_synthetic_no_fill_lane(
            output_root=root,
            scratch_root=scratch,
        )
    )

    assert summary.candidate_count == 4

    assert (
        summary.first_decision_local_ns
        == 31_000_000_000
    )

    assert (
        summary.last_decision_local_ns
        == 46_000_000_000
    )

    assert summary.accepted_count == 4
    assert (
        summary.rejected_at_arrival_count
        == 0
    )
    assert (
        summary.censored_before_placement_count
        == 0
    )

    assert summary.fill_event_count == 0
    assert (
        summary.filled_candidate_count
        == 0
    )

    assert (
        summary.canceled_candidate_count
        == 4
    )

    # Last 46s candidate reaches its cancel lifecycle after feed EOF.
    # Its longer horizons are censored rather than causing lane failure.
    assert (
        summary.eof_censored_candidate_count
        >= 1
    )

    assert (
        summary.artifact.row_count
        == 4
    )

    data = _read(
        root,
        summary.artifact,
    )

    assert data[
        "decision_local_ns"
    ] == [
        31_000_000_000,
        36_000_000_000,
        41_000_000_000,
        46_000_000_000,
    ]

    assert data["side"] == [
        "BID",
        "BID",
        "BID",
        "BID",
    ]

    assert data[
        "distance_ticks"
    ] == [0, 0, 0, 0]

    assert data["phase"] == [
        1,
        1,
        1,
        1,
    ]

    # Early candidates are fully observed no-fill.
    assert (
        data[
            "fill_5s__state"
        ][0]
        == p1.NOT_FILLED_WITHIN_TAU
    )

    # Final decision survives EOF and is censored only where required.
    assert (
        data[
            "fill_250ms__state"
        ][-1]
        == p1.NOT_FILLED_WITHIN_TAU
    )

    assert (
        data[
            "fill_500ms__state"
        ][-1]
        == p1.NOT_FILLED_WITHIN_TAU
    )

    assert (
        data[
            "fill_1s__state"
        ][-1]
        == p1.NOT_FILLED_WITHIN_TAU
    )

    assert (
        data[
            "fill_2s__state"
        ][-1]
        == p1.CENSORED
    )

    assert (
        data[
            "fill_5s__state"
        ][-1]
        == p1.CENSORED
    )


def test_fill_path_labels_match_frozen_r14_reference_exactly(
    tmp_path: Path,
):
    expected = r14.run_grid_case(
        side="BID",
        distance_ticks=0,
        with_fill=True,
    )

    root = (
        tmp_path
        / "fill_output"
    )

    scratch = (
        tmp_path
        / "fill_scratch"
    )

    summary = (
        r21.run_synthetic_fill_lane(
            output_root=root,
            scratch_root=scratch,
        )
    )

    assert summary.candidate_count >= 1
    assert summary.accepted_count >= 1
    assert summary.fill_event_count >= 1
    assert (
        summary.filled_candidate_count
        >= 1
    )

    data = _read(
        root,
        summary.artifact,
    )

    assert data[
        "decision_local_ns"
    ][0] == int(
        expected.candidate.decision_local_ns
    )

    assert data[
        "placement_outcome"
    ][0] == expected.placement_outcome

    suffixes = {
        250_000_000: "250ms",
        500_000_000: "500ms",
        1_000_000_000: "1s",
        2_000_000_000: "2s",
        5_000_000_000: "5s",
    }

    for label in expected.labels.fill_labels:
        suffix = suffixes[
            int(
                label.horizon_ns
            )
        ]

        assert (
            data[
                f"fill_{suffix}__state"
            ][0]
            == label.state
        )

        assert (
            data[
                f"fill_{suffix}__any_fill"
            ][0]
            == label.any_fill_within_tau
        )

        observed_fraction = data[
            f"fill_{suffix}__fill_fraction"
        ][0]

        if (
            label.fill_fraction_at_tau
            is None
        ):
            assert (
                observed_fraction
                is None
            )
        else:
            assert (
                observed_fraction
                == pytest.approx(
                    label.fill_fraction_at_tau,
                    rel=0.0,
                    abs=1e-12,
                )
            )

        assert (
            data[
                f"fill_{suffix}__fill_fraction_censored"
            ][0]
            == label.fill_fraction_censored
        )

    for label in expected.labels.markout_labels:
        suffix = suffixes[
            int(
                label.horizon_ns
            )
        ]

        assert (
            data[
                f"markout_{suffix}__status"
            ][0]
            == label.status
        )

        observed = data[
            f"markout_{suffix}__value_bps"
        ][0]

        if label.value_bps is None:
            assert observed is None
        else:
            assert observed == pytest.approx(
                label.value_bps,
                rel=0.0,
                abs=1e-12,
            )


def test_index_label_builder_does_not_require_python_midpoint_history():
    assert (
        r21.MARKOUTS_USE_R20_FILE_BACKED_INDEX
        is True
    )

    assert (
        r21.FULL_MIDPOINT_HISTORY_MATERIALIZATION_FORBIDDEN
        is True
    )

    assert (
        r21.PER_CANDIDATE_RAW_MIDPOINT_SCAN_FORBIDDEN
        is True
    )
