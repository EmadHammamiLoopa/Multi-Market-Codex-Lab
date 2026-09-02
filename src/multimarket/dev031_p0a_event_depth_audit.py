"""DEV031-P0A corrected read-only raw L2 feasibility audit."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
import csv, gzip, hashlib, json, math, os
from pathlib import Path
from typing import Any, Iterable, Mapping

EXPERIMENT_ID="DEV031-P0A"
DESIGN_VERSION="event-depth-raw-l2-feasibility-v2"
DEVELOPMENT_DAYS=tuple(date(2026,m,1) for m in range(1,8))
SYMBOL="BTCUSDT"; EXCHANGE="binance-futures"
EXPECTED_HEADER=("exchange","symbol","timestamp","local_timestamp","is_snapshot","side","price","amount")
DEFAULT_RAW_ROOT=Path("/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw/incremental_book_L2/BTCUSDT")
REAL_OUTPUT_DIRECTORY=Path("/home/emadh/Multi-Market/evidence/dev031_p0a_event_depth_raw_l2_v1")
ARTIFACT_FILENAME="DEV031_P0A_EVENT_DEPTH_RAW_L2_RESULT.json"
GRID_US=250_000
STATUS_PASS="DATA_READY_EVENT_DEPTH_RAW_L2"
STATUS_FAIL="FAIL_EVENT_DEPTH_RAW_L2_INCOMPLETE"
FORWARD_GUARDS={"aug01_opened":False,"aug30_opened":False,"sep01_or_later_opened":False,"railway_opened":False,"archive_bucket_opened":False,"abundant_love_opened":False,"downloads_or_acquisition_run":False}

class P0AAuditError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason); super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class DayAudit:
    day: date; path:str; bytes:int; sha256:str; rows:int; bad_rows:int
    snapshot_rows:int; snapshot_groups:int; rows_before_first_snapshot:int
    local_timestamp_regressions:int; bid_rows:int; ask_rows:int; deletion_rows:int
    distinct_local_timestamp_groups:int; multirow_group_rows:int; max_group_size:int
    nonempty_250ms_buckets:int; multirow_250ms_buckets:int; multigroup_250ms_buckets:int
    max_rows_per_250ms_bucket:int; post_valid_initialization_incremental_rows:int
    valid_book_groups_after_snapshot:int; book_integrity_invalidations:int
    max_bid_levels:int; max_ask_levels:int; max_simultaneous_min_side_depth:int
    first_local_timestamp:int|None; last_local_timestamp:int|None
    first_exchange_timestamp:int|None; last_exchange_timestamp:int|None
    initialized_after_snapshot:bool; path_within_frozen_scope:bool

@dataclass(frozen=True)
class ArtifactWriteResult:
    output_directory:Path; artifact_path:Path; artifact_sha256:str; artifact_bytes:int

def _sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def _day_bounds_us(d:date)->tuple[int,int]:
    s=int(datetime(d.year,d.month,d.day,tzinfo=timezone.utc).timestamp()*1_000_000)
    return s,s+86_400_000_000

def _validate_path(path:Path,root:Path,day:date)->None:
    if day not in DEVELOPMENT_DAYS: raise P0AAuditError("day_outside_frozen_scope")
    exp=root/f"{day.isoformat()}.csv.gz"
    if path!=exp: raise P0AAuditError("raw_path_outside_frozen_scope",f"expected={exp} actual={path}")

def audit_day(path:Path,*,raw_root:Path,day:date)->DayAudit:
    path=Path(path); raw_root=Path(raw_root); _validate_path(path,raw_root,day)
    if not path.is_file(): raise P0AAuditError("raw_file_missing",str(path))
    size=path.stat().st_size
    if size<=0: raise P0AAuditError("raw_file_empty",str(path))
    sha=_sha256_file(path); start,end=_day_bounds_us(day)

    rows=bad=snap_rows=snap_groups=pre_snap=reg=bid_rows=ask_rows=deletions=0
    groups=multirow_group_rows=max_group=0
    nonempty_buckets=multirow_buckets=multigroup_buckets=max_bucket_rows=0
    post_valid_inc=valid_groups=invalidations=0
    max_bid_levels=max_ask_levels=max_min_depth=0
    first_local=last_local=first_ex=last_ex=None
    prev_local=None; seen_snapshot=False

    bids:dict[float,float]={}; asks:dict[float,float]={}; book_ready=False
    group_ts=None; group_updates:list[tuple[bool,str,float,float]]=[]
    bucket_id=None; bucket_rows=0; bucket_groups=0

    def structurally_valid()->bool:
        return bool(bids and asks and max(bids)<min(asks))

    def flush_group()->None:
        nonlocal groups,multirow_group_rows,max_group,snap_groups,book_ready
        nonlocal valid_groups,invalidations,max_bid_levels,max_ask_levels,max_min_depth,post_valid_inc
        if not group_updates: return
        groups+=1; n=len(group_updates); max_group=max(max_group,n)
        if n>1: multirow_group_rows+=n
        has_snapshot=any(x[0] for x in group_updates)
        was_ready=book_ready
        if has_snapshot:
            snap_groups+=1; bids.clear(); asks.clear(); book_ready=False
        non_snapshot_rows=0
        for is_snap,side,price,amount in group_updates:
            if not is_snap: non_snapshot_rows+=1
            book=bids if side=="bid" else asks
            if amount==0.0: book.pop(price,None)
            else: book[price]=amount
        valid=structurally_valid()
        if has_snapshot:
            book_ready=valid
        elif book_ready and not valid:
            book_ready=False; invalidations+=1
        if was_ready and not has_snapshot:
            post_valid_inc+=non_snapshot_rows
        if book_ready:
            valid_groups+=1
            bl=len(bids); al=len(asks)
            max_bid_levels=max(max_bid_levels,bl); max_ask_levels=max(max_ask_levels,al)
            max_min_depth=max(max_min_depth,min(bl,al))

    def flush_bucket()->None:
        nonlocal nonempty_buckets,multirow_buckets,multigroup_buckets,max_bucket_rows
        if bucket_rows<=0:return
        nonempty_buckets+=1; max_bucket_rows=max(max_bucket_rows,bucket_rows)
        if bucket_rows>1: multirow_buckets+=1
        if bucket_groups>1: multigroup_buckets+=1

    with gzip.open(path,"rt",encoding="utf-8",newline="") as fh:
        r=csv.reader(fh)
        try: header=tuple(next(r))
        except StopIteration as exc: raise P0AAuditError("missing_header") from exc
        if header!=EXPECTED_HEADER: raise P0AAuditError("header_mismatch",repr(header))
        pos={n:i for i,n in enumerate(header)}
        for row in r:
            rows+=1
            if len(row)!=8: bad+=1; continue
            try:
                ex=row[pos["exchange"]]; sy=row[pos["symbol"]]; ets=int(row[pos["timestamp"]]); lts=int(row[pos["local_timestamp"]])
                snap_text=row[pos["is_snapshot"]].lower(); side=row[pos["side"]]; price=float(row[pos["price"]]); amount=float(row[pos["amount"]])
            except Exception:
                bad+=1; continue
            row_bad=(ex!=EXCHANGE or sy!=SYMBOL or not(start<=lts<end) or snap_text not in ("true","false") or side not in ("bid","ask") or not math.isfinite(price) or price<=0 or not math.isfinite(amount) or amount<0)
            if prev_local is not None and lts<prev_local: reg+=1; row_bad=True
            if row_bad: bad+=1; prev_local=lts; continue
            is_snap=snap_text=="true"
            if is_snap: snap_rows+=1; seen_snapshot=True
            elif not seen_snapshot: pre_snap+=1
            if side=="bid": bid_rows+=1
            else: ask_rows+=1
            if amount==0.0: deletions+=1
            if first_local is None: first_local=lts; first_ex=ets
            last_local=lts; last_ex=ets

            if group_ts is None:
                group_ts=lts
            elif lts!=group_ts:
                flush_group(); group_updates.clear(); group_ts=lts
            group_updates.append((is_snap,side,price,amount))

            b=(lts-start)//GRID_US
            if bucket_id is None:
                bucket_id=b; bucket_rows=1; bucket_groups=1
            elif b==bucket_id:
                bucket_rows+=1
                if prev_local is not None and lts!=prev_local: bucket_groups+=1
            else:
                flush_bucket(); bucket_id=b; bucket_rows=1; bucket_groups=1
            prev_local=lts
    flush_group(); flush_bucket()
    initialized=valid_groups>0

    return DayAudit(day,str(path),size,sha,rows,bad,snap_rows,snap_groups,pre_snap,reg,bid_rows,ask_rows,deletions,groups,multirow_group_rows,max_group,nonempty_buckets,multirow_buckets,multigroup_buckets,max_bucket_rows,post_valid_inc,valid_groups,invalidations,max_bid_levels,max_ask_levels,max_min_depth,first_local,last_local,first_ex,last_ex,initialized,True)

def day_gates(x:DayAudit)->dict[str,bool]:
    return {
      "file_nonempty":x.bytes>0,"rows_nonzero":x.rows>0,"zero_bad_rows":x.bad_rows==0,
      "zero_local_timestamp_regressions":x.local_timestamp_regressions==0,
      "snapshot_group_present":x.snapshot_groups>0,
      "valid_book_initialized_after_snapshot":x.initialized_after_snapshot,
      "post_valid_initialization_incremental_rows_present":x.post_valid_initialization_incremental_rows>0,
      "deletions_present":x.deletion_rows>0,
      "multirow_250ms_buckets_present":x.multirow_250ms_buckets>0,
      "multigroup_250ms_buckets_present":x.multigroup_250ms_buckets>0,
      "simultaneous_depth_beyond_top10_present":x.max_simultaneous_min_side_depth>=11,
      "within_frozen_scope":x.path_within_frozen_scope,
    }

def _public(x:DayAudit)->dict[str,Any]:
    d=dict(x.__dict__); d["day"]=x.day.isoformat(); d["gates"]=day_gates(x); return d

def canonical_json_bytes(payload:Mapping[str,Any])->bytes:
    return (json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False)+"\n").encode()

def _fsync_dir(path:Path)->None:
    fd=os.open(path,os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)

def write_result_once(output_directory:Path,payload:Mapping[str,Any],*,require_canonical_output:bool=True)->ArtifactWriteResult:
    out=Path(output_directory)
    if out.exists() or out.is_symlink(): raise P0AAuditError("output_directory_already_exists")
    if require_canonical_output and out!=REAL_OUTPUT_DIRECTORY: raise P0AAuditError("noncanonical_output_directory")
    if not require_canonical_output and out==REAL_OUTPUT_DIRECTORY: raise P0AAuditError("canonical_output_requires_real_mode")
    content=canonical_json_bytes(payload); out.mkdir(mode=0o755); _fsync_dir(out.parent)
    final=out/ARTIFACT_FILENAME; part=final.with_name(final.name+".part")
    with part.open("xb") as f: f.write(content); f.flush(); os.fsync(f.fileno())
    os.replace(part,final); _fsync_dir(out)
    return ArtifactWriteResult(out,final,hashlib.sha256(content).hexdigest(),len(content))

def run_p0a(*,raw_root:Path=DEFAULT_RAW_ROOT,output_directory:Path=REAL_OUTPUT_DIRECTORY,require_canonical_output:bool=True)->ArtifactWriteResult:
    root=Path(raw_root); out=Path(output_directory)
    if require_canonical_output and root!=DEFAULT_RAW_ROOT: raise P0AAuditError("canonical_raw_root_override_forbidden")
    if require_canonical_output and out!=REAL_OUTPUT_DIRECTORY: raise P0AAuditError("noncanonical_output_directory")
    if out.exists() or out.is_symlink(): raise P0AAuditError("output_directory_already_exists")
    days=[]; errors=[]
    for d in DEVELOPMENT_DAYS:
        try: days.append(audit_day(root/f"{d.isoformat()}.csv.gz",raw_root=root,day=d))
        except Exception as exc: errors.append({"day":d.isoformat(),"type":type(exc).__name__,"reason":getattr(exc,"reason","exception"),"detail":str(exc)})
    all_gates=(not errors and len(days)==7 and all(all(day_gates(x).values()) for x in days) and not any(FORWARD_GUARDS.values()))
    payload={
      "experiment_id":EXPERIMENT_ID,"design_version":DESIGN_VERSION,
      "status":STATUS_PASS if all_gates else STATUS_FAIL,"pass":bool(all_gates),
      "scope":{"symbol":SYMBOL,"data_type":"incremental_book_L2","development_days":[d.isoformat() for d in DEVELOPMENT_DAYS],"labels_opened":False,"predictive_metrics_run":False,"model_fit_run":False},
      "days":[_public(x) for x in days],"errors":errors,"forward_guards":dict(FORWARD_GUARDS),
      "scientific_interpretation":"raw event-time/depth information exists and is structurally auditable" if all_gates else "raw event-time/depth feasibility gates not fully satisfied"
    }
    return write_result_once(out,payload,require_canonical_output=require_canonical_output)
