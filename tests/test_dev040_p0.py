from __future__ import annotations

import numpy as np

from multimarket import dev040_p0_core as core
from multimarket import dev040_p0_harness as harness
from multimarket import dev040_p0_runner as runner

def _raw(n=2000):
    ts=np.arange(n,dtype=np.int64)*250_000
    bid=np.full(n,100.0,dtype=np.float64)
    ask=np.full(n,100.1,dtype=np.float64)
    valid=np.ones(n,dtype=bool)
    return ts,bid,ask,valid

def test_frozen_constants():
    assert core.LATENCIES_MS==(250,500,1000)
    assert core.HOLD_SECONDS==120

def test_flat_only_ignores_overlap():
    ts,bid,ask,valid=_raw(3000)
    # Decisions at 1s, 60s, 130s. With 250ms entry/exit latency and 120s hold,
    # second signal overlaps first and must be ignored; third is accepted.
    dts=np.array([1_000_000,60_000_000,130_000_000],dtype=np.int64)
    actions=np.array([2,1,1],dtype=np.int8)
    trades,ignored=core.flat_only_audit(
        decision_timestamps_us=dts,
        actions=actions,
        raw_timestamps_us=ts,
        bid=bid,
        ask=ask,
        book_valid=valid,
        latency_ms=250,
    )
    assert len(trades)==2
    assert ignored==1
    assert [t.action for t in trades]==[2,1]

def test_flat_only_exact_execution_timestamps():
    ts,bid,ask,valid=_raw(3000)
    dts=np.array([1_000_000],dtype=np.int64)
    actions=np.array([2],dtype=np.int8)
    trades,_=core.flat_only_audit(
        decision_timestamps_us=dts,
        actions=actions,
        raw_timestamps_us=ts,
        bid=bid,
        ask=ask,
        book_valid=valid,
        latency_ms=500,
    )
    t=trades[0]
    assert t.entry_timestamp_us==1_500_000
    assert t.exit_timestamp_us==122_000_000

def test_missing_exit_fails_closed():
    ts,bid,ask,valid=_raw(10)
    dts=np.array([1_000_000],dtype=np.int64)
    actions=np.array([2],dtype=np.int8)
    try:
        core.flat_only_audit(
            decision_timestamps_us=dts,
            actions=actions,
            raw_timestamps_us=ts,
            bid=bid,
            ask=ask,
            book_valid=valid,
            latency_ms=250,
        )
    except core.P0Error as exc:
        assert "timestamp_missing" in str(exc)
    else:
        raise AssertionError("expected fail-closed timestamp error")

def test_invalid_book_fails_closed():
    ts,bid,ask,valid=_raw(3000)
    valid[5]=False
    dts=np.array([1_000_000],dtype=np.int64)
    actions=np.array([2],dtype=np.int8)
    try:
        core.flat_only_audit(
            decision_timestamps_us=dts,
            actions=actions,
            raw_timestamps_us=ts,
            bid=bid,
            ask=ask,
            book_valid=valid,
            latency_ms=250,
        )
    except core.P0Error as exc:
        assert "book_invalid" in str(exc)
    else:
        raise AssertionError("expected fail-closed invalid book")

def test_public_summary_contains_no_pnl_metrics():
    ts,bid,ask,valid=_raw(3000)
    dts=np.array([1_000_000],dtype=np.int64)
    actions=np.array([2],dtype=np.int8)
    trades,ignored=core.flat_only_audit(
        decision_timestamps_us=dts,
        actions=actions,
        raw_timestamps_us=ts,
        bid=bid,
        ask=ask,
        book_valid=valid,
        latency_ms=250,
    )
    z=core.public_summary(trades,ignored,1)
    forbidden={"gross_bps","net_bps","profit_factor","drawdown","win_rate","break_even"}
    assert not (set(z)&forbidden)

def test_forward_guards_false_and_parent_identity():
    assert not any(runner.FORWARD_GUARDS.values())
    assert runner.PARENT_SHA=="df32874a362cd75f646cdca483dc46956797431ac9a5861435639dfbf7f4b311"
    assert runner.PARENT_BYTES==191547

def test_harness_smoke():
    assert harness.process_pool_smoke(2)==(1,4,9,16)
