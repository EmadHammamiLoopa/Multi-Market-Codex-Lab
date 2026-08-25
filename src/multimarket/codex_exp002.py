from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np


EXPERIMENT_ID = "CODEX-EXP-002"
DAYS = tuple(f"2026-{month:02d}-01" for month in range(1, 8))
SYMBOLS = ("BTCUSDT", "ETHUSDT")
ORDER_SIZE = {"BTCUSDT": 0.001, "ETHUSDT": 0.001}
GRID_US = 250_000
CANDIDATE_SPACING_US = 15_000_000
FIRST_CANDIDATE_US = 15_000_000
ORDER_LIFETIME_US = 3_000_000
MARKOUT_HORIZONS_S = (1, 3, 10)
PRIMARY_LATENCY_US = 250_000
SLOW_LATENCY_US = 500_000
PRIMARY_MAKER_FEE_BPS = 2.0
PRIMARY_TAKER_FEE_BPS = 4.0
STRESS_MAKER_FEE_BPS = 3.0
STRESS_TAKER_FEE_BPS = 5.0
RIDGE_ALPHA = 10.0
LOGISTIC_C = 1.0
EV_THRESHOLDS_BPS = (0.0, 0.10, 0.25)
RANDOM_SEED = 20260825
EXPECTED_ROWS = 345_600

RAW_TRADE_HEADER = (
    "exchange,symbol,timestamp,local_timestamp,id,side,price,amount"
)
FEATURE_COLUMNS = (
    "spread_bps",
    "microprice_minus_mid_bps",
    "obi_l1",
    "obi_l5",
    "log_bid_qty_l1",
    "log_ask_qty_l1",
    "ofi_l1_1s",
    "trade_qty_imbalance_1s",
)
MODEL_FEATURE_NAMES = (
    "symbol_is_eth",
    "spread_bps",
    "side_microprice_minus_mid_bps",
    "side_obi_l1",
    "side_obi_l5",
    "log_own_qty_l1",
    "side_ofi_l1_1s",
    "side_trade_qty_imbalance_1s",
)


class ExperimentSealError(RuntimeError):
    pass


def assert_allowed_day(day: str) -> None:
    if day not in DAYS:
        raise ExperimentSealError(f"{EXPERIMENT_ID} rejects non-sandbox day: {day}")


def assert_allowed_path(path: Path) -> None:
    value = path.as_posix()
    if "2026-08" in value:
        raise ExperimentSealError(f"{EXPERIMENT_ID} rejects sealed August path: {value}")
    dated = [part for part in path.parts if part.startswith("2026-")]
    for part in dated:
        day = part[:10]
        if len(day) == 10:
            assert_allowed_day(day)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class QueueEvent:
    timestamp_us: int
    kind: str
    quantity: float


@dataclass(frozen=True)
class QueueReplay:
    initial_queue: float
    queue_advanced: float
    trade_quantity: float
    fill_quantity: float
    first_fill_us: int | None
    full_fill_us: int | None
    effective_cancel_us: int
    timed_out: bool

    @property
    def filled(self) -> bool:
        return self.fill_quantity > 0.0


def replay_queue(
    *,
    initial_queue: float,
    order_size: float,
    arrival_us: int,
    timeout_request_us: int,
    response_latency_us: int,
    events: Iterable[QueueEvent],
    cancellation_credit: float = 0.0,
) -> QueueReplay:
    """Replay one MBP queue; only qualifying trades can execute the order."""

    if initial_queue < 0 or order_size <= 0:
        raise ValueError("queue and order size must be nonnegative/positive")
    if not 0.0 <= cancellation_credit <= 1.0:
        raise ValueError("cancellation_credit must be in [0, 1]")
    ahead = float(initial_queue)
    remaining = float(order_size)
    trade_quantity = 0.0
    first_fill: int | None = None
    full_fill: int | None = None
    effective_cancel = int(timeout_request_us + response_latency_us)
    partial_cancel_requested = False
    for event in sorted(events, key=lambda item: (item.timestamp_us, item.kind != "trade")):
        if event.timestamp_us <= arrival_us or event.timestamp_us >= effective_cancel:
            continue
        if event.quantity < 0:
            raise ValueError("event quantity cannot be negative")
        if event.kind == "cancel":
            ahead = max(0.0, ahead - cancellation_credit * event.quantity)
            continue
        if event.kind != "trade":
            raise ValueError(f"unknown queue event: {event.kind}")
        trade_quantity += event.quantity
        at_front = max(0.0, event.quantity - ahead)
        ahead = max(0.0, ahead - event.quantity)
        if at_front <= 0.0 or remaining <= 0.0:
            continue
        executed = min(remaining, at_front)
        remaining -= executed
        if first_fill is None:
            first_fill = event.timestamp_us
        if remaining <= 1e-12:
            remaining = 0.0
            full_fill = event.timestamp_us
            effective_cancel = event.timestamp_us
            break
        if not partial_cancel_requested:
            effective_cancel = min(effective_cancel, event.timestamp_us + response_latency_us)
            partial_cancel_requested = True
    fill_quantity = order_size - remaining
    return QueueReplay(
        initial_queue=float(initial_queue),
        queue_advanced=float(initial_queue - ahead),
        trade_quantity=float(trade_quantity),
        fill_quantity=float(fill_quantity),
        first_fill_us=first_fill,
        full_fill_us=full_fill,
        effective_cancel_us=effective_cancel,
        timed_out=first_fill is None and effective_cancel >= timeout_request_us,
    )


@dataclass
class BookDay:
    timestamp_us: np.ndarray
    bid: np.ndarray
    ask: np.ndarray
    bid_qty: np.ndarray
    ask_qty: np.ndarray
    mid: np.ndarray
    valid: np.ndarray


@dataclass
class Candidate:
    day: str
    symbol: str
    decision_us: int
    decision_index: int
    side: int
    limit_price: float
    order_size: float
    features: np.ndarray
    trade_events: list[QueueEvent] = field(default_factory=list)
    variants: dict[str, dict[str, Any]] = field(default_factory=dict)


def _header_positions(path: Path) -> dict[str, int]:
    with path.open("r", encoding="utf-8") as handle:
        return {name: index for index, name in enumerate(handle.readline().rstrip("\r\n").split(","))}


def _load_numeric_columns(path: Path, columns: Sequence[str]) -> np.ndarray:
    positions = _header_positions(path)
    missing = sorted(set(columns) - set(positions))
    if missing:
        raise RuntimeError(f"{path}: missing columns {missing}")
    return np.loadtxt(
        path,
        delimiter=",",
        skiprows=1,
        usecols=[positions[name] for name in columns],
        dtype=np.float64,
        ndmin=2,
    )


def load_book_day(path: Path) -> BookDay:
    assert_allowed_path(path)
    columns = (
        "local_timestamp_us",
        "best_bid",
        "best_ask",
        "bid_qty_l1",
        "ask_qty_l1",
        "mid",
        "book_valid",
    )
    values = _load_numeric_columns(path, columns)
    if len(values) != EXPECTED_ROWS:
        raise RuntimeError(f"{path}: expected {EXPECTED_ROWS} rows, got {len(values)}")
    timestamps = values[:, 0].astype(np.int64)
    if np.any(np.diff(timestamps) != GRID_US):
        raise RuntimeError(f"{path}: non-250ms time grid")
    return BookDay(
        timestamp_us=timestamps,
        bid=values[:, 1],
        ask=values[:, 2],
        bid_qty=values[:, 3],
        ask_qty=values[:, 4],
        mid=values[:, 5],
        valid=values[:, 6].astype(bool),
    )


def candidate_window_within_day(decision_us: int, day_start_us: int) -> bool:
    day_end = day_start_us + 86_400_000_000
    last_possible_exit = (
        decision_us
        + SLOW_LATENCY_US
        + ORDER_LIFETIME_US
        + SLOW_LATENCY_US
        + 10_000_000
        + SLOW_LATENCY_US
    )
    return day_start_us <= decision_us and last_possible_exit < day_end


def load_candidates(path: Path, book: BookDay, day: str, symbol: str) -> list[Candidate]:
    assert_allowed_day(day)
    assert_allowed_path(path)
    columns = ("local_timestamp_us", "l2_valid", *FEATURE_COLUMNS)
    values = _load_numeric_columns(path, columns)
    if len(values) != EXPECTED_ROWS:
        raise RuntimeError(f"{path}: expected {EXPECTED_ROWS} rows, got {len(values)}")
    timestamps = values[:, 0].astype(np.int64)
    if not np.array_equal(timestamps, book.timestamp_us):
        raise RuntimeError(f"{path}: feature/book timestamp mismatch")
    start = int(timestamps[0])
    candidates: list[Candidate] = []
    spacing_rows = CANDIDATE_SPACING_US // GRID_US
    first_row = FIRST_CANDIDATE_US // GRID_US
    for slot, row in enumerate(range(first_row, len(values), spacing_rows)):
        decision_us = int(timestamps[row])
        if not candidate_window_within_day(decision_us, start) or not bool(values[row, 1]):
            continue
        side = 1 if slot % 2 == 0 else -1
        limit = float(book.bid[row] if side > 0 else book.ask[row])
        raw = values[row, 2:]
        if not book.valid[row] or not np.isfinite(limit) or not np.all(np.isfinite(raw)):
            continue
        spread, micro, obi1, obi5, log_bid, log_ask, ofi, trade_imb = raw
        model_features = np.asarray(
            [
                1.0 if symbol == "ETHUSDT" else 0.0,
                spread,
                side * micro,
                side * obi1,
                side * obi5,
                log_bid if side > 0 else log_ask,
                side * ofi,
                side * trade_imb,
            ],
            dtype=np.float64,
        )
        candidates.append(
            Candidate(
                day=day,
                symbol=symbol,
                decision_us=decision_us,
                decision_index=row,
                side=side,
                limit_price=limit,
                order_size=ORDER_SIZE[symbol],
                features=model_features,
            )
        )
    return candidates


def _load_snapshot_times(path: Path) -> np.ndarray:
    assert_allowed_path(path)
    values = np.loadtxt(path, delimiter=",", skiprows=1, dtype=np.int64, ndmin=1)
    return np.asarray(values, dtype=np.int64).reshape(-1)


def attach_trade_events(path: Path, candidates: list[Candidate]) -> int:
    assert_allowed_path(path)
    if not candidates:
        return 0
    by_slot = {candidate.decision_us: candidate for candidate in candidates}
    day_start = candidates[0].decision_us - (
        (candidates[0].decision_us % 86_400_000_000)
    )
    parsed = 0
    with gzip.open(path, "rb") as handle:
        header = handle.readline().rstrip(b"\r\n").decode("utf-8")
        if header != RAW_TRADE_HEADER:
            raise RuntimeError(f"{path}: unexpected trade header")
        for line in handle:
            fields = line.rstrip(b"\r\n").split(b",")
            if len(fields) != 8:
                raise RuntimeError(f"{path}: malformed trade row")
            parsed += 1
            timestamp_us = int(fields[3])
            offset = timestamp_us - day_start - FIRST_CANDIDATE_US
            if offset < 0:
                continue
            decision_us = day_start + FIRST_CANDIDATE_US + (
                offset // CANDIDATE_SPACING_US
            ) * CANDIDATE_SPACING_US
            candidate = by_slot.get(decision_us)
            if candidate is None:
                continue
            if timestamp_us <= decision_us or timestamp_us >= decision_us + 4_000_000:
                continue
            aggressor = fields[5]
            if (candidate.side > 0 and aggressor != b"sell") or (
                candidate.side < 0 and aggressor != b"buy"
            ):
                continue
            price = float(fields[6])
            if price != candidate.limit_price:
                continue
            candidate.trade_events.append(
                QueueEvent(timestamp_us=timestamp_us, kind="trade", quantity=float(fields[7]))
            )
    return parsed


def _grid_index_at_or_after(book: BookDay, timestamp_us: int) -> int:
    return int(np.searchsorted(book.timestamp_us, timestamp_us, side="left"))


def _inferred_cancel_events(
    candidate: Candidate,
    book: BookDay,
    arrival_index: int,
    end_us: int,
) -> list[QueueEvent]:
    events: list[QueueEvent] = []
    previous_timestamp = int(book.timestamp_us[arrival_index])
    previous_depth = float(book.bid_qty[arrival_index] if candidate.side > 0 else book.ask_qty[arrival_index])
    for index in range(arrival_index + 1, min(len(book.timestamp_us), _grid_index_at_or_after(book, end_us) + 1)):
        timestamp = int(book.timestamp_us[index])
        if timestamp >= end_us:
            break
        same_price = (
            book.valid[index]
            and (book.bid[index] if candidate.side > 0 else book.ask[index]) == candidate.limit_price
        )
        if not same_price:
            previous_timestamp = timestamp
            previous_depth = math.nan
            continue
        current_depth = float(book.bid_qty[index] if candidate.side > 0 else book.ask_qty[index])
        if math.isfinite(previous_depth):
            traded = sum(
                event.quantity
                for event in candidate.trade_events
                if previous_timestamp < event.timestamp_us <= timestamp
            )
            inferred = max(0.0, previous_depth - current_depth - traded)
            if inferred > 0.0:
                events.append(QueueEvent(timestamp, "cancel", inferred))
        previous_timestamp = timestamp
        previous_depth = current_depth
    return events


def _variant_no_fill(status: str, arrival_us: int, *, initial_queue: float | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "arrival_us": arrival_us,
        "timeout_request_us": None,
        "effective_cancel_us": None,
        "initial_queue": initial_queue,
        "queue_advanced": 0.0,
        "trade_quantity": 0.0,
        "fill_quantity": 0.0,
        "first_fill_us": None,
        "full_fill_us": None,
        "order_age_ms": None,
        "depth_ratio": None if initial_queue in (None, 0.0) else 0.0,
        "exit_price": None,
        "gross_bps": None,
        "gross_usd": 0.0,
        "markout_1s_bps": None,
        "markout_3s_bps": None,
        "markout_10s_bps": None,
        "primary_net_bps": None,
        "primary_net_usd": 0.0,
        "stress_net_bps": None,
        "stress_net_usd": 0.0,
    }


def simulate_variant(
    candidate: Candidate,
    book: BookDay,
    snapshots: np.ndarray,
    *,
    latency_us: int,
    cancellation_credit: float,
) -> dict[str, Any]:
    if latency_us % GRID_US:
        raise ValueError("latency must align to the 250ms grid")
    arrival_us = candidate.decision_us + latency_us
    arrival_index = candidate.decision_index + latency_us // GRID_US
    if arrival_index >= len(book.timestamp_us) or not book.valid[arrival_index]:
        return _variant_no_fill("arrival_invalid", arrival_us)
    current_side_price = book.bid[arrival_index] if candidate.side > 0 else book.ask[arrival_index]
    if current_side_price != candidate.limit_price:
        return _variant_no_fill("arrival_price_miss", arrival_us)
    initial_queue = float(book.bid_qty[arrival_index] if candidate.side > 0 else book.ask_qty[arrival_index])
    if not math.isfinite(initial_queue) or initial_queue < 0.0:
        return _variant_no_fill("arrival_invalid_queue", arrival_us)
    timeout_request = arrival_us + ORDER_LIFETIME_US
    tracking_end = timeout_request + latency_us
    snapshot_after = snapshots[(snapshots > arrival_us) & (snapshots < tracking_end)]
    if len(snapshot_after):
        tracking_end = int(snapshot_after[0])
    events = [event for event in candidate.trade_events if arrival_us < event.timestamp_us < tracking_end]
    if cancellation_credit:
        events.extend(_inferred_cancel_events(candidate, book, arrival_index, tracking_end))
    replay = replay_queue(
        initial_queue=initial_queue,
        order_size=candidate.order_size,
        arrival_us=arrival_us,
        timeout_request_us=timeout_request,
        response_latency_us=latency_us,
        events=events,
        cancellation_credit=cancellation_credit,
    )
    if not replay.filled:
        status = "snapshot_cancel" if len(snapshot_after) else "timeout_cancel"
        result = _variant_no_fill(status, arrival_us, initial_queue=initial_queue)
        result.update(
            queue_advanced=replay.queue_advanced,
            trade_quantity=replay.trade_quantity,
            depth_ratio=candidate.order_size / initial_queue if initial_queue > 0 else math.inf,
            timeout_request_us=timeout_request,
            effective_cancel_us=(int(snapshot_after[0]) if len(snapshot_after) else replay.effective_cancel_us),
        )
        return result

    fill_us = int(replay.first_fill_us)
    markouts: dict[int, float] = {}
    for horizon in MARKOUT_HORIZONS_S:
        index = _grid_index_at_or_after(book, fill_us + horizon * 1_000_000)
        if index >= len(book.mid) or not book.valid[index]:
            raise RuntimeError("markout book state unavailable inside an allowed day")
        markouts[horizon] = candidate.side * 10_000.0 * (
            float(book.mid[index]) / candidate.limit_price - 1.0
        )
    exit_index = _grid_index_at_or_after(book, fill_us + 10_000_000 + latency_us)
    if exit_index >= len(book.mid) or not book.valid[exit_index]:
        raise RuntimeError("exit book state unavailable inside an allowed day")
    exit_price = float(book.bid[exit_index] if candidate.side > 0 else book.ask[exit_index])
    quantity = replay.fill_quantity
    gross_usd = candidate.side * quantity * (exit_price - candidate.limit_price)
    entry_notional = quantity * candidate.limit_price
    exit_notional = quantity * exit_price

    def economics(maker_bps: float, taker_bps: float) -> tuple[float, float]:
        fees = maker_bps / 10_000.0 * entry_notional + taker_bps / 10_000.0 * exit_notional
        net_usd = gross_usd - fees
        return 10_000.0 * net_usd / entry_notional, net_usd

    primary_net_bps, primary_net_usd = economics(PRIMARY_MAKER_FEE_BPS, PRIMARY_TAKER_FEE_BPS)
    stress_net_bps, stress_net_usd = economics(STRESS_MAKER_FEE_BPS, STRESS_TAKER_FEE_BPS)
    gross_bps = 10_000.0 * gross_usd / entry_notional
    full = replay.fill_quantity >= candidate.order_size - 1e-12
    return {
        "status": "full_fill" if full else "partial_fill_cancel",
        "arrival_us": arrival_us,
        "timeout_request_us": timeout_request,
        "effective_cancel_us": replay.effective_cancel_us if not full else None,
        "initial_queue": initial_queue,
        "queue_advanced": replay.queue_advanced,
        "trade_quantity": replay.trade_quantity,
        "fill_quantity": replay.fill_quantity,
        "first_fill_us": fill_us,
        "full_fill_us": replay.full_fill_us,
        "order_age_ms": (fill_us - arrival_us) / 1_000.0,
        "depth_ratio": candidate.order_size / initial_queue if initial_queue > 0 else math.inf,
        "exit_price": exit_price,
        "gross_bps": gross_bps,
        "gross_usd": gross_usd,
        "markout_1s_bps": markouts[1],
        "markout_3s_bps": markouts[3],
        "markout_10s_bps": markouts[10],
        "primary_net_bps": primary_net_bps,
        "primary_net_usd": primary_net_usd,
        "stress_net_bps": stress_net_bps,
        "stress_net_usd": stress_net_usd,
    }


def simulate_day(original_root: Path, day: str, symbol: str) -> tuple[list[Candidate], dict[str, Any]]:
    assert_allowed_day(day)
    if symbol not in SYMBOLS:
        raise ValueError(f"unsupported symbol: {symbol}")
    paths = {
        "book": original_root / f"evidence/v23/phase0dl_book250/{symbol}/{day}_BOOK250.csv",
        "features": original_root / f"evidence/v23/phase0dl_features250/{symbol}/{day}_FEATURES250.csv",
        "snapshots": original_root / f"evidence/v23/phase0dl_snapshots/{symbol}/{day}_SNAPSHOTS.csv",
        "trades": original_root / f"data/v23_phase0dl_l2_raw/trades/{symbol}/{day}.csv.gz",
    }
    for path in paths.values():
        assert_allowed_path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
    book = load_book_day(paths["book"])
    candidates = load_candidates(paths["features"], book, day, symbol)
    snapshots = _load_snapshot_times(paths["snapshots"])
    parsed_trades = attach_trade_events(paths["trades"], candidates)
    for candidate in candidates:
        candidate.variants["risk250"] = simulate_variant(
            candidate, book, snapshots, latency_us=PRIMARY_LATENCY_US, cancellation_credit=0.0
        )
        candidate.variants["q50_250"] = simulate_variant(
            candidate, book, snapshots, latency_us=PRIMARY_LATENCY_US, cancellation_credit=0.5
        )
        candidate.variants["risk500"] = simulate_variant(
            candidate, book, snapshots, latency_us=SLOW_LATENCY_US, cancellation_credit=0.0
        )
        candidate.trade_events.clear()
    return candidates, {
        "day": day,
        "symbol": symbol,
        "candidate_count": len(candidates),
        "parsed_trade_rows": parsed_trades,
        "input_sha256": {name: sha256_file(path) for name, path in paths.items()},
    }


@dataclass
class FittedModels:
    scaler: Any
    fill_model: Any
    markout_model: Any

    def predict(self, candidates: Sequence[Candidate]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if not candidates:
            empty = np.empty(0, dtype=np.float64)
            return empty, empty, empty
        X = np.stack([candidate.features for candidate in candidates])
        transformed = self.scaler.transform(X)
        fill_probability = self.fill_model.predict_proba(transformed)[:, 1]
        gross_if_filled = self.markout_model.predict(transformed)
        expected_net = fill_probability * (
            gross_if_filled - PRIMARY_MAKER_FEE_BPS - PRIMARY_TAKER_FEE_BPS
        )
        return fill_probability, gross_if_filled, expected_net

    def audit(self) -> dict[str, Any]:
        return {
            "feature_names": list(MODEL_FEATURE_NAMES),
            "scaler_mean": self.scaler.mean_.tolist(),
            "scaler_scale": self.scaler.scale_.tolist(),
            "fill_intercept": self.fill_model.intercept_.tolist(),
            "fill_coefficients": self.fill_model.coef_.tolist(),
            "markout_intercept": float(self.markout_model.intercept_),
            "markout_coefficients": self.markout_model.coef_.tolist(),
        }


def fit_models(candidates: Sequence[Candidate]) -> FittedModels:
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.preprocessing import StandardScaler

    if len(candidates) < 500:
        raise RuntimeError("fewer than 500 training candidates")
    X = np.stack([candidate.features for candidate in candidates])
    fill = np.asarray(
        [candidate.variants["risk250"]["fill_quantity"] > 0.0 for candidate in candidates],
        dtype=np.int8,
    )
    if fill.sum() < 50 or fill.sum() == len(fill):
        raise RuntimeError("fill model lacks at least 50 fills and both classes")
    scaler = StandardScaler().fit(X)
    transformed = scaler.transform(X)
    fill_model = LogisticRegression(
        C=LOGISTIC_C,
        solver="lbfgs",
        max_iter=1_000,
        random_state=RANDOM_SEED,
    ).fit(transformed, fill)
    filled_indices = np.flatnonzero(fill)
    gross = np.asarray(
        [candidates[index].variants["risk250"]["gross_bps"] for index in filled_indices],
        dtype=np.float64,
    )
    if len(gross) < 50 or not np.all(np.isfinite(gross)):
        raise RuntimeError("markout model lacks at least 50 finite filled outcomes")
    markout_model = Ridge(alpha=RIDGE_ALPHA).fit(transformed[filled_indices], gross)
    return FittedModels(scaler=scaler, fill_model=fill_model, markout_model=markout_model)


def select_threshold(
    candidates: Sequence[Candidate], expected_net_bps: np.ndarray
) -> tuple[float, list[dict[str, Any]]]:
    if len(candidates) != len(expected_net_bps):
        raise ValueError("candidate/prediction length mismatch")
    rows: list[dict[str, Any]] = []
    for threshold in EV_THRESHOLDS_BPS:
        selected = np.isfinite(expected_net_bps) & (expected_net_bps > threshold)
        fills = [
            candidates[index].variants["risk250"]
            for index in np.flatnonzero(selected)
            if candidates[index].variants["risk250"]["fill_quantity"] > 0.0
        ]
        rows.append(
            {
                "threshold_bps_per_submitted_order": threshold,
                "submitted": int(selected.sum()),
                "completed": len(fills),
                "total_primary_net_usd": float(sum(item["primary_net_usd"] for item in fills)),
                "net_bps_per_completed": float(np.mean([item["primary_net_bps"] for item in fills]))
                if fills
                else None,
                "eligible": bool(selected.sum() >= 250 and len(fills) >= 20),
            }
        )
    eligible = [row for row in rows if row["eligible"]]
    if not eligible:
        raise RuntimeError("no expected-value threshold meets inner coverage")
    chosen = max(
        eligible,
        key=lambda row: (
            row["total_primary_net_usd"],
            -row["threshold_bps_per_submitted_order"],
        ),
    )
    return float(chosen["threshold_bps_per_submitted_order"]), rows


def _max_drawdown(values: Sequence[float]) -> float:
    peak = 0.0
    equity = 0.0
    maximum = 0.0
    for value in values:
        equity += float(value)
        peak = max(peak, equity)
        maximum = max(maximum, peak - equity)
    return maximum


def policy_metrics(
    candidates: Sequence[Candidate],
    selected: np.ndarray,
    *,
    variant: str,
) -> dict[str, Any]:
    if len(candidates) != len(selected):
        raise ValueError("candidate/selection length mismatch")
    chosen = [candidates[index] for index in np.flatnonzero(selected)]
    outcomes = [candidate.variants[variant] for candidate in chosen]
    filled_pairs = [
        (candidate, outcome)
        for candidate, outcome in zip(chosen, outcomes)
        if outcome["fill_quantity"] > 0.0
    ]
    filled = [outcome for _, outcome in filled_pairs]
    primary_values = [float(outcome["primary_net_usd"]) for outcome in filled]
    stress_values = [float(outcome["stress_net_usd"]) for outcome in filled]
    profits = sum(value for value in primary_values if value > 0.0)
    losses = -sum(value for value in primary_values if value < 0.0)
    drawdown = _max_drawdown(primary_values)
    total = sum(primary_values)
    days = sorted({candidate.day for candidate in chosen})
    daily = {
        day: sum(
            float(outcome["primary_net_usd"])
            for candidate, outcome in filled_pairs
            if candidate.day == day
        )
        for day in days
    }
    hourly: dict[str, float] = {}
    for candidate, outcome in filled_pairs:
        timestamp = int(outcome["first_fill_us"])
        key = datetime.fromtimestamp(timestamp / 1_000_000, tz=timezone.utc).strftime("%Y-%m-%dT%H")
        hourly[key] = hourly.get(key, 0.0) + float(outcome["primary_net_usd"])
    positive_day_total = sum(max(0.0, value) for value in daily.values())
    positive_hour_total = sum(max(0.0, value) for value in hourly.values())
    waits = np.asarray([outcome["order_age_ms"] for outcome in filled], dtype=np.float64)
    queues = np.asarray(
        [outcome["initial_queue"] for outcome in outcomes if outcome["initial_queue"] is not None],
        dtype=np.float64,
    )
    ratios = np.asarray(
        [outcome["depth_ratio"] for outcome in outcomes if outcome["depth_ratio"] is not None],
        dtype=np.float64,
    )
    primary_bps = np.asarray([outcome["primary_net_bps"] for outcome in filled], dtype=np.float64)
    stress_bps = np.asarray([outcome["stress_net_bps"] for outcome in filled], dtype=np.float64)
    gross_bps = np.asarray([outcome["gross_bps"] for outcome in filled], dtype=np.float64)

    def quantile(values: np.ndarray, probability: float) -> float | None:
        return float(np.quantile(values, probability)) if len(values) else None

    def mean_field(name: str) -> float | None:
        values = [float(outcome[name]) for outcome in filled if outcome[name] is not None]
        return float(np.mean(values)) if values else None

    side_breakdown: dict[str, dict[str, Any]] = {}
    for side_value, side_name in ((1, "buy"), (-1, "sell")):
        side_filled = [
            outcome for candidate, outcome in filled_pairs if candidate.side == side_value
        ]
        side_breakdown[side_name] = {
            "filled_orders": len(side_filled),
            "net_expectancy_bps": float(np.mean([item["primary_net_bps"] for item in side_filled]))
            if side_filled
            else None,
            "total_net_usd": float(sum(item["primary_net_usd"] for item in side_filled)),
            "adverse_fill_rate_1s": float(np.mean([item["markout_1s_bps"] < 0.0 for item in side_filled]))
            if side_filled
            else None,
        }

    return {
        "submitted_orders": len(chosen),
        "resting_orders": sum(outcome["initial_queue"] is not None for outcome in outcomes),
        "filled_orders": len(filled),
        "full_fills": sum(outcome["status"] == "full_fill" for outcome in filled),
        "partial_fills": sum(outcome["status"] == "partial_fill_cancel" for outcome in filled),
        "fill_rate": len(filled) / len(chosen) if chosen else 0.0,
        "partial_fill_rate": sum(outcome["status"] == "partial_fill_cancel" for outcome in filled)
        / len(chosen)
        if chosen
        else 0.0,
        "arrival_miss_rate": sum(outcome["status"].startswith("arrival_") for outcome in outcomes)
        / len(chosen)
        if chosen
        else 0.0,
        "cancel_rate": sum(outcome["status"] != "full_fill" for outcome in outcomes) / len(chosen)
        if chosen
        else 0.0,
        "timeout_rate": sum(outcome["status"] == "timeout_cancel" for outcome in outcomes) / len(chosen)
        if chosen
        else 0.0,
        "fill_wait_ms": {
            "median": quantile(waits, 0.50),
            "p90": quantile(waits, 0.90),
            "p99": quantile(waits, 0.99),
        },
        "initial_queue": {
            "median": quantile(queues, 0.50),
            "p90": quantile(queues, 0.90),
            "p99": quantile(queues, 0.99),
        },
        "order_size_over_displayed_depth": {
            "median": quantile(ratios, 0.50),
            "p90": quantile(ratios, 0.90),
            "p99": quantile(ratios, 0.99),
        },
        "gross_expectancy_bps": float(gross_bps.mean()) if len(gross_bps) else None,
        "net_expectancy_bps": float(primary_bps.mean()) if len(primary_bps) else None,
        "stress_net_expectancy_bps": float(stress_bps.mean()) if len(stress_bps) else None,
        "total_gross_usd": float(sum(outcome["gross_usd"] for outcome in filled)),
        "total_net_usd": float(total),
        "total_fees_usd": float(sum(outcome["gross_usd"] - outcome["primary_net_usd"] for outcome in filled)),
        "stress_total_net_usd": float(sum(stress_values)),
        "profit_factor": profits / losses if losses > 0 else (math.inf if profits > 0 else 0.0),
        "max_drawdown_usd": float(drawdown),
        "pnl_over_max_drawdown": total / drawdown if drawdown > 0 else (math.inf if total > 0 else 0.0),
        "completed_opportunities_per_day": len(filled) / len(days) if days else 0.0,
        "positive_day_fraction": sum(value > 0 for value in daily.values()) / len(daily) if daily else 0.0,
        "positive_active_hour_fraction": sum(value > 0 for value in hourly.values()) / len(hourly)
        if hourly
        else 0.0,
        "day_concentration": max((max(0.0, value) for value in daily.values()), default=0.0)
        / positive_day_total
        if positive_day_total > 0
        else 1.0,
        "hour_concentration": max((max(0.0, value) for value in hourly.values()), default=0.0)
        / positive_hour_total
        if positive_hour_total > 0
        else 1.0,
        "tail_loss_bps": {
            "p01": quantile(primary_bps, 0.01),
            "p05": quantile(primary_bps, 0.05),
            "worst": float(primary_bps.min()) if len(primary_bps) else None,
        },
        "markout_bps": {
            "1s": mean_field("markout_1s_bps"),
            "3s": mean_field("markout_3s_bps"),
            "10s": mean_field("markout_10s_bps"),
        },
        "adverse_fill_rate_1s": float(
            np.mean([outcome["markout_1s_bps"] < 0.0 for outcome in filled])
        )
        if filled
        else None,
        "maker_fee_bps": PRIMARY_MAKER_FEE_BPS,
        "taker_exit_fee_bps": PRIMARY_TAKER_FEE_BPS,
        "stress_maker_fee_bps": STRESS_MAKER_FEE_BPS,
        "stress_taker_exit_fee_bps": STRESS_TAKER_FEE_BPS,
        "fee_break_even_round_trip_bps": float(gross_bps.mean()) if len(gross_bps) else None,
        "daily_net_usd": daily,
        "active_hour_net_usd": hourly,
        "side_breakdown": side_breakdown,
    }


def incremental_metrics(p0: dict[str, Any], p1: dict[str, Any]) -> dict[str, Any]:
    def difference(name: str) -> float | None:
        left, right = p1.get(name), p0.get(name)
        return float(left - right) if left is not None and right is not None else None

    return {
        "net_expectancy_bps_delta": difference("net_expectancy_bps"),
        "total_net_usd_delta": difference("total_net_usd"),
        "filled_orders_delta": int(p1["filled_orders"] - p0["filled_orders"]),
        "fill_rate_delta": difference("fill_rate"),
        "adverse_fill_rate_1s_delta": difference("adverse_fill_rate_1s"),
        "markout_1s_bps_delta": float(p1["markout_bps"]["1s"] - p0["markout_bps"]["1s"])
        if p1["markout_bps"]["1s"] is not None and p0["markout_bps"]["1s"] is not None
        else None,
        "markout_10s_bps_delta": float(p1["markout_bps"]["10s"] - p0["markout_bps"]["10s"])
        if p1["markout_bps"]["10s"] is not None and p0["markout_bps"]["10s"] is not None
        else None,
        "fees_usd_saved": float(p0["total_fees_usd"] - p1["total_fees_usd"]),
        "p0_side_breakdown": p0["side_breakdown"],
        "p1_side_breakdown": p1["side_breakdown"],
    }


def _candidate_ledger_row(candidate: Candidate) -> dict[str, Any]:
    row: dict[str, Any] = {
        "day": candidate.day,
        "symbol": candidate.symbol,
        "decision_us": candidate.decision_us,
        "side": "buy" if candidate.side > 0 else "sell",
        "limit_price": candidate.limit_price,
        "order_size": candidate.order_size,
    }
    row.update({name: value for name, value in zip(MODEL_FEATURE_NAMES, candidate.features.tolist())})
    for variant_name, outcome in candidate.variants.items():
        row.update({f"{variant_name}_{key}": value for key, value in outcome.items()})
    return row


def write_candidate_ledger(path: Path, candidates: Sequence[Candidate]) -> str:
    if not candidates:
        raise ValueError("cannot write empty candidate ledger")
    path.parent.mkdir(parents=True, exist_ok=True)
    first = _candidate_ledger_row(candidates[0])
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(first))
        writer.writeheader()
        writer.writerow(first)
        for candidate in candidates[1:]:
            writer.writerow(_candidate_ledger_row(candidate))
    return sha256_file(path)


def evaluate_gates(
    p0: dict[str, Any],
    p1: dict[str, Any],
    fold_metrics: Sequence[dict[str, Any]],
    *,
    model_failures: Sequence[str],
) -> dict[str, Any]:
    p0_net = p0["net_expectancy_bps"]
    p1_net = p1["net_expectancy_bps"]
    p0_adverse = p0["adverse_fill_rate_1s"]
    p1_adverse = p1["adverse_fill_rate_1s"]
    ratios = p1["order_size_over_displayed_depth"]
    gates = {
        "models_valid": not model_failures,
        "completed_opportunities_at_least_200": p1["filled_orders"] >= 200,
        "each_outer_fold_at_least_20_completions": bool(fold_metrics)
        and all(fold["p1"]["filled_orders"] >= 20 for fold in fold_metrics),
        "positive_primary_expectancy": p1_net is not None and p1_net > 0.0,
        "positive_primary_total_pnl": p1["total_net_usd"] > 0.0,
        "profit_factor_at_least_1_20": p1["profit_factor"] >= 1.20,
        "pnl_over_drawdown_at_least_1": p1["pnl_over_max_drawdown"] >= 1.0,
        "at_least_four_of_five_positive_outer_folds": len(fold_metrics) == 5
        and sum(fold["p1"]["total_net_usd"] > 0.0 for fold in fold_metrics) >= 4,
        "positive_day_fraction_at_least_0_80": p1["positive_day_fraction"] >= 0.80,
        "positive_active_hour_fraction_at_least_0_50": p1["positive_active_hour_fraction"] >= 0.50,
        "day_concentration_at_most_0_40": p1["day_concentration"] <= 0.40,
        "hour_concentration_at_most_0_20": p1["hour_concentration"] <= 0.20,
        "positive_stress_expectancy": p1["stress_net_expectancy_bps"] is not None
        and p1["stress_net_expectancy_bps"] > 0.0,
        "positive_stress_total_pnl": p1["stress_total_net_usd"] > 0.0,
        "p1_expectancy_beats_p0_by_0_50_bps": p1_net is not None
        and p0_net is not None
        and p1_net >= p0_net + 0.50,
        "p1_total_pnl_beats_p0": p1["total_net_usd"] > p0["total_net_usd"],
        "p1_adverse_fill_rate_improves_by_0_02": p1_adverse is not None
        and p0_adverse is not None
        and p1_adverse <= p0_adverse - 0.02,
        "fill_rate_at_least_0_005": p1["fill_rate"] >= 0.005,
        "median_order_depth_ratio_at_most_0_01": ratios["median"] is not None
        and ratios["median"] <= 0.01,
        "p90_order_depth_ratio_at_most_0_10": ratios["p90"] is not None
        and ratios["p90"] <= 0.10,
        "conservative_queue_is_primary": True,
    }
    return {"gates": gates, "pass": all(gates.values())}


def _git_output(workspace: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=workspace,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout.strip()


def _finite_json(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _finite_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_finite_json(item) for item in value]
    return value


def run_experiment(original_root: Path, workspace: Path, output_dir: Path, frozen_commit: str) -> dict[str, Any]:
    head = _git_output(workspace, "rev-parse", "HEAD")
    if head != frozen_commit:
        raise RuntimeError(f"frozen commit mismatch: expected {frozen_commit}, current {head}")
    status = _git_output(workspace, "status", "--porcelain", "--untracked-files=no")
    if status:
        raise RuntimeError("tracked worktree changes detected after freeze")
    all_candidates: list[Candidate] = []
    input_audits: list[dict[str, Any]] = []
    for day in DAYS:
        for symbol in SYMBOLS:
            print(f"simulating {day} {symbol}", file=sys.stderr, flush=True)
            candidates, audit = simulate_day(original_root, day, symbol)
            all_candidates.extend(candidates)
            input_audits.append(audit)
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = output_dir / "CODEX_EXP002_CANDIDATE_LEDGER.csv.gz"
    ledger_sha256 = write_candidate_ledger(ledger_path, all_candidates)

    outer_days = DAYS[2:]
    fold_results: list[dict[str, Any]] = []
    selected_p1 = np.zeros(len(all_candidates), dtype=bool)
    outer_mask = np.asarray([candidate.day in outer_days for candidate in all_candidates], dtype=bool)
    model_failures: list[str] = []
    model_audits: list[dict[str, Any]] = []
    for outer_position, outer_day in enumerate(outer_days, start=2):
        train_days = set(DAYS[: outer_position - 1])
        inner_day = DAYS[outer_position - 1]
        train = [candidate for candidate in all_candidates if candidate.day in train_days]
        inner = [candidate for candidate in all_candidates if candidate.day == inner_day]
        outer_indices = np.flatnonzero(
            np.asarray([candidate.day == outer_day for candidate in all_candidates], dtype=bool)
        )
        outer = [all_candidates[index] for index in outer_indices]
        try:
            models = fit_models(train)
            _, _, inner_ev = models.predict(inner)
            threshold, threshold_rows = select_threshold(inner, inner_ev)
            fill_probability, gross_prediction, outer_ev = models.predict(outer)
            selected = np.isfinite(outer_ev) & (outer_ev > threshold)
            selected_p1[outer_indices] = selected
            model_audits.append(
                {
                    "outer_day": outer_day,
                    "train_days": sorted(train_days),
                    "inner_day": inner_day,
                    "chosen_threshold_bps": threshold,
                    "threshold_selection": threshold_rows,
                    "model": models.audit(),
                    "outer_prediction": {
                        "fill_probability_mean": float(fill_probability.mean()),
                        "gross_if_filled_mean_bps": float(gross_prediction.mean()),
                        "expected_order_net_mean_bps": float(outer_ev.mean()),
                    },
                }
            )
        except Exception as exc:
            selected = np.zeros(len(outer), dtype=bool)
            model_failures.append(f"{outer_day}: {type(exc).__name__}: {exc}")
        p0_selected = np.ones(len(outer), dtype=bool)
        fold_results.append(
            {
                "outer_day": outer_day,
                "p0": policy_metrics(outer, p0_selected, variant="risk250"),
                "p1": policy_metrics(outer, selected, variant="risk250"),
            }
        )

    outer_candidates = [candidate for candidate, include in zip(all_candidates, outer_mask) if include]
    p0_selected = np.ones(len(outer_candidates), dtype=bool)
    p1_outer_selected = selected_p1[outer_mask]
    primary_p0 = policy_metrics(outer_candidates, p0_selected, variant="risk250")
    primary_p1 = policy_metrics(outer_candidates, p1_outer_selected, variant="risk250")
    diagnostic = {
        "probability_queue_q50": {
            "description": "Diagnostic only: 50% of conservatively inferred same-price sampled depth reductions are credited ahead; it cannot rescue primary failure.",
            "p0": policy_metrics(outer_candidates, p0_selected, variant="q50_250"),
            "p1": policy_metrics(outer_candidates, p1_outer_selected, variant="q50_250"),
        },
        "slower_500ms_risk_averse": {
            "description": "Slower-only latency sensitivity; it cannot rescue 250ms primary failure.",
            "p0": policy_metrics(outer_candidates, p0_selected, variant="risk500"),
            "p1": policy_metrics(outer_candidates, p1_outer_selected, variant="risk500"),
        },
    }
    gates = evaluate_gates(primary_p0, primary_p1, fold_results, model_failures=model_failures)
    result = {
        "experiment_id": EXPERIMENT_ID,
        "status": "PASS" if gates["pass"] else "FAIL",
        "sandbox_only": True,
        "profitability_claim_permitted": False,
        "frozen_commit": frozen_commit,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {"python": sys.version, "platform": platform.platform()},
        "configuration": {
            "days": list(DAYS),
            "symbols": list(SYMBOLS),
            "order_size": ORDER_SIZE,
            "candidate_spacing_s": CANDIDATE_SPACING_US / 1_000_000,
            "order_lifetime_s": ORDER_LIFETIME_US / 1_000_000,
            "primary_latency_ms": PRIMARY_LATENCY_US / 1_000,
            "slower_latency_ms": SLOW_LATENCY_US / 1_000,
            "markout_horizons_s": list(MARKOUT_HORIZONS_S),
            "primary_fees_bps": [PRIMARY_MAKER_FEE_BPS, PRIMARY_TAKER_FEE_BPS],
            "stress_fees_bps": [STRESS_MAKER_FEE_BPS, STRESS_TAKER_FEE_BPS],
            "fill_model": {"family": "LogisticRegression", "C": LOGISTIC_C},
            "markout_model": {"family": "Ridge", "alpha": RIDGE_ALPHA},
            "ev_thresholds_bps": list(EV_THRESHOLDS_BPS),
            "feature_names": list(MODEL_FEATURE_NAMES),
        },
        "input_audits": input_audits,
        "candidate_ledger": {"path": str(ledger_path), "sha256": ledger_sha256, "rows": len(all_candidates)},
        "model_failures": model_failures,
        "model_audits": model_audits,
        "outer_folds": fold_results,
        "primary_risk_averse_250ms": {"p0": primary_p0, "p1": primary_p1, "no_trade": {"total_net_usd": 0.0}},
        "p1_incremental_over_p0": incremental_metrics(primary_p0, primary_p1),
        "diagnostic_only": diagnostic,
        **gates,
    }
    result_path = output_dir / "CODEX_EXP002_RESULT.json"
    with result_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(_finite_json(result), handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-root", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    args = parser.parse_args()
    result = run_experiment(args.original_root, args.workspace, args.output_dir, args.frozen_commit)
    print(json.dumps({"experiment_id": EXPERIMENT_ID, "status": result["status"], "pass": result["pass"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
