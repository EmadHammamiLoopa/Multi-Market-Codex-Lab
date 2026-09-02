"""DEV031-P0 read-only raw L2 event-time/depth feasibility audit.

No labels, predictive fitting, target outcomes, PnL, or forward data are used.
The canonical run is restricted to seven consumed BTCUSDT Jan-Jul development
raw incremental_book_L2 files.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
import csv
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable, Mapping


EXPERIMENT_ID = "DEV031-P0"
DESIGN_VERSION = "event-depth-raw-l2-feasibility-v1"

DEVELOPMENT_DAYS = tuple(date(2026, m, 1) for m in range(1, 8))
SYMBOL = "BTCUSDT"
EXCHANGE = "binance-futures"
DATA_TYPE = "incremental_book_L2"

EXPECTED_HEADER = (
    "exchange",
    "symbol",
    "timestamp",
    "local_timestamp",
    "is_snapshot",
    "side",
    "price",
    "amount",
)

DEFAULT_RAW_ROOT = Path("data/v23_phase0dl_l2_raw/incremental_book_L2/BTCUSDT")
REAL_OUTPUT_DIRECTORY = Path(
    "/home/emadh/Multi-Market/evidence/dev031_p0_event_depth_raw_l2_v1"
)
ARTIFACT_FILENAME = "DEV031_P0_EVENT_DEPTH_RAW_L2_RESULT.json"

GRID_US = 250_000

STATUS_PASS = "DATA_READY_EVENT_DEPTH_RAW_L2"
STATUS_FAIL = "FAIL_EVENT_DEPTH_RAW_L2_INCOMPLETE"
STATUS_INCONCLUSIVE = "INCONCLUSIVE_EVENT_DEPTH_RAW_L2_AUDIT"

FORWARD_GUARDS = {
    "aug01_opened": False,
    "aug30_opened": False,
    "sep01_or_later_opened": False,
    "railway_opened": False,
    "archive_bucket_opened": False,
    "abundant_love_opened": False,
    "downloads_or_acquisition_run": False,
}


class P0AuditError(RuntimeError):
    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")


@dataclass(frozen=True)
class DayAudit:
    day: date
    path: str
    bytes: int
    sha256: str
    header_ok: bool
    rows: int
    bad_rows: int
    snapshot_rows: int
    rows_before_first_snapshot: int
    first_local_timestamp: int | None
    last_local_timestamp: int | None
    first_exchange_timestamp: int | None
    last_exchange_timestamp: int | None
    local_timestamp_regressions: int
    distinct_local_timestamp_groups: int
    multirow_group_rows: int
    max_group_size: int
    median_group_size: float
    bid_rows: int
    ask_rows: int
    deletion_rows: int
    distinct_prices_touched: int
    nonempty_250ms_buckets: int
    total_day_250ms_buckets: int
    multirow_250ms_buckets: int
    multigroup_250ms_buckets: int
    max_rows_per_250ms_bucket: int
    median_rows_per_nonempty_250ms_bucket: float
    post_snapshot_incremental_rows: int
    exchange_local_offset_us_quantiles: dict[str, float]
    initialized_after_snapshot: bool
    path_within_frozen_scope: bool


@dataclass(frozen=True)
class ArtifactWriteResult:
    output_directory: Path
    artifact_path: Path
    artifact_sha256: str
    artifact_bytes: int


def _day_bounds_us(day: date) -> tuple[int, int]:
    start = int(
        datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp()
        * 1_000_000
    )
    return start, start + 86_400_000_000


def _sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _median_from_counter(counter: Counter[int]) -> float:
    total = sum(counter.values())
    if total <= 0:
        return 0.0
    targets = ((total - 1) // 2, total // 2)
    values: list[int] = []
    cumulative = 0
    for value in sorted(counter):
        next_cumulative = cumulative + counter[value]
        for target in targets:
            if cumulative <= target < next_cumulative:
                values.append(value)
        cumulative = next_cumulative
        if len(values) == 2:
            break
    if len(values) != 2:
        raise P0AuditError("median_counter_internal_error")
    return float(sum(values) / 2.0)


def _quantiles(values: list[int]) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values)
    n = len(ordered)

    def q(prob: float) -> float:
        if n == 1:
            return float(ordered[0])
        position = prob * (n - 1)
        lo = int(math.floor(position))
        hi = int(math.ceil(position))
        if lo == hi:
            return float(ordered[lo])
        weight = position - lo
        return float(ordered[lo] * (1.0 - weight) + ordered[hi] * weight)

    return {
        "q01": q(0.01),
        "q05": q(0.05),
        "q50": q(0.50),
        "q95": q(0.95),
        "q99": q(0.99),
    }


def _validate_frozen_path(path: Path, *, raw_root: Path, day: date) -> None:
    expected = raw_root / f"{day.isoformat()}.csv.gz"
    if path != expected:
        raise P0AuditError(
            "raw_path_outside_frozen_scope",
            f"expected={expected} actual={path}",
        )
    if day not in DEVELOPMENT_DAYS:
        raise P0AuditError("day_outside_frozen_scope", day.isoformat())


def audit_day(path: Path, *, raw_root: Path, day: date) -> DayAudit:
    """Stream one frozen raw L2 file read-only."""
    path = Path(path)
    raw_root = Path(raw_root)
    _validate_frozen_path(path, raw_root=raw_root, day=day)

    if not path.is_file():
        raise P0AuditError("raw_file_missing", str(path))

    file_bytes = path.stat().st_size
    if file_bytes <= 0:
        raise P0AuditError("raw_file_empty", str(path))

    sha = _sha256_file(path)
    start_us, end_us = _day_bounds_us(day)
    total_buckets = 86_400_000_000 // GRID_US

    rows = 0
    bad_rows = 0
    snapshots = 0
    rows_before_first_snapshot = 0
    seen_snapshot = False
    post_snapshot_incremental_rows = 0
    bid_rows = 0
    ask_rows = 0
    deletion_rows = 0
    local_regressions = 0

    first_local = last_local = None
    first_exchange = last_exchange = None
    prev_local: int | None = None

    current_group_ts: int | None = None
    current_group_size = 0
    group_size_counts: Counter[int] = Counter()
    distinct_groups = 0
    multirow_group_rows = 0

    current_bucket: int | None = None
    current_bucket_rows = 0
    current_bucket_groups = 0
    bucket_row_count_distribution: Counter[int] = Counter()
    nonempty_buckets = 0
    multirow_buckets = 0
    multigroup_buckets = 0
    max_rows_bucket = 0

    distinct_prices: set[float] = set()
    offsets: list[int] = []

    def flush_group() -> None:
        nonlocal current_group_size, distinct_groups, multirow_group_rows
        if current_group_size <= 0:
            return
        distinct_groups += 1
        group_size_counts[current_group_size] += 1
        if current_group_size > 1:
            multirow_group_rows += current_group_size
        current_group_size = 0

    def flush_bucket() -> None:
        nonlocal current_bucket_rows, current_bucket_groups
        nonlocal nonempty_buckets, multirow_buckets, multigroup_buckets
        nonlocal max_rows_bucket
        if current_bucket_rows <= 0:
            return
        nonempty_buckets += 1
        bucket_row_count_distribution[current_bucket_rows] += 1
        max_rows_bucket = max(max_rows_bucket, current_bucket_rows)
        if current_bucket_rows > 1:
            multirow_buckets += 1
        if current_bucket_groups > 1:
            multigroup_buckets += 1
        current_bucket_rows = 0
        current_bucket_groups = 0

    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = tuple(next(reader))
        except StopIteration as exc:
            raise P0AuditError("missing_header", str(path)) from exc

        header_ok = header == EXPECTED_HEADER
        if not header_ok:
            raise P0AuditError(
                "header_mismatch",
                f"actual={header} expected={EXPECTED_HEADER}",
            )

        pos = {name: i for i, name in enumerate(header)}

        for row in reader:
            rows += 1
            row_bad = False
            if len(row) != len(EXPECTED_HEADER):
                bad_rows += 1
                continue

            try:
                exchange = row[pos["exchange"]]
                symbol = row[pos["symbol"]]
                exchange_ts = int(row[pos["timestamp"]])
                local_ts = int(row[pos["local_timestamp"]])
                snapshot_text = row[pos["is_snapshot"]].strip().lower()
                side = row[pos["side"]]
                price = float(row[pos["price"]])
                amount = float(row[pos["amount"]])
            except Exception:
                bad_rows += 1
                continue

            if exchange != EXCHANGE:
                row_bad = True
            if symbol != SYMBOL:
                row_bad = True
            if not (start_us <= local_ts < end_us):
                row_bad = True
            if snapshot_text not in ("true", "false"):
                row_bad = True
            if side not in ("bid", "ask"):
                row_bad = True
            if not math.isfinite(price) or price <= 0.0:
                row_bad = True
            if not math.isfinite(amount) or amount < 0.0:
                row_bad = True
            if prev_local is not None and local_ts < prev_local:
                local_regressions += 1
                row_bad = True

            if row_bad:
                bad_rows += 1
                prev_local = local_ts
                continue

            is_snapshot = snapshot_text == "true"
            if is_snapshot:
                snapshots += 1
                seen_snapshot = True
            elif not seen_snapshot:
                rows_before_first_snapshot += 1
            else:
                post_snapshot_incremental_rows += 1

            if side == "bid":
                bid_rows += 1
            else:
                ask_rows += 1
            if amount == 0.0:
                deletion_rows += 1

            distinct_prices.add(price)
            offsets.append(local_ts - exchange_ts)

            if first_local is None:
                first_local = local_ts
                first_exchange = exchange_ts
            last_local = local_ts
            last_exchange = exchange_ts

            if current_group_ts is None:
                current_group_ts = local_ts
                current_group_size = 1
            elif local_ts == current_group_ts:
                current_group_size += 1
            else:
                flush_group()
                current_group_ts = local_ts
                current_group_size = 1

            bucket = (local_ts - start_us) // GRID_US
            if current_bucket is None:
                current_bucket = bucket
                current_bucket_rows = 1
                current_bucket_groups = 1
            elif bucket == current_bucket:
                current_bucket_rows += 1
                if prev_local is not None and local_ts != prev_local:
                    current_bucket_groups += 1
            else:
                flush_bucket()
                current_bucket = bucket
                current_bucket_rows = 1
                current_bucket_groups = 1

            prev_local = local_ts

    flush_group()
    flush_bucket()

    initialized = snapshots > 0 and post_snapshot_incremental_rows > 0

    return DayAudit(
        day=day,
        path=str(path),
        bytes=int(file_bytes),
        sha256=sha,
        header_ok=True,
        rows=int(rows),
        bad_rows=int(bad_rows),
        snapshot_rows=int(snapshots),
        rows_before_first_snapshot=int(rows_before_first_snapshot),
        first_local_timestamp=first_local,
        last_local_timestamp=last_local,
        first_exchange_timestamp=first_exchange,
        last_exchange_timestamp=last_exchange,
        local_timestamp_regressions=int(local_regressions),
        distinct_local_timestamp_groups=int(distinct_groups),
        multirow_group_rows=int(multirow_group_rows),
        max_group_size=int(max(group_size_counts) if group_size_counts else 0),
        median_group_size=_median_from_counter(group_size_counts),
        bid_rows=int(bid_rows),
        ask_rows=int(ask_rows),
        deletion_rows=int(deletion_rows),
        distinct_prices_touched=int(len(distinct_prices)),
        nonempty_250ms_buckets=int(nonempty_buckets),
        total_day_250ms_buckets=int(total_buckets),
        multirow_250ms_buckets=int(multirow_buckets),
        multigroup_250ms_buckets=int(multigroup_buckets),
        max_rows_per_250ms_bucket=int(max_rows_bucket),
        median_rows_per_nonempty_250ms_bucket=_median_from_counter(
            bucket_row_count_distribution
        ),
        post_snapshot_incremental_rows=int(post_snapshot_incremental_rows),
        exchange_local_offset_us_quantiles=_quantiles(offsets),
        initialized_after_snapshot=bool(initialized),
        path_within_frozen_scope=True,
    )


def day_gates(item: DayAudit) -> dict[str, bool]:
    return {
        "file_nonempty": item.bytes > 0,
        "header_exact": item.header_ok,
        "rows_nonzero": item.rows > 0,
        "zero_bad_rows": item.bad_rows == 0,
        "zero_local_timestamp_regressions": item.local_timestamp_regressions == 0,
        "snapshot_present": item.snapshot_rows > 0,
        "book_initialization_feasible": item.initialized_after_snapshot,
        "post_snapshot_incremental_events_present": (
            item.post_snapshot_incremental_rows > 0
        ),
        "deletions_present": item.deletion_rows > 0,
        "multirow_250ms_buckets_present": item.multirow_250ms_buckets > 0,
        "multigroup_250ms_buckets_present": item.multigroup_250ms_buckets > 0,
        "distinct_price_levels_gt_10": item.distinct_prices_touched > 10,
        "within_frozen_scope": item.path_within_frozen_scope,
    }


def aggregate_novelty(days: Iterable[DayAudit]) -> dict[str, Any]:
    items = tuple(days)
    if len(items) != len(DEVELOPMENT_DAYS):
        raise P0AuditError("day_count_mismatch")
    return {
        "all_days_have_multirow_250ms_buckets": all(
            item.multirow_250ms_buckets > 0 for item in items
        ),
        "all_days_have_multigroup_250ms_buckets": all(
            item.multigroup_250ms_buckets > 0 for item in items
        ),
        "all_days_have_deletions": all(item.deletion_rows > 0 for item in items),
        "all_days_touch_more_than_10_prices": all(
            item.distinct_prices_touched > 10 for item in items
        ),
        "within_grid_event_sequence_information_present": all(
            item.multigroup_250ms_buckets > 0 for item in items
        ),
        "level_deletion_information_present": all(
            item.deletion_rows > 0 for item in items
        ),
        "depth_beyond_preserved_top10_structurally_possible": all(
            item.distinct_prices_touched > 10 for item in items
        ),
    }


def _public_day(item: DayAudit) -> dict[str, Any]:
    result = {
        key: value
        for key, value in item.__dict__.items()
        if key != "day"
    }
    result["day"] = item.day.isoformat()
    result["deletion_fraction"] = (
        float(item.deletion_rows / item.rows) if item.rows else 0.0
    )
    result["multirow_group_row_fraction"] = (
        float(item.multirow_group_rows / item.rows) if item.rows else 0.0
    )
    result["nonempty_250ms_bucket_fraction"] = (
        float(item.nonempty_250ms_buckets / item.total_day_250ms_buckets)
        if item.total_day_250ms_buckets
        else 0.0
    )
    result["gates"] = day_gates(item)
    return result


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_result_once(
    output_directory: Path,
    payload: Mapping[str, Any],
    *,
    require_canonical_output: bool = True,
) -> ArtifactWriteResult:
    output = Path(output_directory)
    if output.exists() or output.is_symlink():
        raise P0AuditError("output_directory_already_exists")
    if require_canonical_output and output != REAL_OUTPUT_DIRECTORY:
        raise P0AuditError("noncanonical_output_directory")
    if not require_canonical_output and output == REAL_OUTPUT_DIRECTORY:
        raise P0AuditError("canonical_output_requires_real_mode")

    content = canonical_json_bytes(payload)
    output.mkdir(mode=0o755)
    _fsync_directory(output.parent)
    final = output / ARTIFACT_FILENAME
    part = final.with_name(final.name + ".part")
    try:
        with part.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(part, final)
        _fsync_directory(output)
    except BaseException as exc:
        if final.exists():
            raise P0AuditError("artifact_directory_fsync_failed", str(exc)) from exc
        try:
            if part.exists():
                part.unlink()
            if output.exists() and not any(output.iterdir()):
                output.rmdir()
        except OSError as cleanup_exc:
            raise P0AuditError("artifact_cleanup_failed", str(cleanup_exc)) from cleanup_exc
        if isinstance(exc, P0AuditError):
            raise
        raise P0AuditError("artifact_write_failed", str(exc)) from exc

    return ArtifactWriteResult(
        output_directory=output,
        artifact_path=final,
        artifact_sha256=hashlib.sha256(content).hexdigest(),
        artifact_bytes=len(content),
    )


def run_p0(
    *,
    raw_root: Path = DEFAULT_RAW_ROOT,
    output_directory: Path = REAL_OUTPUT_DIRECTORY,
    require_canonical_output: bool = True,
) -> ArtifactWriteResult:
    root = Path(raw_root)
    output = Path(output_directory)

    if require_canonical_output and root != DEFAULT_RAW_ROOT:
        raise P0AuditError("canonical_raw_root_override_forbidden")
    if require_canonical_output and output != REAL_OUTPUT_DIRECTORY:
        raise P0AuditError("noncanonical_output_directory")
    if output.exists() or output.is_symlink():
        raise P0AuditError("output_directory_already_exists")

    days: list[DayAudit] = []
    errors: list[dict[str, str]] = []

    for day in DEVELOPMENT_DAYS:
        path = root / f"{day.isoformat()}.csv.gz"
        try:
            days.append(audit_day(path, raw_root=root, day=day))
        except Exception as exc:
            errors.append(
                {
                    "day": day.isoformat(),
                    "type": type(exc).__name__,
                    "reason": getattr(exc, "reason", "exception"),
                    "detail": str(exc),
                }
            )

    if errors:
        status = STATUS_FAIL
        pass_gate = False
        novelty = {}
        day_payloads = [_public_day(item) for item in days]
    else:
        novelty = aggregate_novelty(days)
        day_payloads = [_public_day(item) for item in days]
        all_day_gates = all(
            all(day_gates(item).values())
            for item in days
        )
        novelty_pass = all(bool(value) for value in novelty.values())
        pass_gate = all_day_gates and novelty_pass and not any(FORWARD_GUARDS.values())
        status = STATUS_PASS if pass_gate else STATUS_FAIL

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "status": status,
        "pass": bool(pass_gate),
        "scope": {
            "symbol": SYMBOL,
            "exchange": EXCHANGE,
            "data_type": DATA_TYPE,
            "development_days": [day.isoformat() for day in DEVELOPMENT_DAYS],
            "labels_opened": False,
            "predictive_metrics_run": False,
            "model_fit_run": False,
        },
        "days": day_payloads,
        "errors": errors,
        "novelty": novelty,
        "forward_guards": dict(FORWARD_GUARDS),
        "scientific_interpretation": (
            "raw event-time/depth information exists and is structurally auditable"
            if pass_gate
            else "raw event-time/depth feasibility gates not fully satisfied"
        ),
    }

    return write_result_once(
        output,
        payload,
        require_canonical_output=require_canonical_output,
    )


__all__ = [
    "ARTIFACT_FILENAME",
    "DEFAULT_RAW_ROOT",
    "DEVELOPMENT_DAYS",
    "DESIGN_VERSION",
    "EXPERIMENT_ID",
    "EXPECTED_HEADER",
    "FORWARD_GUARDS",
    "P0AuditError",
    "REAL_OUTPUT_DIRECTORY",
    "STATUS_FAIL",
    "STATUS_INCONCLUSIVE",
    "STATUS_PASS",
    "audit_day",
    "day_gates",
    "run_p0",
]
