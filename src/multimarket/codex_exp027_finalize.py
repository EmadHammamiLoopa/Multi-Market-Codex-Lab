from __future__ import annotations

import argparse
import gzip
import json
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Protocol

from .codex_exp025_collect import INITIAL_SYMBOLS, SUPPORTED_SYMBOLS
from .codex_exp025_finalize import (
    GRID_US,
    EXPECTED_ROWS,
    build_grid,
    grid_relative_path,
    sha256_file,
)
from .codex_exp027_archive import (
    EXPERIMENT_ID,
    FULL_DAY_STATUS,
    daily_manifest_path,
)
from .codex_exp027_collect import (
    ArchiveConfig,
    ArchiveOperationalError,
    S3ArchiveClient,
    _write_once_json,
)


STATUS_READY = "FULL_DAY_ARCHIVE_GRID_READY"
STATUS_INVALID = "INVALID"


class ArchiveDownloadClient(Protocol):
    def verify_existing(
        self,
        key: str,
        expected_bytes: int,
        expected_sha256: str,
    ) -> Any: ...

    def download_verified(
        self,
        key: str,
        expected_bytes: int,
        expected_sha256: str,
        destination: Path,
    ) -> Path: ...


def _require_symbol(symbol: str) -> str:
    if symbol not in SUPPORTED_SYMBOLS:
        raise ValueError(f"unsupported EXP027 symbol: {symbol}")
    return symbol


def exp027_grid_path(output_root: Path, symbol: str, day: date) -> Path:
    _require_symbol(symbol)
    return (
        output_root
        / "multimarket"
        / "evidence-exp027"
        / symbol
        / f"{day.isoformat()}_BOOKTICKER250.csv"
    )


def exp027_audit_path(output_root: Path, symbol: str, day: date) -> Path:
    _require_symbol(symbol)
    return (
        output_root
        / "multimarket"
        / "audits-exp027"
        / symbol
        / f"{day.isoformat()}_AUDIT.json"
    )


def _validate_day_manifest(
    payload: dict[str, Any],
    *,
    symbol: str,
    day: date,
) -> list[dict[str, Any]]:
    if payload.get("experiment_id") != EXPERIMENT_ID:
        raise ArchiveOperationalError("EXP027 day manifest experiment mismatch")
    if payload.get("status") != FULL_DAY_STATUS:
        raise ArchiveOperationalError(
            f"EXP027 day is not FULL_DAY_RAW_ARCHIVE_READY: "
            f"{payload.get('status')}"
        )
    if payload.get("symbol") != symbol:
        raise ArchiveOperationalError("EXP027 day manifest symbol mismatch")
    if payload.get("collection_day") != day.isoformat():
        raise ArchiveOperationalError("EXP027 day manifest date mismatch")
    if payload.get("verified_hour_count") != 24:
        raise ArchiveOperationalError("EXP027 day manifest does not have 24 hours")
    if payload.get("missing_hours") != []:
        raise ArchiveOperationalError("EXP027 day manifest has missing hours")
    if payload.get("rollover_observed_after_day") is not True:
        raise ArchiveOperationalError("EXP027 day rollover not observed")
    hours = payload.get("hourly_archives")
    if not isinstance(hours, list) or len(hours) != 24:
        raise ArchiveOperationalError("EXP027 hourly archive list invalid")
    return hours


def _iter_hour_records(
    path: Path,
    *,
    expected_hour: datetime,
) -> Iterator[dict[str, Any]]:
    saw_hour_started = False
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("record_type") == "transport":
                event = str(record.get("event", ""))
                if event == "hour_started":
                    if saw_hour_started:
                        raise ArchiveOperationalError(
                            f"duplicate hour_started in {path}"
                        )
                    if record.get("collection_hour_utc") != expected_hour.isoformat():
                        raise ArchiveOperationalError(
                            f"hour_started timestamp mismatch in {path}"
                        )
                    saw_hour_started = True
                    # Preserve EXP025 grid semantics while carrying the current
                    # connection epoch into the new hour and invalidating any
                    # previous-hour quote. The next quote is therefore fresh.
                    yield {
                        **record,
                        "event": "connection_carried",
                    }
                    continue
            yield record
    if not saw_hour_started:
        raise ArchiveOperationalError(f"missing hour_started in {path}")


def _iter_day_records(
    chunk_paths: list[tuple[datetime, Path]],
) -> Iterator[dict[str, Any]]:
    for hour, path in chunk_paths:
        yield from _iter_hour_records(path, expected_hour=hour)


def finalize_archived_day(
    output_root: Path,
    manifest_root: Path,
    client: ArchiveDownloadClient,
    *,
    symbol: str,
    day: date,
    expected_rows: int = EXPECTED_ROWS,
) -> dict[str, Any]:
    _require_symbol(symbol)
    day_manifest = daily_manifest_path(manifest_root, symbol, day)
    if not day_manifest.is_file():
        raise FileNotFoundError(day_manifest)
    manifest_payload = json.loads(day_manifest.read_text(encoding="utf-8"))
    hourly = _validate_day_manifest(
        manifest_payload,
        symbol=symbol,
        day=day,
    )

    grid = exp027_grid_path(output_root, symbol, day)
    audit = exp027_audit_path(output_root, symbol, day)
    grid_part = grid.with_suffix(grid.suffix + ".part")
    audit_part = audit.with_suffix(audit.suffix + ".part")
    for path in (grid, audit, grid_part, audit_part):
        if path.exists():
            raise FileExistsError(f"EXP027 finalizer output already exists: {path}")

    with tempfile.TemporaryDirectory(
        prefix=f".exp027-{symbol}-{day.isoformat()}-",
        dir=output_root,
    ) as temp_dir:
        scratch = Path(temp_dir)
        chunks: list[tuple[datetime, Path]] = []
        archive_records: list[dict[str, Any]] = []
        for index, item in enumerate(hourly):
            expected_hour = datetime(
                day.year,
                day.month,
                day.day,
                index,
                tzinfo=timezone.utc,
            )
            expected_hour_text = expected_hour.isoformat()
            if item.get("hour") != expected_hour_text:
                raise ArchiveOperationalError(
                    f"hour order mismatch at index {index}"
                )
            key = item.get("archive_key")
            size = item.get("bytes")
            digest = item.get("sha256")
            if (
                not isinstance(key, str)
                or type(size) is not int
                or size <= 0
                or not isinstance(digest, str)
                or len(digest) != 64
            ):
                raise ArchiveOperationalError("invalid day-manifest chunk metadata")
            client.verify_existing(key, size, digest)
            local = scratch / f"{index:02d}.jsonl.gz"
            client.download_verified(key, size, digest, local)
            if int(local.stat().st_size) != size or sha256_file(local) != digest:
                raise ArchiveOperationalError(
                    f"local post-download integrity mismatch: {key}"
                )
            chunks.append((expected_hour, local))
            archive_records.append(
                {
                    "hour": expected_hour_text,
                    "archive_key": key,
                    "bytes": size,
                    "sha256": digest,
                }
            )

        grid.parent.mkdir(parents=True, exist_ok=True)
        diagnostics = build_grid(
            _iter_day_records(chunks),
            grid,
            symbol=symbol,
            day=day,
            expected_rows=expected_rows,
        )

    grid_sha = sha256_file(grid)
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "status": STATUS_READY,
        "symbol": symbol,
        "collection_day": day.isoformat(),
        "source_day_manifest": str(day_manifest),
        "source_day_manifest_status": manifest_payload["status"],
        "archive_chunks_verified": 24,
        "archive_records": archive_records,
        "grid_path": str(grid),
        "grid_sha256": grid_sha,
        "grid_bytes": int(grid.stat().st_size),
        "grid_diagnostics": diagnostics,
        "grid_rows_exact_345600": (
            diagnostics["rows"] == EXPECTED_ROWS
            if expected_rows == EXPECTED_ROWS
            else None
        ),
        "grid_step_exact_250000us": diagnostics["grid_step_us"] == GRID_US,
        "no_future_quote_used": diagnostics["future_quote_violations"] == 0,
        "predictive_metrics_calculated": False,
        "features_constructed": False,
        "target_scored": False,
        "model_fit": False,
        "auc_scored": False,
        "ap_scored": False,
        "direction_scored": False,
        "pnl_scored": False,
        "leverage_scored": False,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    _write_once_json(audit, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--manifest-root", type=Path, required=True)
    parser.add_argument("--symbol", choices=INITIAL_SYMBOLS, required=True)
    parser.add_argument("--day", type=date.fromisoformat, required=True)
    args = parser.parse_args(argv)
    client = S3ArchiveClient(ArchiveConfig.from_env())
    payload = finalize_archived_day(
        args.output_root,
        args.manifest_root,
        client,
        symbol=args.symbol,
        day=args.day,
    )
    print(
        json.dumps(
            {
                "experiment_id": payload["experiment_id"],
                "status": payload["status"],
                "symbol": payload["symbol"],
                "collection_day": payload["collection_day"],
                "grid_sha256": payload["grid_sha256"],
                "grid_bytes": payload["grid_bytes"],
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
