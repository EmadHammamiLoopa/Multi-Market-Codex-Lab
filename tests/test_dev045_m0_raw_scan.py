from __future__ import annotations

import gzip
import json
import subprocess
from pathlib import Path

from multimarket import dev045_m0_feasibility as m0


def _write_gz(path:Path,lines):
    with gzip.open(path,"wt",encoding="utf-8",newline="") as h:
        h.write("\n".join(lines)+"\n")


def test_raw_scanner_valid_synthetic_day(tmp_path):
    l2=tmp_path/"l2.csv.gz"
    tr=tmp_path/"trades.csv.gz"

    _write_gz(l2,[
        m0.L2_HEADER,
        "binance-futures,BTCUSDT,1000000,1000100,true,bid,100.0,2.0",
        "binance-futures,BTCUSDT,1000000,1000100,true,ask,100.1,3.0",
        "binance-futures,BTCUSDT,1001000,1001200,false,bid,100.0,1.5",
        "binance-futures,BTCUSDT,1002000,1002300,false,ask,100.1,0.0",
    ])

    _write_gz(tr,[
        m0.TRADE_HEADER,
        "binance-futures,BTCUSDT,1000500,1000600,1,buy,100.1,0.2",
        "binance-futures,BTCUSDT,1001500,1001700,2,sell,100.0,0.3",
    ])

    exe=m0._compile_scanner(tmp_path)
    p=subprocess.run([str(exe),str(l2),str(tr)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    rows=[json.loads(x) for x in p.stdout.splitlines() if x.strip()]
    assert len(rows)==2
    by={x["kind"]:x for x in rows}
    assert by["incremental_book_L2"]["snapshot_rows"]==2
    assert by["incremental_book_L2"]["zero_qty_rows"]==1
    assert by["incremental_book_L2"]["bad_rows"]==0
    assert by["trades"]["buy_rows"]==1
    assert by["trades"]["sell_rows"]==1
    assert by["trades"]["bad_rows"]==0


def test_raw_scanner_rejects_negative_feed_latency(tmp_path):
    l2=tmp_path/"l2.csv.gz"
    tr=tmp_path/"trades.csv.gz"

    _write_gz(l2,[
        m0.L2_HEADER,
        "binance-futures,BTCUSDT,1000000,999000,true,bid,100.0,2.0",
        "binance-futures,BTCUSDT,1000000,999000,true,ask,100.1,3.0",
    ])
    _write_gz(tr,[
        m0.TRADE_HEADER,
        "binance-futures,BTCUSDT,1000000,1000100,1,buy,100.1,0.2",
        "binance-futures,BTCUSDT,1001000,1001100,2,sell,100.0,0.2",
    ])

    exe=m0._compile_scanner(tmp_path)
    p=subprocess.run([str(exe),str(l2),str(tr)],capture_output=True,text=True)
    assert p.returncode==4
