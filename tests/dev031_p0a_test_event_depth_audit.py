from datetime import datetime,timezone
import csv,gzip
from pathlib import Path
import pytest
from multimarket import dev031_p0a_event_depth_audit as p0a

def _fixture(path:Path, crossed:bool=False):
    d=p0a.DEVELOPMENT_DAYS[0]; start=int(datetime(d.year,d.month,d.day,tzinfo=timezone.utc).timestamp()*1_000_000)
    rows=[]
    for i in range(11):
        rows.append(["binance-futures","BTCUSDT",start+1000,start+1000,"true","bid",100-i,1])
        rows.append(["binance-futures","BTCUSDT",start+1000,start+1000,"true","ask",(99 if crossed else 101)+i,1])
    rows += [
      ["binance-futures","BTCUSDT",start+2000,start+2000,"false","bid",90,0],
      ["binance-futures","BTCUSDT",start+3000,start+3000,"false","ask",112,2],
    ]
    path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(path,"wt",encoding="utf-8",newline="") as f:
        w=csv.writer(f,lineterminator="\n"); w.writerow(p0a.EXPECTED_HEADER); w.writerows(rows)

def test_valid_snapshot_reconstruction_and_live_depth(tmp_path):
    d=p0a.DEVELOPMENT_DAYS[0]; root=tmp_path/"raw"; path=root/f"{d.isoformat()}.csv.gz"; _fixture(path)
    x=p0a.audit_day(path,raw_root=root,day=d)
    assert x.snapshot_groups==1
    assert x.initialized_after_snapshot is True
    assert x.max_bid_levels>=11 and x.max_ask_levels>=11
    assert x.max_simultaneous_min_side_depth>=11
    assert x.post_valid_initialization_incremental_rows>0
    assert all(p0a.day_gates(x).values())

def test_crossed_snapshot_does_not_initialize(tmp_path):
    d=p0a.DEVELOPMENT_DAYS[0]; root=tmp_path/"raw"; path=root/f"{d.isoformat()}.csv.gz"; _fixture(path,crossed=True)
    x=p0a.audit_day(path,raw_root=root,day=d)
    assert x.initialized_after_snapshot is False
    assert p0a.day_gates(x)["valid_book_initialized_after_snapshot"] is False
    assert p0a.day_gates(x)["simultaneous_depth_beyond_top10_present"] is False

def test_forward_guards_false():
    assert not any(p0a.FORWARD_GUARDS.values())

def test_exact_scope():
    assert [d.isoformat() for d in p0a.DEVELOPMENT_DAYS]==["2026-01-01","2026-02-01","2026-03-01","2026-04-01","2026-05-01","2026-06-01","2026-07-01"]

def test_canonical_override_rejected(tmp_path):
    with pytest.raises(p0a.P0AAuditError) as e:
        p0a.run_p0a(raw_root=tmp_path,output_directory=p0a.REAL_OUTPUT_DIRECTORY,require_canonical_output=True)
    assert e.value.reason=="canonical_raw_root_override_forbidden"

def test_output_identity():
    assert p0a.EXPERIMENT_ID=="DEV031-P0A"
    assert p0a.DESIGN_VERSION=="event-depth-raw-l2-feasibility-v2"


def test_worker_matches_direct_audit(tmp_path):
    d=p0a.DEVELOPMENT_DAYS[0]
    root=tmp_path/"raw"
    path=root/f"{d.isoformat()}.csv.gz"
    _fixture(path)
    direct=p0a.audit_day(path,raw_root=root,day=d)
    wd,item,error=p0a._audit_day_worker((str(root),d))
    assert error is None
    assert wd==d
    assert item==direct
