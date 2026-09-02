from __future__ import annotations

import numpy as np

from multimarket import dev037_p0_r1_coverage_core as r1
from multimarket import dev037_p0_r2_runner as r2
from multimarket import dev037_p0_r2_harness as harness

def _record(w,coverage=.2,err=.0):
    return r1.ControllerResult(
        window=w,
        thresholds=np.array([.5]),
        actions=np.array([1,2,0,0,0],dtype=np.int8),
        coverage=coverage,
        action_count=2,
        abstain_count=3,
        long_count=1,
        short_count=1,
        coverage_abs_error=err,
        rolling60_coverage=np.array([.2]),
        mean_abs_rolling60_error=err,
        max_abs_rolling60_error=err,
        rolling60_outside_count=0,
        action_state_switches=2,
        warm_start_count=w,
    )

def test_retained_policy_family_exact():
    assert r2.RETAINED_POLICY_IDS==("S0","S1","S2","S5")
    assert r2.WINDOWS==(120,360,720)

def test_rank_prefers_lower_coverage_error():
    records={
        120:[_record(120,.2,.01) for _ in range(16)],
        360:[_record(360,.2,.02) for _ in range(16)],
        720:[_record(720,.2,.03) for _ in range(16)],
    }
    ranked,stats=r2._rank(records)
    assert ranked==[120,360,720]
    assert set(stats)=={120,360,720}

def test_rank_excludes_globally_infeasible_window():
    bad=_record(120,.8,.6)
    records={
        120:[bad]+[_record(120,.2,.01) for _ in range(15)],
        360:[_record(360,.2,.02) for _ in range(16)],
        720:[_record(720,.2,.03) for _ in range(16)],
    }
    ranked,_=r2._rank(records)
    assert 120 not in ranked
    assert ranked[0]==360

def test_forward_guards_false_and_smoke():
    assert not any(r2.FORWARD_GUARDS.values())
    assert harness.process_pool_smoke(2)==(1,4,9,16)
