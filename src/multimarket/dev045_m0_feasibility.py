from __future__ import annotations

from datetime import date
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

EXPERIMENT_ID="DEV045-M0"
DESIGN_VERSION="maker-feasibility-mbp-queue-audit-v1"

DAYS=tuple(date(2026,m,1) for m in range(1,8))
SYMBOL="BTCUSDT"

RAW_ROOT=Path("/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw")
REAL_OUTPUT_DIRECTORY=Path("/home/emadh/Multi-Market/evidence/dev045_m0_maker_feasibility_v1")
ARTIFACT_FILENAME="DEV045_M0_MAKER_FEASIBILITY_RESULT.json"

L2_HEADER="exchange,symbol,timestamp,local_timestamp,is_snapshot,side,price,amount"
TRADE_HEADER="exchange,symbol,timestamp,local_timestamp,id,side,price,amount"

HFTBACKTEST_PIN="2.4.4"
QUEUE_PRIMARY="RISK_ADVERSE"
QUEUE_DIAGNOSTIC="LOG_PROB"

FORWARD_GUARDS={
    "maker_pnl_run":False,
    "spread_capture_computed":False,
    "strategy_pf_computed":False,
    "strategy_drawdown_computed":False,
    "maker_leaderboard_run":False,
    "sep01_plus_opened":False,
    "other_market_opened":False,
}

class M0Error(RuntimeError):
    pass

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _repo_root()->Path:
    return Path(__file__).resolve().parents[2]

def _compile_scanner(build_dir:Path)->Path:
    src=_repo_root()/"tools"/"dev045_m0_raw_scan.cpp"
    if not src.is_file():
        raise M0Error("scanner_source_missing")
    cxx=shutil.which("g++")
    if cxx is None:
        raise M0Error("g++_missing")
    exe=build_dir/"dev045_m0_raw_scan"
    p=subprocess.run(
        [cxx,"-std=c++17","-O3","-DNDEBUG",str(src),"-lz","-o",str(exe)],
        capture_output=True,text=True,
    )
    if p.returncode!=0:
        raise M0Error("scanner_build:"+p.stderr[-2000:])
    return exe

def _paths(day:date):
    d=day.isoformat()
    return (
        RAW_ROOT/"incremental_book_L2"/SYMBOL/f"{d}.csv.gz",
        RAW_ROOT/"trades"/SYMBOL/f"{d}.csv.gz",
    )

def _scan_one(exe:Path,day:date)->dict:
    l2,tr=_paths(day)
    if not l2.is_file():
        raise M0Error(f"l2_missing:{day}")
    if not tr.is_file():
        raise M0Error(f"trades_missing:{day}")
    p=subprocess.run([str(exe),str(l2),str(tr)],capture_output=True,text=True)
    if p.returncode!=0:
        raise M0Error(f"scanner_fail:{day}:rc={p.returncode}:stderr={p.stderr[-2000:]}")
    lines=[x for x in p.stdout.splitlines() if x.strip()]
    if len(lines)!=2:
        raise M0Error(f"scanner_output:{day}:{len(lines)}")
    rec=[json.loads(x) for x in lines]
    kinds={x["kind"]:x for x in rec}
    if set(kinds)!={"incremental_book_L2","trades"}:
        raise M0Error(f"scanner_kinds:{day}")
    l2s=kinds["incremental_book_L2"];trs=kinds["trades"]

    checks={
        "l2_rows_positive":int(l2s["rows"])>0,
        "trades_rows_positive":int(trs["rows"])>0,
        "l2_bad_rows_zero":int(l2s["bad_rows"])==0,
        "trades_bad_rows_zero":int(trs["bad_rows"])==0,
        "snapshot_rows_positive":int(l2s["snapshot_rows"])>0,
        "bid_rows_positive":int(l2s["bid_rows"])>0,
        "ask_rows_positive":int(l2s["ask_rows"])>0,
        "buy_trades_positive":int(trs["buy_rows"])>0,
        "sell_trades_positive":int(trs["sell_rows"])>0,
        "l2_local_regressions_zero":int(l2s["local_regressions"])==0,
        "trade_local_regressions_zero":int(trs["local_regressions"])==0,
        "l2_negative_feed_latency_zero":int(l2s["negative_feed_latency"])==0,
        "trade_negative_feed_latency_zero":int(trs["negative_feed_latency"])==0,
        "l2_exchange_and_local_ts_present":(
            int(l2s["min_exchange_ts"])>0 and int(l2s["min_local_ts"])>0
        ),
        "trade_exchange_and_local_ts_present":(
            int(trs["min_exchange_ts"])>0 and int(trs["min_local_ts"])>0
        ),
    }
    return {
        "day":day.isoformat(),
        "l2_path":str(l2),
        "l2_bytes":int(l2.stat().st_size),
        "l2_sha256":_sha(l2),
        "trades_path":str(tr),
        "trades_bytes":int(tr.stat().st_size),
        "trades_sha256":_sha(tr),
        "l2":l2s,
        "trades":trs,
        "checks":checks,
        "pass":bool(all(checks.values())),
    }

def _aggregate(days)->dict:
    return {
        "days":len(days),
        "all_days_pass":bool(all(x["pass"] for x in days)),
        "total_l2_rows":int(sum(int(x["l2"]["rows"]) for x in days)),
        "total_trade_rows":int(sum(int(x["trades"]["rows"]) for x in days)),
        "total_snapshot_rows":int(sum(int(x["l2"]["snapshot_rows"]) for x in days)),
        "total_l2_zero_qty_rows":int(sum(int(x["l2"]["zero_qty_rows"]) for x in days)),
        "total_unknown_trade_rows":int(sum(int(x["trades"]["unknown_rows"]) for x in days)),
        "max_l2_feed_latency_us":int(max(int(x["l2"]["max_feed_latency_us"]) for x in days)),
        "max_trade_feed_latency_us":int(max(int(x["trades"]["max_feed_latency_us"]) for x in days)),
    }

def run(*,execution_commit:str,output_directory:Path=REAL_OUTPUT_DIRECTORY,require_canonical_output:bool=True):
    if any(FORWARD_GUARDS.values()):
        raise M0Error("forward_guard")
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise M0Error("execution_commit")
    out=Path(output_directory)
    if require_canonical_output and out!=REAL_OUTPUT_DIRECTORY:
        raise M0Error("noncanonical_output")
    if not require_canonical_output and out==REAL_OUTPUT_DIRECTORY:
        raise M0Error("canonical_requires_real")
    if out.exists() or out.is_symlink():
        raise M0Error("output_exists")

    with tempfile.TemporaryDirectory(prefix="dev045_m0_") as td:
        exe=_compile_scanner(Path(td))
        day_records=[_scan_one(exe,d) for d in DAYS]

    agg=_aggregate(day_records)

    # Existing source is explicitly Market-By-Price. Exact FIFO queue rank is
    # not observable; even a successful data audit therefore remains
    # conditional on conservative queue modeling and later live calibration.
    if agg["all_days_pass"]:
        status="DEV045_M0_CONDITIONAL_MBP_QUEUE_MODEL_ONLY"
    else:
        status="DEV045_M0_FAIL_MAKER_DATA_INSUFFICIENT"

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "status":status,
        "symbol":SYMBOL,
        "days":[d.isoformat() for d in DAYS],
        "source":"Tardis Binance Futures incremental_book_L2 + trades",
        "market_data_representation":"MARKET_BY_PRICE_L2",
        "market_by_order_available":False,
        "exact_fifo_queue_rank_observable":False,
        "raw_headers":{
            "incremental_book_L2":L2_HEADER,
            "trades":TRADE_HEADER,
        },
        "queue_model_plan":{
            "primary":QUEUE_PRIMARY,
            "diagnostic":QUEUE_DIAGNOSTIC,
            "touch_equals_fill_forbidden":True,
            "prospective_live_fill_calibration_required":True,
        },
        "latency_feasibility_ms":{
            "diagnostic":100,
            "primary":250,
            "stress":500,
        },
        "simulator":{
            "name":"hftbacktest",
            "pinned_version":HFTBACKTEST_PIN,
            "api_compatibility_required_before_m1":True,
            "required_capabilities":[
                "risk_adverse_queue_model",
                "probability_queue_model",
                "partial_fill_exchange",
                "no_partial_fill_exchange",
                "constant_order_latency",
                "fee_model_hooks",
                "initial_snapshot",
                "market_by_price_replay",
            ],
        },
        "day_records":day_records,
        "aggregate":agg,
        "maker_pnl_run":False,
        "spread_capture_computed":False,
        "strategy_pf_computed":False,
        "strategy_drawdown_computed":False,
        "maker_leaderboard_run":False,
        "sep01_plus_opened":False,
        "other_market_opened":False,
        "forward_guards":dict(FORWARD_GUARDS),
    }

    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    staging=out.parent/f".{out.name}.part-{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise M0Error("staging_exists")
    staging.mkdir(parents=True)
    try:
        final=staging/ARTIFACT_FILENAME
        with final.open("xb") as h:
            h.write(content);h.flush();os.fsync(h.fileno())
        os.replace(staging,out)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging,ignore_errors=True)
        raise

    final=out/ARTIFACT_FILENAME
    return {
        "status":status,
        "artifact_path":str(final),
        "artifact_bytes":int(final.stat().st_size),
        "artifact_sha256":_sha(final),
        "aggregate":agg,
    }
