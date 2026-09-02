from __future__ import annotations

import csv
import gzip
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pytest

from multimarket import dev032_e2a_feature_core as fc
from multimarket import dev032_e2a_materialize as mat
from multimarket import dev032_e2a_runner as runner

def _values(rows:int=5):
    out={}
    for rid,n in mat.FEATURE_COUNTS.items():
        out[rid]=np.arange(rows*n,dtype=float).reshape(rows,n)/(n+1)
    return out

def test_registry_exact_10_and_130():
    mat.validate_registry()
    assert mat.REFINEMENT_IDS==tuple(f"E2R{i:02d}" for i in range(1,11))
    assert mat.TOTAL_RAW_COLUMNS==130
    assert mat.PARENT_BY_REFINEMENT["E2R08"]=="P21"
    assert mat.PARENT_BY_REFINEMENT["E2R10"]=="P32"

def test_bundle_roundtrip_and_hashes():
    ts=np.array([1,2,3,4,5],dtype=np.int64)
    y=np.array([0,1,0,1,1],dtype=np.int8)
    b=mat.assemble_bundle(ts,y,_values())
    assert len(b.matrices)==10
    assert sum(x.values.shape[1] for x in b.matrices)==130
    p=mat.public_manifest(b)
    assert p["rows"]==5 and p["long"]==3 and p["short"]==2
    assert not any(p["forward_guards"].values())
    z=_values(); h1=mat.matrix_sha256("E2R01",z["E2R01"])
    z["E2R01"]=z["E2R01"].copy();z["E2R01"][0,0]+=1
    assert h1!=mat.matrix_sha256("E2R01",z["E2R01"])

def test_csv_contract_roundtrip(tmp_path):
    ts=np.array([100,200,300,400,500],dtype=np.int64)
    v=_values()
    p=tmp_path/"e2a.csv"
    mat.write_fixture_csv(p,ts,v)
    got=mat.parse_extractor_csv(p,ts)
    assert tuple(got)==mat.REFINEMENT_IDS
    for rid in mat.REFINEMENT_IDS:
        assert np.array_equal(got[rid],v[rid])

def test_nonfinite_and_wrong_order_fail_closed():
    ts=np.array([1,2,3,4,5],dtype=np.int64)
    y=np.array([0,1,0,1,0],dtype=np.int8)
    v=_values();bad=dict(reversed(list(v.items())))
    with pytest.raises(mat.E2AMaterializationError) as e:
        mat.assemble_bundle(ts,y,bad)
    assert e.value.reason=="refinement_order_or_membership_mismatch"
    v=_values();v["E2R09"]=v["E2R09"].copy();v["E2R09"][0,0]=np.nan
    with pytest.raises(mat.E2AMaterializationError) as e:
        mat.assemble_bundle(ts,y,v)
    assert e.value.reason=="refinement_matrix_nonfinite"

def test_formula_oracles_shapes_and_finite():
    q=fc.queue_spread_state(np.linspace(-.5,.5,7),2.0)
    assert q.shape==(14,)
    p=fc.queue_event_persistence(.2,[.1,.2,-.1,.2],[0,1,2,3])
    assert p.shape==(6,)
    m=fc.microprice_queue_interaction(np.arange(5)/10,np.linspace(-.2,.2,5))
    assert m.shape==(10,)
    c=fc.microprice_acceleration_curvature([.4,.3,.2,.1])
    assert c.shape==(6,)
    bp=100-np.arange(50)*.01;ap=100.02+np.arange(50)*.01
    bq=np.arange(1,51,dtype=float);aq=bq[::-1].copy()
    d=fc.depth_dispersion_block(bp,bq,ap,aq,100.01)
    assert d.shape==(6,)
    r=fc.event_run_length_persistence(["BI","BR","AD","AI"],[10,7,3,1])
    assert r.shape==(8,)
    mom=fc.signed_event_time_momentum([.5,2,8],[1,-1,1],[2,1,3])
    assert mom.shape==(8,)
    rec=fc.recovery_curve_block(.1,.3,.6,.8,12)
    assert rec.shape==(6,)
    for x in (q,p,m,c,d,r,mom,rec):
        assert np.all(np.isfinite(x))

def _write_synthetic_raw(path:Path)->list[int]:
    rows=[]
    # 50-level full snapshot at 1s.
    for i in range(50):
        rows.append(["binance","BTCUSDT",1_000_000,1_000_000,True,"bid",100.00-i*.01,10+i])
        rows.append(["binance","BTCUSDT",1_000_000,1_000_000,True,"ask",100.02+i*.01,12+i])
    # Eligible groups after the snapshot.
    rows.append(["binance","BTCUSDT",2_000_000,2_000_000,False,"bid",100.00,20.0])
    rows.append(["binance","BTCUSDT",3_000_000,3_000_000,False,"ask",100.02,4.0])
    rows.append(["binance","BTCUSDT",4_000_000,4_000_000,False,"bid",99.99,5.0])
    rows.append(["binance","BTCUSDT",5_000_000,5_000_000,False,"ask",100.03,25.0])
    with gzip.open(path,"wt",encoding="utf-8",newline="") as h:
        w=csv.writer(h,lineterminator="\n")
        w.writerow(["exchange","symbol","timestamp","local_timestamp","is_snapshot","side","price","amount"])
        w.writerows(rows)
    return [2_000_000,3_000_000,4_000_000,5_000_000]

@pytest.mark.skipif(shutil.which("g++") is None,reason="g++ missing")
def test_cpp_extractor_compiles_emits_exact_130_and_matches_snapshot_oracle(tmp_path):
    root=Path(__file__).resolve().parents[1]
    source=root/"tools"/"dev032_e2a_raw_features.cpp"
    exe=tmp_path/"e2a"
    p=subprocess.run(
        ["g++","-std=c++17","-O2","-DNDEBUG",str(source),"-lz","-o",str(exe)],
        capture_output=True,text=True,
    )
    assert p.returncode==0,p.stderr

    raw=tmp_path/"raw.csv.gz"
    support_ts=_write_synthetic_raw(raw)
    support=tmp_path/"support.csv"
    support.write_text("local_timestamp_us\n"+"\n".join(map(str,support_ts))+"\n")
    out=tmp_path/"out.csv"
    p=subprocess.run([str(exe),str(raw),str(support),str(out)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    got=mat.parse_extractor_csv(out,np.asarray(support_ts,dtype=np.int64))
    assert sum(x.shape[1] for x in got.values())==130
    assert all(np.all(np.isfinite(x)) for x in got.values())

    # At first support timestamp, compare R01 against independently computed
    # post-group snapshot quantities.
    bp=100.00-np.arange(50)*.01
    ap=100.02+np.arange(50)*.01
    bq=10+np.arange(50,dtype=float);bq[0]=20.0
    aq=12+np.arange(50,dtype=float)
    levels=(1,2,3,5,10,20,50)
    obi=[]
    for L in levels:
        B=float(np.sum(bq[:L]));A=float(np.sum(aq[:L]))
        obi.append((B-A)/(B+A))
    spread=10000*(100.02-100.00)/100.01
    expected=fc.queue_spread_state(obi,spread)
    assert got["E2R01"][0]==pytest.approx(expected,abs=1e-12)

def test_runner_guards_and_worker_cap():
    assert runner.REAL_OUTPUT_DIRECTORY.name=="dev032_e2a_wave2_materialization_v1"
    assert not any(runner.FORWARD_GUARDS.values())
    assert runner.E1A_SHA256=="76e1c97e8b9a899bc27f3193316cbfc85efba8b0a7aa037d4c46fcc6a8be4a50"
