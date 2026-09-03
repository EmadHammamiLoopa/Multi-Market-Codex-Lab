from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import csv
import hashlib
import json
import os
import shutil

import numpy as np

from . import dev044_t0c_flow_toxicity as t0c

EXPERIMENT_ID="DEV044-T0D"
DESIGN_VERSION="vpin-bucket-calibration-v1"
STATUS_PASS="DEV044_T0D_VPIN_BUCKET_CALIBRATION_PASS"

CALIBRATION_DAYS=(date(2026,1,1),date(2026,2,1),date(2026,3,1))
TRADE250_ROOT=Path("/home/emadh/Multi-Market/evidence/v23/phase0dl_trade250/BTCUSDT")

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev044_t0d_vpin_calibration_v1"
)
ARTIFACT_FILENAME="DEV044_T0D_VPIN_CALIBRATION_RESULT.json"

EXPECTED_ROWS=345_600
EXPECTED_HEADER=(
    "local_timestamp_us",
    "buy_qty_250ms",
    "sell_qty_250ms",
    "unknown_qty_250ms",
    "buy_count_250ms",
    "sell_count_250ms",
    "unknown_count_250ms",
)

class T0DCalibrationError(RuntimeError):
    pass

@dataclass(frozen=True)
class TradeDay:
    day:date
    timestamps_us:np.ndarray
    buy_qty:np.ndarray
    sell_qty:np.ndarray
    unknown_qty:np.ndarray


def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()


def _load_trade_day(day:date)->TradeDay:
    path=TRADE250_ROOT/f"{day.isoformat()}_TRADE250.csv"
    if not path.is_file():
        raise T0DCalibrationError(f"trade250_missing:{day}:{path}")

    with path.open("r",encoding="utf-8",newline="") as h:
        r=csv.reader(h)
        try:
            header=tuple(next(r))
        except StopIteration:
            raise T0DCalibrationError(f"trade250_empty:{day}")
        if header!=EXPECTED_HEADER:
            raise T0DCalibrationError(f"trade250_header:{day}:{header}")
        rows=list(r)

    if len(rows)!=EXPECTED_ROWS:
        raise T0DCalibrationError(f"trade250_rows:{day}:{len(rows)}")

    a=np.asarray([[float(v) for v in row] for row in rows],dtype=np.float64)
    if a.shape!=(EXPECTED_ROWS,7) or np.any(~np.isfinite(a)):
        raise T0DCalibrationError(f"trade250_matrix:{day}")

    ts=a[:,0].astype(np.int64,copy=False)
    if np.any(np.diff(ts)!=250_000):
        raise T0DCalibrationError(f"trade250_grid:{day}")

    buy=a[:,1]
    sell=a[:,2]
    unknown=a[:,3]
    counts=a[:,4:7]
    if np.any(buy<0) or np.any(sell<0) or np.any(unknown<0) or np.any(counts<0):
        raise T0DCalibrationError(f"trade250_negative:{day}")

    # Frozen Phase0DL FEATURE250 integrity reported zero unknown trades/qty.
    # Fail closed if the underlying calibration input disagrees.
    if np.any(unknown!=0.0) or np.any(a[:,6]!=0.0):
        raise T0DCalibrationError(f"trade250_unknown_nonzero:{day}")

    return TradeDay(day,ts,buy,sell,unknown)


def _positive_30m_volumes(day:TradeDay)->np.ndarray:
    block_rows=1800*4
    if len(day.timestamps_us)%block_rows!=0:
        raise T0DCalibrationError(f"block_geometry:{day.day}")
    total=day.buy_qty+day.sell_qty
    blocks=total.reshape(-1,block_rows).sum(axis=1)
    pos=blocks[blocks>0]
    if len(pos)==0 or np.any(~np.isfinite(pos)):
        raise T0DCalibrationError(f"positive_blocks:{day.day}")
    return pos.astype(np.float64,copy=False)


def calibrate_from_days(days:tuple[TradeDay,...])->dict:
    if tuple(d.day for d in days)!=CALIBRATION_DAYS:
        raise T0DCalibrationError("calendar")

    all_ts=np.concatenate([d.timestamps_us for d in days])
    all_buy=np.concatenate([d.buy_qty for d in days])
    all_sell=np.concatenate([d.sell_qty for d in days])

    # The shared implementation groups relative to the first timestamp. Since
    # project sample days are discontinuous, calibrate each day into 30m blocks
    # and pool the positive block totals explicitly.
    blocks=np.concatenate([_positive_30m_volumes(d) for d in days])
    median_30m=float(np.median(blocks))
    bucket=float(median_30m/t0c.VPIN_BUCKETS)

    if not np.isfinite(bucket) or bucket<=0:
        raise T0DCalibrationError("bucket")

    per_day=[]
    for d in days:
        v=_positive_30m_volumes(d)
        per_day.append({
            "day":d.day.isoformat(),
            "rows":int(len(d.timestamps_us)),
            "directional_qty":float(np.sum(d.buy_qty+d.sell_qty)),
            "positive_30m_blocks":int(len(v)),
            "median_30m_directional_qty":float(np.median(v)),
            "trade250_sha256":_sha(TRADE250_ROOT/f"{d.day.isoformat()}_TRADE250.csv"),
        })

    return {
        "median_30m_directional_qty":median_30m,
        "vpin_bucket_volume":bucket,
        "rolling_buckets":int(t0c.VPIN_BUCKETS),
        "calibration_block_seconds":int(t0c.CALIBRATION_BLOCK_SECONDS),
        "positive_30m_blocks_total":int(len(blocks)),
        "per_day":per_day,
    }


def run(
    *,
    execution_commit:str,
    output_directory:Path=REAL_OUTPUT_DIRECTORY,
    require_canonical_output:bool=True,
):
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise T0DCalibrationError("execution_commit")
    out=Path(output_directory)
    if require_canonical_output and out!=REAL_OUTPUT_DIRECTORY:
        raise T0DCalibrationError("noncanonical_output")
    if not require_canonical_output and out==REAL_OUTPUT_DIRECTORY:
        raise T0DCalibrationError("canonical_requires_real")
    if out.exists() or out.is_symlink():
        raise T0DCalibrationError("output_exists")

    days=tuple(_load_trade_day(d) for d in CALIBRATION_DAYS)
    cal=calibrate_from_days(days)

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "status":STATUS_PASS,
        "symbol":"BTCUSDT",
        "calibration_days":[d.isoformat() for d in CALIBRATION_DAYS],
        "source":"TRADE250",
        "formula":"median_positive_nonoverlapping_30m_directional_volume_div_50",
        **cal,
        "pnl_run":False,
        "labels_opened":False,
        "apr_jul_economic_scoring_opened":False,
        "sep01_plus_opened":False,
        "other_market_opened":False,
    }

    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    staging=out.parent/f".{out.name}.part-{os.getpid()}"
    if staging.exists():
        raise T0DCalibrationError("staging_exists")
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
        "artifact_path":str(final),
        "artifact_sha256":_sha(final),
        "artifact_bytes":int(final.stat().st_size),
        "status":STATUS_PASS,
        "vpin_bucket_volume":cal["vpin_bucket_volume"],
        "median_30m_directional_qty":cal["median_30m_directional_qty"],
    }
