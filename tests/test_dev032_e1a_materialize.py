from __future__ import annotations
import numpy as np
import pytest

from multimarket import dev032_e1a_feature_core as fc
from multimarket import dev032_e1a_materialize as m

def values(rows=5):
    out={}
    for sid,n in fc.strategy_feature_counts().items():
        x=np.arange(rows*n,dtype=float).reshape(rows,n)/(n+1)
        out[sid]=x
    return out

def test_exact_strategy_membership_and_counts():
    fc.validate_strategy_registry()
    assert len(m.ALL_IDS)==36
    assert m.CONTROL_IDS==("S00","S01","S02","S03")
    assert m.RAW_IDS[0]=="S04" and m.RAW_IDS[-1]=="S35"
    assert fc.strategy_feature_counts()["S03"]==12

def test_assemble_bundle_roundtrip_small():
    ts=np.array([100,200,300,400,500],dtype=np.int64)
    y=np.array([0,1,0,1,1],dtype=np.int8)
    b=m.assemble_bundle(ts,y,values())
    assert len(b.matrices)==36
    assert b.matrices[0].values.shape==(5,23)
    assert b.matrices[-1].values.shape==(5,24)
    p=m.public_manifest(b)
    assert p["rows"]==5 and p["long"]==3 and p["short"]==2
    assert len(p["strategies"])==36
    assert not any(p["forward_guards"].values())

def test_strategy_order_mismatch_fails():
    v=values()
    bad=dict(reversed(list(v.items())))
    with pytest.raises(m.E1AMaterializationError) as e:
        m.assemble_bundle(np.array([1,2,3,4,5]),np.array([0,1,0,1,0]),bad)
    assert e.value.reason=="strategy_order_or_membership_mismatch"

def test_nonfinite_fails_closed():
    v=values()
    v["S12"]=v["S12"].copy()
    v["S12"][0,0]=np.nan
    with pytest.raises(m.E1AMaterializationError) as e:
        m.assemble_bundle(np.array([1,2,3,4,5]),np.array([0,1,0,1,0]),v)
    assert e.value.reason=="strategy_matrix_nonfinite"

def test_shape_mismatch_fails_closed():
    v=values()
    v["S20"]=np.zeros((5,7))
    with pytest.raises(m.E1AMaterializationError) as e:
        m.assemble_bundle(np.array([1,2,3,4,5]),np.array([0,1,0,1,0]),v)
    assert e.value.reason=="strategy_matrix_shape"

def test_support_must_be_unique_chronological():
    with pytest.raises(m.E1AMaterializationError) as e:
        m.assemble_bundle(np.array([1,3,2,4,5]),np.array([0,1,0,1,0]),values())
    assert e.value.reason=="support_not_unique_chronological"

def test_campaign_counts_fail_closed_before_fit():
    with pytest.raises(m.E1AMaterializationError) as e:
        m.assemble_bundle(
            np.array([1,2,3,4,5]),np.array([0,1,0,1,0]),values(),
            require_full_campaign_counts=True,
        )
    assert e.value.reason=="campaign_support_count_mismatch"

def test_raw_csv_contract_roundtrip(tmp_path):
    rows=5
    ts=np.array([100,200,300,400,500],dtype=np.int64)
    allv=values(rows)
    raw={sid:allv[sid] for sid in m.RAW_IDS}
    p=tmp_path/"raw.csv"
    m.write_raw_extractor_fixture_csv(p,ts,raw)
    got=m.parse_raw_extractor_csv(p,ts)
    assert tuple(got)==m.RAW_IDS
    for sid in m.RAW_IDS:
        assert np.array_equal(got[sid],raw[sid])

def test_raw_csv_support_mismatch_fails(tmp_path):
    rows=5
    ts=np.array([100,200,300,400,500],dtype=np.int64)
    allv=values(rows)
    p=tmp_path/"raw.csv"
    m.write_raw_extractor_fixture_csv(p,ts,{sid:allv[sid] for sid in m.RAW_IDS})
    with pytest.raises(m.E1AMaterializationError) as e:
        m.parse_raw_extractor_csv(p,np.array([100,200,300,400,501]))
    assert e.value.reason=="raw_extractor_support_mismatch"

def test_hashes_change_when_matrix_changes():
    v=values()
    h1=m.matrix_sha256("S04",v["S04"])
    z=v["S04"].copy(); z[0,0]+=1
    h2=m.matrix_sha256("S04",z)
    assert h1!=h2

def test_canonical_json_deterministic():
    a=m.canonical_json_bytes({"b":2,"a":1})
    b=m.canonical_json_bytes({"a":1,"b":2})
    assert a==b
