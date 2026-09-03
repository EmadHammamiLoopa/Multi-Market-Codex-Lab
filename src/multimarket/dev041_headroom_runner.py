from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import shutil

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev030_first_passage as fp
from . import dev041_headroom_core as core

EXPERIMENT_ID="DEV041-P2"
DESIGN_VERSION="model-free-executable-headroom-screen-v1"

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev041_p2_model_free_headroom_v1"
)
ARTIFACT_FILENAME="DEV041_P2_MODEL_FREE_HEADROOM_RESULT.json"

FORWARD_GUARDS={
    "sep01_plus_opened":False,
    "other_market_opened":False,
    "predictive_model_fit":False,
    "feature_search_run":False,
    "stop_grid_run":False,
    "passive_rescue_run":False,
    "cost_grid_changed":False,
    "candidate_grid_changed":False,
}

class RunnerError(RuntimeError):
    pass

def _sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def _sanitize(x):
    if isinstance(x,float) and math.isinf(x):
        return "INF"
    if isinstance(x,dict):
        return {k:_sanitize(v) for k,v in x.items()}
    if isinstance(x,list):
        return [_sanitize(v) for v in x]
    return x

def _load_days():
    rows=tuple(dd.load_authorized_days())
    if tuple(x.day for x in rows)!=dd.HISTORICAL_DAYS:
        raise RunnerError("calendar")
    return rows

def _candidate_records(day,candidate):
    idx=dd.exact_minute_decision_indices(day.ts)
    records=fp.label_first_passage_targets(
        day,
        idx,
        horizon_seconds=candidate.horizon_seconds,
        barrier_bps=candidate.barrier_bps,
        latency_ms=fp.LATENCY_MS,
    )
    return idx,records

def _evaluate_candidate(candidate,days):
    day_records=[]
    all_oracle=[]
    aggregate_support={
        "valid_decisions":0,
        "invalid_decisions":0,
        "long_first_count":0,
        "short_first_count":0,
        "none_count":0,
        "ambiguity_count":0,
        "clean_touch_count":0,
    }
    pooled_times=[]
    pooled_long_times=[]
    pooled_short_times=[]

    for day in days:
        idx,records=_candidate_records(day,candidate)
        summary=core.records_summary(records)
        raw_trades,response_unavailable=core.oracle_trades_from_records(
            day.day.isoformat(),
            records,
            raw_timestamps_us=day.ts,
            bid=day.bid,
            ask=day.ask,
            book_valid=day.book_valid,
            response_latency_ms=250,
        )
        accepted,ignored=core.flat_only(raw_trades)
        all_oracle.extend(accepted)

        for key in aggregate_support:
            aggregate_support[key]+=int(summary[key])
        for r in records:
            if r.get("target_valid") is True and r.get("label") in (fp.LONG_FIRST,fp.SHORT_FIRST):
                t=float(r["time_to_first_barrier_ms"])
                pooled_times.append(t)
                if r["label"]==fp.LONG_FIRST:
                    pooled_long_times.append(t)
                else:
                    pooled_short_times.append(t)

        day_records.append({
            "day":day.day.isoformat(),
            "decision_count":int(len(idx)),
            "support":summary,
            "raw_clean_touches":int(summary["clean_touch_count"]),
            "response_exit_unavailable":int(response_unavailable),
            "raw_realizable_opportunities":int(len(raw_trades)),
            "accepted_flat_only_oracle_trades":int(len(accepted)),
            "ignored_overlap_opportunities":int(ignored),
            "long_oracle_trades":int(sum(t.side=="LONG" for t in accepted)),
            "short_oracle_trades":int(sum(t.side=="SHORT" for t in accepted)),
        })

    valid=aggregate_support["valid_decisions"]
    aggregate_support["clean_touch_prevalence"]=(
        float(aggregate_support["clean_touch_count"]/valid) if valid else None
    )
    def timing(v):
        if not v:
            return {"median_ms":None,"p90_ms":None}
        a=np.asarray(v,dtype=np.float64)
        return {
            "median_ms":float(np.median(a)),
            "p90_ms":float(np.quantile(a,0.90,method="higher")),
        }
    aggregate_support["time_to_first_passage"]=timing(pooled_times)
    aggregate_support["long_time_to_first_passage"]=timing(pooled_long_times)
    aggregate_support["short_time_to_first_passage"]=timing(pooled_short_times)

    accepted=tuple(sorted(all_oracle,key=lambda t:(t.day,t.decision_timestamp_us)))
    activity={
        "raw_clean_touches":int(sum(r["raw_clean_touches"] for r in day_records)),
        "response_exit_unavailable":int(sum(r["response_exit_unavailable"] for r in day_records)),
        "raw_realizable_opportunities":int(sum(r["raw_realizable_opportunities"] for r in day_records)),
        "realizable_opportunity_fraction":float(
            sum(r["raw_realizable_opportunities"] for r in day_records)
            / max(1,sum(r["raw_clean_touches"] for r in day_records))
        ),
        "accepted_oracle_trades":int(len(accepted)),
        "ignored_overlap_opportunities":int(sum(r["ignored_overlap_opportunities"] for r in day_records)),
        "oracle_trades_per_day":float(len(accepted)/7.0),
        "long_oracle_trades":int(sum(t.side=="LONG" for t in accepted)),
        "short_oracle_trades":int(sum(t.side=="SHORT" for t in accepted)),
    }

    execution=core.execution_decomposition(accepted)
    gross=core.economics(accepted,0.0)
    c1=core.economics(accepted,core.C1_COST_BPS)
    c2=core.economics(accepted,core.C2_COST_BPS)

    rec={
        "candidate_id":candidate.candidate_id,
        "horizon_seconds":int(candidate.horizon_seconds),
        "barrier_bps":int(candidate.barrier_bps),
        "support":aggregate_support,
        "activity":activity,
        "response_latency_ms":250,
        "execution_decomposition":execution,
        "gross":gross,
        "c1":c1,
        "c2":c2,
        "per_day":day_records,
    }
    eligible,gates=core.eligibility(rec)
    rec["eligibility_gates"]=gates
    rec["eligible"]=bool(eligible)
    return rec

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

    days=_load_days()
    if len(core.CANDIDATES)!=30:
        raise RunnerError("candidate_count")

    records=[_evaluate_candidate(c,days) for c in core.CANDIDATES]
    ranked=core.rank(records)
    advanced=[ranked[0]["candidate_id"]] if ranked else []
    status=(
        f"DEV041_HEADROOM_SURVIVOR_{advanced[0]}"
        if advanced else
        "DEV041_NO_EXECUTABLE_HEADROOM_SURVIVOR"
    )

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":"model-free-executable-headroom-screen-v2-response-latency",
        "execution_commit":execution_commit,
        "status":status,
        "candidate_count":30,
        "candidate_registry":core.registry(),
        "cost_envelopes_bps":{
            "C0_GROSS":0.0,
            "C1_PRIMARY":core.C1_COST_BPS,
            "C2_SEVERE":core.C2_COST_BPS,
        },
        "days":[d.day.isoformat() for d in days],
        "leaderboard":records,
        "eligible_candidates":[r["candidate_id"] for r in records if r["eligible"]],
        "survivor_ranking":[r["candidate_id"] for r in ranked],
        "advanced_candidate":advanced,
        "forward_guards":dict(FORWARD_GUARDS),
        "response_latency_ms":250,
        "oracle_warning":(
            "future first-passage direction is used only as a model-free headroom ceiling; "
            "eligibility uses realized executable return at touch+250ms, not touch return; "
            "this artifact is not a trading strategy or profitability validation"
        ),
        "sep01_plus_remains_sealed":True,
        "other_markets_remain_sealed":True,
    }

    content=(json.dumps(_sanitize(payload),sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
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
        "advanced_candidate":advanced,
    }
