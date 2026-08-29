from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import math
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import websockets


EXPERIMENT_ID = "CODEX-EXP-024-P0"
SYMBOL = "BTCUSDT"
COLLECTION_DAY = date(2026, 8, 30)
COLLECTION_START = datetime(2026, 8, 30, tzinfo=timezone.utc)
COLLECTION_END = datetime(2026, 8, 31, tzinfo=timezone.utc)
PREREGISTRATION_SHA256 = (
    "1630ab4591b20a26640a45c980b28b788516434110795d5d406f0189d92a6bd2"
)
READINESS_ARTIFACT_SHA256 = (
    "4eaf158b2517cf6c0be2efc2e7026a73a6b9986977d2c78499bb5785f142c1af"
)
WS_URL = "wss://fstream.binance.com/stream?streams=btcusdt@bookTicker"
RAW_REL = Path("bookticker/BTCUSDT/2026-08-30.jsonl.gz")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_from_ns(ns: int) -> str:
    return datetime.fromtimestamp(
        ns / 1_000_000_000,
        tz=timezone.utc,
    ).isoformat(timespec="microseconds")


def _full_hex_commit(value: str) -> str:
    if len(value) != 40:
        raise ValueError("full 40-character frozen implementation commit required")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError("frozen implementation commit must be hexadecimal") from exc
    return value.lower()


def no_analysis_guards() -> dict[str, bool]:
    return {
        "older_august_holdout_opened": False,
        "historical_aug1_feature_reparsed": False,
        "target_scored": False,
        "model_fit": False,
        "auc_scored": False,
        "direction_scored": False,
        "pnl_scored": False,
        "leverage_scored": False,
    }


@dataclass
class CollectorState:
    epoch: int = 0
    accepted_quotes: int = 0
    rejected_quotes: int = 0
    transport_events: int = 0
    last_wall_ns: int | None = None
    last_mono_ns: int | None = None


class RawWriter:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.handle = gzip.open(
            path,
            mode="xt",
            encoding="utf-8",
            compresslevel=3,
        )

    def write(self, record: dict[str, Any]) -> None:
        self.handle.write(
            json.dumps(
                record,
                separators=(",", ":"),
                sort_keys=True,
                allow_nan=False,
            )
            + "\n"
        )
        self.handle.flush()

    def close(self) -> None:
        self.handle.close()


def _validate_payload(payload: dict[str, Any]) -> tuple[bool, str | None]:
    if str(payload.get("s", "")).upper() != SYMBOL:
        return False, "WRONG_SYMBOL"
    try:
        bid = float(payload["b"])
        ask = float(payload["a"])
        bid_qty = float(payload["B"])
        ask_qty = float(payload["A"])
    except Exception:
        return False, "PARSE_FAIL"
    values = (bid, ask, bid_qty, ask_qty)
    if not all(math.isfinite(value) for value in values):
        return False, "NONFINITE"
    if bid <= 0 or ask <= 0 or ask <= bid:
        return False, "INVALID_OR_CROSSED_PRICE"
    if bid_qty < 0 or ask_qty < 0:
        return False, "NEGATIVE_QUANTITY"
    return True, None


def _rejected_record(
    *,
    reason: str,
    epoch: int,
    wall_ns: int,
    mono_ns: int,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "record_type": "rejected",
        "reason": reason,
        "connection_epoch": epoch,
        "receive_wall_ns": wall_ns,
        "receive_wall_utc": _iso_from_ns(wall_ns),
        "receive_monotonic_ns": mono_ns,
    }
    if payload is not None:
        record["payload"] = payload
    return record


def process_quote_payload(
    state: CollectorState,
    payload: dict[str, Any],
    *,
    epoch: int,
    wall_ns: int,
    mono_ns: int,
) -> dict[str, Any]:
    if state.last_wall_ns is not None and wall_ns < state.last_wall_ns:
        state.rejected_quotes += 1
        return _rejected_record(
            reason="WALL_CLOCK_REVERSAL",
            epoch=epoch,
            wall_ns=wall_ns,
            mono_ns=mono_ns,
        )
    if state.last_mono_ns is not None and mono_ns < state.last_mono_ns:
        state.rejected_quotes += 1
        return _rejected_record(
            reason="MONOTONIC_CLOCK_REVERSAL",
            epoch=epoch,
            wall_ns=wall_ns,
            mono_ns=mono_ns,
        )

    valid, reason = _validate_payload(payload)
    if not valid:
        state.rejected_quotes += 1
        return _rejected_record(
            reason=str(reason),
            epoch=epoch,
            wall_ns=wall_ns,
            mono_ns=mono_ns,
            payload=payload,
        )

    state.last_wall_ns = wall_ns
    state.last_mono_ns = mono_ns
    state.accepted_quotes += 1
    return {
        "record_type": "quote",
        "connection_epoch": epoch,
        "receive_wall_ns": wall_ns,
        "receive_wall_utc": _iso_from_ns(wall_ns),
        "receive_monotonic_ns": mono_ns,
        "exchange_event_time_ms": payload.get("E"),
        "exchange_transaction_time_ms": payload.get("T"),
        "update_id": payload.get("u"),
        "symbol": str(payload["s"]).upper(),
        "best_bid": float(payload["b"]),
        "best_bid_qty": float(payload["B"]),
        "best_ask": float(payload["a"]),
        "best_ask_qty": float(payload["A"]),
    }


def _transport_record(
    event: str,
    epoch: int,
    *,
    wall_ns: int | None = None,
    mono_ns: int | None = None,
    **extra: Any,
) -> dict[str, Any]:
    wall = time.time_ns() if wall_ns is None else wall_ns
    mono = time.monotonic_ns() if mono_ns is None else mono_ns
    return {
        "record_type": "transport",
        "event": event,
        "connection_epoch": epoch,
        "receive_wall_ns": wall,
        "receive_wall_utc": _iso_from_ns(wall),
        "receive_monotonic_ns": mono,
        **extra,
    }


def _validate_collection_window(start_utc: datetime, end_utc: datetime) -> None:
    if start_utc != COLLECTION_START or end_utc != COLLECTION_END:
        raise ValueError("EXP024-P0 collection window is frozen to 2026-08-30 UTC")


async def collect(
    output_root: Path,
    start_utc: datetime,
    end_utc: datetime,
    *,
    frozen_commit: str,
) -> dict[str, Any]:
    _validate_collection_window(start_utc, end_utc)
    implementation_commit = _full_hex_commit(frozen_commit)
    raw_path = output_root / RAW_REL
    if raw_path.exists():
        raise FileExistsError(
            "EXP024 raw output already exists; preserve it and do not resume"
        )

    armed_wall_ns = time.time_ns()
    armed_mono_ns = time.monotonic_ns()
    if armed_wall_ns >= int(start_utc.timestamp() * 1_000_000_000):
        raise RuntimeError(
            "collector was not armed before 2026-08-30T00:00:00Z"
        )

    writer = RawWriter(raw_path)
    state = CollectorState()
    writer.write(
        _transport_record(
            "collector_armed",
            0,
            wall_ns=armed_wall_ns,
            mono_ns=armed_mono_ns,
            experiment_id=EXPERIMENT_ID,
            symbol=SYMBOL,
            collection_day=COLLECTION_DAY.isoformat(),
            collection_start_utc=COLLECTION_START.isoformat(),
            collection_end_utc=COLLECTION_END.isoformat(),
            frozen_implementation_commit=implementation_commit,
            preregistration_sha256=PREREGISTRATION_SHA256,
            readiness_artifact_sha256=READINESS_ARTIFACT_SHA256,
        )
    )
    state.transport_events += 1

    try:
        while _utc_now() < end_utc:
            if _utc_now() < start_utc:
                await asyncio.sleep(
                    min(
                        30.0,
                        max(0.1, (start_utc - _utc_now()).total_seconds()),
                    )
                )
                continue

            state.epoch += 1
            epoch = state.epoch
            writer.write(_transport_record("connection_open_attempt", epoch))
            state.transport_events += 1

            try:
                async with websockets.connect(
                    WS_URL,
                    ping_interval=20,
                    ping_timeout=60,
                    open_timeout=20,
                    max_queue=100_000,
                ) as websocket:
                    writer.write(_transport_record("connection_opened", epoch))
                    state.transport_events += 1

                    async for raw_message in websocket:
                        wall_ns = time.time_ns()
                        mono_ns = time.monotonic_ns()
                        now = _utc_now()
                        if now >= end_utc:
                            break
                        if now < start_utc:
                            continue

                        try:
                            envelope = json.loads(raw_message)
                            payload = envelope.get("data", envelope)
                            if not isinstance(payload, dict):
                                raise TypeError("bookTicker payload is not an object")
                        except Exception:
                            state.rejected_quotes += 1
                            writer.write(
                                _rejected_record(
                                    reason="JSON_PARSE_FAIL",
                                    epoch=epoch,
                                    wall_ns=wall_ns,
                                    mono_ns=mono_ns,
                                )
                            )
                            continue

                        writer.write(
                            process_quote_payload(
                                state,
                                payload,
                                epoch=epoch,
                                wall_ns=wall_ns,
                                mono_ns=mono_ns,
                            )
                        )

                    writer.write(_transport_record("connection_closed", epoch))
                    state.transport_events += 1

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                writer.write(
                    _transport_record(
                        "transport_error",
                        epoch,
                        detail=repr(exc),
                    )
                )
                state.transport_events += 1
                if _utc_now() < end_utc:
                    await asyncio.sleep(2.0)

        writer.write(_transport_record("collection_end", state.epoch))
        state.transport_events += 1
    finally:
        writer.close()

    return {
        "experiment_id": EXPERIMENT_ID,
        "symbol": SYMBOL,
        "collection_day": COLLECTION_DAY.isoformat(),
        "raw_path": str(raw_path),
        "frozen_implementation_commit": implementation_commit,
        "collector_armed_before_utc_midnight": True,
        "accepted_quotes": state.accepted_quotes,
        "rejected_quotes": state.rejected_quotes,
        "transport_events": state.transport_events,
        "connection_epochs": state.epoch,
        **no_analysis_guards(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    args = parser.parse_args(argv)

    implementation_commit = _full_hex_commit(args.frozen_commit)
    now = _utc_now()
    if now >= COLLECTION_START:
        raise SystemExit(
            "missed EXP024 arming deadline; use a newly frozen future UTC day"
        )

    raw_path = args.output_root / RAW_REL
    if raw_path.exists():
        raise SystemExit(
            "EXP024 raw output exists; preserve it and do not restart or merge"
        )

    result = asyncio.run(
        collect(
            args.output_root,
            COLLECTION_START,
            COLLECTION_END,
            frozen_commit=implementation_commit,
        )
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
