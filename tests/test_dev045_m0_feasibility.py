from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from multimarket import dev045_m0_feasibility as m0


def test_frozen_scope_and_guards():
    assert m0.SYMBOL=="BTCUSDT"
    assert tuple(d.isoformat() for d in m0.DAYS)==(
        "2026-01-01","2026-02-01","2026-03-01",
        "2026-04-01","2026-05-01","2026-06-01","2026-07-01",
    )
    assert m0.HFTBACKTEST_PIN=="2.4.4"
    assert m0.QUEUE_PRIMARY=="RISK_ADVERSE"
    assert m0.QUEUE_DIAGNOSTIC=="LOG_PROB"
    assert not any(m0.FORWARD_GUARDS.values())


def test_expected_raw_headers_are_frozen():
    assert m0.L2_HEADER=="exchange,symbol,timestamp,local_timestamp,is_snapshot,side,price,amount"
    assert m0.TRADE_HEADER=="exchange,symbol,timestamp,local_timestamp,id,side,price,amount"


def test_aggregate_pass():
    days=[]
    for i in range(7):
        days.append({
            "pass":True,
            "l2":{"rows":100,"snapshot_rows":2,"zero_qty_rows":20,"max_feed_latency_us":1000},
            "trades":{"rows":50,"unknown_rows":0,"max_feed_latency_us":2000},
        })
    a=m0._aggregate(days)
    assert a["days"]==7
    assert a["all_days_pass"] is True
    assert a["total_l2_rows"]==700
    assert a["total_trade_rows"]==350
    assert a["total_snapshot_rows"]==14


def test_aggregate_fail_if_one_day_fails():
    days=[]
    for i in range(7):
        days.append({
            "pass":i!=3,
            "l2":{"rows":1,"snapshot_rows":1,"zero_qty_rows":0,"max_feed_latency_us":0},
            "trades":{"rows":1,"unknown_rows":0,"max_feed_latency_us":0},
        })
    assert m0._aggregate(days)["all_days_pass"] is False


def test_run_rejects_bad_execution_commit(tmp_path):
    with pytest.raises(m0.M0Error):
        m0.run(
            execution_commit="bad",
            output_directory=tmp_path/"x",
            require_canonical_output=False,
        )


def test_run_rejects_existing_output(tmp_path):
    out=tmp_path/"x";out.mkdir()
    with pytest.raises(m0.M0Error):
        m0.run(
            execution_commit="a"*40,
            output_directory=out,
            require_canonical_output=False,
        )
