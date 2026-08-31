from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

import websockets

from .codex_exp025_collect import (
    ASSET_CLASS,
    INITIAL_SYMBOLS,
    MARKET,
    QUEUE_MAXSIZE,
    SUPPORTED_SYMBOLS,
    VENUE,
    WRITER_SHUTDOWN_TIMEOUT_S,
    WS_URL,
    AcquisitionOperationalError,
    AsyncSymbolSink,
    CollectorIdentity,
    MultiSymbolRouter,
    RawWriter,
    _full_hex_commit,
    _iso_from_ns,
    _parse_message,
    _rejected_record,
    _transport_record,
    no_analysis_guards,
)

EXPERIMENT_ID = "CODEX-EXP-027-P0"
STAGING_RELATIVE_ROOT = Path("staging/bookticker")
MANIFEST_RELATIVE_ROOT = Path("archive-manifests/bookticker")
FAILURE_RELATIVE_ROOT = Path("operational-failures/bookticker")
ARCHIVE_KEY_ROOT = "bookticker"
ARCHIVE_METADATA_SHA = "sha256"
ARCHIVE_METADATA_BYTES = "bytes"
ARCHIVE_METADATA_EXPERIMENT = "experiment-id"
DEFAULT_URL_STYLE = "virtual"


class ArchiveOperationalError(RuntimeError):
    pass


class ArchiveClientProtocol(Protocol):
    def put_verified(self, path: Path, key: str) -> "ArchiveVerification": ...


@dataclass(frozen=True)
class ArchiveConfig:
    endpoint: str
    access_key_id: str
    secret_access_key: str
    bucket: str
    region: str
    url_style: str

    @classmethod
    def from_env(cls) -> "ArchiveConfig":
        endpoint = os.getenv("AWS_ENDPOINT_URL") or os.getenv("ENDPOINT")
        access = os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("ACCESS_KEY_ID")
        secret = os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("SECRET_ACCESS_KEY")
        bucket = os.getenv("AWS_S3_BUCKET_NAME") or os.getenv("BUCKET")
        region = os.getenv("AWS_DEFAULT_REGION") or os.getenv("REGION") or "auto"
        style = os.getenv("AWS_S3_URL_STYLE") or DEFAULT_URL_STYLE
        missing = [
            name
            for name, value in (
                ("endpoint", endpoint),
                ("access_key_id", access),
                ("secret_access_key", secret),
                ("bucket", bucket),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "missing bucket credentials: " + ", ".join(missing)
            )
        if style not in {"virtual", "path"}:
            raise RuntimeError("AWS_S3_URL_STYLE must be virtual or path")
        return cls(
            endpoint=str(endpoint),
            access_key_id=str(access),
            secret_access_key=str(secret),
            bucket=str(bucket),
            region=str(region),
            url_style=str(style),
        )


@dataclass(frozen=True)
class ArchiveVerification:
    key: str
    byte_size: int
    sha256: str
    remote_byte_size: int
    remote_sha256: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def floor_utc_hour_from_ns(wall_ns: int) -> datetime:
    dt = datetime.fromtimestamp(wall_ns / 1_000_000_000, tz=timezone.utc)
    return dt.replace(minute=0, second=0, microsecond=0)


def _hour_token(hour: datetime) -> tuple[str, str]:
    if hour.tzinfo is None or hour.utcoffset() != timedelta(0):
        raise ValueError("hour must be timezone-aware UTC")
    if any((hour.minute, hour.second, hour.microsecond)):
        raise ValueError("hour must be aligned to UTC hour")
    return hour.strftime("%Y-%m-%d"), hour.strftime("%H")


def staging_path(output_root: Path, symbol: str, hour: datetime) -> Path:
    if symbol not in SUPPORTED_SYMBOLS:
        raise ValueError(f"unsupported EXP027 symbol: {symbol}")
    day, hh = _hour_token(hour)
    return (
        output_root
        / STAGING_RELATIVE_ROOT
        / symbol
        / day
        / f"{hh}.jsonl.gz"
    )


def archive_key(symbol: str, hour: datetime) -> str:
    if symbol not in SUPPORTED_SYMBOLS:
        raise ValueError(f"unsupported EXP027 symbol: {symbol}")
    day, hh = _hour_token(hour)
    return f"{ARCHIVE_KEY_ROOT}/{symbol}/{day}/{hh}.jsonl.gz"


def manifest_path(output_root: Path, symbol: str, hour: datetime) -> Path:
    day, hh = _hour_token(hour)
    return (
        output_root
        / MANIFEST_RELATIVE_ROOT
        / symbol
        / day
        / f"{hh}.archive.json"
    )


def operational_failure_path(
    output_root: Path, symbol: str, hour: datetime
) -> Path:
    day, hh = _hour_token(hour)
    return (
        output_root
        / FAILURE_RELATIVE_ROOT
        / symbol
        / day
        / f"{hh}.operational-failure.json"
    )


def _write_once_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    if path.exists() or part.exists():
        raise FileExistsError(f"one-shot artifact already exists: {path}")
    encoded = (
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    with part.open("x", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    part.replace(path)


class S3ArchiveClient:
    def __init__(self, config: ArchiveConfig) -> None:
        boto3 = importlib.import_module("boto3")
        botocore_config = importlib.import_module("botocore.config")
        self.config = config
        self.client = boto3.client(
            "s3",
            endpoint_url=config.endpoint,
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            region_name=config.region,
            config=botocore_config.Config(
                retries={"max_attempts": 5, "mode": "standard"},
                s3={"addressing_style": config.url_style},
            ),
        )

    def put_verified(self, path: Path, key: str) -> ArchiveVerification:
        resolved = path.resolve(strict=True)
        if not resolved.is_file():
            raise ArchiveOperationalError(f"not a regular file: {resolved}")
        size = int(resolved.stat().st_size)
        if size <= 0:
            raise ArchiveOperationalError(f"refusing empty archive chunk: {resolved}")
        digest = sha256_file(resolved)

        with resolved.open("rb") as handle:
            try:
                self.client.put_object(
                    Bucket=self.config.bucket,
                    Key=key,
                    Body=handle,
                    ContentLength=size,
                    ContentType="application/gzip",
                    Metadata={
                        ARCHIVE_METADATA_SHA: digest,
                        ARCHIVE_METADATA_BYTES: str(size),
                        ARCHIVE_METADATA_EXPERIMENT: EXPERIMENT_ID,
                    },
                    IfNoneMatch="*",
                )
            except Exception as exc:
                raise ArchiveOperationalError(
                    f"archive upload failed for {key}: {type(exc).__name__}: {exc}"
                ) from exc

        try:
            head = self.client.head_object(
                Bucket=self.config.bucket,
                Key=key,
            )
        except Exception as exc:
            raise ArchiveOperationalError(
                f"archive HEAD verification failed for {key}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        remote_size = int(head.get("ContentLength", -1))
        metadata = {
            str(k).lower(): str(v)
            for k, v in dict(head.get("Metadata", {})).items()
        }
        remote_sha = metadata.get(ARCHIVE_METADATA_SHA, "")
        remote_bytes_meta = metadata.get(ARCHIVE_METADATA_BYTES, "")
        remote_experiment = metadata.get(ARCHIVE_METADATA_EXPERIMENT, "")
        if remote_size != size:
            raise ArchiveOperationalError(
                f"remote size mismatch for {key}: {remote_size} != {size}"
            )
        if remote_sha != digest:
            raise ArchiveOperationalError(
                f"remote SHA metadata mismatch for {key}"
            )
        if remote_bytes_meta != str(size):
            raise ArchiveOperationalError(
                f"remote byte metadata mismatch for {key}"
            )
        if remote_experiment != EXPERIMENT_ID:
            raise ArchiveOperationalError(
                f"remote experiment metadata mismatch for {key}"
            )

        return ArchiveVerification(
            key=key,
            byte_size=size,
            sha256=digest,
            remote_byte_size=remote_size,
            remote_sha256=remote_sha,
        )


def _hour_started_record(
    *,
    symbol: str,
    hour: datetime,
    identity: CollectorIdentity,
    wall_ns: int,
    mono_ns: int,
    active_epoch: int | None,
) -> dict[str, Any]:
    hour_end = hour + timedelta(hours=1)
    day_start = hour.replace(hour=0)
    process_armed_before_day = identity.collector_started_wall_ns < int(
        day_start.timestamp() * 1_000_000_000
    )
    record = _transport_record(
        "hour_started",
        active_epoch or 0,
        wall_ns=wall_ns,
        mono_ns=mono_ns,
        experiment_id=EXPERIMENT_ID,
        collector_run_id=identity.collector_run_id,
        process_id=identity.process_id,
        frozen_implementation_commit=identity.frozen_implementation_commit,
        collector_started_wall_ns=identity.collector_started_wall_ns,
        collector_started_utc=identity.collector_started_utc,
        symbol=symbol,
        collection_day=hour.date().isoformat(),
        collection_hour_utc=hour.isoformat(),
        collection_hour_end_utc=hour_end.isoformat(),
        armed_before_day_start=process_armed_before_day,
        initial_symbols=list(INITIAL_SYMBOLS),
        venue=VENUE,
        asset_class=ASSET_CLASS,
        market=MARKET,
        source="BINANCE_FUTURES_BOOKTICKER_WEBSOCKET",
    )
    return record


class AsyncHourlyArchiveBank:
    def __init__(
        self,
        output_root: Path,
        identity: CollectorIdentity,
        archive: ArchiveClientProtocol,
        *,
        symbols: tuple[str, ...] = INITIAL_SYMBOLS,
        queue_maxsize: int = QUEUE_MAXSIZE,
        writer_shutdown_timeout_s: float = WRITER_SHUTDOWN_TIMEOUT_S,
        writer_factory: Any = RawWriter,
    ) -> None:
        if symbols != INITIAL_SYMBOLS:
            raise ValueError("EXP027 symbol set and order are exact")
        self.output_root = output_root
        self.identity = identity
        self.archive = archive
        self.symbols = symbols
        self.queue_maxsize = queue_maxsize
        self.writer_shutdown_timeout_s = writer_shutdown_timeout_s
        self.writer_factory = writer_factory
        self.current_hour: datetime | None = None
        self.sinks: dict[str, AsyncSymbolSink] = {}

    async def open_hour(
        self,
        hour: datetime,
        *,
        wall_ns: int,
        mono_ns: int,
        active_epoch: int | None,
    ) -> None:
        _hour_token(hour)
        if self.sinks:
            raise RuntimeError("hourly bank already has open writers")
        paths = {
            symbol: staging_path(self.output_root, symbol, hour)
            for symbol in self.symbols
        }
        blockers: list[str] = []
        for symbol, path in paths.items():
            if path.exists():
                blockers.append(str(path))
            if manifest_path(self.output_root, symbol, hour).exists():
                blockers.append(str(manifest_path(self.output_root, symbol, hour)))
            if operational_failure_path(self.output_root, symbol, hour).exists():
                blockers.append(
                    str(operational_failure_path(self.output_root, symbol, hour))
                )
        if blockers:
            raise FileExistsError(
                "refusing append/resume/overwrite for hourly partition: "
                + ", ".join(blockers)
            )

        opened: dict[str, RawWriter] = {}
        try:
            for symbol, path in paths.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                opened[symbol] = self.writer_factory(path)
        except Exception:
            for writer in opened.values():
                writer.close()
            raise

        self.sinks = {
            symbol: AsyncSymbolSink(
                symbol,
                opened[symbol],
                maxsize=self.queue_maxsize,
                shutdown_timeout_s=self.writer_shutdown_timeout_s,
            )
            for symbol in self.symbols
        }
        self.current_hour = hour
        for symbol in self.symbols:
            self.emit(
                symbol,
                _hour_started_record(
                    symbol=symbol,
                    hour=hour,
                    identity=self.identity,
                    wall_ns=wall_ns,
                    mono_ns=mono_ns,
                    active_epoch=active_epoch,
                ),
            )

    def emit(self, symbol: str, record: dict[str, Any]) -> None:
        if symbol not in self.sinks:
            raise ValueError(f"no open writer for symbol: {symbol}")
        self.sinks[symbol].emit(record)

    def broadcast(self, record: dict[str, Any]) -> None:
        for symbol in self.symbols:
            self.emit(symbol, dict(record))

    def _write_failure(
        self, symbol: str, hour: datetime, exc: BaseException
    ) -> None:
        path = operational_failure_path(self.output_root, symbol, hour)
        if path.exists():
            return
        _write_once_json(
            path,
            {
                "experiment_id": EXPERIMENT_ID,
                "status": "OPERATIONAL_FAILURE",
                "symbol": symbol,
                "collection_hour_utc": hour.isoformat(),
                "failure_type": type(exc).__name__,
                "failure_message": str(exc),
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                **no_analysis_guards(),
            },
        )

    async def _close_sinks(self) -> None:
        sinks = tuple(self.sinks.values())
        results = await asyncio.gather(
            *(sink.close() for sink in sinks),
            return_exceptions=True,
        )
        failures = [
            result for result in results if isinstance(result, BaseException)
        ]
        if failures:
            raise failures[0]

    async def close_archive_and_delete(self) -> dict[str, ArchiveVerification]:
        if self.current_hour is None or not self.sinks:
            return {}
        hour = self.current_hour
        try:
            await self._close_sinks()
        except BaseException as exc:
            for symbol in self.symbols:
                self._write_failure(symbol, hour, exc)
            raise

        paths = {
            symbol: staging_path(self.output_root, symbol, hour)
            for symbol in self.symbols
        }

        async def one(symbol: str) -> tuple[str, ArchiveVerification]:
            verification = await asyncio.to_thread(
                self.archive.put_verified,
                paths[symbol],
                archive_key(symbol, hour),
            )
            return symbol, verification

        upload_results = await asyncio.gather(
            *(one(symbol) for symbol in self.symbols),
            return_exceptions=True,
        )
        failures = [
            result for result in upload_results if isinstance(result, BaseException)
        ]
        if failures:
            exc = failures[0]
            for symbol in self.symbols:
                self._write_failure(symbol, hour, exc)
            raise exc

        verified = {
            symbol: verification
            for symbol, verification in upload_results
            if isinstance(symbol, str)
        }
        if set(verified) != set(self.symbols):
            exc = ArchiveOperationalError("incomplete archive verification set")
            for symbol in self.symbols:
                self._write_failure(symbol, hour, exc)
            raise exc

        for symbol in self.symbols:
            verification = verified[symbol]
            _write_once_json(
                manifest_path(self.output_root, symbol, hour),
                {
                    "experiment_id": EXPERIMENT_ID,
                    "status": "HOURLY_RAW_ARCHIVE_VERIFIED",
                    "symbol": symbol,
                    "collection_hour_utc": hour.isoformat(),
                    "archive_key": verification.key,
                    "local_bytes": verification.byte_size,
                    "local_sha256": verification.sha256,
                    "remote_bytes": verification.remote_byte_size,
                    "remote_sha256": verification.remote_sha256,
                    "frozen_implementation_commit": (
                        self.identity.frozen_implementation_commit
                    ),
                    "collector_run_id": self.identity.collector_run_id,
                    "archived_at_utc": datetime.now(timezone.utc).isoformat(),
                    **no_analysis_guards(),
                },
            )

        # Delete only after all three symbols have exact verified archive objects
        # and immutable local manifests.
        for symbol in self.symbols:
            paths[symbol].unlink()

        self.sinks = {}
        self.current_hour = None
        return verified

    async def rollover(
        self,
        next_hour: datetime,
        *,
        wall_ns: int,
        mono_ns: int,
        active_epoch: int | None,
    ) -> dict[str, ArchiveVerification]:
        if self.current_hour is None:
            raise RuntimeError("cannot roll over closed hourly bank")
        if next_hour != self.current_hour + timedelta(hours=1):
            raise RuntimeError("hourly rollover must advance exactly one UTC hour")
        self.broadcast(
            _transport_record(
                "hour_rollover",
                active_epoch or 0,
                wall_ns=wall_ns,
                mono_ns=mono_ns,
                completed_hour=self.current_hour.isoformat(),
                next_hour=next_hour.isoformat(),
            )
        )
        verified = await self.close_archive_and_delete()
        await self.open_hour(
            next_hour,
            wall_ns=wall_ns,
            mono_ns=mono_ns,
            active_epoch=active_epoch,
        )
        return verified


async def collect_continuously(
    output_root: Path,
    *,
    frozen_commit: str,
    archive: ArchiveClientProtocol | None = None,
    stop_event: asyncio.Event | None = None,
) -> dict[str, Any]:
    implementation_commit = _full_hex_commit(frozen_commit)
    started_wall_ns = time.time_ns()
    started_mono_ns = time.monotonic_ns()
    identity = CollectorIdentity(
        collector_run_id=str(uuid.uuid4()),
        process_id=os.getpid(),
        frozen_implementation_commit=implementation_commit,
        collector_started_wall_ns=started_wall_ns,
        collector_started_utc=_iso_from_ns(started_wall_ns),
    )
    archive_client = archive or S3ArchiveClient(ArchiveConfig.from_env())
    router = MultiSymbolRouter()
    bank = AsyncHourlyArchiveBank(output_root, identity, archive_client)
    current_hour = floor_utc_hour_from_ns(started_wall_ns)
    await bank.open_hour(
        current_hour,
        wall_ns=started_wall_ns,
        mono_ns=started_mono_ns,
        active_epoch=None,
    )

    epoch = 0
    active_epoch: int | None = None
    archived_hours = 0

    async def advance_hour(wall_ns: int, mono_ns: int) -> None:
        nonlocal archived_hours
        target = floor_utc_hour_from_ns(wall_ns)
        while bank.current_hour is not None and target > bank.current_hour:
            await bank.rollover(
                bank.current_hour + timedelta(hours=1),
                wall_ns=wall_ns,
                mono_ns=mono_ns,
                active_epoch=active_epoch,
            )
            archived_hours += 1
            for state in router.states.values():
                state.latest_quote = None

    try:
        while stop_event is None or not stop_event.is_set():
            epoch += 1
            active_epoch = None
            router.invalidate_all()
            attempt_wall_ns = time.time_ns()
            attempt_mono_ns = time.monotonic_ns()
            await advance_hour(attempt_wall_ns, attempt_mono_ns)
            bank.broadcast(
                _transport_record(
                    "connection_open_attempt",
                    epoch,
                    wall_ns=attempt_wall_ns,
                    mono_ns=attempt_mono_ns,
                    experiment_id=EXPERIMENT_ID,
                )
            )
            try:
                async with websockets.connect(
                    WS_URL,
                    ping_interval=20,
                    ping_timeout=60,
                    open_timeout=20,
                    max_queue=100_000,
                ) as websocket:
                    opened_wall_ns = time.time_ns()
                    opened_mono_ns = time.monotonic_ns()
                    await advance_hour(opened_wall_ns, opened_mono_ns)
                    active_epoch = epoch
                    router.connection_opened(epoch)
                    bank.broadcast(
                        _transport_record(
                            "connection_opened",
                            epoch,
                            wall_ns=opened_wall_ns,
                            mono_ns=opened_mono_ns,
                            experiment_id=EXPERIMENT_ID,
                        )
                    )
                    while stop_event is None or not stop_event.is_set():
                        boundary_wall_ns = time.time_ns()
                        boundary_mono_ns = time.monotonic_ns()
                        await advance_hour(boundary_wall_ns, boundary_mono_ns)
                        try:
                            raw_message = await asyncio.wait_for(
                                websocket.recv(), timeout=1.0
                            )
                        except asyncio.TimeoutError:
                            continue
                        wall_ns = time.time_ns()
                        mono_ns = time.monotonic_ns()
                        await advance_hour(wall_ns, mono_ns)
                        try:
                            payload = _parse_message(raw_message)
                        except Exception:
                            bank.broadcast(
                                _rejected_record(
                                    reason="JSON_PARSE_FAIL",
                                    epoch=epoch,
                                    wall_ns=wall_ns,
                                    mono_ns=mono_ns,
                                    observed_symbol=None,
                                )
                            )
                            continue

                        symbol, record = router.route(
                            payload,
                            epoch=epoch,
                            wall_ns=wall_ns,
                            mono_ns=mono_ns,
                        )
                        if symbol is None:
                            bank.broadcast(record)
                        else:
                            bank.emit(symbol, record)

                    closed_wall_ns = time.time_ns()
                    closed_mono_ns = time.monotonic_ns()
                    await advance_hour(closed_wall_ns, closed_mono_ns)
                    bank.broadcast(
                        _transport_record(
                            "connection_closed",
                            epoch,
                            wall_ns=closed_wall_ns,
                            mono_ns=closed_mono_ns,
                            experiment_id=EXPERIMENT_ID,
                        )
                    )
                    router.invalidate_all()
                    active_epoch = None
            except asyncio.CancelledError:
                raise
            except (AcquisitionOperationalError, ArchiveOperationalError):
                raise
            except Exception as exc:
                error_wall_ns = time.time_ns()
                error_mono_ns = time.monotonic_ns()
                await advance_hour(error_wall_ns, error_mono_ns)
                router.invalidate_all()
                active_epoch = None
                bank.broadcast(
                    _transport_record(
                        "transport_error",
                        epoch,
                        wall_ns=error_wall_ns,
                        mono_ns=error_mono_ns,
                        detail=repr(exc),
                        experiment_id=EXPERIMENT_ID,
                    )
                )
                if stop_event is None or not stop_event.is_set():
                    await asyncio.sleep(2.0)
    finally:
        if bank.sinks:
            if not any(
                sink.operational_failure is not None
                for sink in bank.sinks.values()
            ):
                bank.broadcast(
                    _transport_record(
                        "collector_stopped",
                        active_epoch or epoch,
                        experiment_id=EXPERIMENT_ID,
                    )
                )
            await bank.close_archive_and_delete()

    return {
        "experiment_id": EXPERIMENT_ID,
        "collector_run_id": identity.collector_run_id,
        "frozen_implementation_commit": implementation_commit,
        "symbols": list(INITIAL_SYMBOLS),
        "connection_epochs": epoch,
        "archived_hour_rollovers": archived_hours,
        "unsupported_symbol_rejections": router.unsupported_rejections,
        "network_accessed_for_acquisition": True,
        "bucket_archive_accessed": True,
        **no_analysis_guards(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    args = parser.parse_args(argv)
    implementation_commit = _full_hex_commit(args.frozen_commit)
    result = asyncio.run(
        collect_continuously(
            args.output_root,
            frozen_commit=implementation_commit,
        )
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
