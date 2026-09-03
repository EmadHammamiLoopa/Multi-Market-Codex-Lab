from __future__ import annotations

from types import SimpleNamespace
import numpy as np

from multimarket import dev044_t0_strategy_contract as c
from multimarket import dev044_t1_execution as x


def synthetic_day(*,seconds=2200,base=100.0):
    n=seconds*4+1
    ts=np.arange(n,dtype=np.int64)*250_000
    bid=np.full(n,base,dtype=float)
    ask=np.full(n,base,dtype=float)
    valid=np.ones(n,dtype=bool)
    return SimpleNamespace(ts=ts,bid=bid,ask=ask,book_valid=valid)


def test_long_take_profit_then_response_exit():
    d=synthetic_day()
    decision=0
    entry_i=1
    touch_i=1+40
    response_i=touch_i+1
    d.bid[touch_i:]=100.40
    d.ask[touch_i:]=100.40
    d.bid[response_i:]=100.35
    d.ask[response_i:]=100.35
    r=x.execute_candidate_day(
        candidate_id="T01U",day_name="2026-04-01",day=d,
        decisions=[decision],actions=[c.LONG],
    )
    assert r.execution_integrity_failures==0
    assert len(r.trades)==1
    t=r.trades[0]
    assert t.exit_reason==x.EXIT_TP
    assert t.barrier_touch_timestamp_us==touch_i*250_000
    assert t.exit_timestamp_us==response_i*250_000
    assert t.gross_bps>32.0


def test_short_stop_loss_then_response_exit():
    d=synthetic_day()
    decision=0
    entry_i=1
    touch_i=1+20
    response_i=touch_i+1
    d.ask[touch_i:]=100.40
    d.bid[touch_i:]=100.40
    d.ask[response_i:]=100.45
    d.bid[response_i:]=100.45
    r=x.execute_candidate_day(
        candidate_id="T01U",day_name="2026-04-01",day=d,
        decisions=[decision],actions=[c.SHORT],
    )
    t=r.trades[0]
    assert t.exit_reason==x.EXIT_SL
    assert t.gross_bps<-32.0


def test_forced_horizon_includes_response_latency():
    d=synthetic_day()
    r=x.execute_candidate_day(
        candidate_id="T01U",day_name="2026-04-01",day=d,
        decisions=[0],actions=[c.LONG],
    )
    t=r.trades[0]
    assert t.exit_reason==x.EXIT_HORIZON
    assert t.entry_timestamp_us==250_000
    assert t.exit_timestamp_us==(1800*1_000_000)+500_000


def test_flat_only_ignores_actions_while_open():
    d=synthetic_day(seconds=4000)
    decisions=[0,60_000_000,1900_000_000]
    actions=[c.LONG,c.SHORT,c.LONG]
    r=x.execute_candidate_day(
        candidate_id="T01U",day_name="2026-04-01",day=d,
        decisions=decisions,actions=actions,
    )
    assert len(r.trades)==2
    assert r.ignored_overlap_actions==1


def test_invalid_full_path_is_execution_failure():
    d=synthetic_day()
    d.book_valid[100]=False
    r=x.execute_candidate_day(
        candidate_id="T01U",day_name="2026-04-01",day=d,
        decisions=[0],actions=[c.LONG],
    )
    assert len(r.trades)==0
    assert r.execution_integrity_failures==1


def test_latency_stress_changes_entry_and_forced_exit():
    d=synthetic_day()
    r=x.execute_candidate_day(
        candidate_id="T01U",day_name="2026-04-01",day=d,
        decisions=[0],actions=[c.LONG],
        entry_latency_ms=500,response_latency_ms=500,
    )
    t=r.trades[0]
    assert t.entry_timestamp_us==500_000
    assert t.exit_timestamp_us==1801_000_000


def test_economics_cost_pf_and_drawdown():
    d=synthetic_day(seconds=5000)
    # Make two horizon trades with deterministic realized exits.
    # First profitable long.
    d.bid[7202]=101.0;d.ask[7202]=101.0
    # second trade starts after first is flat and loses.
    start=2000_000_000
    ei=start//250_000+1
    fi=ei+7200+1
    d.bid[fi]=99.0;d.ask[fi]=99.0
    r=x.execute_candidate_day(
        candidate_id="T01U",day_name="2026-04-01",day=d,
        decisions=[0,start],actions=[c.LONG,c.LONG],
    )
    e=x.economics(r.trades,10.0)
    assert e["accepted_trades"]==2
    assert np.isfinite(e["profit_factor"])
    assert e["max_drawdown_bps"]>=0.0


def test_aligned_4h_blocks_have_24_slots():
    d=synthetic_day(seconds=2200)
    r=x.execute_candidate_day(
        candidate_id="T01U",day_name="2026-04-01",day=d,
        decisions=[0],actions=[c.LONG],
    )
    z=x.aligned_block_totals(
        r.trades,cost_bps=10.0,
        days=["2026-04-01","2026-05-01","2026-06-01","2026-07-01"],
        block_hours=4,
    )
    assert z.shape==(24,)
    assert np.count_nonzero(z)==1
