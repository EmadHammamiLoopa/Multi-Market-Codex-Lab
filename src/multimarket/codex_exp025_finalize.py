from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import sqlite3
import tempfile
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from .codex_exp025_collect import (
    ASSET_CLASS,
    EXPERIMENT_ID,
    INITIAL_SYMBOLS,
    MARKET,
    SUPPORTED_SYMBOLS,
    VENUE,
    no_analysis_guards,
    operational_failure_path,
)


STATUS_FULL = "FULL_DAY_DATA_READY"
STATUS_PARTIAL = "PARTIAL_START_DAY"
STATUS_FAIL = "FAIL_DATA_INTEGRITY"
STATUS_INVALID = "INVALID"

GRID_US = 250_000
EXPECTED_ROWS = 345_600
MAX_AGE_US = 2_000_000
MIN_VALID_COVERAGE = 0.99
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
INVENTORY_FIELDS = (
    "experiment_id",
    "market",
    "venue",
    "asset_class",
    "symbol",
    "day",
    "status",
    "raw_path",
    "raw_sha256",
    "raw_bytes",
    "grid_path",
    "grid_sha256",
    "grid_bytes",
    "coverage",
    "frozen_collector_commit",
    "collector_run_id",
    "created_at",
)
FORBIDDEN_INVENTORY_FIELDS = frozenset(
    {
        "feature",
        "features",
        "target",
        "targets",
        "label",
        "labels",
        "auc",
        "roc_auc",
        "ap",
        "average_precision",
        "future_return",
        "future_returns",
        "direction",
        "pnl",
        "leverage",
        "strategy_score",
        "model_probability",
    }
)


def validate_builtin_bool_invariants(
    invariants: Mapping[str, Any],
) -> dict[str, bool]:
    if not isinstance(invariants, Mapping):
        raise TypeError("invariants must be a mapping")
    checked: dict[str, bool] = {}
    for name, value in invariants.items():
        if type(name) is not str or type(value) is not bool:
            raise TypeError("every invariant must map a string to built-in bool")
        checked[name] = value
    return checked


def adjudicate_invariants(
    invariants: Mapping[str, Any],
    *,
    expected: Mapping[str, Any],
) -> bool:
    checked = validate_builtin_bool_invariants(invariants)
    expectations = validate_builtin_bool_invariants(expected)
    if checked.keys() != expectations.keys():
        raise TypeError("invariant and expectation names differ")
    return bool(
        all(checked[name] == expectations[name] for name in checked)
    )


def _normalize_json(value: Any, *, location: str = "$") -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise TypeError(f"non-finite JSON float at {location}")
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError(f"non-string JSON key at {location}")
            normalized[key] = _normalize_json(
                item,
                location=f"{location}.{key}",
            )
        return normalized
    if isinstance(value, (list, tuple)):
        return [
            _normalize_json(item, location=f"{location}[{index}]")
            for index, item in enumerate(value)
        ]
    raise TypeError(
        f"unsupported JSON type at {location}: {type(value).__name__}"
    )


def encode_result_payload(payload: Mapping[str, Any]) -> str:
    normalized = _normalize_json(payload)
    return json.dumps(
        normalized,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def day_bounds_us(day: date) -> tuple[int, int]:
    start = datetime.combine(day, datetime_time(), tzinfo=timezone.utc)
    start_us = int(start.timestamp() * 1_000_000)
    return start_us, start_us + 86_400_000_000


def grid_relative_path(symbol: str, day: date) -> Path:
    _require_symbol(symbol)
    return Path("multimarket/evidence") / symbol / (
        f"{day.isoformat()}_BOOKTICKER250.csv"
    )


def audit_relative_path(symbol: str, day: date) -> Path:
    _require_symbol(symbol)
    return Path("multimarket/audits") / symbol / f"{day.isoformat()}_AUDIT.json"


def inventory_relative_path(symbol: str, day: date) -> Path:
    _require_symbol(symbol)
    return Path("multimarket/inventory") / symbol / f"{day.isoformat()}.json"


def _require_symbol(symbol: str) -> str:
    normalized = symbol.upper()
    if normalized not in SUPPORTED_SYMBOLS:
        raise ValueError(f"unsupported EXP025 symbol: {symbol}")
    if normalized != symbol:
        raise ValueError("symbol must use exact uppercase canonical form")
    return normalized


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _wall_us(record: Mapping[str, Any]) -> int:
    return int(record["receive_wall_ns"]) // 1000


def _full_hex_commit(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 40:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def _valid_quote_record(record: Mapping[str, Any], symbol: str) -> bool:
    if record.get("record_type") != "quote":
        return False
    if record.get("symbol") != symbol:
        return False
    if record.get("market") != MARKET:
        return False
    if record.get("venue") != VENUE:
        return False
    if record.get("asset_class") != ASSET_CLASS:
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


def _timeline_sort_key(record: Mapping[str, Any]) -> tuple[int, int, int]:
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
        "day_started_records": 0,
        "collector_armed_before_day_start": False,
        "collector_metadata_exact": False,
        "frozen_implementation_commit": None,
        "collector_run_id": None,
        "process_id": None,
        "connection_open_attempts": 0,
        "connections_opened": 0,
        "connections_carried": 0,
        "connections_closed": 0,
        "transport_errors": 0,
        "rollover_records": 0,
        "rollover_after_day": False,
        "collector_stopped_records": 0,
        "connection_epochs": 0,
        "first_accepted_quote_utc": None,
        "last_accepted_quote_utc": None,
    }


class RawTimeline:
    def __init__(self, path: Path, *, symbol: str, day: date) -> None:
        self.path = path
        self.symbol = _require_symbol(symbol)
        self.day = day
        self.day_start_us, self.day_end_us = day_bounds_us(day)
        self.diagnostics = _empty_raw_diagnostics()
        self.sort_ordered = True
        self._started = False
        self._epochs: set[int] = set()

    def __iter__(self) -> Iterator[dict[str, Any]]:
        if self._started:
            raise RuntimeError("raw timeline stream can only be consumed once")
        self._started = True
        return self._records()

    def _metadata_exact(self, record: Mapping[str, Any]) -> bool:
        start = datetime.combine(
            self.day, datetime_time(), tzinfo=timezone.utc
        )
        end = start + timedelta(days=1)
        collector_started_wall_ns = record.get("collector_started_wall_ns")
        claimed_armed = record.get("armed_before_day_start")
        return bool(
            record.get("experiment_id") == EXPERIMENT_ID
            and record.get("symbol") == self.symbol
            and record.get("collection_day") == self.day.isoformat()
            and record.get("collection_start_utc") == start.isoformat()
            and record.get("collection_end_utc") == end.isoformat()
            and record.get("initial_symbols") == list(INITIAL_SYMBOLS)
            and record.get("venue") == VENUE
            and record.get("asset_class") == ASSET_CLASS
            and record.get("source")
            == "BINANCE_FUTURES_BOOKTICKER_WEBSOCKET"
            and _full_hex_commit(record.get("frozen_implementation_commit"))
            and isinstance(record.get("collector_run_id"), str)
            and bool(record.get("collector_run_id"))
            and type(record.get("process_id")) is int
            and record.get("process_id") > 0
            and type(collector_started_wall_ns) is int
            and isinstance(record.get("collector_started_utc"), str)
            and type(claimed_armed) is bool
            and claimed_armed
            is (
                collector_started_wall_ns
                < int(start.timestamp()) * 1_000_000_000
            )
        )

    def _record_rejection(self, record: Mapping[str, Any]) -> None:
        self.diagnostics["rejected_records"] += 1
        reason = str(record.get("reason", "UNKNOWN"))
        reasons = self.diagnostics["rejected_by_reason"]
        reasons[reason] = int(reasons.get(reason, 0)) + 1

    def _record_transport(self, record: Mapping[str, Any]) -> bool:
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
        if event == "day_started":
            self.diagnostics["day_started_records"] += 1
            exact = self._metadata_exact(record)
            if self.diagnostics["day_started_records"] == 1:
                self.diagnostics["collector_armed_before_day_start"] = bool(
                    exact and record.get("armed_before_day_start") is True
                )
                self.diagnostics["collector_metadata_exact"] = bool(exact)
                self.diagnostics["frozen_implementation_commit"] = record.get(
                    "frozen_implementation_commit"
                )
                self.diagnostics["collector_run_id"] = record.get(
                    "collector_run_id"
                )
                self.diagnostics["process_id"] = record.get("process_id")
            else:
                self.diagnostics["collector_armed_before_day_start"] = False
                self.diagnostics["collector_metadata_exact"] = False
        elif event == "connection_open_attempt":
            self.diagnostics["connection_open_attempts"] += 1
        elif event == "connection_opened":
            self.diagnostics["connections_opened"] += 1
        elif event == "connection_carried":
            self.diagnostics["connections_carried"] += 1
        elif event == "connection_closed":
            self.diagnostics["connections_closed"] += 1
        elif event == "transport_error":
            self.diagnostics["transport_errors"] += 1
        elif event == "day_rollover":
            self.diagnostics["rollover_records"] += 1
            if (
                wall_us >= self.day_end_us
                and record.get("completed_day") == self.day.isoformat()
                and record.get("next_day")
                == (self.day + timedelta(days=1)).isoformat()
            ):
                self.diagnostics["rollover_after_day"] = True
        elif event == "collector_stopped":
            self.diagnostics["collector_stopped_records"] += 1
        return True

    def _record_quote(
        self,
        record: Mapping[str, Any],
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
        if not (self.day_start_us <= wall_us < self.day_end_us):
            self.diagnostics["quotes_outside_collection_day_accepted"] += 1
        epoch = int(record.get("connection_epoch", 0))
        if epoch > 0:
            self._epochs.add(epoch)
        if record.get("symbol") != self.symbol:
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
        timestamp = record.get("receive_timestamp_utc")
        if self.diagnostics["first_accepted_quote_utc"] is None:
            self.diagnostics["first_accepted_quote_utc"] = timestamp
        self.diagnostics["last_accepted_quote_utc"] = timestamp
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
                        record, last_wall, last_mono
                    )
                else:
                    continue
                sort_key = _timeline_sort_key(record)
                if last_sort_key is not None and sort_key < last_sort_key:
                    self.sort_ordered = False
                last_sort_key = sort_key
                yield record
        self.diagnostics["connection_epochs"] = len(self._epochs)


class TimelineOutOfOrder(RuntimeError):
    pass


def _raw_timeline_records(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("record_type") == "transport" and (
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
        prefix=".codex-exp025-sort-", dir=scratch_dir
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
                SELECT payload FROM timeline
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
            "day_started",
            "connection_open_attempt",
            "connection_opened",
            "connection_carried",
            "connection_closed",
            "transport_error",
            "day_rollover",
            "collector_stopped",
        }:
            latest = None
        if event_name in {"connection_opened", "connection_carried"}:
            active_epoch = epoch
        elif event_name in {
            "connection_open_attempt",
            "connection_closed",
            "transport_error",
            "day_rollover",
            "collector_stopped",
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
    *,
    symbol: str,
    day: date,
    expected_rows: int = EXPECTED_ROWS,
) -> dict[str, Any]:
    _require_symbol(symbol)
    day_start_us, _ = day_bounds_us(day)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    if output.exists() or temporary.exists():
        raise FileExistsError("EXP025 grid or partial output already exists")
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
        for index in range(expected_rows):
            timestamp_us = day_start_us + index * GRID_US
            while event is not None:
                if _wall_us(event) > timestamp_us:
                    break
                latest, active_epoch = _apply_timeline_event(
                    latest, active_epoch, event
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
                    if age_us <= MAX_AGE_US and _valid_quote_record(
                        latest, symbol
                    ):
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
    if isinstance(timeline, RawTimeline) and not timeline.sort_ordered:
        temporary.unlink()
        raise TimelineOutOfOrder
    temporary.replace(output)
    return {
        "rows": expected_rows,
        "valid_rows": valid_rows,
        "valid_coverage": valid_rows / expected_rows,
        "future_quote_violations": future_quote_violations,
        "stale_or_unavailable_rows": stale_rows,
        "reconnect_invalid_rows": reconnect_invalid_rows,
        "first_timestamp_us": day_start_us,
        "last_timestamp_us": day_start_us + (expected_rows - 1) * GRID_US,
        "grid_step_us": GRID_US,
    }


def stream_raw_to_grid(
    raw: Path,
    grid: Path,
    *,
    symbol: str,
    day: date,
    expected_rows: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = EXPECTED_ROWS if expected_rows is None else expected_rows
    timeline = RawTimeline(raw, symbol=symbol, day=day)
    try:
        grid_diagnostics = build_grid(
            timeline,
            grid,
            symbol=symbol,
            day=day,
            expected_rows=rows,
        )
    except TimelineOutOfOrder:
        grid_diagnostics = build_grid(
            _externally_sorted_timeline(raw, grid.parent),
            grid,
            symbol=symbol,
            day=day,
            expected_rows=rows,
        )
    return timeline.diagnostics, grid_diagnostics


def _fresh_outputs(*paths: Path) -> None:
    for path in paths:
        part = path.with_suffix(path.suffix + ".part")
        if path.exists() or part.exists():
            raise FileExistsError(
                f"EXP025 output or partial already exists: {path}"
            )


def _write_json_once(path: Path, payload: Mapping[str, Any]) -> None:
    part = path.with_suffix(path.suffix + ".part")
    if path.exists() or part.exists():
        raise FileExistsError(f"immutable EXP025 JSON output exists: {path}")
    encoded = encode_result_payload(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    with part.open("x", encoding="utf-8") as handle:
        handle.write(encoded)
    if path.exists():
        raise FileExistsError(f"EXP025 JSON output appeared: {path}")
    part.replace(path)


def _integrity_gates(
    raw: Path,
    grid: Path,
    raw_diagnostics: Mapping[str, Any],
    grid_diagnostics: Mapping[str, Any],
    raw_sha256: str,
    grid_sha256: str,
    *,
    day: date,
) -> dict[str, bool]:
    day_start_us, _ = day_bounds_us(day)
    gates = {
        "raw_file_nonempty": bool(raw.stat().st_size > 0),
        "grid_rows_exact_345600": bool(
            grid_diagnostics["rows"] == EXPECTED_ROWS
        ),
        "grid_step_exact_250000us": bool(
            grid_diagnostics["grid_step_us"] == GRID_US
        ),
        "first_timestamp_exact": bool(
            grid_diagnostics["first_timestamp_us"] == day_start_us
        ),
        "last_timestamp_exact": bool(
            grid_diagnostics["last_timestamp_us"]
            == day_start_us + (EXPECTED_ROWS - 1) * GRID_US
        ),
        "valid_coverage_at_least_0_99": bool(
            grid_diagnostics["valid_coverage"] >= MIN_VALID_COVERAGE
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
        "day_start_metadata_exact": bool(
            raw_diagnostics["day_started_records"] == 1
            and raw_diagnostics["collector_metadata_exact"]
        ),
        "collector_armed_before_utc_midnight": bool(
            raw_diagnostics["collector_armed_before_day_start"]
        ),
        "day_rollover_observed_after_day": bool(
            raw_diagnostics["rollover_records"] == 1
            and raw_diagnostics["rollover_after_day"]
        ),
        "at_least_one_connection_epoch": bool(
            raw_diagnostics["connection_epochs"] >= 1
        ),
        "no_quote_outside_collection_day_accepted": bool(
            raw_diagnostics["quotes_outside_collection_day_accepted"] == 0
        ),
        "no_malformed_transport_record": bool(
            raw_diagnostics["malformed_transport_records"] == 0
        ),
        **no_analysis_guards(),
    }
    return validate_builtin_bool_invariants(gates)


def _status_for_day(
    raw_diagnostics: Mapping[str, Any],
    gates: Mapping[str, bool],
) -> str:
    partial_start = (
        raw_diagnostics["day_started_records"] == 1
        and raw_diagnostics["collector_metadata_exact"]
        and not raw_diagnostics["collector_armed_before_day_start"]
    )
    if partial_start:
        ignored_for_partial = {
            "collector_armed_before_utc_midnight",
            "valid_coverage_at_least_0_99",
        }
        for name, value in gates.items():
            if name in ignored_for_partial:
                continue
            expected_value = False if name in no_analysis_guards() else True
            if value != expected_value:
                return STATUS_FAIL
        return STATUS_PARTIAL
    expected = {
        name: False if name in no_analysis_guards() else True for name in gates
    }
    return (
        STATUS_FULL
        if adjudicate_invariants(gates, expected=expected)
        else STATUS_FAIL
    )


def _inventory_payload(
    audit_payload: Mapping[str, Any],
) -> dict[str, Any]:
    entry = {
        "experiment_id": EXPERIMENT_ID,
        "market": MARKET,
        "venue": VENUE,
        "asset_class": ASSET_CLASS,
        "symbol": audit_payload["symbol"],
        "day": audit_payload["collection_day"],
        "status": audit_payload["status"],
        "raw_path": audit_payload["raw_path"],
        "raw_sha256": audit_payload["raw_sha256"],
        "raw_bytes": audit_payload["raw_bytes"],
        "grid_path": audit_payload["grid_path"],
        "grid_sha256": audit_payload["grid_sha256"],
        "grid_bytes": audit_payload["grid_bytes"],
        "coverage": audit_payload["grid_diagnostics"]["valid_coverage"],
        "frozen_collector_commit": audit_payload[
            "frozen_collector_commit"
        ],
        "collector_run_id": audit_payload["collector_run_id"],
        "created_at": audit_payload["created_at"],
    }
    if set(entry) != set(INVENTORY_FIELDS):
        raise RuntimeError("EXP025 inventory schema changed")
    if FORBIDDEN_INVENTORY_FIELDS.intersection(
        name.lower() for name in entry
    ):
        raise RuntimeError("predictive field reached sealed inventory")
    return entry


def load_inventory(inventory_root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not inventory_root.exists():
        return entries
    for path in sorted(inventory_root.glob("*/*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if set(payload) != set(INVENTORY_FIELDS):
            raise RuntimeError(f"invalid inventory schema: {path}")
        entries.append(payload)
    return entries


def full_day_counts(entries: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    return untouched_full_day_counts(entries, analytical_openings=())


def untouched_full_day_counts(
    entries: Iterable[Mapping[str, Any]],
    *,
    analytical_openings: Iterable[Mapping[str, Any]],
) -> dict[str, int]:
    opened: set[tuple[str, str]] = set()
    for opening in analytical_openings:
        symbol = str(opening.get("symbol", ""))
        day = str(opening.get("day", ""))
        if symbol not in SUPPORTED_SYMBOLS or not day:
            raise RuntimeError("invalid analytical-opening metadata")
        opened.add((symbol, day))

    counts = {symbol: 0 for symbol in INITIAL_SYMBOLS}
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        symbol = str(entry.get("symbol", ""))
        day = str(entry.get("day", ""))
        if symbol not in counts:
            raise RuntimeError("inventory contains unsupported symbol")
        key = (symbol, day)
        if key in seen:
            raise RuntimeError("duplicate symbol/day inventory entry")
        seen.add(key)
        if entry.get("status") == STATUS_FULL and key not in opened:
            counts[symbol] += 1
    return counts


def run(
    raw: Path,
    grid: Path,
    audit: Path,
    inventory_entry: Path,
    *,
    symbol: str,
    day: date,
) -> dict[str, Any]:
    _require_symbol(symbol)
    _, day_end_us = day_bounds_us(day)
    if int(_utc_now().timestamp() * 1_000_000) < day_end_us:
        raise RuntimeError("cannot finalize an EXP025 day before UTC rollover")
    if not raw.is_file() or raw.stat().st_size == 0:
        raise RuntimeError("EXP025 raw daily file missing or empty")
    failure_marker = operational_failure_path(raw)
    if failure_marker.exists():
        raise RuntimeError(
            "EXP025 raw partition has an operational-failure marker: "
            f"{failure_marker}"
        )
    _fresh_outputs(grid, audit, inventory_entry)
    raw_diagnostics, grid_diagnostics = stream_raw_to_grid(
        raw,
        grid,
        symbol=symbol,
        day=day,
    )
    raw_sha256 = sha256_file(raw)
    grid_sha256 = sha256_file(grid)
    gates = _integrity_gates(
        raw,
        grid,
        raw_diagnostics,
        grid_diagnostics,
        raw_sha256,
        grid_sha256,
        day=day,
    )
    status = _status_for_day(raw_diagnostics, gates)
    guards = no_analysis_guards()
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "scope": "CONTINUOUS_MULTIMARKET_DATA_ACQUISITION_AND_INTEGRITY_ONLY",
        "status": status,
        "market": MARKET,
        "venue": VENUE,
        "asset_class": ASSET_CLASS,
        "symbol": symbol,
        "collection_day": day.isoformat(),
        "raw_path": str(raw),
        "grid_path": str(grid),
        "raw_bytes": int(raw.stat().st_size),
        "grid_bytes": int(grid.stat().st_size),
        "raw_sha256": raw_sha256,
        "grid_sha256": grid_sha256,
        "raw_diagnostics": raw_diagnostics,
        "grid_diagnostics": grid_diagnostics,
        "integrity_gates": gates,
        "frozen_collector_commit": raw_diagnostics[
            "frozen_implementation_commit"
        ],
        "collector_run_id": raw_diagnostics["collector_run_id"],
        "created_at": _utc_now().isoformat(),
        "network_accessed_for_acquisition": True,
        "predictive_metrics_calculated": False,
        **guards,
    }
    _write_json_once(audit, payload)
    _write_json_once(inventory_entry, _inventory_payload(payload))
    return payload


def invalid_payload(
    exc: Exception,
    *,
    symbol: str,
    day: date,
) -> dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "scope": "CONTINUOUS_MULTIMARKET_DATA_ACQUISITION_AND_INTEGRITY_ONLY",
        "status": STATUS_INVALID,
        "symbol": symbol,
        "collection_day": day.isoformat(),
        "failure_type": type(exc).__name__,
        "failure_message": str(exc),
        "predictive_metrics_calculated": False,
        **no_analysis_guards(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--inventory-entry", type=Path, required=True)
    parser.add_argument("--symbol", choices=INITIAL_SYMBOLS, required=True)
    parser.add_argument("--day", type=date.fromisoformat, required=True)
    args = parser.parse_args(argv)
    _fresh_outputs(args.grid, args.audit, args.inventory_entry)
    try:
        result = run(
            args.raw,
            args.grid,
            args.audit,
            args.inventory_entry,
            symbol=args.symbol,
            day=args.day,
        )
    except Exception as exc:
        result = invalid_payload(exc, symbol=args.symbol, day=args.day)
        if not args.audit.exists() and not args.audit.with_suffix(
            args.audit.suffix + ".part"
        ).exists():
            _write_json_once(args.audit, result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["status"] != STATUS_INVALID else 1


if __name__ == "__main__":
    raise SystemExit(main())
