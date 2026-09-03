from __future__ import annotations

from datetime import datetime, timezone

import pytest

from multimarket.dev045_m3_policy import POLICY_IDS
from multimarket.dev045_m5_prereg import AUTHORIZED_DAYS, TOTAL_BLOCKS
from multimarket.dev045_m6_economic_arena import (
    FillRecord,
    M6ArenaError,
    PRIMARY_SCENARIO,
    STRESS_SCENARIO,
    ReplayAudit,
    account_fill_bucket,
    block_cycle_pnl,
    cycle_block_index,
    run_economic_arena,
)


def ns(day: str, hour: int, minute: int = 0, second: int = 0) -> int:
    dt = datetime.fromisoformat(day).replace(
        hour=hour, minute=minute, second=second, tzinfo=timezone.utc
    )
    return int(dt.timestamp() * 1_000_000_000)


def fill(pid: str, day: str, ts: int, side: str, qty: float, price: float, liquidity: str) -> FillRecord:
    return FillRecord(pid, day, ts, side, qty, price, liquidity)


def all_audits() -> list[ReplayAudit]:
    return [
        ReplayAudit(pid, day, scenario, 0, True)
        for pid in POLICY_IDS
        for day in AUTHORIZED_DAYS
        for scenario in (PRIMARY_SCENARIO, STRESS_SCENARIO)
    ]


def test_primary_cycle_uses_frozen_maker_fees() -> None:
    day = AUTHORIZED_DAYS[0]
    fills = [
        fill("M01", day, ns(day, 0), "BUY", 0.001, 100_000.0, "MAKER"),
        fill("M01", day, ns(day, 0, 0, 1), "SELL", 0.001, 100_100.0, "MAKER"),
    ]
    cycle = account_fill_bucket(fills, scenario=PRIMARY_SCENARIO)[0]
    assert cycle.cash_pnl_before_fees == pytest.approx(0.1)
    assert cycle.fees == pytest.approx((100.0 + 100.1) * 0.0002)
    assert cycle.net_pnl == pytest.approx(0.1 - (200.1 * 0.0002))
    assert cycle.entry_notional == pytest.approx(100.0)


def test_stress_cycle_uses_frozen_1p5x_fee_rates() -> None:
    day = AUTHORIZED_DAYS[0]
    fills = [
        fill("M01", day, ns(day, 0), "BUY", 0.001, 100_000.0, "MAKER"),
        fill("M01", day, ns(day, 0, 0, 1), "SELL", 0.001, 100_100.0, "TAKER"),
    ]
    cycle = account_fill_bucket(fills, scenario=STRESS_SCENARIO)[0]
    assert cycle.fees == pytest.approx((100.0 * 0.0003) + (100.1 * 0.00075))


def test_partial_fills_stay_inside_same_flat_to_flat_cycle() -> None:
    day = AUTHORIZED_DAYS[0]
    fills = [
        fill("M02", day, ns(day, 1), "BUY", 0.0004, 100_000.0, "MAKER"),
        fill("M02", day, ns(day, 1, 0, 1), "BUY", 0.0006, 100_010.0, "MAKER"),
        fill("M02", day, ns(day, 1, 0, 2), "SELL", 0.0003, 100_020.0, "MAKER"),
        fill("M02", day, ns(day, 1, 0, 3), "SELL", 0.0007, 100_030.0, "TAKER"),
    ]
    cycles = account_fill_bucket(fills, scenario=PRIMARY_SCENARIO)
    assert len(cycles) == 1
    assert cycles[0].fill_count == 4
    assert cycles[0].maker_notional > 0.0
    assert cycles[0].taker_notional > 0.0


def test_terminal_nonflat_fails_closed() -> None:
    day = AUTHORIZED_DAYS[0]
    with pytest.raises(M6ArenaError, match="terminal_inventory_not_flat"):
        account_fill_bucket(
            [fill("M03", day, ns(day, 2), "BUY", 0.001, 100_000.0, "MAKER")],
            scenario=PRIMARY_SCENARIO,
        )


def test_inventory_sign_flip_without_observed_flat_fails_closed() -> None:
    day = AUTHORIZED_DAYS[0]
    with pytest.raises(M6ArenaError, match="inventory_sign_flip_without_flat"):
        account_fill_bucket(
            [
                fill("M04", day, ns(day, 3), "BUY", 0.001, 100_000.0, "MAKER"),
                fill("M04", day, ns(day, 3, 0, 1), "SELL", 0.002, 100_010.0, "MAKER"),
            ],
            scenario=PRIMARY_SCENARIO,
        )


def test_fill_order_is_not_silently_sorted() -> None:
    day = AUTHORIZED_DAYS[0]
    with pytest.raises(M6ArenaError, match="out_of_order_fill"):
        account_fill_bucket(
            [
                fill("M05", day, ns(day, 4, 0, 2), "BUY", 0.001, 100_000.0, "MAKER"),
                fill("M05", day, ns(day, 4, 0, 1), "SELL", 0.001, 100_010.0, "MAKER"),
            ],
            scenario=PRIMARY_SCENARIO,
        )


def test_block_assignment_uses_cycle_start_utc_block() -> None:
    day = AUTHORIZED_DAYS[2]
    cycle = account_fill_bucket(
        [
            fill("M06", day, ns(day, 7, 59), "BUY", 0.001, 100_000.0, "MAKER"),
            fill("M06", day, ns(day, 8, 1), "SELL", 0.001, 100_050.0, "MAKER"),
        ],
        scenario=PRIMARY_SCENARIO,
    )[0]
    # Day index 2, hour 07 belongs to block 1 => 2*6+1.
    assert cycle_block_index(cycle) == 13


def test_block_matrix_has_frozen_42_by_8_geometry() -> None:
    empty = {pid: [] for pid in POLICY_IDS}
    matrix = block_cycle_pnl(empty)
    assert tuple(matrix) == tuple(POLICY_IDS)
    assert all(len(matrix[pid]) == TOTAL_BLOCKS for pid in POLICY_IDS)
    assert all(all(x == 0.0 for x in matrix[pid]) for pid in POLICY_IDS)


def test_full_arena_zero_activity_cannot_promote() -> None:
    result = run_economic_arena(primary_fills=[], stress_fills=[], audits=all_audits())
    assert result["schema"] == "DEV045_M6_ECONOMIC_ARENA_V1"
    assert result["development_survivors"] == []
    assert result["live_trading_authorized"] is False
    assert all(not result["policies"][pid]["passes_all_gates"] for pid in POLICY_IDS)


def test_missing_audit_fails_closed() -> None:
    audits = all_audits()[:-1]
    with pytest.raises(M6ArenaError, match="audit_matrix"):
        run_economic_arena(primary_fills=[], stress_fills=[], audits=audits)


def test_unauthorized_day_fails_closed() -> None:
    with pytest.raises(M6ArenaError, match="authorized_day"):
        account_fill_bucket(
            [
                fill("M01", "2026-08-01", ns("2026-08-01", 0), "BUY", 0.001, 100_000.0, "MAKER"),
                fill("M01", "2026-08-01", ns("2026-08-01", 0, 0, 1), "SELL", 0.001, 100_010.0, "MAKER"),
            ],
            scenario=PRIMARY_SCENARIO,
        )
