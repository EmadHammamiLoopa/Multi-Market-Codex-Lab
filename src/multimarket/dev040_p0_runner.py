from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev036_c1_loader as c1loader
from . import dev037_p0_r1_coverage_core as coverage
from . import dev037_p0_r1_coverage_runner as r1runner
from . import dev040_p0_core as core

EXPERIMENT_ID="DEV040-P0"
DESIGN_VERSION="economic-support-executable-price-audit-v1"

PARENT_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev038a_p2_final_controller_correctness_v1/"
    "DEV038A_P2_FINAL_CONTROLLER_CORRECTNESS_RESULT.json"
)
PARENT_SHA="df32874a362cd75f646cdca483dc46956797431ac9a5861435639dfbf7f4b311"
PARENT_BYTES=191547

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev040_p0_economic_support_audit_v1"
)
ARTIFACT_FILENAME="DEV040_P0_ECONOMIC_SUPPORT_AUDIT_RESULT.json"

FORWARD_GUARDS={
    "sep01_plus_opened":False,
    "other_market_opened":False,
    "gross_pnl_calculated":False,
    "net_pnl_calculated":False,
    "profit_factor_calculated":False,
    "drawdown_calculated":False,
    "win_rate_calculated":False,
    "cost_break_even_calculated":False,
    "fees_applied":False,
    "slippage_applied":False,
    "predictive_tuning_run":False,
}

class RunnerError(RuntimeError):
    pass

def _sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _action_hash(fid:int,actions):
    h=hashlib.sha256(f"DEV038-A-P2-ACTION-C2-F{fid}".encode()+b"\0")
    h.update(np.asarray(actions,dtype=np.int8).tobytes())
    return h.hexdigest()

def _load_parent():
    if not PARENT_ARTIFACT.is_file():
        raise RunnerError("parent_missing")
    if _sha(PARENT_ARTIFACT)!=PARENT_SHA or PARENT_ARTIFACT.stat().st_size!=PARENT_BYTES:
        raise RunnerError("parent_identity")
    x=json.loads(PARENT_ARTIFACT.read_text(encoding="utf-8"))
    if x.get("status")!="DEV038A_P2_CONTROLLER_SURVIVOR_FOUND":
        raise RunnerError("parent_status")
    if x.get("advanced_controller")!=["C2"]:
        raise RunnerError("parent_advanced_controller")
    if x.get("window_by_id",{}).get("C2")!=720:
        raise RunnerError("parent_c2_window")
    return x

def _raw_day_map():
    rows=tuple(dd.load_authorized_days())
    if tuple(x.day for x in rows)!=dd.HISTORICAL_DAYS:
        raise RunnerError("raw_calendar")
    return {x.day:x for x in rows}

def _fold_action_streams(e,parent):
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
        if len(actions)!=len(ts):
            raise RunnerError(f"action_timestamp_length_F{outer.fold_id}")
        observed=_action_hash(outer.fold_id,actions)
        expected=(
            parent["controller_records"]["C2"]["folds"][outer.fold_id-1]["action_sha256"]
        )
        if observed!=expected:
            raise RunnerError(f"c2_action_hash_F{outer.fold_id}")
        total+=int(np.sum(actions!=0))
        out.append({
            "fold_id":int(outer.fold_id),
            "day":outer.validation_day,
            "decision_timestamps_us":ts,
            "actions":actions,
            "action_sha256":observed,
            "raw_action_count":int(np.sum(actions!=0)),
        })
    if total!=1104:
        raise RunnerError(f"pooled_c2_action_count:{total}")
    return tuple(out)

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

    parent=_load_parent()
    e=c1loader.load_c1()
    raw=_raw_day_map()
    folds=_fold_action_streams(e,parent)

    per_fold=[]
    pooled={str(lat):{
        "raw_actions":0,
        "accepted_flat_only_trades":0,
        "ignored_overlap_actions":0,
        "long_trades":0,
        "short_trades":0,
    } for lat in core.LATENCIES_MS}

    for f in folds:
        day=f["day"]
        d=raw[day]
        rec={
            "fold_id":f["fold_id"],
            "day":day.isoformat(),
            "action_sha256":f["action_sha256"],
            "raw_action_count":f["raw_action_count"],
            "latencies":{},
        }

        for lat in core.LATENCIES_MS:
            trades,ignored=core.flat_only_audit(
                decision_timestamps_us=f["decision_timestamps_us"],
                actions=f["actions"],
                raw_timestamps_us=d.ts,
                bid=d.bid,
                ask=d.ask,
                book_valid=d.book_valid,
                latency_ms=lat,
            )
            summary=core.public_summary(
                trades,
                ignored,
                f["raw_action_count"],
            )
            rec["latencies"][str(lat)]=summary

            p=pooled[str(lat)]
            p["raw_actions"]+=int(summary["raw_action_count"])
            p["accepted_flat_only_trades"]+=int(summary["accepted_flat_only_trades"])
            p["ignored_overlap_actions"]+=int(summary["ignored_overlap_actions"])
            p["long_trades"]+=int(summary["long_trades"])
            p["short_trades"]+=int(summary["short_trades"])

        per_fold.append(rec)

    p250=pooled["250"]
    pass_checks={
        "parent_identity":True,
        "c2_actions_exact":True,
        "pooled_raw_actions_1104":p250["raw_actions"]==1104,
        "accepted_primary_trades_ge_100":p250["accepted_flat_only_trades"]>=100,
        "primary_long_trades_positive":p250["long_trades"]>0,
        "primary_short_trades_positive":p250["short_trades"]>0,
        "all_four_days_have_primary_trades":all(
            int(r["latencies"]["250"]["accepted_flat_only_trades"])>0
            for r in per_fold
        ),
        "all_latency_audits_nonempty":all(
            pooled[str(lat)]["accepted_flat_only_trades"]>0
            for lat in core.LATENCIES_MS
        ),
        "all_forward_guards_false":not any(FORWARD_GUARDS.values()),
    }

    status=(
        "DEV040_P0_ECONOMIC_SUPPORT_AUDIT_PASS"
        if all(pass_checks.values())
        else "DEV040_P0_ECONOMIC_SUPPORT_AUDIT_FAIL"
    )

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "status":status,
        "parent_dev038a_p2":{
            "path":str(PARENT_ARTIFACT),
            "sha256":PARENT_SHA,
            "bytes":PARENT_BYTES,
            "advanced_controller":"C2",
            "window":720,
        },
        "economic_days":[x.validation_day.isoformat() for x in dd.OUTER_FOLDS],
        "latencies_ms":list(core.LATENCIES_MS),
        "holding_seconds":core.HOLD_SECONDS,
        "primary_execution":{
            "entry_latency_ms":250,
            "exit_response_latency_ms":250,
            "entry_long":"ask",
            "entry_short":"bid",
            "exit_long":"bid",
            "exit_short":"ask",
            "overlap_rule":"FLAT_ONLY",
        },
        "folds":per_fold,
        "pooled":pooled,
        "pass_checks":pass_checks,
        "forward_guards":dict(FORWARD_GUARDS),
        "explicit_no_result_guarantee":{
            "gross_pnl":False,
            "net_pnl":False,
            "profit_factor":False,
            "drawdown":False,
            "win_rate":False,
            "cost_break_even":False,
            "fees":False,
            "slippage":False,
            "sep01_plus_access":False,
            "other_market_access":False,
        },
    }

    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    staging=out.parent/f".{out.name}.part-{os.getpid()}"
    if staging.exists():
        raise RunnerError("staging_exists")
    staging.mkdir(parents=True)
    try:
        final=staging/ARTIFACT_FILENAME
        with final.open("xb") as h:
            h.write(content)
            h.flush()
            os.fsync(h.fileno())
        os.replace(staging,out)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging,ignore_errors=True)
        raise

    final=out/ARTIFACT_FILENAME
    return {
        "artifact_path":str(final),
        "artifact_sha256":_sha(final),
        "artifact_bytes":int(final.stat().st_size),
        "status":status,
        "primary_accepted_trades":int(p250["accepted_flat_only_trades"]),
    }
