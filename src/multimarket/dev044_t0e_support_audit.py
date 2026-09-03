from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import csv
import hashlib
import json
import math
import os
import shutil

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev044_t0_strategy_contract as contract
from . import dev044_t0a_a0_oof as a0
from . import dev044_t0b_raw_adapter as raw_adapter
from . import dev044_t0b_state_materializer as sm
from . import dev044_t0c_flow_toxicity as tox
from . import dev044_t0d_vpin_calibration as t0d

EXPERIMENT_ID="DEV044-T0E"
DESIGN_VERSION="apr-jul-action-support-audit-v1"
STATUS_PASS="DEV044_T0E_ACTION_SUPPORT_AUDIT_PASS"

VPIN_BUCKET_VOLUME=45.56983
T0D_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev044_t0d_vpin_calibration_v1/"
    "DEV044_T0D_VPIN_CALIBRATION_RESULT.json"
)
T0D_ARTIFACT_BYTES=1314
T0D_ARTIFACT_SHA256="c0cf0362f2f4a0559ff28c95e72824f5a8e5fa34a20394c33fe71f263f88143c"

TRADE250_ROOT=Path("/home/emadh/Multi-Market/evidence/v23/phase0dl_trade250/BTCUSDT")
REAL_OUTPUT_DIRECTORY=Path("/home/emadh/Multi-Market/evidence/dev044_t0e_support_audit_v1")
MANIFEST_FILENAME="DEV044_T0E_SUPPORT_AUDIT_RESULT.json"

APR_JUL=(date(2026,4,1),date(2026,5,1),date(2026,6,1),date(2026,7,1))
GRID_US=250_000
STATE_HISTORY_STEPS=128

REQUIRED_SOURCE_FIELDS=(
    "microprice_minus_mid_bps",
    "obi_l1",
    "obi_l5",
    "spread_bps",
    "trade_qty_imbalance_1s",
    "mlofi_l10_250ms",
)

class T0EAuditError(RuntimeError):
    pass

@dataclass(frozen=True)
class TradeDay:
    timestamps_us:np.ndarray
    buy_qty:np.ndarray
    sell_qty:np.ndarray


def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()


def verify_t0d_parent()->dict:
    p=T0D_ARTIFACT
    if not p.is_file():
        raise T0EAuditError("t0d_missing")
    if p.stat().st_size!=T0D_ARTIFACT_BYTES:
        raise T0EAuditError("t0d_bytes")
    if _sha(p)!=T0D_ARTIFACT_SHA256:
        raise T0EAuditError("t0d_sha")
    x=json.loads(p.read_text(encoding="utf-8"))
    if x.get("status")!=t0d.STATUS_PASS:
        raise T0EAuditError("t0d_status")
    if not math.isclose(float(x.get("vpin_bucket_volume")),VPIN_BUCKET_VOLUME,rel_tol=0.0,abs_tol=1e-12):
        raise T0EAuditError("t0d_bucket")
    if x.get("pnl_run") is not False or x.get("labels_opened") is not False:
        raise T0EAuditError("t0d_guard")
    return x


def _load_trade250(day:date)->TradeDay:
    p=TRADE250_ROOT/f"{day.isoformat()}_TRADE250.csv"
    if not p.is_file():
        raise T0EAuditError(f"trade250_missing:{day}")
    with p.open("r",encoding="utf-8",newline="") as h:
        r=csv.DictReader(h)
        expected=(
            "local_timestamp_us","buy_qty_250ms","sell_qty_250ms",
            "unknown_qty_250ms","buy_count_250ms","sell_count_250ms",
            "unknown_count_250ms",
        )
        if tuple(r.fieldnames or ())!=expected:
            raise T0EAuditError(f"trade250_header:{day}")
        ts=[];buy=[];sell=[]
        for row in r:
            if float(row["unknown_qty_250ms"])!=0.0 or float(row["unknown_count_250ms"])!=0.0:
                raise T0EAuditError(f"trade250_unknown:{day}")
            ts.append(int(row["local_timestamp_us"]))
            buy.append(float(row["buy_qty_250ms"]))
            sell.append(float(row["sell_qty_250ms"]))
    t=np.asarray(ts,dtype=np.int64)
    b=np.asarray(buy,dtype=np.float64)
    s=np.asarray(sell,dtype=np.float64)
    if len(t)!=345600 or np.any(np.diff(t)!=GRID_US):
        raise T0EAuditError(f"trade250_grid:{day}")
    if np.any(~np.isfinite(b)) or np.any(~np.isfinite(s)) or np.any(b<0) or np.any(s<0):
        raise T0EAuditError(f"trade250_values:{day}")
    return TradeDay(t,b,s)


def _source_map(day)->dict[str,np.ndarray]:
    full=np.asarray(day.X["L2"],dtype=np.float64)
    if full.ndim!=2 or full.shape[1]!=len(dd.SOURCE_FEATURE_ORDER):
        raise T0EAuditError("source_matrix")
    pos={name:i for i,name in enumerate(dd.SOURCE_FEATURE_ORDER)}
    missing=[x for x in REQUIRED_SOURCE_FIELDS if x not in pos]
    if missing:
        raise T0EAuditError("required_source_missing:"+",".join(missing))
    return {name:full[:,pos[name]] for name in REQUIRED_SOURCE_FIELDS}


def _slice_state_inputs(day,source:dict[str,np.ndarray],decision_ts:int):
    ts=np.asarray(day.ts,dtype=np.int64)
    i=int(np.searchsorted(ts,int(decision_ts),side="left"))
    if i>=len(ts) or int(ts[i])!=int(decision_ts):
        raise T0EAuditError("decision_timestamp_missing")
    start=i-STATE_HISTORY_STEPS
    if start<0:
        raise T0EAuditError("state_history")
    sl=slice(start,i+1)
    t=ts[sl]
    if len(t)!=129 or np.any(np.diff(t)!=GRID_US):
        raise T0EAuditError("state_history_grid")
    mid=np.asarray(day.mid,dtype=np.float64)[sl]
    src={k:np.asarray(v,dtype=np.float64)[sl] for k,v in source.items()}
    for k,v in src.items():
        if np.any(~np.isfinite(v)):
            raise T0EAuditError(f"state_source_nonfinite:{k}:{decision_ts}")
    if np.any(~np.isfinite(mid)) or np.any(mid<=0):
        raise T0EAuditError(f"state_mid:{decision_ts}")
    return t,mid,src


def _toxicity_map(trade:TradeDay)->dict[int,float|None]:
    v=tox.vpin_series(
        trade.timestamps_us,
        trade.buy_qty,
        trade.sell_qty,
        bucket_volume=VPIN_BUCKET_VOLUME,
        rolling_buckets=50,
    )
    return {int(t):tox.toxicity_at(v,i) for i,t in enumerate(v.timestamps_us.tolist())}


def _actions_for_state(state:contract.StrategyState,p_touch:float,*,toxicity_available:bool)->tuple[list[int],list[int]]:
    core=[]
    cand=[]
    for cid in contract.CORE_IDS:
        if cid=="T16" and not toxicity_available:
            a=contract.ABSTAIN
        else:
            a=contract.core_action(cid,state)
        core.append(int(a))
        for suffix in ("U","A"):
            candidate=f"{cid}{suffix}"
            if cid=="T16" and not toxicity_available:
                ca=contract.ABSTAIN
            elif suffix=="U":
                ca=a
            else:
                ca=a if float(p_touch)>=contract.A0_GATE_THRESHOLD else contract.ABSTAIN
            cand.append(int(ca))
    return core,cand


def _summary_counts(core_matrix:np.ndarray,cand_matrix:np.ndarray,p:np.ndarray,tox_avail:np.ndarray)->dict:
    out={
        "rows":int(len(p)),
        "a0_gate_pass_rows":int(np.sum(p>=contract.A0_GATE_THRESHOLD)),
        "a0_gate_fail_rows":int(np.sum(p<contract.A0_GATE_THRESHOLD)),
        "toxicity_available_rows":int(np.sum(tox_avail)),
        "toxicity_unavailable_rows":int(np.sum(~tox_avail)),
        "core":{},
        "candidates":{},
    }
    for j,cid in enumerate(contract.CORE_IDS):
        a=core_matrix[:,j]
        out["core"][cid]={
            "long":int(np.sum(a==contract.LONG)),
            "short":int(np.sum(a==contract.SHORT)),
            "abstain":int(np.sum(a==contract.ABSTAIN)),
            "active":int(np.sum(a!=contract.ABSTAIN)),
        }
    for j,cid in enumerate(contract.CANDIDATE_IDS):
        a=cand_matrix[:,j]
        out["candidates"][cid]={
            "long":int(np.sum(a==contract.LONG)),
            "short":int(np.sum(a==contract.SHORT)),
            "abstain":int(np.sum(a==contract.ABSTAIN)),
            "active":int(np.sum(a!=contract.ABSTAIN)),
        }
    return out


def _write_day_csv(path:Path,ts:np.ndarray,p:np.ndarray,toxicity:np.ndarray,tox_avail:np.ndarray,core:np.ndarray,cand:np.ndarray):
    header=[
        "local_timestamp_us","p_touch","toxicity_available","toxicity",
        *[f"{x}_ACTION" for x in contract.CORE_IDS],
        *[f"{x}_ACTION" for x in contract.CANDIDATE_IDS],
    ]
    with path.open("x",encoding="utf-8",newline="") as h:
        w=csv.writer(h,lineterminator="\n")
        w.writerow(header)
        for i in range(len(ts)):
            tox_val="" if not bool(tox_avail[i]) else format(float(toxicity[i]),".17g")
            w.writerow([
                int(ts[i]),format(float(p[i]),".17g"),int(bool(tox_avail[i])),tox_val,
                *[int(x) for x in core[i].tolist()],
                *[int(x) for x in cand[i].tolist()],
            ])


def run(*,execution_commit:str,output_directory:Path=REAL_OUTPUT_DIRECTORY,require_canonical_output:bool=True)->dict:
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise T0EAuditError("execution_commit")
    out=Path(output_directory)
    if require_canonical_output and out!=REAL_OUTPUT_DIRECTORY:
        raise T0EAuditError("noncanonical_output")
    if out.exists() or out.is_symlink():
        raise T0EAuditError("output_exists")

    verify_t0d_parent()
    contract.validate_registry()

    folds=a0.replay_all()
    fold_by_day={date.fromisoformat(f.validation_day):f for f in folds}
    if tuple(sorted(fold_by_day))!=APR_JUL:
        raise T0EAuditError("a0_calendar")

    days={d.day:d for d in dd.load_authorized_days() if d.day in APR_JUL}
    if tuple(sorted(days))!=APR_JUL:
        raise T0EAuditError("feature_calendar")

    staging=out.parent/f".{out.name}.part-{os.getpid()}"
    if staging.exists():
        raise T0EAuditError("staging_exists")
    staging.mkdir(parents=True)

    day_records=[]
    pooled_core=[]
    pooled_cand=[]
    pooled_p=[]
    pooled_tox_avail=[]

    try:
        for day in APR_JUL:
            f=fold_by_day[day]
            support=np.asarray(f.timestamps_us,dtype=np.int64)
            p_touch=np.asarray(f.p_touch,dtype=np.float64)
            if len(support)!=len(p_touch):
                raise T0EAuditError("a0_shape")

            raw=raw_adapter.materialize_raw_adapter(
                workspace=Path(__file__).resolve().parents[2],
                day=day,
                timestamps_us=support,
            )
            raw_adapter.validate_mapping(raw.values)
            row_map=raw_adapter.raw_row_map(raw)

            d=days[day]
            source=_source_map(d)
            trade=_load_trade250(day)
            tox_map=_toxicity_map(trade)

            core_rows=[]
            cand_rows=[]
            tox_values=[]
            tox_available=[]
            for t,pv in zip(support.tolist(),p_touch.tolist()):
                t=int(t)
                tt,mid,src=_slice_state_inputs(d,source,t)
                tx=tox_map.get(t)
                avail=tx is not None and math.isfinite(float(tx))
                # StrategyState cannot represent missing toxicity. For warm-up
                # rows pass a neutral placeholder that is NEVER used by T16;
                # _actions_for_state enforces frozen unavailable -> ABSTAIN.
                tx_for_state=float(tx) if avail else 0.0
                rr=sm.materialize_state(
                    timestamps_us=tt,
                    mid=mid,
                    source=src,
                    decision_timestamp_us=t,
                    raw=raw.values,
                    raw_row=row_map[t],
                    toxicity=tx_for_state,
                )
                missing=[cid for cid in contract.CORE_IDS if not rr.readiness.get(cid,False)]
                if missing:
                    raise T0EAuditError("strategy_not_ready:"+",".join(missing))
                ca,aa=_actions_for_state(rr.state,float(pv),toxicity_available=bool(avail))
                core_rows.append(ca);cand_rows.append(aa)
                tox_values.append(float(tx) if avail else np.nan)
                tox_available.append(bool(avail))

            core=np.asarray(core_rows,dtype=np.int8)
            cand=np.asarray(cand_rows,dtype=np.int8)
            tox_arr=np.asarray(tox_values,dtype=np.float64)
            tox_av=np.asarray(tox_available,dtype=bool)

            if core.shape!=(len(support),16) or cand.shape!=(len(support),32):
                raise T0EAuditError("action_shape")

            csv_path=staging/f"{day.isoformat()}_DEV044_ACTIONS.csv"
            _write_day_csv(csv_path,support,p_touch,tox_arr,tox_av,core,cand)
            summary=_summary_counts(core,cand,p_touch,tox_av)
            day_records.append({
                "day":day.isoformat(),
                "rows":int(len(support)),
                "a0_support_sha256":dd.support_sha256(support),
                "action_csv":csv_path.name,
                "action_csv_bytes":int(csv_path.stat().st_size),
                "action_csv_sha256":_sha(csv_path),
                "summary":summary,
            })
            pooled_core.append(core);pooled_cand.append(cand);pooled_p.append(p_touch);pooled_tox_avail.append(tox_av)

        pc=np.concatenate(pooled_core,axis=0)
        pa=np.concatenate(pooled_cand,axis=0)
        pp=np.concatenate(pooled_p)
        pt=np.concatenate(pooled_tox_avail)

        pooled=_summary_counts(pc,pa,pp,pt)

        payload={
            "experiment_id":EXPERIMENT_ID,
            "design_version":DESIGN_VERSION,
            "execution_commit":execution_commit,
            "status":STATUS_PASS,
            "symbol":"BTCUSDT",
            "days":[d.isoformat() for d in APR_JUL],
            "candidate_count":32,
            "core_count":16,
            "a0_gate_threshold":0.50,
            "vpin_bucket_volume":VPIN_BUCKET_VOLUME,
            "t16_missing_toxicity_rule":"ABSTAIN",
            "day_records":day_records,
            "pooled_summary":pooled,
            "pnl_run":False,
            "returns_computed":False,
            "trade_outcomes_computed":False,
            "profit_factor_computed":False,
            "drawdown_computed":False,
            "economic_ranking_run":False,
            "sep01_plus_opened":False,
            "other_market_opened":False,
        }
        manifest=staging/MANIFEST_FILENAME
        manifest.write_text(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n",encoding="utf-8")
        os.replace(staging,out)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging,ignore_errors=True)
        raise

    final=out/MANIFEST_FILENAME
    return {
        "status":STATUS_PASS,
        "artifact_path":str(final),
        "artifact_bytes":int(final.stat().st_size),
        "artifact_sha256":_sha(final),
        "rows":int(pooled["rows"]),
        "a0_gate_pass_rows":int(pooled["a0_gate_pass_rows"]),
        "toxicity_unavailable_rows":int(pooled["toxicity_unavailable_rows"]),
    }
