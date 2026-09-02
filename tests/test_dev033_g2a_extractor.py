from __future__ import annotations

import csv
import gzip
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pytest

from multimarket import dev033_g2a_materialize as mat

ROOT=Path(__file__).resolve().parents[1]
CPP=ROOT/"tools/dev033_g2a_raw_temporal.cpp"

def _write_fixture(path:Path):
    rows=[]
    ts0=0
    for i in range(50):
        rows.append(["binance","BTCUSDT",ts0,ts0,"true","bid",f"{100.00-i*0.01:.2f}",f"{100+i:.1f}"])
        rows.append(["binance","BTCUSDT",ts0,ts0,"true","ask",f"{100.02+i*0.01:.2f}",f"{110+i:.1f}"])
    for sec in range(1,41):
        t=sec*1_000_000
        # keep both top queues alive while creating classified replenishment/depletion events
        b=100.0 + (sec%3-1)*5.0
        a=110.0 + ((sec+1)%3-1)*4.0
        rows.append(["binance","BTCUSDT",t,t,"false","bid","100.00",f"{b:.1f}"])
        rows.append(["binance","BTCUSDT",t,t,"false","ask","100.02",f"{a:.1f}"])
    with gzip.open(path,"wt",encoding="utf-8",newline="") as h:
        w=csv.writer(h,lineterminator="\n")
        w.writerow(["exchange","symbol","timestamp","local_timestamp","is_snapshot","side","price","amount"])
        w.writerows(rows)

@pytest.mark.skipif(shutil.which("g++") is None,reason="g++ unavailable")
def test_cpp_extractor_end_to_end(tmp_path:Path):
    exe=tmp_path/"g2a"
    p=subprocess.run(
        ["g++","-std=c++17","-O2",str(CPP),"-lz","-o",str(exe)],
        capture_output=True,text=True,
    )
    assert p.returncode==0,p.stderr

    raw=tmp_path/"day.csv.gz"
    _write_fixture(raw)

    support=tmp_path/"support.csv"
    support.write_text("local_timestamp_us\n40000000\n",encoding="utf-8")
    out=tmp_path/"out.csv"

    q=subprocess.run([str(exe),str(raw),str(support),str(out)],capture_output=True,text=True)
    assert q.returncode==0,q.stderr
    assert "support=1 emitted=1" in q.stderr

    with out.open("r",encoding="utf-8",newline="") as h:
        r=csv.reader(h)
        header=next(r)
        body=list(r)

    expected=["local_timestamp_us","feature_valid"]
    for cid in mat.CANDIDATE_IDS:
        expected.extend(mat.expected_feature_names(cid))

    assert header==expected
    assert len(header)==2522
    assert len(body)==1
    assert body[0][0]=="40000000"
    assert body[0][1]=="1"
    vals=np.asarray([float(x) for x in body[0][2:]],dtype=float)
    assert vals.shape==(2520,)
    assert np.all(np.isfinite(vals))

    parsed=mat.parse_extractor_csv(out,np.asarray([40_000_000],dtype=np.int64))
    assert tuple(parsed)==mat.CANDIDATE_IDS
    for rrec in mat.REGISTRY:
        cid=rrec["candidate_id"]
        assert parsed[cid].shape==(1,rrec["feature_count"])

    # Nested-window contract: newest bins of W16/W32 equal W08 for same family.
    for family_index in range(8):
        c8=f"G2C{family_index+1:02d}"
        c16=f"G2C{family_index+9:02d}"
        c32=f"G2C{family_index+17:02d}"
        width8=mat.BY_ID[c8]["feature_count"]
        assert np.array_equal(parsed[c8][0],parsed[c16][0,:width8])
        assert np.array_equal(parsed[c8][0],parsed[c32][0,:width8])
