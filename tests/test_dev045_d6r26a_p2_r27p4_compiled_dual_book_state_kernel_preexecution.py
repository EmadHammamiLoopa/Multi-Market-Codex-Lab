from __future__ import annotations

import numpy as np
import pytest

from multimarket import dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9
from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p4_compiled_dual_book_state_kernel_preexecution as r


def test_contract_passes() -> None:
    r.validate_r27p4_contract()


def test_dual_book_kernel_exact_parity_on_r20_fixture() -> None:
    events = r20.make_synthetic_dual_context_fixture()
    kernel = r.build_dual_book_kernel()
    r.assert_dual_book_parity(events, kernel=kernel)


def test_kernel_surfaces_are_read_only_and_nonempty() -> None:
    events = r20.make_synthetic_dual_context_fixture()
    out = r.run_dual_book_kernel(events)
    assert out.local_ns.size > 0
    assert out.midpoint_exchange_ns.size > 0
    assert out.bid_ticks.shape[1] == 5
    assert out.ask_ticks.shape[1] == 5
    assert out.local_ns.flags.writeable is False
    assert out.midpoint_tick_sum.flags.writeable is False
    assert np.all(out.bid_ticks[:, 0] < out.ask_ticks[:, 0])


def test_unknown_event_fails_closed() -> None:
    events = r20.make_synthetic_dual_context_fixture().copy()
    events[0]["ev"] = np.uint64((int(events[0]["ev"]) & ~int(r9.EVENT_KIND_MASK)) | 99)
    with pytest.raises(r.R27P4Error, match="unknown_event_kind"):
        r.run_dual_book_kernel(events)


def test_local_timestamp_regression_fails_closed() -> None:
    events = r20.make_synthetic_dual_context_fixture().copy()
    local_indices = np.flatnonzero((events["ev"] & np.uint64(r9.LOCAL_EVENT)) != 0)
    assert local_indices.size >= 2
    j = int(local_indices[-1])
    events[j]["local_ts"] = 0
    with pytest.raises(r.R27P4Error, match="local_timestamp"):
        r.run_dual_book_kernel(events)


def test_r27p4_remains_preexecution() -> None:
    assert r.FULL_CONTEXT_REPLACEMENT_AUTHORIZED is False
    assert r.REAL_HISTORICAL_BENCHMARK_AUTHORIZED is False
    assert r.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r.DURABLE_CONTEXT_WRITE_AUTHORIZED is False
    assert r.P2_ATTEMPT_CONSUMED is False
    assert r.SIMULATOR_LANE_AUTHORIZED is False
    assert r.MODEL_FIT_AUTHORIZED is False
    assert r.PNL_AUTHORIZED is False
