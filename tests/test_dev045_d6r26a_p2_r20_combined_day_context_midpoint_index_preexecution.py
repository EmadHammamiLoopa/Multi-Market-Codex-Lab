from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from multimarket import (
    dev045_d6r26a_p1_synthetic_candidate_labeler as p1,
)
from multimarket import (
    dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b,
)
from multimarket import (
    dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9,
)
from multimarket import (
    dev045_d6r26a_p2_r18_generic_lane_materializer_integration_preexecution as r18,
)
from multimarket import (
    dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19,
)
from multimarket import (
    dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20,
)


def _build(
    tmp_path: Path,
):
    data = (
        r20.make_synthetic_dual_context_fixture()
    )

    result = r20.build_once_day_context(
        data,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=(
            100_000_000_000
        ),
        scratch_root=tmp_path,
    )

    return data, result


def test_r20_contract_is_strictly_preauthorization():
    r20.validate_r20_contract()

    assert (
        r20.COMBINED_RAW_EVENT_PASSES_PER_DAY
        == 1
    )
    assert (
        r20.SECOND_RAW_PASS_FOR_MIDPOINTS_FORBIDDEN
        is True
    )
    assert (
        r20.PER_LANE_RAW_MIDPOINT_RESCAN_FORBIDDEN
        is True
    )
    assert (
        r20.PER_LANE_RAW_FEATURE_RESCAN_FORBIDDEN
        is True
    )

    assert r20.MIDPOINT_INDEX_FILE_BACKED is True

    assert (
        r20.MIDPOINT_HISTORY_PYTHON_OBJECT_MATERIALIZATION_FORBIDDEN
        is True
    )

    assert r20.P2_ATTEMPT_CONSUMED is False
    assert r20.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r20.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r20.CANONICAL_LABEL_WRITE_AUTHORIZED is False


def test_combined_single_pass_feature_cache_is_exact_r19_parity(
    tmp_path: Path,
):
    data, combined = _build(
        tmp_path
    )

    try:
        reference = (
            r19.build_once_day_dense_feature_cache(
                data,
                nominal_day_start_local_ns=0,
                nominal_day_end_exclusive_local_ns=(
                    100_000_000_000
                ),
            )
        )

        assert (
            combined.feature_summary
            == reference.summary
        )

        observed = (
            combined.feature_cache
        )
        expected = (
            reference.cache
        )

        assert np.array_equal(
            observed.decision_local_ns,
            expected.decision_local_ns,
        )

        assert np.array_equal(
            observed.best_bid_tick,
            expected.best_bid_tick,
        )

        assert np.array_equal(
            observed.best_ask_tick,
            expected.best_ask_tick,
        )

        assert np.array_equal(
            observed.values,
            expected.values,
        )

        assert (
            combined.raw_event_pass_count
            == 1
        )

    finally:
        r20.close_midpoint_index(
            combined.midpoint_index
        )


def test_midpoint_file_index_is_exact_r9_batch_parity(
    tmp_path: Path,
):
    data, combined = _build(
        tmp_path
    )

    index = combined.midpoint_index

    try:
        expected = (
            r9.decode_exchange_midpoints(
                data
            )
        )

        assert index.count == len(
            expected
        )

        assert index.bytes == (
            index.count
            * r20.MIDPOINT_RECORD_BYTES
        )

        assert index.path.is_file()

        assert isinstance(
            index.records,
            np.memmap,
        )

        assert (
            index.records.flags.writeable
            is False
        )

        assert index.records.dtype == (
            r20.MIDPOINT_RECORD_DTYPE
        )

        for i, midpoint in enumerate(
            expected
        ):
            record = (
                index.records[i]
            )

            assert int(
                record["exchange_ns"]
            ) == int(
                midpoint.exchange_ns
            )

            assert int(
                record["mid_tick_sum"]
            ) == (
                int(
                    midpoint.best_bid_tick
                )
                + int(
                    midpoint.best_ask_tick
                )
            )

        assert (
            index.source_exchange_observed_through_ns
            == int(
                np.max(
                    data["exch_ts"]
                )
            )
        )

    finally:
        path = index.path

        r20.close_midpoint_index(
            index
        )

        assert not path.exists()


def test_midpoint_asof_is_exact_p1_rule(
    tmp_path: Path,
):
    data, combined = _build(
        tmp_path
    )

    index = combined.midpoint_index

    try:
        expected_series = (
            r9.decode_exchange_midpoints(
                data
            )
        )

        observed_through = int(
            np.max(
                data["exch_ts"]
            )
        )

        targets = {
            int(
                expected_series[0].exchange_ns
            ),
            int(
                expected_series[0].exchange_ns
            ) + 1,
            int(
                expected_series[
                    len(expected_series) // 2
                ].exchange_ns
            ),
            int(
                expected_series[-1].exchange_ns
            ),
        }

        for target in sorted(
            targets
        ):
            expected = p1.mid_asof(
                midpoints=expected_series,
                target_exchange_ns=target,
                source_exchange_observed_through_ns=(
                    observed_through
                ),
            )

            observed = (
                r20.midpoint_asof(
                    index=index,
                    target_exchange_ns=target,
                )
            )

            assert observed == pytest.approx(
                expected,
                rel=0.0,
                abs=1e-12,
            )

        assert (
            r20.midpoint_asof(
                index=index,
                target_exchange_ns=(
                    observed_through + 1
                ),
            )
            is None
        )

    finally:
        r20.close_midpoint_index(
            index
        )


def test_all_eight_feature_cases_remain_consumable_from_combined_cache(
    tmp_path: Path,
):
    _, combined = _build(
        tmp_path
    )

    try:
        cache = (
            combined.feature_cache
        )

        decision = int(
            cache.decision_local_ns[0]
        )

        best_bid = int(
            cache.best_bid_tick[0]
        )

        best_ask = int(
            cache.best_ask_tick[0]
        )

        for side, distance in (
            r18.CANDIDATE_GRID
        ):
            candidate = p1.CandidateSpec(
                side=side,
                distance_ticks=int(
                    distance
                ),
                decision_local_ns=decision,
                best_bid_tick=best_bid,
                best_ask_tick=best_ask,
            )

            vector = (
                r18.lookup_feature_vector(
                    cache=cache,
                    candidate=candidate,
                )
            )

            assert tuple(
                vector.values
            ) == tuple(
                r8b.FEATURE_NAMES
            )

            assert all(
                int(ts) == decision
                for ts in (
                    vector.observable_local_ns.values()
                )
            )

    finally:
        r20.close_midpoint_index(
            combined.midpoint_index
        )


def test_combined_builder_does_not_delegate_to_second_r19_raw_pass(
    tmp_path: Path,
    monkeypatch,
):
    data = (
        r20.make_synthetic_dual_context_fixture()
    )

    def forbidden_second_pass(*args, **kwargs):
        del args, kwargs
        raise AssertionError(
            "second_raw_pass_forbidden"
        )

    monkeypatch.setattr(
        r19,
        "build_once_day_dense_feature_cache",
        forbidden_second_pass,
    )

    result = r20.build_once_day_context(
        data,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=(
            100_000_000_000
        ),
        scratch_root=tmp_path,
    )

    try:
        assert (
            result.raw_event_pass_count
            == 1
        )
    finally:
        r20.close_midpoint_index(
            result.midpoint_index
        )


def test_midpoint_index_name_collision_fails_closed(
    tmp_path: Path,
):
    _, first = _build(
        tmp_path
    )

    try:
        data = (
            r20.make_synthetic_dual_context_fixture()
        )

        with pytest.raises(
            r20.CombinedDayContextError,
            match="midpoint_index_exists",
        ):
            r20.build_once_day_context(
                data,
                nominal_day_start_local_ns=0,
                nominal_day_end_exclusive_local_ns=(
                    100_000_000_000
                ),
                scratch_root=tmp_path,
            )

    finally:
        r20.close_midpoint_index(
            first.midpoint_index
        )
