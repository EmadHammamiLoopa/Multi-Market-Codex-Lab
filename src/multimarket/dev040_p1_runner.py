from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import shutil

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev036_c1_loader as c1loader
from . import dev037_p0_r1_coverage_core as coverage
from . import dev037_p0_r1_coverage_runner as r1runner
from . import dev040_p0_core as p0core
from . import dev040_p1_core as core

EXPERIMENT_ID="DEV040-P1"
DESIGN_VERSION="single-frozen-economic-baseline-v1"

PARENT_P0=Path(
    "/home/emadh/Multi-Market/evidence/dev040_p0_economic_support_audit_v1/"
    "DEV040_P0_ECONOMIC_SUPPORT_AUDIT_RESULT.json"
)
PARENT_P0_SHA="c328cc52bf7fee9239c1713fd6fedbfc7738f1b448d24b7b537b6111526f118a"
PARENT_P0_BYTES=7289

PARENT_P2=Path(
    "/home/emadh/Multi-Market/evidence/dev038a_p2_final_controller_correctness_v1/"
    "DEV038A_P2_FINAL_CONTROLLER_CORRECTNESS_RESULT.json"
)
PARENT_P2_SHA="df32874a362cd75f646cdca483dc46956797431ac9a5861435639dfbf7f4b311"
PARENT_P2_BYTES=191547

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev040_p1_economic_baseline_v1"
)
ARTIFACT_FILENAME="DEV040_P1_ECONOMIC_BASELINE_RESULT.json"

FORWARD_GUARDS={
    "sep01_plus_opened":False,
    "other_market_opened":False,
    "predictive_tuning_run":False,
    "alternate_holding_period_tested":False,
    "tp_sl_grid_run":False,
    "maker_rescue_run":False,
    "fee_optimization_run":False,
    "slippage_optimization_run":False,
    "latency_optimization_run":False,
    "leverage_run":False,
    "position_sizing_search_run":False,
}

class RunnerError(RuntimeError):
    pass

def _sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _load_json(path:Path,sha:str,nbytes:int,status:str):
    if not path.is_file():
        raise RunnerError(f"missing:{path.name}")
    if _sha(path)!=sha or path.stat().st_size!=nbytes:
        raise RunnerError(f"identity:{path.name}")
    x=json.loads(path.read_text(encoding="utf-8"))
    if x.get("status")!=status:
        raise RunnerError(f"status:{path.name}:{x.get('status')}")
    return x

def _raw():
    rows=tuple(dd.load_authorized_days())
    if tuple(x.day for x in rows)!=dd.HISTORICAL_DAYS:
        raise RunnerError("raw_calendar")
    return {x.day:x for x in rows}

def _action_hash(fid:int,actions):
    h=hashlib.sha256(f"DEV038-A-P2-ACTION-C2-F{fid}".encode()+b"\0")
    h.update(np.asarray(actions,dtype=np.int8).tobytes())
    return h.hexdigest()

def _folds(e,p2):
    out=[]
    total=0
    for outer in dd.OUTER_FOLDS:
        z=r1runner._fold_score_streams(e,outer)
        rr=coverage.summarize(
            scores=z["validation_scores"]["S0"],
            p_long=z["validation_p_long"],
            warm_scores=z["train_scores"]["S0"],
            window=720,
        )
        actions=np.asarray(rr.actions,dtype=np.int8)
        ts=np.asarray(e.per_day[outer.validation_day].t2.timestamps_us,dtype=np.int64)
        observed=_action_hash(outer.fold_id,actions)
        expected=p2["controller_records"]["C2"]["folds"][outer.fold_id-1]["action_sha256"]
        if observed!=expected:
            raise RunnerError(f"action_hash_F{outer.fold_id}")
        total+=int(np.sum(actions!=0))
        out.append((outer,ts,actions,observed))
    if total!=1104:
        raise RunnerError(f"raw_actions:{total}")
    return tuple(out)

def _build_trades(daydata,day_iso:str,audits):
    out=[]
    for t in audits:
        eb=float(daydata.bid[t.entry_index])
        ea=float(daydata.ask[t.entry_index])
        xb=float(daydata.bid[t.exit_index])
        xa=float(daydata.ask[t.exit_index])
        g=core.gross_bps(t.action,eb,ea,xb,xa)
        out.append(core.TradeEconomic(
            day=day_iso,
            action=int(t.action),
            decision_timestamp_us=int(t.decision_timestamp_us),
            entry_timestamp_us=int(t.entry_timestamp_us),
            exit_timestamp_us=int(t.exit_timestamp_us),
            entry_price=float(ea if t.action==p0core.ACTION_LONG else eb),
            exit_price=float(xb if t.action==p0core.ACTION_LONG else xa),
            entry_spread_bps=float(t.entry_spread_bps),
            exit_spread_bps=float(t.exit_spread_bps),
            gross_bps=float(g),
        ))
    return tuple(out)

def _trade_hash(latency_ms:int,trades):
    h=hashlib.sha256(f"DEV040-P1-TRADE-LEDGER-L{latency_ms}".encode()+b"\0")
    for t in trades:
        h.update(
            f"{t.day}|{t.action}|{t.decision_timestamp_us}|{t.entry_timestamp_us}|"
            f"{t.exit_timestamp_us}|{t.entry_price:.12g}|{t.exit_price:.12g}|"
            f"{t.entry_spread_bps:.12g}|{t.exit_spread_bps:.12g}|{t.gross_bps:.12g}\n".encode()
        )
    return h.hexdigest()

def _sanitize(obj):
    if isinstance(obj,float) and math.isinf(obj):
        return "INF"
    if isinstance(obj,dict):
        return {k:_sanitize(v) for k,v in obj.items()}
    if isinstance(obj,list):
        return [_sanitize(v) for v in obj]
    return obj

def run(*,execution_commit:str,output_directory:Path=REAL_OUTPUT_DIRECTORY,require_canonical_output:bool=True):
    if any(FORWARD_GUARDS.values()):
        raise RunnerError("forbidden_activity_guard")
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise RunnerError("execution_commit")

    out=Path(output_directory)
    if require_canonical_output and out!=REAL_OUTPUT_DIRECTORY:
        raise RunnerError("noncanonical_output")
    if not require_canonical_output and out==REAL_OUTPUT_DIRECTORY:
        raise RunnerError("canonical_requires_real")
    if out.exists() or out.is_symlink():
        raise RunnerError("output_exists")

    p0=_load_json(PARENT_P0,PARENT_P0_SHA,PARENT_P0_BYTES,"DEV040_P0_ECONOMIC_SUPPORT_AUDIT_PASS")
    p2=_load_json(PARENT_P2,PARENT_P2_SHA,PARENT_P2_BYTES,"DEV038A_P2_CONTROLLER_SURVIVOR_FOUND")
    if p2.get("advanced_controller")!=["C2"]:
        raise RunnerError("p2_controller")

    e=c1loader.load_c1()
    raw=_raw()
    folds=_folds(e,p2)

    trades_by_latency={lat:[] for lat in p0core.LATENCIES_MS}
    per_day_support=[]

    for outer,ts,actions,ahash in folds:
        d=raw[outer.validation_day]
        row={"fold_id":int(outer.fold_id),"day":outer.validation_day.isoformat(),"action_sha256":ahash,"latencies":{}}

        for lat in p0core.LATENCIES_MS:
            audits,ignored=p0core.flat_only_audit(
                decision_timestamps_us=ts,
                actions=actions,
                raw_timestamps_us=d.ts,
                bid=d.bid,
                ask=d.ask,
                book_valid=d.book_valid,
                latency_ms=lat,
            )
            pub=p0core.public_summary(audits,ignored,int(np.sum(actions!=0)))
            frozen=p0["folds"][outer.fold_id-1]["latencies"][str(lat)]
            if pub!=frozen:
                raise RunnerError(f"p0_reproduction_F{outer.fold_id}_L{lat}")
            built=_build_trades(d,outer.validation_day.isoformat(),audits)
            trades_by_latency[lat].extend(built)
            row["latencies"][str(lat)]={
                "accepted_flat_only_trades":len(built),
                "ignored_overlap_actions":int(ignored),
                "trade_ledger_sha256":_trade_hash(lat,built),
            }
        per_day_support.append(row)

    for lat in p0core.LATENCIES_MS:
        if len(trades_by_latency[lat])!=570:
            raise RunnerError(f"trade_count_L{lat}:{len(trades_by_latency[lat])}")

    scenario_specs=[
        ("PRIMARY_8FEE_1SLIP_SIDE",250,8.0,1.0),
        ("PRIMARY_8FEE_0SLIP",250,8.0,0.0),
        ("STRESS_12FEE_0SLIP",250,12.0,0.0),
        ("SEVERE_12FEE_2SLIP_SIDE",250,12.0,2.0),
        ("LATENCY500_8FEE_1SLIP_SIDE",500,8.0,1.0),
        ("LATENCY1000_8FEE_1SLIP_SIDE",1000,8.0,1.0),
    ]

    scenarios={}
    for sid,lat,fee,slip in scenario_specs:
        scenarios[sid]=core.scenario_metrics(
            trades_by_latency[lat],
            fee_roundtrip_bps=fee,
            slippage_per_side_bps=slip,
        )

    primary=scenarios["PRIMARY_8FEE_1SLIP_SIDE"]
    lat500_gross=scenarios["LATENCY500_8FEE_1SLIP_SIDE"]["mean_gross_bps"]
    status,gates,taxonomy=core.classify(primary,lat500_gross)

    # Gates 2/3 in the design also require both directions.
    directions={
        "long_trades":int(sum(t.action==p0core.ACTION_LONG for t in trades_by_latency[250])),
        "short_trades":int(sum(t.action==p0core.ACTION_SHORT for t in trades_by_latency[250])),
    }
    gates["long_and_short_positive"]=directions["long_trades"]>0 and directions["short_trades"]>0
    if not gates["long_and_short_positive"]:
        status="DEV040_P1_ECONOMIC_BASELINE_FAIL"
        taxonomy="F2_NET_POSITIVE_BUT_UNSTABLE" if primary["mean_net_bps"]>0 else taxonomy

    pooled_spreads={
        str(lat):{
            "entry_median_bps":float(np.median([t.entry_spread_bps for t in trades_by_latency[lat]])),
            "entry_p90_bps":float(np.quantile([t.entry_spread_bps for t in trades_by_latency[lat]],0.90,method="higher")),
            "exit_median_bps":float(np.median([t.exit_spread_bps for t in trades_by_latency[lat]])),
            "exit_p90_bps":float(np.quantile([t.exit_spread_bps for t in trades_by_latency[lat]],0.90,method="higher")),
        } for lat in p0core.LATENCIES_MS
    }

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "status":status,
        "failure_taxonomy":taxonomy,
        "parent_p0":{"path":str(PARENT_P0),"sha256":PARENT_P0_SHA,"bytes":PARENT_P0_BYTES},
        "parent_p2":{"path":str(PARENT_P2),"sha256":PARENT_P2_SHA,"bytes":PARENT_P2_BYTES},
        "frozen_policy":"A0_PRICE32+BTC45+S0+W720",
        "economic_days":[x.validation_day.isoformat() for x in dd.OUTER_FOLDS],
        "raw_actions":1104,
        "primary_flat_only_trades":570,
        "primary_directions":directions,
        "holding_seconds":120,
        "scenario_specs":[{"id":sid,"latency_ms":lat,"fee_roundtrip_bps":fee,"slippage_per_side_bps":slip} for sid,lat,fee,slip in scenario_specs],
        "scenarios":_sanitize(scenarios),
        "pooled_spreads_bps":pooled_spreads,
        "support_reproduction":per_day_support,
        "trade_ledger_sha256":{str(lat):_trade_hash(lat,trades_by_latency[lat]) for lat in p0core.LATENCIES_MS},
        "primary_gates":gates,
        "forward_guards":dict(FORWARD_GUARDS),
        "predictive_search_closed":True,
        "sep01_plus_remains_sealed":True,
        "other_markets_remain_sealed":True,
    }

    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    staging=out.parent/f".{out.name}.part-{os.getpid()}"
    if staging.exists():
        raise RunnerError("staging_exists")
    staging.mkdir(parents=True)
    try:
        final=staging/ARTIFACT_FILENAME
        with final.open("xb") as h:
            h.write(content);h.flush();os.fsync(h.fileno())
        os.replace(staging,out)
    except BaseException:
        if staging.exists(): shutil.rmtree(staging,ignore_errors=True)
        raise

    final=out/ARTIFACT_FILENAME
    return {
        "artifact_path":str(final),
        "artifact_sha256":_sha(final),
        "artifact_bytes":int(final.stat().st_size),
        "status":status,
        "failure_taxonomy":taxonomy,
    }
