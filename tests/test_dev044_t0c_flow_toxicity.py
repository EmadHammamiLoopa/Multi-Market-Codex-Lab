from __future__ import annotations

import numpy as np
import pytest

from multimarket import dev044_t0c_flow_toxicity as x


def test_normalized_mlofi_triplet_bounds_and_sign():
    a=np.ones(200,dtype=np.float64)
    a[100:132]=-2.0
    one,sixteen,thirtytwo=x.t10_triplet(a,199)
    assert -1.0<=one<=1.0
    assert -1.0<=sixteen<=1.0
    assert -1.0<=thirtytwo<=1.0


def test_normalized_mlofi_zero_denominator_is_zero():
    a=np.zeros(200,dtype=np.float64)
    assert x.normalized_mlofi(a,199,1)==0.0
    assert x.normalized_mlofi(a,199,16)==0.0
    assert x.normalized_mlofi(a,199,32)==0.0


def test_normalized_mlofi_all_positive_is_one():
    a=np.full(200,3.0)
    assert x.t10_triplet(a,199)==pytest.approx((1.0,1.0,1.0))


def test_normalized_mlofi_insufficient_history_fails():
    with pytest.raises(x.T0CError):
        x.normalized_mlofi(np.ones(10),9,32)


def test_vpin_bucket_calibration_uses_median_30m_volume_over_50():
    # Four complete 30m blocks, 2 qty per 250ms row.
    rows=4*1800*4
    ts=np.arange(rows,dtype=np.int64)*250_000
    buy=np.ones(rows)
    sell=np.ones(rows)
    got=x.calibrate_vpin_bucket_volume(ts,buy,sell)
    expected=(1800*4*2)/50
    assert got==pytest.approx(expected)


def test_vpin_equal_volume_buckets_and_warmup():
    n=1000
    ts=np.arange(n,dtype=np.int64)*250_000
    # Pure buy flow: every completed bucket has imbalance 1.
    buy=np.ones(n)
    sell=np.zeros(n)
    out=x.vpin_series(ts,buy,sell,bucket_volume=10.0,rolling_buckets=5)
    assert np.isnan(out.toxicity[0])
    finite=np.flatnonzero(np.isfinite(out.toxicity))
    assert len(finite)>0
    assert np.allclose(out.toxicity[finite],1.0)
    assert np.all(out.completed_buckets[1:]>=out.completed_buckets[:-1])


def test_vpin_balanced_flow_is_zero_after_warmup():
    n=1000
    ts=np.arange(n,dtype=np.int64)*250_000
    buy=np.ones(n)
    sell=np.ones(n)
    out=x.vpin_series(ts,buy,sell,bucket_volume=10.0,rolling_buckets=5)
    finite=np.flatnonzero(np.isfinite(out.toxicity))
    assert len(finite)>0
    assert np.allclose(out.toxicity[finite],0.0)


def test_vpin_splits_large_bin_across_buckets():
    ts=np.arange(20,dtype=np.int64)*250_000
    buy=np.zeros(20);sell=np.zeros(20)
    buy[0]=25.0
    out=x.vpin_series(ts,buy,sell,bucket_volume=10.0,rolling_buckets=2)
    assert out.completed_buckets[0]==2
    assert out.toxicity[0]==pytest.approx(1.0)


def test_toxicity_at_none_before_warmup():
    ts=np.arange(20,dtype=np.int64)*250_000
    out=x.vpin_series(ts,np.ones(20),np.zeros(20),bucket_volume=100.0,rolling_buckets=5)
    assert x.toxicity_at(out,0) is None


def test_bad_vpin_input_fails():
    ts=np.arange(10,dtype=np.int64)*250_000
    buy=np.ones(10);sell=np.ones(10)
    buy[3]=-1
    with pytest.raises(x.T0CError):
        x.vpin_series(ts,buy,sell,bucket_volume=10)
