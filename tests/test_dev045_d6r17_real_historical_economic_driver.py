from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

from multimarket import dev045_d6r5_memmap_adapter as adapter
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_d6r17_real_historical_economic_driver as d
from multimarket import dev045_d6r17_real_historical_economic_driver_contract as c
from multimarket import dev045_m5a_a0_support_semantics as m5a
from multimarket import dev045_m6_policy_integration as d3
from multimarket.dev044_t0_strategy_contract import StrategyState


def test_implementation_stage_surfaces_stay_closed():
    assert d.CANONICAL_SOURCE_OPEN_IMPLEMENTED is False
    assert (
        d.CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT
        is False
    )
    assert d.AUTOMATIC_RETRY is False
    assert d.CANONICAL_PNL_WRITE_ENABLED is False
    assert d.NETWORK_ACQUISITION_ENABLED is False
    assert d.LIVE_TRADING_AUTHORIZED is False


def test_terminal_shutdown_lead_is_derived_from_frozen_latency():
    assert d.terminal_shutdown_lead_ns(
        "Q0_PRIMARY_250_250"
    ) == 2_000_000_000

    assert d.terminal_shutdown_lead_ns(
        "Q0_STRESS_500_500"
    ) == 3_000_000_000


def test_contract_and_matrix_identity():
    c.validate_contract()

    assert c.POLICY_IDS == (
        "M01",
        "M02",
        "M03",
        "M04",
        "M05",
        "M06",
        "M07",
        "M08",
    )

    assert c.SCENARIOS == (
        "Q0_PRIMARY_250_250",
        "Q0_STRESS_500_500",
    )

    assert len(c.DAY_SPECS) == 7
    assert (
        c.TOTAL_POLICY_DAY_SCENARIO_REPLAYS
        == 112
    )


def _state() -> StrategyState:
    return StrategyState(
        ofi_1s=0.1,
        ofi_16s=0.1,
        ofi_32s=0.1,
        mid_price=100.0,
        round_level=100.0,
        round_distance_bps=0.0,
        spread_bps=3.0,
    )


def test_historical_legacy_index_exact_only():
    points = (
        d.HistoricalLegacyStatePoint(
            1_000_000,
            _state(),
        ),
        d.HistoricalLegacyStatePoint(
            2_000_000,
            _state(),
        ),
    )

    idx = d.HistoricalLegacyStateIndex(
        day="2026-04-01",
        points=points,
    )

    assert idx.exact(1_000_000) is points[0].state
    assert idx.exact(1_500_000) is None
    assert idx.exact(2_000_000) is points[1].state


def test_historical_legacy_index_rejects_duplicates():
    with pytest.raises(
        d.RealHistoricalDriverError,
        match="legacy_index_not_strict",
    ):
        d.HistoricalLegacyStateIndex(
            day="2026-04-01",
            points=(
                d.HistoricalLegacyStatePoint(
                    1_000,
                    _state(),
                ),
                d.HistoricalLegacyStatePoint(
                    1_000,
                    _state(),
                ),
            ),
        )


def _support(
    day: str = "2026-04-01",
) -> d.HistoricalAdapterSupport:
    a0 = m5a.ExactA0ScoreIndex(
        day=day,
        points=(
            m5a.A0ScorePoint(
                1_000_000,
                0.75,
            ),
        ),
    )

    legacy = d.HistoricalLegacyStateIndex(
        day=day,
        points=(
            d.HistoricalLegacyStatePoint(
                1_000_000,
                _state(),
            ),
        ),
    )

    return d.HistoricalAdapterSupport(
        a0_index=a0,
        legacy_index=legacy,
    )


def test_adapter_support_fail_closed_on_apr_jul_missing():
    with pytest.raises(
        d.RealHistoricalDriverError,
        match=(
            "required_historical_adapter_support_missing"
        ),
    ):
        d._validate_support(
            policy_id="M06",
            day="2026-04-01",
            support=None,
        )


def test_adapter_support_forbidden_on_jan_mar():
    with pytest.raises(
        d.RealHistoricalDriverError,
        match=(
            "adapter_support_on_frozen_unavailable_day"
        ),
    ):
        d._validate_support(
            policy_id="M06",
            day="2026-01-01",
            support=_support(),
        )


def test_adapter_support_forbidden_for_nonadapter():
    with pytest.raises(
        d.RealHistoricalDriverError,
        match=(
            "adapter_support_for_nonadapter_policy"
        ),
    ):
        d._validate_support(
            policy_id="M02",
            day="2026-04-01",
            support=_support(),
        )


def test_canonical_day_matrix_gate_fails_before_source_use():
    with pytest.raises(
        d.RealHistoricalDriverError,
        match="execution_gate_closed",
    ):
        d.run_canonical_day_matrix(
            None,  # must never be touched with closed gate
            day="2026-01-01",
            support_by_policy={},
            authorization_token=c.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )


def test_module_does_not_open_canonical_files():
    text = Path(
        d.__file__
    ).read_text(
        encoding="utf-8"
    )

    forbidden = (
        "open_canonical_jan(",
        "_open_verified_file(",
        "np.load(",
        "numpy.load(",
        "requests.",
        "urllib.",
        "httpx.",
    )

    for token in forbidden:
        assert token not in text


@pytest.mark.skipif(
    importlib.util.find_spec(
        "hftbacktest"
    ) is None,
    reason=(
        "patched hftbacktest is verified "
        "in dedicated D6R17 CI"
    ),
)
def test_continuous_kernel_runs_multiple_cycles_to_eod(
    tmp_path,
):
    import numpy as np
    import hftbacktest as h

    day = "2026-01-01"

    first = d3._policy_fixture(
        day
    )

    second = first.copy()

    second["exch_ts"] += 80_000_000_000
    second["local_ts"] += 80_000_000_000

    data = np.concatenate(
        (first, second)
    )

    assert data.dtype == h.event_dtype

    assert np.all(
        data["local_ts"][1:]
        >= data["local_ts"][:-1]
    )

    path = (
        tmp_path
        / "synthetic_two_cycle.npy"
    )

    np.save(
        path,
        data,
        allow_pickle=False,
    )

    digest = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()

    source = adapter._open_verified_file(
        path,
        expected_sha256=digest,
        expected_bytes=int(
            path.stat().st_size
        ),
        expected_rows=len(data),
    )

    try:
        result = (
            d.run_bound_verified_replay(
                source,
                policy_id="M02",
                day=day,
                scenario=(
                    "Q0_PRIMARY_250_250"
                ),
                support=None,
                initial_snapshot=(
                    d3._policy_initial_snapshot()
                ),
            )
        )

        # Core D6R17 successor proof:
        # first flat lifecycle does NOT terminate replay.
        assert result.natural_end_of_data is True
        assert result.terminal_flat is True
        assert result.terminal_position == 0.0

        assert result.forced_flatten_count >= 2

        # Regression for the exact rc=10 failure:
        # every actual MARKET flatten must use a fresh ID.
        assert len(result.flatten_order_ids) >= 2
        assert len(set(result.flatten_order_ids)) == (
            len(result.flatten_order_ids)
        )
        assert result.flatten_order_ids[0] == (
            m4.FLATTEN_ORDER_ID
        )
        assert result.flatten_order_ids == tuple(
            range(
                m4.FLATTEN_ORDER_ID,
                m4.FLATTEN_ORDER_ID
                + len(result.flatten_order_ids),
            )
        )

        assert len(result.cycles) >= 2

        assert result.maker_fill_count >= 2
        assert result.taker_fill_count >= 2
        assert result.total_fill_count >= 4

        # wait_next_feed wakeups are simulator-visible wakeups,
        # not an identity count of raw ndarray rows.
        assert result.market_wakeups > 0
        assert result.policy_epochs > 60

        # Frozen sample-boundary integrity:
        # no post-EOD cleanup is allowed.
        assert result.terminal_shutdown_started is True
        assert result.terminal_shutdown_quiescent is True
        assert result.terminal_working_quote_slots == 0
        assert result.terminal_position == 0.0
        assert result.audit.execution_integrity_failures == 0
        assert result.audit.terminal_flat is True

        assert (
            result.terminal_shutdown_start_ns
            is not None
        )

        assert (
            result.terminal_shutdown_start_ns
            >= result.terminal_shutdown_cutoff_ns
        )

        assert (
            result.terminal_shutdown_start_ns
            - result.terminal_shutdown_cutoff_ns
            < d.d1.BASE_MAKER_STEP_NS
        )

        # Driver closes hftbacktest first but does not own/unmap source.
        assert source._closed is False

    finally:
        source.close()

    assert source._closed is True
