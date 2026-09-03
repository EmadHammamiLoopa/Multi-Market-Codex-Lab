from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import subprocess
import tempfile
from typing import Mapping

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev031_p1a_event_depth_materialize as p1a
from . import dev032_e1a_materialize as e1mat
from . import dev032_e1a_runner as e1run
from . import dev044_t0b_state_materializer as sm

RAW_IDS_NEEDED=("S05","S06","S21","S30","S31","S32")

class RawAdapterError(RuntimeError):
    pass

@dataclass(frozen=True)
class RawAdapterResult:
    day:date
    timestamps_us:np.ndarray
    values:dict[str,np.ndarray]
    extractor_stderr:str


def _write_support(path:Path,timestamps_us)->None:
    ts=np.asarray(timestamps_us,dtype=np.int64)
    if ts.ndim!=1 or len(ts)==0 or np.any(np.diff(ts)<=0):
        raise RawAdapterError("support_order")
    with path.open("w",encoding="utf-8",newline="") as h:
        h.write("local_timestamp_us\n")
        for t in ts.tolist():
            h.write(f"{int(t)}\n")


def materialize_raw_adapter(
    *,
    workspace:Path,
    day:date,
    timestamps_us,
    temp_directory:Path|None=None,
)->RawAdapterResult:
    if day not in dd.HISTORICAL_DAYS:
        raise RawAdapterError(f"unauthorized_day:{day}")
    ts=np.asarray(timestamps_us,dtype=np.int64)
    if ts.ndim!=1 or len(ts)==0 or np.any(np.diff(ts)<=0):
        raise RawAdapterError("support")

    raw=p1a.RAW_ROOT/f"{day.isoformat()}.csv.gz"
    if not raw.is_file():
        raise RawAdapterError(f"raw_missing:{raw}")

    own_tmp=temp_directory is None
    td_ctx=tempfile.TemporaryDirectory(prefix="dev044_t0b_") if own_tmp else None
    td=Path(td_ctx.name if td_ctx is not None else temp_directory)
    td.mkdir(parents=True,exist_ok=True)
    try:
        # Build outside the Git worktree so canonical materialization never
        # creates untracked .build/ residue. Scientific extractor source and
        # compiler flags remain exactly those of DEV032.
        exe=e1run._compile_tool(Path(workspace),td/"dev032_e1a_build")
        support=td/f"{day.isoformat()}_support.csv"
        output=td/f"{day.isoformat()}_dev044_raw.csv"
        _write_support(support,ts)
        p=subprocess.run(
            [str(exe),str(raw),str(support),str(output)],
            capture_output=True,text=True,
        )
        if p.returncode!=0:
            raise RawAdapterError(f"extractor_failed:{day}:rc={p.returncode}:{p.stderr}")
        parsed=e1mat.parse_raw_extractor_csv(output,ts)
        vals={sid:np.asarray(parsed[sid],dtype=np.float64) for sid in RAW_IDS_NEEDED}
        for sid in RAW_IDS_NEEDED:
            a=vals[sid]
            if a.shape[0]!=len(ts) or np.any(~np.isfinite(a)):
                raise RawAdapterError(f"matrix:{sid}")
        return RawAdapterResult(day,ts,vals,p.stderr.strip())
    finally:
        if td_ctx is not None:
            td_ctx.cleanup()


def validate_mapping(values:Mapping[str,np.ndarray])->None:
    missing=[sid for sid in RAW_IDS_NEEDED if sid not in values]
    if missing:
        raise RawAdapterError("missing:"+",".join(missing))

    widths={"S05":7,"S06":2,"S21":8,"S30":6,"S31":6,"S32":4}
    rows=None
    for sid,w in widths.items():
        a=np.asarray(values[sid],dtype=np.float64)
        if a.ndim!=2 or a.shape[1]!=w or np.any(~np.isfinite(a)):
            raise RawAdapterError(f"shape:{sid}")
        rows=len(a) if rows is None else rows
        if len(a)!=rows:
            raise RawAdapterError("row_alignment")


def raw_row_map(result:RawAdapterResult)->dict[int,int]:
    ts=np.asarray(result.timestamps_us,dtype=np.int64)
    if len(np.unique(ts))!=len(ts):
        raise RawAdapterError("duplicate_support")
    return {int(t):i for i,t in enumerate(ts.tolist())}
