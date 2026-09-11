from __future__ import annotations

import numpy as np

from multimarket import dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9
from multimarket import dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r


def _bounds(events: np.ndarray) -> tuple[int, int]:
    start = 0
    end = int(events[-1]["local_ts"]) + 1
    return start, end


def test_contract_passes() -> None:
    r.validate_r27p5_contract()


def test_exact_25_feature_and_8_case_parity_on_frozen_fixture() -> None:
    events = r19.make_synthetic_feature_fixture()
    start, end = _bounds(events)
    kernel = r.build_feature_kernel()
    r.assert_exact_feature_parity(
        events,
        nominal_day_start_local_ns=start,
        nominal_day_end_exclusive_local_ns=end,
        kernel=kernel,
    )


def test_compiled_surface_is_float64_and_read_only() -> None:
    events = r19.make_synthetic_feature_fixture()
    start, end = _bounds(events)
    result = r.build_synthetic_compiled_feature_result(
        events,
        nominal_day_start_local_ns=start,
        nominal_day_end_exclusive_local_ns=end,
    )
    assert result.values.dtype == np.dtype("<f8")
    assert result.values.shape[1:] == (8, 25)
    assert result.values.flags.writeable is False
    assert result.decision_local_ns.flags.writeable is False
    assert result.best_bid_tick.flags.writeable is False
    assert result.best_ask_tick.flags.writeable is False


def test_same_local_timestamp_trade_order_remains_causal() -> None:
    events = r19.make_synthetic_feature_fixture().copy()
    # Add exchange flags only; LOCAL feature semantics must remain unchanged.
    events["ev"] = events["ev"] | np.uint64(r9.EXCH_EVENT)
    start, end = _bounds(events)
    r.assert_exact_feature_parity(
        events,
        nominal_day_start_local_ns=start,
        nominal_day_end_exclusive_local_ns=end,
    )


def test_preexecution_guards_remain_closed() -> None:
    assert r.RAW_EVENT_FUSION_COMPLETE is False
    assert r.FULL_CONTEXT_REPLACEMENT_AUTHORIZED is False
    assert r.REAL_HISTORICAL_BENCHMARK_AUTHORIZED is False
    assert r.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r.DURABLE_CONTEXT_WRITE_AUTHORIZED is False
    assert r.P2_ATTEMPT_CONSUMED is False
    assert r.SIMULATOR_LANE_AUTHORIZED is False
    assert r.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r.MODEL_FIT_AUTHORIZED is False
    assert r.PNL_AUTHORIZED is False
