from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev032_e1a_feature_core as fc
from . import dev032_e1a_materialize as mat
from . import dev032_e1b_screen_core as core

E1A_ROOT = Path(
    "/home/emadh/Multi-Market/evidence/dev032_e1a_wave1_materialization_v1"
)
E1A_ARTIFACT = E1A_ROOT / "DEV032_E1A_WAVE1_MATERIALIZATION.json"
E1A_SHA256 = "76e1c97e8b9a899bc27f3193316cbfc85efba8b0a7aa037d4c46fcc6a8be4a50"
E1A_BYTES = 44689

P1B_ARTIFACT = Path(
    "/home/emadh/Multi-Market/evidence/dev031_p1b_event_depth_incremental_v1/"
    "DEV031_P1B_EVENT_DEPTH_INCREMENTAL_RESULT.json"
)
P1B_SHA256 = "4e55554151b8caba588ea2ffdf7c6b1454a5eabe74f833a44f3784a980ddb56b"
P1B_BYTES = 14796

PRIMARY_IDS = tuple(["P02"] + [f"P{i:02d}" for i in range(3,36)])
STANDALONE_IDS = tuple(["S01"] + [f"S{i:02d}" for i in range(3,36)])

FAMILY_BY_PRIMARY = {
    "P02":"legacy_event_depth",
    "P03":"aggregated_snapshot_control",
    **{f"P{i:02d}":"queue_depth_imbalance" for i in range(4,8)},
    **{f"P{i:02d}":"microprice_fair_value" for i in range(8,11)},
    **{f"P{i:02d}":"multilevel_stationary_order_flow" for i in range(11,16)},
    **{f"P{i:02d}":"book_geometry" for i in range(16,21)},
    **{f"P{i:02d}":"event_pressure_transition" for i in range(21,25)},
    **{f"P{i:02d}":"event_timing_activity" for i in range(25,29)},
    **{f"P{i:02d}":"hawkes_excitation_inspired" for i in range(29,32)},
    **{f"P{i:02d}":"resilience_recovery" for i in range(32,34)},
    **{f"P{i:02d}":"temporal_shape" for i in range(34,36)},
}

class E1BLoaderError(RuntimeError):
    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class LoadedEvidence:
    e1a_manifest: dict[str,Any]
    p1b_manifest: dict[str,Any]
    strategy_days: dict[str, dict[date, core.DayMatrix]]

def _sha(path: Path) -> str:
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def _load_json_identity(path: Path, sha: str, size: int) -> dict[str,Any]:
    if not path.is_file():
        raise E1BLoaderError("artifact_missing", str(path))
    if path.stat().st_size != size:
        raise E1BLoaderError("artifact_bytes_mismatch", str(path))
    if _sha(path) != sha:
        raise E1BLoaderError("artifact_sha256_mismatch", str(path))
    payload=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload,dict):
        raise E1BLoaderError("artifact_not_object", str(path))
    return payload

def _expected_full_header() -> list[str]:
    header=["local_timestamp_us","t1_label"]
    for sid in mat.ALL_IDS:
        header.extend(mat.expected_feature_names(sid))
    return header

def _strategy_offsets() -> dict[str,tuple[int,int]]:
    pos=2
    out={}
    for sid in mat.ALL_IDS:
        n=fc.strategy_feature_counts()[sid]
        out[sid]=(pos,pos+n)
        pos+=n
    return out

def load_evidence() -> LoadedEvidence:
    e1a=_load_json_identity(E1A_ARTIFACT,E1A_SHA256,E1A_BYTES)
    p1b=_load_json_identity(P1B_ARTIFACT,P1B_SHA256,P1B_BYTES)

    if e1a.get("experiment_id")!="DEV032-E1A":
        raise E1BLoaderError("e1a_experiment_id")
    if e1a.get("status")!="DEV032_WAVE1_EXACT_SUPPORT_MATERIALIZED":
        raise E1BLoaderError("e1a_status")
    if e1a.get("pass") is not True:
        raise E1BLoaderError("e1a_not_pass")
    if (e1a.get("rows"),e1a.get("long"),e1a.get("short"))!=(1374,684,690):
        raise E1BLoaderError("e1a_support_counts")
    if e1a.get("p3_support_contract_reproduced_exactly") is not True:
        raise E1BLoaderError("e1a_p3_support_contract")
    if any(e1a.get("forward_guards",{}).values()):
        raise E1BLoaderError("e1a_forward_guard")

    if p1b.get("experiment_id")!="DEV031-P1B":
        raise E1BLoaderError("p1b_experiment_id")
    if p1b.get("status")!="FAIL_EVENT_DEPTH_NO_STABLE_INCREMENTAL_DIRECTION_VALUE":
        raise E1BLoaderError("p1b_terminal_status")
    if any(p1b.get("forward_guards",{}).values()):
        raise E1BLoaderError("p1b_forward_guard")

    days=e1a.get("days")
    if not isinstance(days,list) or len(days)!=7:
        raise E1BLoaderError("e1a_days")
    if [date.fromisoformat(x["day"]) for x in days] != list(dd.HISTORICAL_DAYS):
        raise E1BLoaderError("e1a_calendar")

    offsets=_strategy_offsets()
    expected_header=_expected_full_header()
    strategy_days={sid:{} for sid in mat.ALL_IDS}
    campaign_ts=[]
    campaign_y=[]
    campaign_values={sid:[] for sid in mat.ALL_IDS}

    for rec in days:
        d=date.fromisoformat(rec["day"])
        path=E1A_ROOT/rec["file"]
        if not path.is_file():
            raise E1BLoaderError("day_file_missing",d.isoformat())
        if path.stat().st_size!=rec["file_bytes"] or _sha(path)!=rec["file_sha256"]:
            raise E1BLoaderError("day_file_identity",d.isoformat())
        with path.open("r",encoding="utf-8",newline="") as f:
            reader=csv.reader(f)
            try:
                header=next(reader)
            except StopIteration as exc:
                raise E1BLoaderError("day_file_empty",d.isoformat()) from exc
            rows=list(reader)
        if header!=expected_header:
            raise E1BLoaderError("day_header",d.isoformat())
        if len(rows)!=rec["rows"]:
            raise E1BLoaderError("day_rows",d.isoformat())

        ts=np.asarray([int(r[0]) for r in rows],dtype=np.int64)
        y=np.asarray([int(r[1]) for r in rows],dtype=np.int8)
        if mat.support_sha256(ts)!=rec["support_sha256"]:
            raise E1BLoaderError("day_support_hash",d.isoformat())
        if mat.label_sha256(ts,y)!=rec["label_sha256"]:
            raise E1BLoaderError("day_label_hash",d.isoformat())

        for sid,(a,b) in offsets.items():
            x=np.asarray([[float(v) for v in row[a:b]] for row in rows],dtype=np.float64)
            mat.validate_matrix(sid,x,rows=len(ts))
            if mat.matrix_sha256(sid,x)!=rec["strategy_matrix_sha256"][sid]:
                raise E1BLoaderError("day_matrix_hash",f"{d.isoformat()}:{sid}")
            strategy_days[sid][d]=core.DayMatrix(d,ts,y,x)
            campaign_values[sid].append(x)
        campaign_ts.append(ts)
        campaign_y.append(y)

    ts_all=np.concatenate(campaign_ts)
    y_all=np.concatenate(campaign_y)
    if mat.support_sha256(ts_all)!=e1a["support_sha256"]:
        raise E1BLoaderError("campaign_support_hash")
    if mat.label_sha256(ts_all,y_all)!=e1a["label_sha256"]:
        raise E1BLoaderError("campaign_label_hash")

    by_sid={x["strategy_id"]:x for x in e1a["strategies"]}
    if tuple(by_sid)!=mat.ALL_IDS:
        raise E1BLoaderError("strategy_order")
    for sid in mat.ALL_IDS:
        x=np.concatenate(campaign_values[sid],axis=0)
        if mat.matrix_sha256(sid,x)!=by_sid[sid]["matrix_sha256"]:
            raise E1BLoaderError("campaign_matrix_hash",sid)

    # Frozen semantic invariant: S02 is exactly S00 then S01.
    for d in dd.HISTORICAL_DAYS:
        x0=strategy_days["S00"][d].values
        x1=strategy_days["S01"][d].values
        x2=strategy_days["S02"][d].values
        if not np.array_equal(x2,np.concatenate([x0,x1],axis=1)):
            raise E1BLoaderError("s02_not_exact_s00_s01_concat",d.isoformat())

    return LoadedEvidence(e1a,p1b,strategy_days)

def outer_folds() -> tuple[core.FoldSpec,...]:
    return tuple(
        core.FoldSpec(int(f.fold_id),tuple(f.train_days),f.validation_day)
        for f in dd.OUTER_FOLDS
    )

def baseline_days(evidence: LoadedEvidence) -> dict[date,core.DayMatrix]:
    return evidence.strategy_days["S00"]

def primary_candidate_days(
    evidence: LoadedEvidence,
    candidate_id: str,
) -> dict[date,core.DayMatrix]:
    if candidate_id not in PRIMARY_IDS:
        raise E1BLoaderError("unknown_primary_candidate",candidate_id)
    if candidate_id=="P02":
        return evidence.strategy_days["S02"]
    sid="S"+candidate_id[1:]
    out={}
    for d in dd.HISTORICAL_DAYS:
        base=evidence.strategy_days["S00"][d]
        extra=evidence.strategy_days[sid][d]
        if not np.array_equal(base.timestamps_us,extra.timestamps_us):
            raise E1BLoaderError("candidate_support_mismatch",candidate_id)
        if not np.array_equal(base.labels,extra.labels):
            raise E1BLoaderError("candidate_label_mismatch",candidate_id)
        out[d]=core.DayMatrix(
            d,
            base.timestamps_us,
            base.labels,
            np.concatenate([base.values,extra.values],axis=1),
        )
    return out

def standalone_days(
    evidence: LoadedEvidence,
    strategy_id: str,
) -> dict[date,core.DayMatrix]:
    if strategy_id not in STANDALONE_IDS:
        raise E1BLoaderError("unknown_standalone_strategy",strategy_id)
    return evidence.strategy_days[strategy_id]
