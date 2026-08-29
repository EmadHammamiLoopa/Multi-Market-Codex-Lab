from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from .codex_exp023_p0 import (
    adjudicate_invariants,
    encode_result_payload,
    validate_builtin_bool_invariants,
)
from .codex_exp024_collect import (
    COLLECTION_DAY,
    COLLECTION_END,
    COLLECTION_START,
    PREREGISTRATION_SHA256,
    READINESS_ARTIFACT_SHA256,
    SYMBOL,
    no_analysis_guards,
)


EXPERIMENT_ID = "CODEX-EXP-024-P0"
STATUS_PASS = "PROSPECTIVE_BOOKTICKER_DATA_READY"
STATUS_FAIL = "FAIL_PROSPECTIVE_BOOKTICKER_DATA_INTEGRITY"
STATUS_INVALID = "INVALID"

DAY_START_US = int(COLLECTION_START.timestamp() * 1_000_000)
DAY_END_US = int(COLLECTION_END.timestamp() * 1_000_000)
GRID_US = 250_000
EXPECTED_ROWS = 345_600
MAX_AGE_US = 2_000_000

RAW_DEFAULT = Path("/data/bookticker/BTCUSDT/2026-08-30.jsonl.gz")
GRID_DEFAULT = Path(
    "/data/evidence/codex/exp024_prospective_bookticker/BTCUSDT/"
    "2026-08-30_BOOKTICKER250.csv"
)
GRID_COLUMNS = (
    "local_timestamp_us",
    "best_bid",
    "best_ask",
    "mid",
    "book_valid",
    "quote_age_ms",
    "connection_epoch",
    "source_update_id",
    "exchange_event_time_ms",
    "exchange_transaction_time_ms",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _wall_us(record: dict[str, Any]) -> int:
    return int(record["receive_wall_ns"]) // 1000


def _full_hex_commit(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 40:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _valid_quote_record(record: dict[str, Any]) -> bool:
    if record.get("record_type") != "quote":
        return False
    if record.get("symbol") != SYMBOL:
        return False
    try:
        values = (
            float(record["best_bid"]),
            float(record["best_ask"]),
            float(record["best_bid_qty"]),
            float(record["best_ask_qty"]),
        )
    except (KeyError, TypeError, ValueError):
        return False
    if not all(math.isfinite(value) for value in values):
        return False
    bid, ask, bid_qty, ask_qty = values
    return bid > 0 and ask > bid and bid_qty >= 0 and ask_qty >= 0


def _timeline_sort_key(record: dict[str, Any]) -> tuple[int, int, int]:
    return (
        int(record["receive_wall_ns"]),
        int(record["receive_monotonic_ns"]),
        0 if record.get("record_type") == "transport" else 1,
    )


def _empty_raw_diagnostics() -> dict[str, Any]:
    return {
        "rejected_records": 0,
        "rejected_by_reason": {},
        "transport_records": 0,
        "malformed_transport_records": 0,
        "accepted_quotes": 0,
        "accepted_wall_clock_reversals": 0,
        "accepted_monotonic_clock_reversals": 0,
        "wrong_symbol_accepted": 0,
        "invalid_price_accepted": 0,
        "negative_quantity_accepted": 0,
        "quotes_outside_collection_day_accepted": 0,
        "collector_armed_records": 0,
        "collector_armed_before_utc_midnight": False,
        "collector_metadata_exact": False,
        "frozen_implementation_commit": None,
        "connection_open_attempts": 0,
        "connections_opened": 0,
        "connections_closed": 0,
        "transport_errors": 0,
        "collection_end_records": 0,
        "collection_end_after_day": False,
        "connection_epochs": 0,
    }


def _collector_metadata_exact(record: dict[str, Any]) -> bool:
    return bool(
        record.get("experiment_id") == EXPERIMENT_ID
        and record.get("symbol") == SYMBOL
        and record.get("collection_day") == COLLECTION_DAY.isoformat()
        and record.get("collection_start_utc") == COLLECTION_START.isoformat()
        and record.get("collection_end_utc") == COLLECTION_END.isoformat()
        and record.get("preregistration_sha256") == PREREGISTRATION_SHA256
        and record.get("readiness_artifact_sha256")
        == READINESS_ARTIFACT_SHA256
        and _full_hex_commit(record.get("frozen_implementation_commit"))
    )


class _RawTimeline:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.diagnostics = _empty_raw_diagnostics()
        self.sort_ordered = True
        self._started = False
        self._epochs: set[int] = set()

    def __iter__(self) -> Iterator[dict[str, Any]]:
        if self._started:
            raise RuntimeError("raw timeline stream can only be consumed once")
        self._started = True
        return self._records()

    def _record_rejection(self, record: dict[str, Any]) -> None:
        self.diagnostics["rejected_records"] += 1
        reason = str(record.get("reason", "UNKNOWN"))
        reasons = self.diagnostics["rejected_by_reason"]
        reasons[reason] = int(reasons.get(reason, 0)) + 1

    def _record_transport(self, record: dict[str, Any]) -> bool:
        self.diagnostics["transport_records"] += 1
        if not (
            "receive_wall_ns" in record
            and "receive_monotonic_ns" in record
        ):
            self.diagnostics["malformed_transport_records"] += 1
            return False

        event = str(record.get("event", ""))
        epoch = int(record.get("connection_epoch", 0))
        if epoch > 0:
            self._epochs.add(epoch)
        wall_us = _wall_us(record)

        if event == "collector_armed":
            self.diagnostics["collector_armed_records"] += 1
            armed_before = wall_us < DAY_START_US
            exact = _collector_metadata_exact(record)
            if self.diagnostics["collector_armed_records"] == 1:
                self.diagnostics["collector_armed_before_utc_midnight"] = bool(
                    armed_before
                )
                self.diagnostics["collector_metadata_exact"] = bool(exact)
                self.diagnostics["frozen_implementation_commit"] = record.get(
                    "frozen_implementation_commit"
                )
            else:
                self.diagnostics["collector_armed_before_utc_midnight"] = False
                self.diagnostics["collector_metadata_exact"] = False
        elif event == "connection_open_attempt":
            self.diagnostics["connection_open_attempts"] += 1
        elif event == "connection_opened":
            self.diagnostics["connections_opened"] += 1
        elif event == "connection_closed":
            self.diagnostics["connections_closed"] += 1
        elif event == "transport_error":
            self.diagnostics["transport_errors"] += 1
        elif event == "collection_end":
            self.diagnostics["collection_end_records"] += 1
            if wall_us >= DAY_END_US:
                self.diagnostics["collection_end_after_day"] = True
        return True

    def _record_quote(
        self,
        record: dict[str, Any],
        last_wall: int | None,
        last_mono: int | None,
    ) -> tuple[int, int]:
        wall = int(record["receive_wall_ns"])
        mono = int(record["receive_monotonic_ns"])
        wall_us = wall // 1000
        if last_wall is not None and wall < last_wall:
            self.diagnostics["accepted_wall_clock_reversals"] += 1
        if last_mono is not None and mono < last_mono:
            self.diagnostics["accepted_monotonic_clock_reversals"] += 1
        if not (DAY_START_US <= wall_us < DAY_END_US):
            self.diagnostics["quotes_outside_collection_day_accepted"] += 1

        epoch = int(record.get("connection_epoch", 0))
        if epoch > 0:
            self._epochs.add(epoch)
        if record.get("symbol") != SYMBOL:
            self.diagnostics["wrong_symbol_accepted"] += 1

        try:
            bid = float(record["best_bid"])
            ask = float(record["best_ask"])
            bid_qty = float(record["best_bid_qty"])
            ask_qty = float(record["best_ask_qty"])
        except (KeyError, TypeError, ValueError):
            bid = ask = bid_qty = ask_qty = float("nan")

        if not (math.isfinite(bid) and math.isfinite(ask)) or not (
            bid > 0 and ask > bid
        ):
            self.diagnostics["invalid_price_accepted"] += 1
        if not (math.isfinite(bid_qty) and math.isfinite(ask_qty)) or (
            bid_qty < 0 or ask_qty < 0
        ):
            self.diagnostics["negative_quantity_accepted"] += 1
        self.diagnostics["accepted_quotes"] += 1
        return wall, mono

    def _records(self) -> Iterator[dict[str, Any]]:
        last_wall: int | None = None
        last_mono: int | None = None
        last_sort_key: tuple[int, int, int] | None = None

        with gzip.open(self.path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                record_type = record.get("record_type")
                if record_type == "rejected":
                    self._record_rejection(record)
                    continue
                if record_type == "transport":
                    if not self._record_transport(record):
                        continue
                elif record_type == "quote":
                    last_wall, last_mono = self._record_quote(
                        record,
                        last_wall,
                        last_mono,
                    )
                else:
                    continue

                sort_key = _timeline_sort_key(record)
                if last_sort_key is not None and sort_key < last_sort_key:
                    self.sort_ordered = False
                last_sort_key = sort_key
                yield record

        self.diagnostics["connection_epochs"] = len(self._epochs)


def load_raw(path: Path) -> tuple[_RawTimeline, dict[str, Any]]:
    timeline = _RawTimeline(path)
    return timeline, timeline.diagnostics


class _TimelineOutOfOrder(RuntimeError):
    pass


def _raw_timeline_records(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("record_type") == "transport":
                if (
                    "receive_wall_ns" in record
                    and "receive_monotonic_ns" in record
                ):
                    yield record
            elif record.get("record_type") == "quote":
                yield record


def _externally_sorted_timeline(
    path: Path,
    scratch_dir: Path,
) -> Iterator[dict[str, Any]]:
    with tempfile.TemporaryDirectory(
        prefix=".codex-exp024-sort-",
        dir=scratch_dir,
    ) as temp_dir:
        database_path = Path(temp_dir) / "timeline.sqlite3"
        connection = sqlite3.connect(database_path)
        try:
            connection.execute("PRAGMA journal_mode = OFF")
            connection.execute("PRAGMA synchronous = OFF")
            connection.execute("PRAGMA temp_store = FILE")
            connection.execute("PRAGMA cache_size = -8192")
            connection.execute(
                """
                CREATE TABLE timeline (
                    wall_ns INTEGER NOT NULL,
                    monotonic_ns INTEGER NOT NULL,
                    type_rank INTEGER NOT NULL,
                    sequence INTEGER NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            batch: list[tuple[int, int, int, int, str]] = []
            for sequence, record in enumerate(_raw_timeline_records(path)):
                wall_ns, monotonic_ns, type_rank = _timeline_sort_key(record)
                batch.append(
                    (
                        wall_ns,
                        monotonic_ns,
                        type_rank,
                        sequence,
                        json.dumps(record, separators=(",", ":")),
                    )
                )
                if len(batch) == 4096:
                    connection.executemany(
                        "INSERT INTO timeline VALUES (?, ?, ?, ?, ?)", batch
                    )
                    batch.clear()
            if batch:
                connection.executemany(
                    "INSERT INTO timeline VALUES (?, ?, ?, ?, ?)", batch
                )
            connection.commit()
            cursor = connection.execute(
                """
                SELECT payload
                FROM timeline
                ORDER BY wall_ns, monotonic_ns, type_rank, sequence
                """
            )
            for (payload,) in cursor:
                yield json.loads(payload)
        finally:
            connection.close()


def _apply_timeline_event(
    latest: dict[str, Any] | None,
    active_epoch: int | None,
    event: dict[str, Any],
) -> tuple[dict[str, Any] | None, int | None]:
    if event.get("record_type") == "transport":
        event_name = str(event.get("event", ""))
        epoch = int(event.get("connection_epoch", 0))
        if event_name in {
            "connection_open_attempt",
            "connection_opened",
            "connection_closed",
            "transport_error",
            "collection_end",
        }:
            latest = None
        if event_name == "connection_opened":
            active_epoch = epoch
        elif event_name in {
            "connection_closed",
            "transport_error",
            "collection_end",
        }:
            active_epoch = None
    elif event.get("record_type") == "quote":
        epoch = int(event["connection_epoch"])
        if active_epoch == epoch:
            latest = event
    return latest, active_epoch


def build_grid(
    timeline: Iterable[dict[str, Any]],
    output: Path,
) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    if output.exists() or temporary.exists():
        raise FileExistsError("EXP024 grid or partial output already exists")

    event_iterator = iter(timeline)
    event = next(event_iterator, None)
    latest: dict[str, Any] | None = None
    active_epoch: int | None = None
    valid_rows = 0
    future_quote_violations = 0
    stale_rows = 0
    reconnect_invalid_rows = 0

    with temporary.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(GRID_COLUMNS)
        for index in range(EXPECTED_ROWS):
            timestamp_us = DAY_START_US + index * GRID_US
            while event is not None:
                if _wall_us(event) > timestamp_us:
                    break
                latest, active_epoch = _apply_timeline_event(
                    latest,
                    active_epoch,
                    event,
                )
                event = next(event_iterator, None)

            valid = False
            bid = ask = mid = float("nan")
            age_ms = float("nan")
            epoch: int | str = ""
            update_id: Any = ""
            event_ms: Any = ""
            transaction_ms: Any = ""

            if latest is None and active_epoch is not None:
                reconnect_invalid_rows += 1
            if latest is not None:
                quote_us = _wall_us(latest)
                if quote_us > timestamp_us:
                    future_quote_violations += 1
                else:
                    age_us = timestamp_us - quote_us
                    age_ms = age_us / 1000.0
                    if age_us <= MAX_AGE_US and _valid_quote_record(latest):
                        valid = True
                        bid = float(latest["best_bid"])
                        ask = float(latest["best_ask"])
                        mid = (bid + ask) / 2.0
                        epoch = int(latest["connection_epoch"])
                        update_id = latest.get("update_id", "")
                        event_ms = latest.get("exchange_event_time_ms", "")
                        transaction_ms = latest.get(
                            "exchange_transaction_time_ms", ""
                        )
                        valid_rows += 1
                    else:
                        stale_rows += 1

            writer.writerow(
                [
                    timestamp_us,
                    bid,
                    ask,
                    mid,
                    1 if valid else 0,
                    age_ms,
                    epoch,
                    update_id,
                    event_ms,
                    transaction_ms,
                ]
            )

    for _ in event_iterator:
        pass

    if isinstance(timeline, _RawTimeline) and not timeline.sort_ordered:
        temporary.unlink()
        raise _TimelineOutOfOrder

    temporary.replace(output)
    return {
        "rows": EXPECTED_ROWS,
        "valid_rows": valid_rows,
        "valid_coverage": valid_rows / EXPECTED_ROWS,
        "future_quote_violations": future_quote_violations,
        "stale_or_unavailable_rows": stale_rows,
        "reconnect_invalid_rows": reconnect_invalid_rows,
        "first_timestamp_us": DAY_START_US,
        "last_timestamp_us": DAY_START_US + (EXPECTED_ROWS - 1) * GRID_US,
        "grid_step_us": GRID_US,
    }


def stream_raw_to_grid(
    raw: Path,
    grid: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    timeline, raw_diagnostics = load_raw(raw)
    try:
        grid_diagnostics = build_grid(timeline, grid)
    except _TimelineOutOfOrder:
        grid_diagnostics = build_grid(
            _externally_sorted_timeline(raw, grid.parent),
            grid,
        )
    return raw_diagnostics, grid_diagnostics


def _fresh_outputs(grid: Path, audit: Path) -> None:
    for path, label in ((grid, "grid"), (audit, "audit")):
        part = path.with_suffix(path.suffix + ".part")
        if path.exists() or part.exists():
            raise FileExistsError(f"EXP024 {label} or partial output already exists")


def _write_audit_once(audit: Path, payload: dict[str, Any]) -> None:
    part = audit.with_suffix(audit.suffix + ".part")
    if audit.exists() or part.exists():
        raise FileExistsError("EXP024 audit or partial output already exists")
    encoded = encode_result_payload(payload)
    audit.parent.mkdir(parents=True, exist_ok=True)
    with part.open("x", encoding="utf-8") as handle:
        handle.write(encoded)
    if audit.exists():
        raise FileExistsError("EXP024 audit appeared during finalization")
    part.replace(audit)


def _integrity_gates(
    raw: Path,
    raw_diagnostics: dict[str, Any],
    grid_diagnostics: dict[str, Any],
    raw_sha256: str,
    grid_sha256: str,
    grid: Path,
) -> dict[str, bool]:
    guards = no_analysis_guards()
    gates = {
        "raw_file_nonempty": bool(raw.stat().st_size > 0),
        "grid_rows_exact_345600": bool(
            grid_diagnostics["rows"] == EXPECTED_ROWS
        ),
        "grid_step_exact_250000us": bool(
            grid_diagnostics["grid_step_us"] == GRID_US
        ),
        "first_timestamp_exact": bool(
            grid_diagnostics["first_timestamp_us"] == DAY_START_US
        ),
        "last_timestamp_exact": bool(
            grid_diagnostics["last_timestamp_us"]
            == DAY_START_US + (EXPECTED_ROWS - 1) * GRID_US
        ),
        "valid_coverage_at_least_0_99": bool(
            grid_diagnostics["valid_coverage"] >= 0.99
        ),
        "no_invalid_crossed_price_accepted": bool(
            raw_diagnostics["invalid_price_accepted"] == 0
        ),
        "no_negative_quantity_accepted": bool(
            raw_diagnostics["negative_quantity_accepted"] == 0
        ),
        "no_accepted_wall_clock_reversal": bool(
            raw_diagnostics["accepted_wall_clock_reversals"] == 0
        ),
        "no_accepted_monotonic_clock_reversal": bool(
            raw_diagnostics["accepted_monotonic_clock_reversals"] == 0
        ),
        "no_other_symbol_accepted": bool(
            raw_diagnostics["wrong_symbol_accepted"] == 0
        ),
        "no_future_quote_used": bool(
            grid_diagnostics["future_quote_violations"] == 0
        ),
        "raw_sha_recorded": bool(len(raw_sha256) == 64),
        "grid_sha_recorded": bool(len(grid_sha256) == 64),
        "raw_bytes_recorded": bool(raw.stat().st_size > 0),
        "grid_bytes_recorded": bool(grid.stat().st_size > 0),
        "collector_armed_before_utc_midnight": bool(
            raw_diagnostics["collector_armed_records"] == 1
            and raw_diagnostics["collector_armed_before_utc_midnight"]
        ),
        "collector_metadata_exact": bool(
            raw_diagnostics["collector_metadata_exact"]
        ),
        "at_least_one_connection_attempt": bool(
            raw_diagnostics["connection_open_attempts"] >= 1
        ),
        "collection_end_recorded_after_day": bool(
            raw_diagnostics["collection_end_records"] == 1
            and raw_diagnostics["collection_end_after_day"]
        ),
        "no_quote_outside_collection_day_accepted": bool(
            raw_diagnostics["quotes_outside_collection_day_accepted"] == 0
        ),
        "no_malformed_transport_record": bool(
            raw_diagnostics["malformed_transport_records"] == 0
        ),
        **guards,
    }
    return validate_builtin_bool_invariants(gates)


def run(raw: Path, grid: Path, audit: Path) -> dict[str, Any]:
    if _utc_now() < COLLECTION_END:
        raise RuntimeError("cannot finalize EXP024 before 2026-08-31T00:00:00Z")
    if not raw.is_file() or raw.stat().st_size == 0:
        raise RuntimeError("raw prospective file missing or empty")
    _fresh_outputs(grid, audit)

    raw_diagnostics, grid_diagnostics = stream_raw_to_grid(raw, grid)
    raw_sha256 = sha256_file(raw)
    grid_sha256 = sha256_file(grid)
    gates = _integrity_gates(
        raw,
        raw_diagnostics,
        grid_diagnostics,
        raw_sha256,
        grid_sha256,
        grid,
    )
    expected = {
        name: not name
        in {
            "older_august_holdout_opened",
            "historical_aug1_feature_reparsed",
            "target_scored",
            "model_fit",
            "auc_scored",
            "direction_scored",
            "pnl_scored",
            "leverage_scored",
        }
        for name in gates
    }
    integrity_pass = adjudicate_invariants(gates, expected=expected)
    guards = no_analysis_guards()

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "status": STATUS_PASS if integrity_pass else STATUS_FAIL,
        "scope": "DATA_ACQUISITION_AND_INTEGRITY_ONLY",
        "collection_day": COLLECTION_DAY.isoformat(),
        "symbol": SYMBOL,
        "frozen_implementation_commit": raw_diagnostics[
            "frozen_implementation_commit"
        ],
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "readiness_artifact_sha256": READINESS_ARTIFACT_SHA256,
        "raw_path": str(raw),
        "grid_path": str(grid),
        "raw_bytes": int(raw.stat().st_size),
        "grid_bytes": int(grid.stat().st_size),
        "raw_sha256": raw_sha256,
        "grid_sha256": grid_sha256,
        "raw_diagnostics": raw_diagnostics,
        "grid_diagnostics": grid_diagnostics,
        "integrity_gates": gates,
        "network_accessed_for_acquisition": True,
        "predictive_metrics_calculated": False,
        **guards,
    }
    _write_audit_once(audit, payload)
    return payload


def invalid_payload(exc: Exception) -> dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "status": STATUS_INVALID,
        "scope": "DATA_ACQUISITION_AND_INTEGRITY_ONLY",
        "failure_type": type(exc).__name__,
        "failure_message": str(exc),
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "readiness_artifact_sha256": READINESS_ARTIFACT_SHA256,
        "predictive_metrics_calculated": False,
        **no_analysis_guards(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=RAW_DEFAULT)
    parser.add_argument("--grid", type=Path, default=GRID_DEFAULT)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.audit.exists() or args.audit.with_suffix(
        args.audit.suffix + ".part"
    ).exists():
        raise SystemExit("EXP024 audit output exists; refusing to overwrite")

    try:
        result = run(args.raw, args.grid, args.audit)
    except Exception as exc:
        result = invalid_payload(exc)
        _write_audit_once(args.audit, result)

    print(encode_result_payload(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
