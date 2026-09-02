from __future__ import annotations

import numpy as np
import pytest

from multimarket import dev033_g2a_feature_core as fc
from multimarket import dev033_g2a_materialize as mat

def _book():
    bp=100.0-np.arange(50)*0.01
    ap=100.02+np.arange(50)*0.01
    bq=np.arange(1,51,dtype=float)
    aq=np.arange(2,52,dtype=float)
    return fc.Snapshot(bp,bq,ap,aq)

def test_registry_exact_24_and_widths():
    assert len(mat.REGISTRY)==24
    assert tuple(r["candidate_id"] for r in mat.REGISTRY)==tuple(f"G2C{i:02d}" for i in range(1,25))
    assert [r["window_seconds"] for r in mat.REGISTRY[:8]]==[8]*8
    assert [r["window_seconds"] for r in mat.REGISTRY[8:16]]==[16]*8
    assert [r["window_seconds"] for r in mat.REGISTRY[16:]]==[32]*8
    assert mat.TOTAL_COLUMNS==2520

def test_feature_name_order_and_width():
    for r in mat.REGISTRY:
        names=mat.expected_feature_names(r["candidate_id"])
        assert len(names)==r["feature_count"]
        assert names[0].startswith(r["candidate_id"]+"__bin00__")
        assert names[-1].startswith(
            r["candidate_id"]+f"__bin{r['window_seconds']-1:02d}__"
        )

def test_snapshot_formula_shapes_and_finite():
    s=_book()
    assert fc.l1_queue_imbalance(s).shape==(1,)
    assert fc.multiscale_depth_imbalance(s).shape==(4,)
    assert fc.microprice_displacement(s).shape==(4,)
    assert fc.book_geometry(s).shape==(6,)
    for z in (
        fc.l1_queue_imbalance(s),
        fc.multiscale_depth_imbalance(s),
        fc.microprice_displacement(s),
        fc.book_geometry(s),
    ):
        assert np.all(np.isfinite(z))

def test_event_formula_exact_simple_case():
    ev=[
        fc.Event("BI",1,5.0),
        fc.Event("BD",1,-2.0),
        fc.Event("AI",2,4.0),
        fc.Event("AD",2,-1.0),
    ]
    m=fc.mlofi_top10(ev)
    assert np.isclose(m[0],3.0/7.0)
    assert np.isclose(m[1],-3.0/5.0)
    assert np.count_nonzero(m[2:])==0

    q=fc.event_qty_share(ev)
    assert np.allclose(q[:2],[5/12,2/12])
    assert np.allclose(q[4:6],[4/12,1/12])
    assert np.isclose(np.sum(q),1.0)

    c=fc.event_count_share(ev)
    assert np.allclose(c[[0,1,4,5]],[0.25]*4)
    assert np.isclose(np.sum(c),1.0)

def test_empty_event_bin_zero():
    assert np.array_equal(fc.mlofi_top10([]),np.zeros(10))
    assert np.array_equal(fc.event_qty_share([]),np.zeros(8))
    assert np.array_equal(fc.event_count_share([]),np.zeros(8))

def test_flatten_newest_to_oldest_row_major():
    x=fc.flatten_bins([[1,2],[3,4],[5,6]],2)
    assert np.array_equal(x,np.asarray([1,2,3,4,5,6],dtype=float))

def test_materialization_validation_and_hashes():
    ts=np.arange(1374,dtype=np.int64)+1
    y=np.asarray(([1]*684)+([0]*690),dtype=np.int8)
    vals={}
    for r in mat.REGISTRY:
        vals[r["candidate_id"]]=np.zeros((1374,r["feature_count"]),dtype=float)
    out=mat.validate_full_campaign(ts,y,vals)
    assert tuple(out)==mat.CANDIDATE_IDS
    assert len(mat.support_sha256(ts))==64
    assert len(mat.label_sha256(ts,y))==64
    for cid,z in out.items():
        assert len(mat.matrix_sha256(cid,z.values))==64

def test_nonfinite_and_wrong_order_fail_closed():
    ts=np.arange(1374,dtype=np.int64)+1
    y=np.asarray(([1]*684)+([0]*690),dtype=np.int8)
    vals={}
    for r in mat.REGISTRY:
        vals[r["candidate_id"]]=np.zeros((1374,r["feature_count"]),dtype=float)
    vals["G2C01"][0,0]=np.nan
    with pytest.raises(mat.G2AMaterializationError) as e:
        mat.validate_full_campaign(ts,y,vals)
    assert e.value.reason=="candidate_matrix_nonfinite"

    vals["G2C01"][0,0]=0.0
    reversed_vals={cid:vals[cid] for cid in reversed(mat.CANDIDATE_IDS)}
    with pytest.raises(mat.G2AMaterializationError) as e2:
        mat.validate_full_campaign(ts,y,reversed_vals)
    assert e2.value.reason=="candidate_membership_order"
