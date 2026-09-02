from __future__ import annotations
import numpy as np
import pytest
from multimarket import dev032_e1a_feature_core as f

def book(n=50):
    bids=100.0-np.arange(n)*0.01
    asks=100.02+np.arange(n)*0.01
    bq=np.arange(1,n+1,dtype=float)
    aq=np.arange(n,0,-1,dtype=float)
    return f.BookSnapshot(f.BookSide(bids,bq),f.BookSide(asks,aq))

def test_registry_exact_36():
    f.validate_strategy_registry()
    c=f.strategy_feature_counts()
    assert len(c)==36
    assert tuple(c)==tuple(f"S{i:02d}" for i in range(36))
    assert c["S00"]==23 and c["S35"]==24

def test_imbalance_and_log_ratio():
    assert f.imbalance(3,1)==pytest.approx(0.5)
    assert f.imbalance(0,0)==0.0
    assert f.log_ratio(2,1)>0
    with pytest.raises(f.E1AFeatureError):
        f.imbalance(-1,1)

def test_book_validation_rejects_wrong_order():
    b=book()
    bad=f.BookSnapshot(f.BookSide(b.bids.prices[::-1],b.bids.quantities),b.asks)
    with pytest.raises(f.E1AFeatureError) as e:
        f.validate_book(bad)
    assert e.value.reason=="bids_not_strictly_descending"

def test_multidepth_and_weighted_obi_shapes():
    b=book()
    assert f.cumulative_depth_imbalance(b).shape==(7,)
    assert f.cumulative_log_depth_ratio(b).shape==(7,)
    x=f.distance_weighted_obi(b)
    assert x.shape==(2,)
    assert np.all((x>=-1)&(x<=1))

def test_generalized_microprice_is_inside_spread():
    b=book()
    disp,norm=f.generalized_microprice(b)
    _,_,spread_bps=f.mid_spread(b)
    assert disp.shape==(5,) and norm.shape==(5,)
    assert np.all(np.abs(disp)<=spread_bps/2+1e-12)

def test_slope_convexity_gap_entropy_finite():
    b=book()
    for x in [
      f.book_slope(b,levels=10),
      f.book_slope(b,levels=50),
      f.slope_convexity(b),
      f.price_gap_asymmetry(b),
      f.depth_centroid_entropy(b),
    ]:
        assert np.all(np.isfinite(x))
    assert f.depth_centroid_entropy(b).shape==(6,)

def test_transition_contrasts_shape_and_direction():
    x=f.event_transition_contrasts(["BI","BD","AI","AR","BI"])
    assert x.shape==(16,)
    assert np.all(np.isfinite(x))
    with pytest.raises(f.E1AFeatureError):
        f.event_transition_contrasts(["BI","XX"])

def test_interarrival_defaults_and_regular_process():
    assert np.array_equal(f.interarrival_moments([]),np.array([32.0,0.0,0.0]))
    x=f.interarrival_moments([0,2,4,6])
    assert x[0]==pytest.approx(2.0)
    assert x[1]==pytest.approx(0.0)
    assert x[2]==pytest.approx(0.0)

def test_burstiness_fano_and_exponential_intensity():
    b=f.burstiness_fano([1,2,3,4,5])
    assert b.shape==(2,)
    e=f.exponential_intensities([0,1,2])
    assert e.shape==(2,)
    assert e[0] < e[1]

def test_multiscale_ratios_bounded():
    x=f.multiscale_intensity_ratios({1.0:100,4.0:100,16.0:1,32.0:1})
    assert x.shape==(2,)
    assert np.all(x<=32)

def test_cosine_zero_and_identical():
    assert f.cosine_or_zero([0,0],[1,2])==0
    assert f.cosine_or_zero([1,2],[1,2])==pytest.approx(1)

def test_stationary_flow_temporal_shape_exact_15():
    v=[
      np.arange(10,dtype=float),
      np.arange(10,dtype=float)+1,
      np.arange(10,dtype=float)+2,
      np.arange(10,dtype=float)+3,
    ]
    x=f.stationary_flow_temporal_shape(v)
    assert x.shape==(15,)
    assert np.all(np.isfinite(x))

def test_event_pressure_temporal_shape_exact_24():
    p=np.arange(16,dtype=float).reshape(4,4)/16
    x=f.event_pressure_temporal_shape(p)
    assert x.shape==(24,)
    assert np.all(np.isfinite(x))

def test_insufficient_depth_fails_closed():
    b=book(10)
    with pytest.raises(f.E1AFeatureError) as e:
        f.distance_weighted_obi(b,levels=50)
    assert e.value.reason=="insufficient_depth"
