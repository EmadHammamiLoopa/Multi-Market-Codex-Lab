from __future__ import annotations

import csv
import gzip
from pathlib import Path
import shutil
import subprocess

import numpy as np
import pytest

from multimarket import dev032_e1a_feature_core as fc
from multimarket import dev032_e1a_materialize as m


def _compile(root: Path, build: Path) -> Path:
    cxx=shutil.which("g++")
    if cxx is None:
        pytest.skip("g++ not available")
    build.mkdir(parents=True,exist_ok=True)
    exe=build/"dev032_e1a_raw_features"
    src=root/"tools"/"dev032_e1a_raw_features.cpp"
    p=subprocess.run(
        [cxx,"-std=c++17","-O2","-DNDEBUG",str(src),"-lz","-o",str(exe)],
        capture_output=True,text=True,
    )
    assert p.returncode==0,p.stderr
    return exe


def _fixture(path: Path, *, t0: int=1_800_000_000_000_000) -> tuple[int,int]:
    rows=[]
    # 60x60 valid snapshot, symmetric prices and quantities.
    for i in range(60):
        rows.append(["binance-futures","BTCUSDT",t0,t0,"true","bid",100.0-0.01*i,10.0])
        rows.append(["binance-futures","BTCUSDT",t0,t0,"true","ask",100.02+0.01*i,10.0])

    # At t0+1s: bid best replenishes +10, ask best depletes -5.
    e1=t0+1_000_000
    rows.extend([
        ["binance-futures","BTCUSDT",e1,e1,"false","bid",100.0,20.0],
        ["binance-futures","BTCUSDT",e1,e1,"false","ask",100.02,5.0],
    ])

    # At t0+2s: add a new bid level inside the old best and delete one ask level.
    e2=t0+2_000_000
    rows.extend([
        ["binance-futures","BTCUSDT",e2,e2,"false","bid",100.005,8.0],
        ["binance-futures","BTCUSDT",e2,e2,"false","ask",100.03,0.0],
    ])

    with gzip.open(path,"wt",encoding="utf-8",newline="") as h:
        w=csv.writer(h,lineterminator="\n")
        w.writerow(("exchange","symbol","timestamp","local_timestamp","is_snapshot","side","price","amount"))
        w.writerows(rows)
    return t0,e2+1_000_000


def test_cpp_raw_extractor_compiles_and_matches_contract(tmp_path: Path):
    root=Path(__file__).resolve().parents[1]
    exe=_compile(root,tmp_path/"build")

    raw=tmp_path/"raw.csv.gz"
    _,support_ts=_fixture(raw)
    support=tmp_path/"support.csv"
    support.write_text(f"local_timestamp_us\n{support_ts}\n",encoding="utf-8")
    out=tmp_path/"out.csv"

    p=subprocess.run([str(exe),str(raw),str(support),str(out)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr

    parsed=m.parse_raw_extractor_csv(out,np.array([support_ts],dtype=np.int64))
    assert tuple(parsed)==m.RAW_IDS
    assert sum(x.shape[1] for x in parsed.values())==278
    assert all(x.shape[0]==1 for x in parsed.values())
    assert all(np.all(np.isfinite(x)) for x in parsed.values())

    # Positive bid replenishment + ask depletion should create positive top-level
    # queue/depth pressure in the synthetic fixture.
    assert parsed["S04"][0,0] > 0
    assert parsed["S05"][0,0] > 0

    # Raw MLOFI/event families must not collapse to all zeros.
    assert np.any(parsed["S11"][0] != 0)
    assert np.any(parsed["S21"][0] != 0)
    assert np.any(parsed["S29"][0] > 0)


def test_cpp_header_exact_strategy_widths(tmp_path: Path):
    root=Path(__file__).resolve().parents[1]
    exe=_compile(root,tmp_path/"build")
    raw=tmp_path/"raw.csv.gz"
    _,support_ts=_fixture(raw)
    support=tmp_path/"support.csv"
    support.write_text(f"local_timestamp_us\n{support_ts}\n",encoding="utf-8")
    out=tmp_path/"out.csv"
    p=subprocess.run([str(exe),str(raw),str(support),str(out)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr

    with out.open(newline="") as h:
        rows=list(csv.reader(h))
    assert len(rows)==2
    assert len(rows[0])==2+278
    assert rows[1][0]==str(support_ts)
    assert rows[1][1]=="1"

    expected=["local_timestamp_us","feature_valid"]
    for sid in m.RAW_IDS:
        expected.extend(m.expected_feature_names(sid))
    assert rows[0]==expected


def test_cpp_insufficient_depth_fails_closed(tmp_path: Path):
    root=Path(__file__).resolve().parents[1]
    exe=_compile(root,tmp_path/"build")
    raw=tmp_path/"raw.csv.gz"
    t0=1_800_000_000_000_000
    with gzip.open(raw,"wt",encoding="utf-8",newline="") as h:
        w=csv.writer(h,lineterminator="\n")
        w.writerow(("exchange","symbol","timestamp","local_timestamp","is_snapshot","side","price","amount"))
        for i in range(10):
            w.writerow(["binance-futures","BTCUSDT",t0,t0,"true","bid",100.0-0.01*i,1.0])
            w.writerow(["binance-futures","BTCUSDT",t0,t0,"true","ask",100.02+0.01*i,1.0])
    support=tmp_path/"support.csv"
    support.write_text(f"local_timestamp_us\n{t0+1_000_000}\n",encoding="utf-8")
    out=tmp_path/"out.csv"
    p=subprocess.run([str(exe),str(raw),str(support),str(out)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    with out.open(newline="") as h:
        rows=list(csv.reader(h))
    assert rows[1][1]=="0"
    with pytest.raises(m.E1AMaterializationError) as e:
        m.parse_raw_extractor_csv(out,np.array([t0+1_000_000],dtype=np.int64))
    assert e.value.reason=="raw_extractor_feature_invalid"
