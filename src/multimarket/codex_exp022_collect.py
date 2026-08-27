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


EXPERIMENT_ID = "CODEX-EXP-022-P0"
SYMBOL = "BTCUSDT"
COLLECTION_DAY = date(2026, 8, 28)
WS_URL = (
    "wss://fstream.binance.com/stream?streams="
    "btcusdt@bookTicker"
)
RAW_REL = Path(
    "bookticker/BTCUSDT/2026-08-28.jsonl.gz"
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_from_ns(ns: int) -> str:
    return datetime.fromtimestamp(
        ns / 1_000_000_000,
        tz=timezone.utc,
    ).isoformat(timespec="microseconds")


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
            mode="at",
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
    vals = (bid, ask, bid_qty, ask_qty)
    if not all(math.isfinite(x) for x in vals):
        return False, "NONFINITE"
    if bid <= 0 or ask <= 0 or ask <= bid:
        return False, "INVALID_OR_CROSSED_PRICE"
    if bid_qty < 0 or ask_qty < 0:
        return False, "NEGATIVE_QUANTITY"
    return True, None


async def collect(
    output_root: Path,
    start_utc: datetime,
    end_utc: datetime,
) -> dict[str, Any]:
    raw_path = output_root / RAW_REL
    writer = RawWriter(raw_path)
    state = CollectorState()

    try:
        while _utc_now() < end_utc:
            if _utc_now() < start_utc:
                await asyncio.sleep(
                    min(
                        30.0,
                        max(
                            0.1,
                            (start_utc - _utc_now()).total_seconds(),
                        ),
                    )
                )
                continue

            state.epoch += 1
            epoch = state.epoch
            opened_wall = time.time_ns()
            opened_mono = time.monotonic_ns()
            writer.write(
                {
                    "record_type": "transport",
                    "event": "connection_open_attempt",
                    "connection_epoch": epoch,
                    "receive_wall_ns": opened_wall,
                    "receive_wall_utc": _iso_from_ns(opened_wall),
                    "receive_monotonic_ns": opened_mono,
                }
            )
            state.transport_events += 1

            try:
                async with websockets.connect(
                    WS_URL,
                    ping_interval=20,
                    ping_timeout=60,
                    open_timeout=20,
                    max_queue=100_000,
                ) as ws:
                    wall = time.time_ns()
                    mono = time.monotonic_ns()
                    writer.write(
                        {
                            "record_type": "transport",
                            "event": "connection_opened",
                            "connection_epoch": epoch,
                            "receive_wall_ns": wall,
                            "receive_wall_utc": _iso_from_ns(wall),
                            "receive_monotonic_ns": mono,
                        }
                    )
                    state.transport_events += 1

                    async for raw in ws:
                        wall_ns = time.time_ns()
                        mono_ns = time.monotonic_ns()

                        if _utc_now() >= end_utc:
                            break

                        try:
                            envelope = json.loads(raw)
                            payload = envelope.get("data", envelope)
                        except Exception:
                            state.rejected_quotes += 1
                            writer.write(
                                {
                                    "record_type": "rejected",
                                    "reason": "JSON_PARSE_FAIL",
                                    "connection_epoch": epoch,
                                    "receive_wall_ns": wall_ns,
                                    "receive_wall_utc": _iso_from_ns(wall_ns),
                                    "receive_monotonic_ns": mono_ns,
                                }
                            )
                            continue

                        if (
                            state.last_wall_ns is not None
                            and wall_ns < state.last_wall_ns
                        ):
                            state.rejected_quotes += 1
                            writer.write(
                                {
                                    "record_type": "rejected",
                                    "reason": "WALL_CLOCK_REVERSAL",
                                    "connection_epoch": epoch,
                                    "receive_wall_ns": wall_ns,
                                    "receive_wall_utc": _iso_from_ns(wall_ns),
                                    "receive_monotonic_ns": mono_ns,
                                }
                            )
                            continue

                        if (
                            state.last_mono_ns is not None
                            and mono_ns < state.last_mono_ns
                        ):
                            state.rejected_quotes += 1
                            writer.write(
                                {
                                    "record_type": "rejected",
                                    "reason": "MONOTONIC_CLOCK_REVERSAL",
                                    "connection_epoch": epoch,
                                    "receive_wall_ns": wall_ns,
                                    "receive_wall_utc": _iso_from_ns(wall_ns),
                                    "receive_monotonic_ns": mono_ns,
                                }
                            )
                            continue

                        valid, reason = _validate_payload(payload)
                        if not valid:
                            state.rejected_quotes += 1
                            writer.write(
                                {
                                    "record_type": "rejected",
                                    "reason": reason,
                                    "connection_epoch": epoch,
                                    "receive_wall_ns": wall_ns,
                                    "receive_wall_utc": _iso_from_ns(wall_ns),
                                    "receive_monotonic_ns": mono_ns,
                                    "payload": payload,
                                }
                            )
                            continue

                        state.last_wall_ns = wall_ns
                        state.last_mono_ns = mono_ns
                        state.accepted_quotes += 1

                        writer.write(
                            {
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
                        )

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                wall = time.time_ns()
                mono = time.monotonic_ns()
                writer.write(
                    {
                        "record_type": "transport",
                        "event": "transport_error",
                        "connection_epoch": epoch,
                        "receive_wall_ns": wall,
                        "receive_wall_utc": _iso_from_ns(wall),
                        "receive_monotonic_ns": mono,
                        "detail": repr(exc),
                    }
                )
                state.transport_events += 1
                if _utc_now() < end_utc:
                    await asyncio.sleep(2.0)

        wall = time.time_ns()
        mono = time.monotonic_ns()
        writer.write(
            {
                "record_type": "transport",
                "event": "collection_end",
                "connection_epoch": state.epoch,
                "receive_wall_ns": wall,
                "receive_wall_utc": _iso_from_ns(wall),
                "receive_monotonic_ns": mono,
            }
        )
        state.transport_events += 1
    finally:
        writer.close()

    return {
        "experiment_id": EXPERIMENT_ID,
        "symbol": SYMBOL,
        "collection_day": COLLECTION_DAY.isoformat(),
        "raw_path": str(raw_path),
        "accepted_quotes": state.accepted_quotes,
        "rejected_quotes": state.rejected_quotes,
        "transport_events": state.transport_events,
        "connection_epochs": state.epoch,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--output-root",
        type=Path,
        default=Path("/home/emadh/Multi-Market/data/codex_exp022"),
    )
    a = p.parse_args(argv)

    start = datetime(
        2026, 8, 28, 0, 0, 0,
        tzinfo=timezone.utc,
    )
    end = datetime(
        2026, 8, 29, 0, 0, 0,
        tzinfo=timezone.utc,
    )

    now = _utc_now()
    if now >= end:
        raise SystemExit("prospective collection day has already ended")

    result = asyncio.run(
        collect(
            a.output_root,
            start,
            end,
        )
    )
    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
