from __future__ import annotations

import numpy as np

from multimarket import dev042_p0_feature_core as core
from multimarket import dev042_p0_harness as harness
from multimarket import dev042_p0_runner as runner

def _synthetic_minutes(n=80):
    ts=np.arange(n,dtype=np.int64)*60_000_000
    mid=100.0*np.exp(np.arange(n,dtype=np.float64)*0.0001)
    book=np.ones(n,dtype=bool)
    l1=np.ones(n,dtype=bool)
    l2=np.ones(n,dtype=bool)
    source={}
    all_names=set(core.OFI_SOURCES)|{
        "spread_bps","microprice_minus_mid_bps","obi_l1","obi_l5","obi_l10",
        "log_bid_depth_l5","log_ask_depth_l5","log_bid_depth_l10","log_ask_depth_l10",
        "bid_replenish_l5_1s","ask_replenish_l5_1s",
        "bid_deplete_l5_1s","ask_deplete_l5_1s",
    }
    for i,name in enumerate(sorted(all_names)):
        if name.startswith("log_bid_depth") or name.startswith("log_ask_depth"):
            source[name]=np.full(n,np.log1p(1000+i),dtype=np.float64)
        elif "replenish" in name or "deplete" in name:
            source[name]=np.full(n,10+i,dtype=np.float64)
        elif name=="spread_bps":
            source[name]=np.full(n,0.2,dtype=np.float64)
        else:
            source[name]=np.linspace(-1,1,n,dtype=np.float64)+(i*0.01)
    return ts,mid,book,l1,l2,source

def test_feature_dimensions_and_uniqueness():
    assert len(core.F0_NAMES)==15
    assert len(core.F1_NAMES)==60
    assert len(core.F2_NAMES)==51
    assert len(core.COMBINED_NAMES)==111
    assert len(set(core.F0_NAMES))==15
    assert len(set(core.F1_NAMES))==60
    assert len(set(core.F2_NAMES))==51
    assert len(set(core.COMBINED_NAMES))==111

def test_price_requires_full_1800_second_history():
    ts,mid,book,l1,l2,source=_synthetic_minutes()
    assert core.build_f0_features(
        decision_timestamp_us=29*60_000_000,
        minute_timestamps_us=ts,mid=mid,book_valid=book
    ) is None
    z=core.build_f0_features(
        decision_timestamp_us=30*60_000_000,
        minute_timestamps_us=ts,mid=mid,book_valid=book
    )
    assert z is not None and z.shape==(15,) and np.all(np.isfinite(z))

def test_independent_native_support():
    ts,mid,book,l1,l2,source=_synthetic_minutes()
    d=40*60_000_000
    f0=core.build_f0_features(
        decision_timestamp_us=d,minute_timestamps_us=ts,mid=mid,book_valid=book
    )
    l1_bad=l1.copy();l1_bad[39]=False
    f1=core.build_f1_features(
        decision_timestamp_us=d,minute_timestamps_us=ts,mid=mid,book_valid=book,
        l1_valid=l1_bad,source=source
    )
    f2=core.build_f2_features(
        decision_timestamp_us=d,minute_timestamps_us=ts,l2_valid=l2,source=source
    )
    assert f0 is not None
    assert f1 is None
    assert f2 is not None

def test_pressure_capacity_finite():
    ts,mid,book,l1,l2,source=_synthetic_minutes()
    z=core.build_f2_features(
        decision_timestamp_us=40*60_000_000,
        minute_timestamps_us=ts,l2_valid=l2,source=source
    )
    assert z is not None
    assert z.shape==(51,)
    assert np.all(np.isfinite(z))

def test_combined_order_exact():
    assert core.COMBINED_NAMES[:15]==core.F0_NAMES
    assert core.COMBINED_NAMES[15:60]==core.ofi_addition_names()
    assert core.COMBINED_NAMES[60:]==core.F2_NAMES

def test_feature_name_hash_stable_shape():
    h=core.feature_name_sha256(core.COMBINED_NAMES)
    assert isinstance(h,str) and len(h)==64
    assert h==core.feature_name_sha256(tuple(core.COMBINED_NAMES))

def test_forward_guards_and_no_result_contract():
    assert not any(runner.FORWARD_GUARDS.values())
    assert runner.FORWARD_GUARDS["labels_constructed"] is False
    assert runner.FORWARD_GUARDS["model_fit"] is False
    assert runner.FORWARD_GUARDS["economic_output_calculated"] is False

def test_harness_smoke():
    assert harness.process_pool_smoke(2)==(1,4,9,16)
