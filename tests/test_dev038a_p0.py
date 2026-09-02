from __future__ import annotations

from datetime import date
import numpy as np

from multimarket import dev030_direction_dataset as dd
from multimarket import dev038a_p0_core as core
from multimarket import dev038a_p0_harness as harness
from multimarket import dev038a_p0_runner as runner

def test_candidate_family_exact():
    assert core.CANDIDATES==(
        ("A0",32,"PRICE"),
        ("A1",32,"PRICE_BOOK"),
        ("A2",32,"PRICE_BOOK_FLOW"),
        ("A3",32,"PRICE_BOOK_FLOW_DYNAMICS"),
        ("A4",60,"PRICE_BOOK_FLOW_DYNAMICS"),
    )

def test_common_support_intersection_and_labels():
    day=dd.HISTORICAL_DAYS[0]
    per={}
    for i,(cid,_,_) in enumerate(core.CANDIDATES):
        ts=np.array([1,2,3,4,5],dtype=np.int64)
        if cid=="A4":
            ts=np.array([2,3,4,5],dtype=np.int64)
        labels=np.array([0,1,0,1,0],dtype=np.int8)[-len(ts):]
        # align labels explicitly by timestamp
        mapping={1:0,2:1,3:0,4:1,5:0}
        yy=np.array([mapping[int(t)] for t in ts],dtype=np.int8)
        per[cid]={day:core.CandidateAuditDay(cid,day,ts,yy,10,1)}
        for d in dd.HISTORICAL_DAYS[1:]:
            per[cid][d]=core.CandidateAuditDay(cid,d,ts,yy,10,1)
    out=core.common_support(per)
    assert np.array_equal(out[day][0],np.array([2,3,4,5],dtype=np.int64))
    assert np.array_equal(out[day][1],np.array([1,0,1,0],dtype=np.int8))

def test_support_hash_deterministic():
    x=np.array([1,2,3],dtype=np.int64)
    assert core.support_sha(x)==core.support_sha(x.copy())

def test_guards_false_and_smoke():
    assert not any(runner.FORWARD_GUARDS.values())
    assert harness.process_pool_smoke(2)==(1,4,9,16)
