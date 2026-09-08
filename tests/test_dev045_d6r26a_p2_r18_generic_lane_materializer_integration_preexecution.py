from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
import pytest

from multimarket import (
    dev045_d6r26a_p1_synthetic_candidate_labeler as p1,
)
from multimarket import (
    dev045_d6r26a_p2_r4_canonical_materialization_runner_preexec as r4,
)
from multimarket import (
    dev045_d6r26a_p2_r8a_real_hooks_writer_preexecution as r8a,
)
from multimarket import (
    dev045_d6r26a_p2_r15_sequential_lane_real_engine_preexecution as r15,
)
from multimarket import (
    dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17,
)
from multimarket import (
    dev045_d6r26a_p2_r18_generic_lane_materializer_integration_preexecution as r18,
)


_SUFFIX = {
    250_000_000: "250ms",
    500_000_000: "500ms",
    1_000_000_000: "1s",
    2_000_000_000: "2s",
    5_000_000_000: "5s",
}


def _read_partition(
    root: Path,
    artifact: r4.LaneArtifact,
):
    path = Path(root) / artifact.relpath

    assert path.is_file()

    return (
        path,
        pq.ParquetFile(path).read(),
    )


def test_r18_contract_is_still_preauthorization_only():
    r18.validate_r18_contract()

    assert r18.P2_ATTEMPT_CONSUMED is False
    assert r18.R4_FULL_RUNNER_BINDING_CREATED is False
    assert r18.EXECUTION_AUTHORIZATION_CREATED is False

    assert r18.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert (
        r18.HISTORICAL_CANDIDATE_SIMULATION_AUTHORIZED
        is False
    )
    assert r18.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r18.CANONICAL_LABEL_WRITE_AUTHORIZED is False

    assert r17.RAW_FEATURE_PASSES_PER_DAY == 1
    assert r17.PER_LANE_RAW_FEATURE_RESCAN_FORBIDDEN is True
    assert r17.FEATURE_CACHE_SHARED_ACROSS_ALL_40_LANES is True


def test_exact_sequential_engine_to_dense_cache_to_parquet_to_atomic_artifact(
    tmp_path: Path,
):
    root = tmp_path / "sequential"

    artifact, cache, result = (
        r18.run_synthetic_sequential_materialization(
            output_root=root,
        )
    )

    assert isinstance(artifact, r4.LaneArtifact)
    assert artifact.row_count == 3

    assert tuple(
        item.candidate.decision_local_ns
        for item in result.candidates
    ) == r15.SEQUENTIAL_DECISION_LOCAL_NS

    assert cache.decision_count == 3

    expected_layout = r17.feature_cache_layout(
        decision_count=3,
    )

    assert cache.total_bytes == expected_layout.total_bytes
    assert cache.values.shape == (3, 8, 25)

    assert cache.decision_local_ns.flags.writeable is False
    assert cache.best_bid_tick.flags.writeable is False
    assert cache.best_ask_tick.flags.writeable is False
    assert cache.values.flags.writeable is False

    # The lane consumes the shared cache, not raw events or histories.
    assert not hasattr(cache, "events")
    assert not hasattr(cache, "books")
    assert not hasattr(cache, "flows")
    assert not hasattr(cache, "decoder")
    assert not hasattr(cache, "accumulator")

    for item in result.candidates:
        observed = r18.lookup_feature_vector(
            cache=cache,
            candidate=item.candidate,
        )

        assert tuple(observed.values) == tuple(
            item.feature_vector.values
        )

        for name, expected in item.feature_vector.values.items():
            assert observed.values[name] == expected

    path, table = _read_partition(
        root,
        artifact,
    )

    assert table.num_rows == 3

    data = table.to_pydict()

    assert data["decision_local_ns"] == list(
        r15.SEQUENTIAL_DECISION_LOCAL_NS
    )

    assert data["side"] == ["BID", "BID", "BID"]
    assert data["distance_ticks"] == [0, 0, 0]
    assert data["phase"] == [1, 1, 1]

    for suffix in _SUFFIX.values():
        assert data[
            f"fill_{suffix}__state"
        ] == [
            p1.NOT_FILLED_WITHIN_TAU,
            p1.NOT_FILLED_WITHIN_TAU,
            p1.NOT_FILLED_WITHIN_TAU,
        ]

        assert data[
            f"markout_{suffix}__status"
        ] == [
            p1.MARKOUT_NOT_APPLICABLE_NO_FILL,
            p1.MARKOUT_NOT_APPLICABLE_NO_FILL,
            p1.MARKOUT_NOT_APPLICABLE_NO_FILL,
        ]

    r8a.verify_partition_impl(
        root=root,
        artifact=artifact,
    )

    # Atomic publish is once-only.
    with pytest.raises(
        r8a.RealHooksPreexecutionError,
        match="artifact_already_exists",
    ):
        r8a.write_partition_bytes_impl(
            root=root,
            lane=next(
                lane
                for lane in __import__(
                    "multimarket.dev045_d6r26a_p2_r1_canonical_label_materializer_preauth",
                    fromlist=["build_materialization_plan"],
                ).build_materialization_plan()
                if lane.lane_id == artifact.lane_id
            ),
            payload=path.read_bytes(),
            row_count=artifact.row_count,
        )


def test_exact_fill_engine_labels_survive_canonical_materialization(
    tmp_path: Path,
):
    root = tmp_path / "fill"

    artifact, cache, result = (
        r18.run_synthetic_fill_materialization(
            output_root=root,
        )
    )

    assert artifact.row_count == 1
    assert result.fills

    observed = r18.lookup_feature_vector(
        cache=cache,
        candidate=result.candidate,
    )

    for name, expected in result.feature_vector.values.items():
        assert observed.values[name] == expected

    _, table = _read_partition(
        root,
        artifact,
    )

    assert table.num_rows == 1

    row = {
        name: values[0]
        for name, values in table.to_pydict().items()
    }

    assert row["decision_local_ns"] == int(
        result.candidate.decision_local_ns
    )
    assert row["side"] == "BID"
    assert row["distance_ticks"] == 0
    assert row["placement_outcome"] == (
        result.placement_outcome
    )

    for label in result.labels.fill_labels:
        suffix = _SUFFIX[
            int(label.horizon_ns)
        ]

        assert row[
            f"fill_{suffix}__state"
        ] == label.state

        assert row[
            f"fill_{suffix}__any_fill"
        ] == label.any_fill_within_tau

        assert row[
            f"fill_{suffix}__fill_fraction_censored"
        ] == label.fill_fraction_censored

    for label in result.labels.markout_labels:
        suffix = _SUFFIX[
            int(label.horizon_ns)
        ]

        assert row[
            f"markout_{suffix}__status"
        ] == label.status

        observed_value = row[
            f"markout_{suffix}__value_bps"
        ]

        if label.value_bps is None:
            assert observed_value is None
        else:
            assert observed_value == pytest.approx(
                label.value_bps,
                rel=0.0,
                abs=1e-12,
            )

    r8a.verify_partition_impl(
        root=root,
        artifact=artifact,
    )
