from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol

from .codex_exp025_collect import (
    INITIAL_SYMBOLS,
    SUPPORTED_SYMBOLS,
    CollectorIdentity,
    no_analysis_guards,
)


EXPERIMENT_ID = "CODEX-EXP-027-P0"
ARCHIVE_KEY_ROOT = "bookticker"
MANIFEST_RELATIVE_ROOT = Path("archive-manifests/bookticker")
FAILURE_RELATIVE_ROOT = Path("operational-failures/bookticker")
FULL_DAY_STATUS = "FULL_DAY_RAW_ARCHIVE_READY"
PARTIAL_DAY_STATUS = "PARTIAL_START_DAY"
FAIL_STATUS = "FAIL_ARCHIVE_INTEGRITY"


class DailyArchiveIntegrityError(RuntimeError):
    pass


class ExistingObjectVerifier(Protocol):
    def verify_existing(
        self,
        key: str,
        expected_bytes: int,
        expected_sha256: str,
    ) -> Any: ...


def _require_symbol(symbol: str) -> str:
    if symbol not in SUPPORTED_SYMBOLS:
        raise ValueError(f"unsupported EXP027 symbol: {symbol}")
    return symbol


def _hour_start(day: date, hour_index: int) -> datetime:
    if not 0 <= hour_index <= 23:
        raise ValueError("hour index outside [0, 23]")
    return datetime(
        day.year,
        day.month,
        day.day,
        hour_index,
        tzinfo=timezone.utc,
    )


def hourly_manifest_path(
    output_root: Path,
    symbol: str,
    hour: datetime,
) -> Path:
    _require_symbol(symbol)
    if hour.tzinfo is None or hour.utcoffset() != timedelta(0):
        raise ValueError("hour must be timezone-aware UTC")
    if any((hour.minute, hour.second, hour.microsecond)):
        raise ValueError("hour must be aligned to UTC hour")
    return (
        output_root
        / MANIFEST_RELATIVE_ROOT
        / symbol
        / hour.date().isoformat()
        / f"{hour:%H}.archive.json"
    )


def daily_manifest_path(
    output_root: Path,
    symbol: str,
    day: date,
) -> Path:
    _require_symbol(symbol)
    return (
        output_root
        / MANIFEST_RELATIVE_ROOT
        / symbol
        / day.isoformat()
        / "DAY_ARCHIVE.json"
    )


def failure_root(
    output_root: Path,
    symbol: str,
    day: date,
) -> Path:
    _require_symbol(symbol)
    return output_root / FAILURE_RELATIVE_ROOT / symbol / day.isoformat()


def expected_archive_key(symbol: str, hour: datetime) -> str:
    _require_symbol(symbol)
    return (
        f"{ARCHIVE_KEY_ROOT}/{symbol}/"
        f"{hour.date().isoformat()}/{hour:%H}.jsonl.gz"
    )


def _write_once_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    if path.exists() or part.exists():
        raise FileExistsError(f"immutable daily archive manifest exists: {path}")
    encoded = json.dumps(
        dict(payload),
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    with part.open("x", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    part.replace(path)


@dataclass(frozen=True)
class VerifiedHourlyArchive:
    hour: str
    archive_key: str
    byte_size: int
    sha256: str


def _parse_hourly_manifest(
    payload: Mapping[str, Any],
    *,
    symbol: str,
    hour: datetime,
    identity: CollectorIdentity,
) -> VerifiedHourlyArchive:
    exact = {
        "experiment_id": EXPERIMENT_ID,
        "status": "HOURLY_RAW_ARCHIVE_VERIFIED",
        "symbol": symbol,
        "collection_hour_utc": hour.isoformat(),
        "archive_key": expected_archive_key(symbol, hour),
        "frozen_implementation_commit": identity.frozen_implementation_commit,
        "collector_run_id": identity.collector_run_id,
    }
    for name, expected in exact.items():
        if payload.get(name) != expected:
            raise DailyArchiveIntegrityError(
                f"hourly manifest mismatch for {symbol} "
                f"{hour.isoformat()}: {name}"
            )
    byte_size = payload.get("local_bytes")
    digest = payload.get("local_sha256")
    remote_bytes = payload.get("remote_bytes")
    remote_sha = payload.get("remote_sha256")
    if type(byte_size) is not int or byte_size <= 0:
        raise DailyArchiveIntegrityError("invalid hourly archive byte size")
    if type(remote_bytes) is not int or remote_bytes != byte_size:
        raise DailyArchiveIntegrityError("hourly remote byte size mismatch")
    if not isinstance(digest, str) or len(digest) != 64:
        raise DailyArchiveIntegrityError("invalid hourly archive SHA-256")
    try:
        int(digest, 16)
    except ValueError as exc:
        raise DailyArchiveIntegrityError(
            "invalid hourly archive SHA-256"
        ) from exc
    if remote_sha != digest:
        raise DailyArchiveIntegrityError("hourly remote SHA-256 mismatch")
    guards = no_analysis_guards()
    for name, expected in guards.items():
        if payload.get(name) is not expected:
            raise DailyArchiveIntegrityError(
                f"hourly no-analysis guard mismatch: {name}"
            )
    return VerifiedHourlyArchive(
        hour=hour.isoformat(),
        archive_key=expected_archive_key(symbol, hour),
        byte_size=byte_size,
        sha256=digest,
    )


def finalize_daily_archive_manifest(
    output_root: Path,
    verifier: ExistingObjectVerifier,
    *,
    symbol: str,
    day: date,
    identity: CollectorIdentity,
) -> dict[str, Any]:
    _require_symbol(symbol)
    day_start = datetime(
        day.year,
        day.month,
        day.day,
        tzinfo=timezone.utc,
    )
    day_start_ns = int(day_start.timestamp() * 1_000_000_000)
    armed_before_day_start = (
        identity.collector_started_wall_ns < day_start_ns
    )

    verified: list[VerifiedHourlyArchive] = []
    missing_hours: list[str] = []
    for hour_index in range(24):
        hour = _hour_start(day, hour_index)
        path = hourly_manifest_path(output_root, symbol, hour)
        if not path.exists():
            missing_hours.append(f"{hour_index:02d}")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        item = _parse_hourly_manifest(
            payload,
            symbol=symbol,
            hour=hour,
            identity=identity,
        )
        verifier.verify_existing(
            item.archive_key,
            item.byte_size,
            item.sha256,
        )
        verified.append(item)

    failures_dir = failure_root(output_root, symbol, day)
    failure_markers = (
        sorted(failures_dir.glob("*.operational-failure.json"))
        if failures_dir.exists()
        else []
    )

    if failure_markers:
        status = FAIL_STATUS
    elif armed_before_day_start:
        if missing_hours:
            raise DailyArchiveIntegrityError(
                f"full-day archive missing hours for {symbol} {day}: "
                + ",".join(missing_hours)
            )
        if len(verified) != 24:
            raise DailyArchiveIntegrityError(
                f"full-day archive expected 24 verified chunks, "
                f"got {len(verified)}"
            )
        status = FULL_DAY_STATUS
    else:
        status = PARTIAL_DAY_STATUS

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "symbol": symbol,
        "collection_day": day.isoformat(),
        "frozen_implementation_commit": identity.frozen_implementation_commit,
        "collector_run_id": identity.collector_run_id,
        "collector_started_wall_ns": identity.collector_started_wall_ns,
        "collector_started_utc": identity.collector_started_utc,
        "armed_before_day_start": bool(armed_before_day_start),
        "rollover_observed_after_day": True,
        "verified_hour_count": len(verified),
        "missing_hours": missing_hours,
        "hourly_archives": [
            {
                "hour": item.hour,
                "archive_key": item.archive_key,
                "bytes": item.byte_size,
                "sha256": item.sha256,
            }
            for item in verified
        ],
        "operational_failure_markers": [
            str(path) for path in failure_markers
        ],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **no_analysis_guards(),
    }
    _write_once_json(
        daily_manifest_path(output_root, symbol, day),
        payload,
    )
    return payload


def finalize_all_symbols_for_day(
    output_root: Path,
    verifier: ExistingObjectVerifier,
    *,
    day: date,
    identity: CollectorIdentity,
) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for symbol in INITIAL_SYMBOLS:
        payload = finalize_daily_archive_manifest(
            output_root,
            verifier,
            symbol=symbol,
            day=day,
            identity=identity,
        )
        statuses[symbol] = str(payload["status"])
    return statuses
