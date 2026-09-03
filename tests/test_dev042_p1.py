from __future__ import annotations

from datetime import date
import numpy as np

from multimarket import dev030_direction_dataset as dd
from multimarket import dev042_p0_feature_core as p0
from multimarket import dev042_p1_materialization as mat
from multimarket import dev042_p1_harness as harness

class Day:
    pass

def _synthetic_day(n=80):
    d=Day()
    d.day=date(2026,1,1)
    d.ts=np.arange(n,dtype=np.int64)*60_000_000
    d.mid=100.0*np.exp(np.arange(n,dtype=np.float64)*0.0001)
    d.book_valid=np.ones(n,dtype=bool)
    d.valid={
        "L1":np.ones(n,dtype=bool),
        "L2":np.ones(n,dtype=bool),
    }

    cols={}
    for i,name in enumerate(dd.SOURCE_FEATURE_ORDER):
        if name.startswith("log_bid_depth") or name.startswith("log_ask_depth"):
            cols[name]=np.full(n,np.log1p(1000+i),dtype=np.float64)
        elif "replenish" in name or "deplete" in name:
            cols[name]=np.full(n,10+i,dtype=np.float64)
        elif name=="spread_bps":
            cols[name]=np.full(n,0.2,dtype=np.float64)
        else:
            cols[name]=np.linspace(-1,1,n,dtype=np.float64)+(i*0.01)
    d.X={"L2":np.column_stack([cols[name] for name in dd.SOURCE_FEATURE_ORDER])}
    return d

def test_materialized_common_shapes_and_identity():
    z=mat.materialize_day(_synthetic_day())
    assert len(z.timestamps_us)==50
    assert z.X0.shape==(50,15)
    assert z.X1.shape==(50,60)
    assert z.X2.shape==(50,51)
    assert z.X3.shape==(50,111)
    assert z.X4.shape==(50,111)
    assert np.array_equal(z.X3,z.X4)
    assert np.all(np.isfinite(z.X0))
    assert np.all(np.isfinite(z.X1))
    assert np.all(np.isfinite(z.X2))

def test_materialization_starts_after_30_minute_lookback():
    z=mat.materialize_day(_synthetic_day())
    assert z.timestamps_us[0]==30*60_000_000
    assert z.timestamps_us[-1]==79*60_000_000

def test_candidate_mapping_uses_same_rows():
    z=mat.materialize_day(_synthetic_day())
    candidates=(
        "C0_PRICE_LOGIT",
        "C1_OFI_LOGIT",
        "C2_PRESSURE_CAPACITY_LOGIT",
        "C3_COMBINED_LOGIT",
        "C4_COMBINED_HGB",
    )
    for cid in candidates:
        X=mat.candidate_matrix(z,cid)
        assert X.shape[0]==len(z.timestamps_us)

def test_combined_feature_order_contract():
    assert p0.COMBINED_NAMES[:15]==p0.F0_NAMES
    assert p0.COMBINED_NAMES[15:60]==p0.ofi_addition_names()
    assert p0.COMBINED_NAMES[60:]==p0.F2_NAMES

def test_frozen_parent_identity_constants():
    assert mat.P0_ARTIFACT_SHA256=="d9259a53d24492f478615c986ed73981f052d483a764935a8dfd68d17212b882"
    assert mat.P0_ARTIFACT_BYTES==12989
    assert len(mat.EXPECTED_COMMON_SUPPORT_SHA256)==7

def test_unknown_candidate_fails():
    z=mat.materialize_day(_synthetic_day())
    try:
        mat.candidate_matrix(z,"C9_UNKNOWN")
    except mat.MaterializationError:
        pass
    else:
        raise AssertionError("unknown candidate should fail closed")

def test_harness_smoke():
    assert harness.process_pool_smoke(2)==(1,4,9,16)
