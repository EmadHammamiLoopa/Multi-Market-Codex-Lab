from __future__ import annotations

import math
import numpy as np

from multimarket import dev040_p1_core as core
from multimarket import dev040_p1_harness as harness
from multimarket import dev040_p1_runner as runner

def _trade(day,gross,action=2):
    return core.TradeEconomic(
        day=day,
        action=action,
        decision_timestamp_us=1,
        entry_timestamp_us=2,
        exit_timestamp_us=3,
        entry_price=100.0,
        exit_price=101.0,
        entry_spread_bps=1.0,
        exit_spread_bps=1.0,
        gross_bps=float(gross),
    )

def test_gross_long_short():
    gl=core.gross_bps(2,99.9,100.0,101.0,101.1)
    gs=core.gross_bps(1,99.9,100.0,98.8,99.0)
    assert gl>0
    assert gs>0

def test_scenario_costs_and_break_even():
    trades=(
        _trade("2026-04-01",12),
        _trade("2026-05-01",8),
        _trade("2026-06-01",6),
        _trade("2026-07-01",14),
    )
    z=core.scenario_metrics(trades,fee_roundtrip_bps=8,slippage_per_side_bps=1)
    assert z["mean_gross_bps"]==10.0
    assert z["mean_net_bps"]==0.0
    assert z["roundtrip_cost_break_even_bps"]==10.0
    assert z["max_extra_slippage_per_side_bps"]==1.0

def test_profit_factor_inf_and_zero():
    p=core.scenario_metrics(
        (_trade("2026-04-01",20),_trade("2026-05-01",20),_trade("2026-06-01",20),_trade("2026-07-01",20)),
        fee_roundtrip_bps=0,
        slippage_per_side_bps=0,
    )
    assert math.isinf(p["profit_factor"])
    q=core.scenario_metrics(
        (_trade("2026-04-01",-2),_trade("2026-05-01",-2),_trade("2026-06-01",-2),_trade("2026-07-01",-2)),
        fee_roundtrip_bps=0,
        slippage_per_side_bps=0,
    )
    assert q["profit_factor"]==0.0

def test_drawdown_and_losing_streak():
    trades=(
        _trade("2026-04-01",12),
        _trade("2026-05-01",-2),
        _trade("2026-06-01",-3),
        _trade("2026-07-01",10),
    )
    z=core.scenario_metrics(trades,fee_roundtrip_bps=0,slippage_per_side_bps=0)
    assert z["max_drawdown_bps"]==5.0
    assert z["max_consecutive_losing_trades"]==2

def test_classification_f0():
    trades=tuple(_trade(f"2026-0{m}-01",-1) for m in range(4,8))
    z=core.scenario_metrics(trades,fee_roundtrip_bps=8,slippage_per_side_bps=1)
    status,gates,tax=core.classify(z,-1)
    assert status=="DEV040_P1_ECONOMIC_BASELINE_FAIL"
    assert tax=="F0_NO_GROSS_EXECUTABLE_EDGE"
    assert not gates["mean_gross_gt_0"]

def test_classification_pass_shape():
    vals=[25,22,24,23]
    trades=tuple(_trade(f"2026-0{m}-01",g) for m,g in zip(range(4,8),vals,strict=True))
    z=core.scenario_metrics(trades,fee_roundtrip_bps=8,slippage_per_side_bps=1)
    status,gates,tax=core.classify(z,20)
    assert status=="DEV040_P1_ECONOMIC_BASELINE_FAIL"  # trade-count gate intentionally fails
    assert tax=="F2_NET_POSITIVE_BUT_UNSTABLE"
    assert gates["mean_net_gt_0"]

def test_forward_guards_and_frozen_parent():
    assert not any(runner.FORWARD_GUARDS.values())
    assert runner.PARENT_P0_SHA=="c328cc52bf7fee9239c1713fd6fedbfc7738f1b448d24b7b537b6111526f118a"
    assert runner.PARENT_P0_BYTES==7289
    assert runner.PARENT_P2_SHA=="df32874a362cd75f646cdca483dc46956797431ac9a5861435639dfbf7f4b311"

def test_harness_smoke():
    assert harness.process_pool_smoke(2)==(1,4,9,16)
