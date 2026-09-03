from __future__ import annotations

from datetime import date
from pathlib import Path
import csv
import hashlib
import json
import math
import os
import shutil
from typing import Any

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev044_t0_strategy_contract as contract
from . import dev044_t0f_gate_bootstrap as gates
from . import dev044_t1_execution as exe

EXPERIMENT_ID="DEV044-T1"
DESIGN_VERSION="economic-arena-common-execution-v1"

T0E_ROOT=Path("/home/emadh/Multi-Market/evidence/dev044_t0e_support_audit_v1")
T0E_MANIFEST=T0E_ROOT/"DEV044_T0E_SUPPORT_AUDIT_RESULT.json"
T0E_MANIFEST_BYTES=23401
T0E_MANIFEST_SHA256="66864b5e90f3c5ca7d53b5a149cdcb65223eac04c04e68511fc998a0efcb84e8"

ACTION_IDENTITIES={
    "2026-04-01":(268243,"5916f11be83d263ec7a3f54146d7d829ed41e88eb9d9cf74bdad5768bbb7bed8"),
    "2026-05-01":(267598,"2bf6f88fb53e55cfd07ba084bd8df6db1007657da659d2a8bab4d04e79b45356"),
    "2026-06-01":(267859,"70535e338a3e84b4dd9add36fbac42e313b583842fba7d73245716d55b88505e"),
    "2026-07-01":(268648,"1fce7c717a744ca8bfb550516ba2baf9c858916f005ace97f2ed9082b71ccf64"),
}
DAYS=tuple(ACTION_IDENTITIES)

REAL_OUTPUT_DIRECTORY=Path("/home/emadh/Multi-Market/evidence/dev044_t1_economic_arena_v1")
MANIFEST_FILENAME="DEV044_T1_ECONOMIC_ARENA_RESULT.json"
PRIMARY_TRADES_FILENAME="DEV044_T1_PRIMARY_TRADES.csv"
LATENCY_TRADES_FILENAME="DEV044_T1_LATENCY_STRESS_TRADES.csv"
BLOCKS_FILENAME="DEV044_T1_PRIMARY_4H_BLOCKS.csv"

FORWARD_GUARDS={
    "sep01_plus_opened":False,
    "other_market_opened":False,
    "maker_execution_run":False,
    "strategy_threshold_changed":False,
    "cost_grid_changed":False,
    "family_reduced":False,
    "post_pnl_rescue_run":False,
}

class T1RunnerError(RuntimeError):
    pass

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _verify_parent()->dict:
    if not T0E_MANIFEST.is_file():
        raise T1RunnerError("t0e_manifest_missing")
    if T0E_MANIFEST.stat().st_size!=T0E_MANIFEST_BYTES:
        raise T1RunnerError("t0e_manifest_bytes")
    if _sha(T0E_MANIFEST)!=T0E_MANIFEST_SHA256:
        raise T1RunnerError("t0e_manifest_sha")
    x=json.loads(T0E_MANIFEST.read_text(encoding="utf-8"))
    if x.get("status")!="DEV044_T0E_ACTION_SUPPORT_AUDIT_PASS":
        raise T1RunnerError("t0e_status")
    if x.get("execution_commit")!="aeaa5c220dbaf936305ebf53d1a70f47dbd6a4d5":
        raise T1RunnerError("t0e_execution_commit")
    if x.get("candidate_count")!=32 or x.get("core_count")!=16:
        raise T1RunnerError("t0e_family")
    if x.get("pnl_run") is not False or x.get("economic_ranking_run") is not False:
        raise T1RunnerError("t0e_guard")
    return x

def _load_actions(day_name:str)->tuple[np.ndarray,dict[str,np.ndarray]]:
    if day_name not in ACTION_IDENTITIES:
        raise T1RunnerError("action_day")
    p=T0E_ROOT/f"{day_name}_DEV044_ACTIONS.csv"
    expected_bytes,expected_sha=ACTION_IDENTITIES[day_name]
    if not p.is_file() or p.stat().st_size!=expected_bytes or _sha(p)!=expected_sha:
        raise T1RunnerError(f"action_identity:{day_name}")
    with p.open("r",encoding="utf-8",newline="") as h:
        r=csv.DictReader(h)
        fields=tuple(r.fieldnames or ())
        required=("local_timestamp_us",)+tuple(f"{cid}_ACTION" for cid in contract.CANDIDATE_IDS)
        if any(x not in fields for x in required):
            raise T1RunnerError(f"action_header:{day_name}")
        ts=[]
        out={cid:[] for cid in contract.CANDIDATE_IDS}
        for row in r:
            ts.append(int(row["local_timestamp_us"]))
            for cid in contract.CANDIDATE_IDS:
                out[cid].append(int(row[f"{cid}_ACTION"]))
    t=np.asarray(ts,dtype=np.int64)
    if len(t)!=1379 or np.any(np.diff(t)<=0):
        raise T1RunnerError(f"action_support:{day_name}")
    arrays={cid:np.asarray(v,dtype=np.int8) for cid,v in out.items()}
    for cid,a in arrays.items():
        if a.shape!=(1379,) or np.any(~np.isin(a,(contract.ABSTAIN,contract.LONG,contract.SHORT))):
            raise T1RunnerError(f"action_values:{day_name}:{cid}")
    return t,arrays

def _load_days():
    rows={x.day.isoformat():x for x in dd.load_authorized_days() if x.day.isoformat() in DAYS}
    if tuple(rows)!=DAYS:
        raise T1RunnerError("day_calendar")
    return rows

def _mechanical_support(parent:dict,cid:str)->gates.MechanicalSupport:
    per=[]
    for rec in parent["day_records"]:
        per.append(int(rec["summary"]["candidates"][cid]["active"]))
    pooled=int(parent["pooled_summary"]["candidates"][cid]["active"])
    return gates.MechanicalSupport(cid,pooled,tuple(per))

def _net_values(trades,cost:float)->np.ndarray:
    return np.asarray([float(t.gross_bps)-float(cost) for t in trades],dtype=np.float64)

def _exact_four_day_metrics(trades,cost:float):
    net=_net_values(trades,cost)
    by_day=[]
    daily=[]
    for d in DAYS:
        vals=np.asarray([net[i] for i,t in enumerate(trades) if t.day==d],dtype=np.float64)
        by_day.append(int(len(vals)))
        daily.append(float(np.sum(vals)) if len(vals) else 0.0)
    loo=[]
    for omit in DAYS:
        vals=np.asarray([net[i] for i,t in enumerate(trades) if t.day!=omit],dtype=np.float64)
        loo.append(float(np.mean(vals)) if len(vals) else 0.0)
    positive=[max(0.0,v) for v in daily]
    pos_total=float(sum(positive))
    concentration=float(max(positive)/pos_total) if pos_total>0 else 1.0
    return tuple(by_day),tuple(daily),tuple(loo),concentration

def _candidate_metric(
    cid:str,
    primary_execs,
    latency_execs,
)->tuple[gates.EconomicMetrics,dict[str,Any],tuple,tuple]:
    primary=tuple(
        sorted(
            [t for r in primary_execs for t in r.trades],
            key=lambda t:(t.decision_timestamp_us,t.exit_timestamp_us),
        )
    )
    latency=tuple(
        sorted(
            [t for r in latency_execs for t in r.trades],
            key=lambda t:(t.decision_timestamp_us,t.exit_timestamp_us),
        )
    )
    e10=exe.economics(primary,gates.PRIMARY_COST_BPS_RT)
    e16=exe.economics(primary,gates.STRESS_COST_BPS_RT)
    elat=exe.economics(latency,gates.PRIMARY_COST_BPS_RT)

    by_day,daily,loo,concentration=_exact_four_day_metrics(primary,gates.PRIMARY_COST_BPS_RT)
    failures=int(sum(r.execution_integrity_failures for r in primary_execs))
    accepted_long=int(sum(t.action==contract.LONG for t in primary))
    accepted_short=int(sum(t.action==contract.SHORT for t in primary))

    metrics=gates.EconomicMetrics(
        candidate_id=cid,
        execution_integrity_failures=failures,
        accepted_trades=int(len(primary)),
        accepted_by_day=by_day,
        accepted_long=accepted_long,
        accepted_short=accepted_short,
        pooled_primary_net_expectancy_bps=float(e10["mean_net_bps"] or 0.0),
        primary_profit_factor=float(e10["profit_factor"]),
        positive_days=int(sum(v>0 for v in daily)),
        loo_primary_net_expectancy_bps=loo,
        positive_day_concentration=float(concentration),
        max_drawdown_bps=float(e10["max_drawdown_bps"]),
        stress_cost_net_expectancy_bps=float(e16["mean_net_bps"] or 0.0),
        latency_stress_net_expectancy_bps=float(elat["mean_net_bps"] or 0.0),
        median_daily_primary_net_bps=float(np.median(daily)),
    )
    extra={
        "primary":e10,
        "stress_16bp":e16,
        "latency_500_500":elat,
        "primary_daily_net_bps":list(daily),
        "primary_loo_mean_net_bps":list(loo),
        "primary_ignored_overlap_actions":int(sum(r.ignored_overlap_actions for r in primary_execs)),
        "primary_emitted_actions":int(sum(r.emitted_actions for r in primary_execs)),
        "latency_execution_integrity_failures":int(sum(r.execution_integrity_failures for r in latency_execs)),
        "latency_ignored_overlap_actions":int(sum(r.ignored_overlap_actions for r in latency_execs)),
    }
    return metrics,extra,primary,latency

def _ranking_key(m:gates.EconomicMetrics):
    return (
        -min(m.loo_primary_net_expectancy_bps),
        -m.median_daily_primary_net_bps,
        -m.pooled_primary_net_expectancy_bps,
        -m.stress_cost_net_expectancy_bps,
        -m.primary_profit_factor,
        m.max_drawdown_bps,
        m.positive_day_concentration,
        -m.accepted_trades,
        m.candidate_id,
    )

def _paired_ci(a:np.ndarray,u:np.ndarray,*,seed:int=440045,reps:int=20_000):
    d=np.asarray(a,dtype=np.float64)-np.asarray(u,dtype=np.float64)
    if d.shape!=(24,):
        raise T1RunnerError("paired_block_shape")
    rng=np.random.default_rng(seed)
    means=np.empty(reps,dtype=np.float64)
    for i in range(reps):
        idx=rng.integers(0,24,size=24)
        means[i]=float(np.mean(d[idx]))
    lo,hi=np.quantile(means,[0.025,0.975],method="linear")
    return {
        "mean_block_delta_bps":float(np.mean(d)),
        "ci95_low":float(lo),
        "ci95_high":float(hi),
        "bootstrap_reps":int(reps),
        "bootstrap_seed":int(seed),
    }

def _write_trades(path:Path,records):
    header=(
        "candidate_id","day","action","decision_timestamp_us","entry_timestamp_us",
        "barrier_touch_timestamp_us","exit_timestamp_us","entry_price","exit_price",
        "gross_bps","exit_reason",
    )
    with path.open("x",encoding="utf-8",newline="") as h:
        w=csv.writer(h,lineterminator="\n");w.writerow(header)
        for cid,trades in records:
            for t in trades:
                w.writerow([
                    cid,t.day,t.action,t.decision_timestamp_us,t.entry_timestamp_us,
                    "" if t.barrier_touch_timestamp_us is None else t.barrier_touch_timestamp_us,
                    t.exit_timestamp_us,format(t.entry_price,".17g"),format(t.exit_price,".17g"),
                    format(t.gross_bps,".17g"),t.exit_reason,
                ])

def _write_blocks(path:Path,block_map):
    with path.open("x",encoding="utf-8",newline="") as h:
        w=csv.writer(h,lineterminator="\n")
        w.writerow(["block_index",*contract.CANDIDATE_IDS])
        for i in range(24):
            w.writerow([i,*[format(float(block_map[c][i]),".17g") for c in contract.CANDIDATE_IDS]])

def _safe_json(x):
    if isinstance(x,float):
        if math.isnan(x): return None
        if math.isinf(x): return "INF" if x>0 else "-INF"
    if isinstance(x,dict): return {k:_safe_json(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [_safe_json(v) for v in x]
    return x

def run(*,execution_commit:str,output_directory:Path=REAL_OUTPUT_DIRECTORY,require_canonical_output:bool=True):
    if any(FORWARD_GUARDS.values()):
        raise T1RunnerError("forward_guard")
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise T1RunnerError("execution_commit")
    out=Path(output_directory)
    if require_canonical_output and out!=REAL_OUTPUT_DIRECTORY:
        raise T1RunnerError("noncanonical_output")
    if not require_canonical_output and out==REAL_OUTPUT_DIRECTORY:
        raise T1RunnerError("canonical_requires_real")
    if out.exists() or out.is_symlink():
        raise T1RunnerError("output_exists")

    parent=_verify_parent()
    days=_load_days()
    actions={d:_load_actions(d) for d in DAYS}

    metric_by={}
    extra_by={}
    primary_by={}
    latency_by={}
    blocks={}

    for cid in contract.CANDIDATE_IDS:
        primary_execs=[]
        latency_execs=[]
        for d in DAYS:
            ts,aa=actions[d]
            primary_execs.append(exe.execute_candidate_day(
                candidate_id=cid,day_name=d,day=days[d],
                decisions=ts,actions=aa[cid],
                entry_latency_ms=250,response_latency_ms=250,
            ))
            latency_execs.append(exe.execute_candidate_day(
                candidate_id=cid,day_name=d,day=days[d],
                decisions=ts,actions=aa[cid],
                entry_latency_ms=500,response_latency_ms=500,
            ))
        m,e,p,l=_candidate_metric(cid,primary_execs,latency_execs)
        metric_by[cid]=m;extra_by[cid]=e;primary_by[cid]=p;latency_by[cid]=l
        blocks[cid]=exe.aligned_block_totals(
            p,cost_bps=gates.PRIMARY_COST_BPS_RT,days=DAYS,block_hours=gates.BLOCK_HOURS
        )

    maxstat=gates.block_maxstat_test(blocks)

    records=[]
    survivors=[]
    for cid in contract.CANDIDATE_IDS:
        ms=_mechanical_support(parent,cid)
        mech=gates.mechanical_eligible(ms)
        m=metric_by[cid]
        eg=gates.economic_gate_results(m)
        econ=bool(all(eg.values()))
        fwer=float(maxstat["fwer_pvalues"][cid])
        family_pass=bool(fwer<=gates.FAMILY_ALPHA)
        survivor=bool(mech and econ and family_pass)
        if survivor:
            survivors.append(cid)
        records.append({
            "candidate_id":cid,
            "mechanical_support":{
                "active_pooled":ms.active_pooled,
                "active_by_day":list(ms.active_by_day),
                "eligible":mech,
            },
            "economic_metrics":m.__dict__,
            "economic_gates":eg,
            "economic_eligible":econ,
            "fwer_p":fwer,
            "fwer_pass":family_pass,
            "survivor":survivor,
            **extra_by[cid],
        })

    ranked=sorted((metric_by[c] for c in survivors),key=_ranking_key)
    ranked_ids=[m.candidate_id for m in ranked]
    promoted=[]
    seen=set()
    for cid in ranked_ids:
        core=cid[:3]
        if core in seen:
            continue
        seen.add(core);promoted.append(cid)
        if len(promoted)>=4:
            break

    paired=[]
    for core in contract.CORE_IDS:
        u=f"{core}U";a=f"{core}A"
        eu=extra_by[u]["primary"];ea=extra_by[a]["primary"]
        paired.append({
            "core_id":core,
            "ungated":u,
            "a0_gated":a,
            "active_removed":int(
                parent["pooled_summary"]["candidates"][u]["active"]
                -parent["pooled_summary"]["candidates"][a]["active"]
            ),
            "accepted_trade_delta":int(ea["accepted_trades"]-eu["accepted_trades"]),
            "gross_bps_trade_delta":float((ea["mean_gross_bps"] or 0.0)-(eu["mean_gross_bps"] or 0.0)),
            "primary_net_bps_trade_delta":float((ea["mean_net_bps"] or 0.0)-(eu["mean_net_bps"] or 0.0)),
            "total_primary_net_delta":float(ea["total_net_bps"]-eu["total_net_bps"]),
            "pf_delta":float(ea["profit_factor"]-eu["profit_factor"]),
            "max_drawdown_delta":float(ea["max_drawdown_bps"]-eu["max_drawdown_bps"]),
            "positive_day_delta":int(ea["positive_days"]-eu["positive_days"]),
            "paired_block_bootstrap":_paired_ci(blocks[a],blocks[u]),
        })

    status=(
        "DEV044_T1_ECONOMIC_SURVIVORS_FOUND"
        if survivors else
        "DEV044_T1_NO_ECONOMIC_SURVIVOR"
    )

    staging=out.parent/f".{out.name}.part-{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise T1RunnerError("staging_exists")
    staging.mkdir(parents=True)
    try:
        p_primary=staging/PRIMARY_TRADES_FILENAME
        p_latency=staging/LATENCY_TRADES_FILENAME
        p_blocks=staging/BLOCKS_FILENAME
        _write_trades(p_primary,[(c,primary_by[c]) for c in contract.CANDIDATE_IDS])
        _write_trades(p_latency,[(c,latency_by[c]) for c in contract.CANDIDATE_IDS])
        _write_blocks(p_blocks,blocks)
        payload={
            "experiment_id":EXPERIMENT_ID,
            "design_version":DESIGN_VERSION,
            "execution_commit":execution_commit,
            "status":status,
            "days":list(DAYS),
            "candidate_count":32,
            "core_count":16,
            "execution_shell":{
                "horizon_seconds":1800,
                "barrier_bps":32.0,
                "primary_entry_latency_ms":250,
                "primary_response_latency_ms":250,
                "latency_stress_entry_ms":500,
                "latency_stress_response_ms":500,
                "primary_roundtrip_cost_bps":10.0,
                "stress_roundtrip_cost_bps":16.0,
                "flat_only":True,
            },
            "t0e_parent":{
                "path":str(T0E_MANIFEST),
                "bytes":T0E_MANIFEST_BYTES,
                "sha256":T0E_MANIFEST_SHA256,
            },
            "records":records,
            "maxstat":maxstat,
            "survivors":survivors,
            "survivor_ranking":ranked_ids,
            "promoted_distinct_core_representatives":promoted,
            "paired_a0_analysis":paired,
            "files":{
                "primary_trades":{"file":p_primary.name,"bytes":p_primary.stat().st_size,"sha256":_sha(p_primary)},
                "latency_stress_trades":{"file":p_latency.name,"bytes":p_latency.stat().st_size,"sha256":_sha(p_latency)},
                "primary_4h_blocks":{"file":p_blocks.name,"bytes":p_blocks.stat().st_size,"sha256":_sha(p_blocks)},
            },
            "forward_guards":dict(FORWARD_GUARDS),
            "sep01_plus_remains_sealed":True,
            "other_markets_remain_sealed":True,
        }
        manifest=staging/MANIFEST_FILENAME
        manifest.write_text(
            json.dumps(_safe_json(payload),sort_keys=True,separators=(",",":"),allow_nan=False)+"\n",
            encoding="utf-8",
        )
        os.replace(staging,out)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging,ignore_errors=True)
        raise

    manifest=out/MANIFEST_FILENAME
    return {
        "status":status,
        "artifact_path":str(manifest),
        "artifact_bytes":int(manifest.stat().st_size),
        "artifact_sha256":_sha(manifest),
        "survivors":survivors,
        "promoted":promoted,
    }
