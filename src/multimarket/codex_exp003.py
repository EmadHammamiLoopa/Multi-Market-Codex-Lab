from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import platform
import subprocess
import sys
from array import array
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Sequence, TextIO

import numpy as np

from .codex_exp001 import (
    CalibratedSideModel,
    ModelPair,
    _economic_metrics,
    calibration_metrics,
    greedy_nonoverlap,
)
from .codex_research import (
    ResearchSealError,
    assert_unsealed_day,
    assert_unsealed_path,
    canonical_sha256,
    sha256_file,
)
from .v23_phase0dl_score import BLOCKS, DayData, _load_day


EXPERIMENT_ID = "CODEX-EXP-003"
DAYS = tuple(date(2026, month, 1) for month in range(1, 8))
SYMBOLS = ("BTCUSDT", "ETHUSDT")
SOURCE_EXCHANGES = ("binance", "bybit")
SOURCE_LABELS = {"binance": "binance_spot", "bybit": "bybit_linear_perpetual"}
TRACKS = ("X0", "X1", "X2", "XALL")
PRIMARY_TRACK = "XALL"
DIAGNOSTIC_TRACKS = ("X1", "X2")
HORIZONS_S = (10, 30)
REGULARIZATION_C = (0.1, 1.0)
PROBABILITY_THRESHOLDS = (0.55, 0.65, 0.75, 0.85, 0.95)
COSTS_BPS = (8.0, 12.0)
PRIMARY_COST_BPS = 8.0
STRESS_COST_BPS = 12.0
GRID_US = 250_000
ENTRY_STEPS = 1
TRAIN_STRIDE = 4
MIN_INNER_TRADES = 20
PRIMARY_DELAY_US = 500_000
DIAGNOSTIC_DELAY_US = 250_000
STRESS_DELAY_US = 1_000_000
FUTURE_CANARY_LEAD_US = 250_000
MAX_BOOK_AGE_US = 2_000_000
GAP_BREAK_US = 2_000_000
RANDOM_SEED = 20260825

SOURCE_FEATURE_NAMES = (
    "mid_return_250ms_bps",
    "mid_return_1s_bps",
    "mid_return_3s_bps",
    "relative_spread_bps",
    "obi_l1",
    "obi_l5",
    "trade_qty_imbalance_250ms",
    "trade_qty_imbalance_1s",
    "trade_qty_imbalance_3s",
    "trade_count_imbalance_250ms",
    "trade_count_imbalance_1s",
    "trade_count_imbalance_3s",
    "realized_volatility_3s_bps",
    "source_age_ms",
    "relative_return_250ms_bps",
    "relative_return_1s_bps",
    "relative_return_3s_bps",
)
SIGNED_SOURCE_FEATURES = frozenset(
    {
        *SOURCE_FEATURE_NAMES[:3],
        "obi_l1",
        "obi_l5",
        *SOURCE_FEATURE_NAMES[6:12],
        *SOURCE_FEATURE_NAMES[14:17],
    }
)


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str = EXPERIMENT_ID
    days: tuple[str, ...] = tuple(day.isoformat() for day in DAYS)
    symbols: tuple[str, ...] = SYMBOLS
    sources: tuple[str, ...] = SOURCE_EXCHANGES
    source_representation: tuple[str, ...] = ("book_snapshot_5", "trades")
    tracks: tuple[str, ...] = TRACKS
    primary_track: str = PRIMARY_TRACK
    horizons_s: tuple[int, ...] = HORIZONS_S
    regularization_c: tuple[float, ...] = REGULARIZATION_C
    probability_thresholds: tuple[float, ...] = PROBABILITY_THRESHOLDS
    primary_delay_us: int = PRIMARY_DELAY_US
    diagnostic_delay_us: int = DIAGNOSTIC_DELAY_US
    stress_delay_us: int = STRESS_DELAY_US
    maximum_book_age_us: int = MAX_BOOK_AGE_US
    gap_break_us: int = GAP_BREAK_US
    grid_us: int = GRID_US
    entry_steps: int = ENTRY_STEPS
    training_stride: int = TRAIN_STRIDE
    minimum_inner_trades: int = MIN_INNER_TRADES
    costs_bps: tuple[float, ...] = COSTS_BPS
    primary_cost_bps: float = PRIMARY_COST_BPS
    stress_cost_bps: float = STRESS_COST_BPS
    random_seed: int = RANDOM_SEED


@dataclass(frozen=True)
class BookSeries:
    local_timestamp_us: np.ndarray
    exchange_timestamp_us: np.ndarray
    mid: np.ndarray
    spread_bps: np.ndarray
    obi_l1: np.ndarray
    obi_l5: np.ndarray
    valid: np.ndarray
    segment: np.ndarray
    realized_variance_prefix: np.ndarray
    audit: dict[str, Any]


@dataclass(frozen=True)
class TradeSeries:
    local_timestamp_us: np.ndarray
    exchange_timestamp_us: np.ndarray
    side: np.ndarray
    amount: np.ndarray
    buy_amount_prefix: np.ndarray
    sell_amount_prefix: np.ndarray
    buy_count_prefix: np.ndarray
    sell_count_prefix: np.ndarray
    audit: dict[str, Any]


@dataclass(frozen=True)
class ExternalFeatures:
    names: tuple[str, ...]
    values: np.ndarray
    valid: np.ndarray
    source_local_timestamp_us: np.ndarray
    source_age_us: np.ndarray
    audit: dict[str, Any]


@dataclass
class Exp003Day:
    day: date
    ts: np.ndarray
    bid: np.ndarray
    ask: np.ndarray
    mid: np.ndarray
    book_valid: np.ndarray
    valid: dict[str, np.ndarray]
    X: dict[str, np.ndarray]
    feature_names: dict[str, tuple[str, ...]]
    source_timestamp_us: dict[str, np.ndarray]
    source_age_us: dict[str, np.ndarray]
    source_audits: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class ExecutableOutcomes:
    valid: np.ndarray
    entry_index: np.ndarray
    exit_index: np.ndarray
    long_gross_bps: np.ndarray
    short_gross_bps: np.ndarray
    long_positive: np.ndarray
    short_positive: np.ndarray


@dataclass
class TrainOnlyStandardizer:
    mean_: np.ndarray | None = None
    scale_: np.ndarray | None = None

    def fit(self, X: np.ndarray) -> "TrainOnlyStandardizer":
        values = np.asarray(X, dtype=np.float64)
        if values.ndim != 2 or not len(values):
            raise ValueError("training scaler requires a nonempty 2D matrix")
        self.mean_ = values.mean(axis=0)
        scale = values.std(axis=0)
        self.scale_ = np.where(scale > 0.0, scale, 1.0)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        if self.mean_ is None or self.scale_ is None:
            raise RuntimeError("scaler is not fit")
        return (np.asarray(X, dtype=np.float64) - self.mean_) / self.scale_

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)


def _open_csv(path: Path) -> TextIO:
    assert_unsealed_path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("r", encoding="utf-8", newline="")


def _day_bounds(day: date) -> tuple[int, int]:
    assert_unsealed_day(day, allowed=DAYS)
    start = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1_000_000)
    return start, start + 86_400_000_000


def _as_int(value: str, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"invalid integer {name}: {value!r}") from exc


def _as_float(value: str, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"invalid float {name}: {value!r}") from exc
    if not math.isfinite(result):
        raise RuntimeError(f"non-finite {name}: {value!r}")
    return result


def _np(values: array, dtype: np.dtype[Any]) -> np.ndarray:
    return np.asarray(values, dtype=dtype)


def load_book_snapshot_5(path: Path, *, exchange: str, symbol: str, day: date) -> BookSeries:
    """Load Tardis wide book_snapshot_5 rows in file/local-arrival order.

    Exchange timestamps are retained for audit only. Equal local timestamps are one
    atomic arrival group and the final file-order state is the eligible state.
    """

    if exchange not in SOURCE_EXCHANGES or symbol not in SYMBOLS:
        raise ValueError("source is outside the frozen experiment")
    start, end = _day_bounds(day)
    required = {"exchange", "symbol", "timestamp", "local_timestamp"}
    for level in range(5):
        required.update(
            {
                f"asks[{level}].price",
                f"asks[{level}].amount",
                f"bids[{level}].price",
                f"bids[{level}].amount",
            }
        )
    local_values, exchange_values = array("q"), array("q")
    mid_values, spread_values = array("d"), array("d")
    obi1_values, obi5_values = array("d"), array("d")
    valid_values = array("b")
    raw_rows = 0
    duplicate_local_rows = 0
    invalid_rows = 0
    previous_local: int | None = None
    with _open_csv(path) as handle:
        reader = csv.DictReader(handle)
        missing = sorted(required - set(reader.fieldnames or ()))
        if missing:
            raise RuntimeError(f"{path}: missing book_snapshot_5 columns: {missing}")
        for row in reader:
            raw_rows += 1
            if row["exchange"] != exchange or row["symbol"] != symbol:
                raise RuntimeError(f"{path}: exchange/symbol mismatch on row {raw_rows}")
            local_ts = _as_int(row["local_timestamp"], "local_timestamp")
            exchange_ts = _as_int(row["timestamp"], "timestamp")
            if not start <= local_ts < end:
                raise ResearchSealError(f"{path}: row is outside frozen local-timestamp day")
            if previous_local is not None and local_ts < previous_local:
                raise RuntimeError(f"{path}: local_timestamp regressed on row {raw_rows}")
            asks_p: list[float] = []
            asks_q: list[float] = []
            bids_p: list[float] = []
            bids_q: list[float] = []
            row_valid = True
            try:
                for level in range(5):
                    asks_p.append(_as_float(row[f"asks[{level}].price"], "ask price"))
                    asks_q.append(_as_float(row[f"asks[{level}].amount"], "ask amount"))
                    bids_p.append(_as_float(row[f"bids[{level}].price"], "bid price"))
                    bids_q.append(_as_float(row[f"bids[{level}].amount"], "bid amount"))
            except RuntimeError:
                row_valid = False
            if row_valid:
                row_valid = bool(
                    all(value > 0.0 for value in (*asks_p, *asks_q, *bids_p, *bids_q))
                    and all(asks_p[i] < asks_p[i + 1] for i in range(4))
                    and all(bids_p[i] > bids_p[i + 1] for i in range(4))
                    and bids_p[0] < asks_p[0]
                )
            if row_valid:
                mid = 0.5 * (bids_p[0] + asks_p[0])
                spread = 10_000.0 * (asks_p[0] - bids_p[0]) / mid
                obi1 = (bids_q[0] - asks_q[0]) / (bids_q[0] + asks_q[0])
                bid5, ask5 = sum(bids_q), sum(asks_q)
                obi5 = (bid5 - ask5) / (bid5 + ask5)
            else:
                invalid_rows += 1
                mid = spread = obi1 = obi5 = math.nan
            if previous_local == local_ts:
                duplicate_local_rows += 1
                exchange_values[-1] = exchange_ts
                mid_values[-1] = mid
                spread_values[-1] = spread
                obi1_values[-1] = obi1
                obi5_values[-1] = obi5
                valid_values[-1] = int(row_valid)
            else:
                local_values.append(local_ts)
                exchange_values.append(exchange_ts)
                mid_values.append(mid)
                spread_values.append(spread)
                obi1_values.append(obi1)
                obi5_values.append(obi5)
                valid_values.append(int(row_valid))
            previous_local = local_ts
    if not raw_rows:
        raise RuntimeError(f"{path}: empty book_snapshot_5 file")
    local_ts = _np(local_values, np.int64)
    exchange_ts = _np(exchange_values, np.int64)
    mid = _np(mid_values, np.float64)
    spread = _np(spread_values, np.float64)
    obi1 = _np(obi1_values, np.float64)
    obi5 = _np(obi5_values, np.float64)
    valid = _np(valid_values, np.int8).astype(bool)
    breaks = np.ones(len(local_ts), dtype=bool)
    if len(local_ts) > 1:
        breaks[1:] = (
            (np.diff(local_ts) > GAP_BREAK_US)
            | (~valid[1:])
            | (~valid[:-1])
        )
    segment = np.cumsum(breaks, dtype=np.int64)
    squared = np.zeros(len(local_ts), dtype=np.float64)
    if len(local_ts) > 1:
        same = valid[1:] & valid[:-1] & (segment[1:] == segment[:-1])
        log_return = np.zeros(len(local_ts) - 1, dtype=np.float64)
        log_return[same] = np.log(mid[1:][same] / mid[:-1][same])
        squared[1:] = log_return * log_return
    rv_prefix = np.concatenate(([0.0], np.cumsum(squared, dtype=np.float64)))
    latency = local_ts - exchange_ts
    audit = {
        "path": str(path),
        "exchange": exchange,
        "symbol": symbol,
        "day": day.isoformat(),
        "raw_rows": raw_rows,
        "atomic_rows": int(len(local_ts)),
        "duplicate_local_rows_collapsed": duplicate_local_rows,
        "invalid_rows": invalid_rows,
        "gap_breaks": int(np.sum(np.diff(local_ts) > GAP_BREAK_US)),
        "exchange_timestamp_regressions": int(np.sum(np.diff(exchange_ts) < 0)),
        "local_minus_exchange_us_quantiles": {
            "p01": float(np.quantile(latency, 0.01)),
            "p50": float(np.quantile(latency, 0.50)),
            "p99": float(np.quantile(latency, 0.99)),
        },
        "ordering_clock": "local_timestamp",
        "exchange_timestamp_used_for_ordering": False,
    }
    return BookSeries(local_ts, exchange_ts, mid, spread, obi1, obi5, valid, segment, rv_prefix, audit)


def load_trades(path: Path, *, exchange: str, symbol: str, day: date) -> TradeSeries:
    if exchange not in SOURCE_EXCHANGES or symbol not in SYMBOLS:
        raise ValueError("source is outside the frozen experiment")
    start, end = _day_bounds(day)
    required = {"exchange", "symbol", "timestamp", "local_timestamp", "id", "side", "price", "amount"}
    local_values, exchange_values = array("q"), array("q")
    side_values, amount_values = array("b"), array("d")
    previous_local: int | None = None
    seen_ids: set[str] = set()
    duplicates = 0
    raw_rows = 0
    with _open_csv(path) as handle:
        reader = csv.DictReader(handle)
        missing = sorted(required - set(reader.fieldnames or ()))
        if missing:
            raise RuntimeError(f"{path}: missing trades columns: {missing}")
        for row in reader:
            raw_rows += 1
            if row["exchange"] != exchange or row["symbol"] != symbol:
                raise RuntimeError(f"{path}: exchange/symbol mismatch on row {raw_rows}")
            local_ts = _as_int(row["local_timestamp"], "local_timestamp")
            exchange_ts = _as_int(row["timestamp"], "timestamp")
            if not start <= local_ts < end:
                raise ResearchSealError(f"{path}: trade is outside frozen local-timestamp day")
            if previous_local is not None and local_ts < previous_local:
                raise RuntimeError(f"{path}: local_timestamp regressed on row {raw_rows}")
            trade_id = row["id"]
            if trade_id and trade_id in seen_ids:
                duplicates += 1
                previous_local = local_ts
                continue
            if trade_id:
                seen_ids.add(trade_id)
            side_text = row["side"].lower()
            if side_text not in {"buy", "sell"}:
                raise RuntimeError(f"{path}: unknown aggressor side on row {raw_rows}")
            amount = _as_float(row["amount"], "trade amount")
            price = _as_float(row["price"], "trade price")
            if amount <= 0.0 or price <= 0.0:
                raise RuntimeError(f"{path}: nonpositive trade value on row {raw_rows}")
            local_values.append(local_ts)
            exchange_values.append(exchange_ts)
            side_values.append(1 if side_text == "buy" else -1)
            amount_values.append(amount)
            previous_local = local_ts
    local_ts = _np(local_values, np.int64)
    exchange_ts = _np(exchange_values, np.int64)
    side = _np(side_values, np.int8)
    amount = _np(amount_values, np.float64)
    buy = np.where(side > 0, amount, 0.0)
    sell = np.where(side < 0, amount, 0.0)
    buy_count = (side > 0).astype(np.int64)
    sell_count = (side < 0).astype(np.int64)
    prefix = lambda values: np.concatenate(([0], np.cumsum(values)))
    latency = local_ts - exchange_ts if len(local_ts) else np.empty(0, dtype=np.int64)
    audit = {
        "path": str(path),
        "exchange": exchange,
        "symbol": symbol,
        "day": day.isoformat(),
        "raw_rows": raw_rows,
        "deduplicated_rows": int(len(local_ts)),
        "duplicate_trade_ids_removed": duplicates,
        "exchange_timestamp_regressions": int(np.sum(np.diff(exchange_ts) < 0)),
        "local_minus_exchange_us_quantiles": {
            key: (float(np.quantile(latency, quantile)) if len(latency) else None)
            for key, quantile in (("p01", 0.01), ("p50", 0.50), ("p99", 0.99))
        },
        "ordering_clock": "local_timestamp",
        "exchange_timestamp_used_for_ordering": False,
    }
    return TradeSeries(
        local_ts,
        exchange_ts,
        side,
        amount,
        prefix(buy).astype(np.float64),
        prefix(sell).astype(np.float64),
        prefix(buy_count).astype(np.int64),
        prefix(sell_count).astype(np.int64),
        audit,
    )


def _window_imbalance(
    trades: TradeSeries,
    cutoff_us: np.ndarray,
    window_us: int,
) -> tuple[np.ndarray, np.ndarray]:
    right = np.searchsorted(trades.local_timestamp_us, cutoff_us, side="right")
    left = np.searchsorted(trades.local_timestamp_us, cutoff_us - window_us, side="right")
    buy_amount = trades.buy_amount_prefix[right] - trades.buy_amount_prefix[left]
    sell_amount = trades.sell_amount_prefix[right] - trades.sell_amount_prefix[left]
    buy_count = trades.buy_count_prefix[right] - trades.buy_count_prefix[left]
    sell_count = trades.sell_count_prefix[right] - trades.sell_count_prefix[left]
    amount_total = buy_amount + sell_amount
    count_total = buy_count + sell_count
    quantity = np.divide(
        buy_amount - sell_amount,
        amount_total,
        out=np.zeros(len(cutoff_us), dtype=np.float64),
        where=amount_total > 0.0,
    )
    count = np.divide(
        buy_count - sell_count,
        count_total,
        out=np.zeros(len(cutoff_us), dtype=np.float64),
        where=count_total > 0,
    )
    return quantity, count


def _target_returns(
    target_mid: np.ndarray,
    target_valid: np.ndarray,
    steps: int,
) -> tuple[np.ndarray, np.ndarray]:
    values = np.full(len(target_mid), np.nan, dtype=np.float64)
    valid = np.zeros(len(target_mid), dtype=bool)
    if steps < len(target_mid):
        current = np.arange(steps, len(target_mid), dtype=np.int64)
        prior = current - steps
        ok = (
            target_valid[current]
            & target_valid[prior]
            & np.isfinite(target_mid[current])
            & np.isfinite(target_mid[prior])
            & (target_mid[current] > 0.0)
            & (target_mid[prior] > 0.0)
        )
        selected = current[ok]
        values[selected] = 10_000.0 * np.log(target_mid[selected] / target_mid[selected - steps])
        valid[selected] = True
    return values, valid


def roc_auc(labels: np.ndarray, scores: np.ndarray) -> float | None:
    y = np.asarray(labels, dtype=np.int8)
    s = np.asarray(scores, dtype=np.float64)
    finite = np.isfinite(s)
    y, s = y[finite], s[finite]
    positives = int(np.sum(y == 1))
    negatives = int(np.sum(y == 0))
    if not positives or not negatives:
        return None
    order = np.argsort(s, kind="mergesort")
    sorted_scores = s[order]
    ranks = np.arange(1, len(s) + 1, dtype=np.float64)
    start = 0
    while start < len(s):
        stop = start + 1
        while stop < len(s) and sorted_scores[stop] == sorted_scores[start]:
            stop += 1
        ranks[start:stop] = 0.5 * ((start + 1) + stop)
        start = stop
    original_ranks = np.empty(len(s), dtype=np.float64)
    original_ranks[order] = ranks
    rank_sum = float(original_ranks[y == 1].sum())
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def build_external_features(
    decision_timestamp_us: np.ndarray,
    target_mid: np.ndarray,
    target_valid: np.ndarray,
    book: BookSeries,
    trades: TradeSeries,
    *,
    delay_us: int = PRIMARY_DELAY_US,
    canary: bool = False,
) -> ExternalFeatures:
    """Build source features using only local-arrival timestamps.

    Negative delay is rejected unless this is the explicit, diagnostic-only future
    canary. No exchange timestamp participates in an index, window, or return.
    """

    decision = np.asarray(decision_timestamp_us, dtype=np.int64)
    target_mid = np.asarray(target_mid, dtype=np.float64)
    target_valid = np.asarray(target_valid, dtype=bool)
    if not (len(decision) == len(target_mid) == len(target_valid)):
        raise ValueError("decision, target mid, and target validity must align")
    if np.any(np.diff(decision) <= 0):
        raise ValueError("decision timestamps must be strictly increasing")
    if delay_us < 0 and not canary:
        raise ResearchSealError("future source access is permitted only for the explicit canary")
    if canary and delay_us != -FUTURE_CANARY_LEAD_US:
        raise ValueError("future canary uses the frozen 250 ms lead only")
    if not len(book.local_timestamp_us):
        raise RuntimeError("empty book series")
    cutoff = decision - int(delay_us)
    current = np.searchsorted(book.local_timestamp_us, cutoff, side="right") - 1
    safe_current = np.clip(current, 0, len(book.local_timestamp_us) - 1)
    has_current = current >= 0
    source_ts = np.full(len(decision), -1, dtype=np.int64)
    source_ts[has_current] = book.local_timestamp_us[safe_current[has_current]]
    source_age = decision - source_ts
    valid = has_current & book.valid[safe_current]
    valid &= source_ts <= cutoff
    if not canary:
        valid &= source_age >= delay_us
    valid &= source_age <= MAX_BOOK_AGE_US

    anchor_indices: dict[int, np.ndarray] = {}
    source_returns: dict[int, np.ndarray] = {}
    anchor_valid: dict[int, np.ndarray] = {}
    for window_us in (250_000, 1_000_000, 3_000_000):
        anchor_time = cutoff - window_us
        anchor = np.searchsorted(book.local_timestamp_us, anchor_time, side="right") - 1
        safe_anchor = np.clip(anchor, 0, len(book.local_timestamp_us) - 1)
        ok = anchor >= 0
        ok &= book.valid[safe_anchor]
        ok &= (anchor_time - book.local_timestamp_us[safe_anchor]) <= MAX_BOOK_AGE_US
        ok &= book.segment[safe_anchor] == book.segment[safe_current]
        returns = np.full(len(decision), np.nan, dtype=np.float64)
        selected = np.flatnonzero(ok & has_current)
        returns[selected] = 10_000.0 * np.log(
            book.mid[safe_current[selected]] / book.mid[safe_anchor[selected]]
        )
        anchor_indices[window_us] = safe_anchor
        source_returns[window_us] = returns
        anchor_valid[window_us] = ok
        valid &= ok

    qty_250, count_250 = _window_imbalance(trades, cutoff, 250_000)
    qty_1s, count_1s = _window_imbalance(trades, cutoff, 1_000_000)
    qty_3s, count_3s = _window_imbalance(trades, cutoff, 3_000_000)
    anchor_3s = anchor_indices[3_000_000]
    realized_variance = (
        book.realized_variance_prefix[safe_current + 1]
        - book.realized_variance_prefix[anchor_3s + 1]
    )
    realized_volatility = 10_000.0 * np.sqrt(np.maximum(realized_variance, 0.0))
    target_returns: dict[int, np.ndarray] = {}
    target_return_valid: dict[int, np.ndarray] = {}
    for window_us in (250_000, 1_000_000, 3_000_000):
        steps = window_us // GRID_US
        target_returns[window_us], target_return_valid[window_us] = _target_returns(
            target_mid, target_valid, steps
        )
        valid &= target_return_valid[window_us]
    values = np.column_stack(
        (
            source_returns[250_000],
            source_returns[1_000_000],
            source_returns[3_000_000],
            book.spread_bps[safe_current],
            book.obi_l1[safe_current],
            book.obi_l5[safe_current],
            qty_250,
            qty_1s,
            qty_3s,
            count_250,
            count_1s,
            count_3s,
            realized_volatility,
            source_age / 1_000.0,
            source_returns[250_000] - target_returns[250_000],
            source_returns[1_000_000] - target_returns[1_000_000],
            source_returns[3_000_000] - target_returns[3_000_000],
        )
    ).astype(np.float32)
    valid &= np.all(np.isfinite(values), axis=1)
    audit = {
        "delay_us": delay_us,
        "future_canary": canary,
        "decision_rows": int(len(decision)),
        "valid_rows": int(valid.sum()),
        "valid_fraction": float(valid.mean()) if len(valid) else 0.0,
        "minimum_valid_age_us": int(source_age[valid].min()) if np.any(valid) else None,
        "maximum_valid_age_us": int(source_age[valid].max()) if np.any(valid) else None,
        "local_timestamp_eligibility_violations": int(np.sum(valid & (source_ts > cutoff))),
        "exchange_timestamp_used": False,
        "book": book.audit,
        "trades": trades.audit,
    }
    return ExternalFeatures(SOURCE_FEATURE_NAMES, values, valid, source_ts, source_age, audit)


def prefix_feature_names(source: str) -> tuple[str, ...]:
    return tuple(f"{SOURCE_LABELS[source]}__{name}" for name in SOURCE_FEATURE_NAMES)


def assemble_tracks(
    base: DayData,
    spot: ExternalFeatures,
    bybit: ExternalFeatures,
) -> Exp003Day:
    n = len(base.ts)
    if len(spot.values) != n or len(bybit.values) != n:
        raise ValueError("external features must align exactly to the target grid")
    common = base.valid["L2"] & spot.valid & bybit.valid
    base_x = base.X["L2"].astype(np.float32, copy=False)
    track_x = {
        "X0": base_x,
        "X1": np.column_stack((base_x, spot.values)).astype(np.float32),
        "X2": np.column_stack((base_x, bybit.values)).astype(np.float32),
        "XALL": np.column_stack((base_x, spot.values, bybit.values)).astype(np.float32),
    }
    feature_names = {
        "X0": tuple(BLOCKS["L2"]),
        "X1": tuple(BLOCKS["L2"]) + prefix_feature_names("binance"),
        "X2": tuple(BLOCKS["L2"]) + prefix_feature_names("bybit"),
        "XALL": tuple(BLOCKS["L2"]) + prefix_feature_names("binance") + prefix_feature_names("bybit"),
    }
    # Every comparator uses identical common-support rows. Missing-source coverage
    # can therefore never make X0 and XALL incomparable.
    valid = {track: common.copy() for track in TRACKS}
    return Exp003Day(
        base.day,
        base.ts,
        base.bid,
        base.ask,
        base.mid,
        base.book_valid,
        valid,
        track_x,
        feature_names,
        {
            "binance": spot.source_local_timestamp_us,
            "bybit": bybit.source_local_timestamp_us,
        },
        {"binance": spot.source_age_us, "bybit": bybit.source_age_us},
        {"binance": spot.audit, "bybit": bybit.audit},
    )


def external_paths(root: Path, source: str, symbol: str, day: date) -> tuple[Path, Path]:
    if source not in SOURCE_EXCHANGES or symbol not in SYMBOLS:
        raise ValueError("unfrozen source")
    assert_unsealed_day(day, allowed=DAYS)
    book = root / source / "book_snapshot_5" / symbol / f"{day.isoformat()}.csv.gz"
    trades = root / source / "trades" / symbol / f"{day.isoformat()}.csv.gz"
    assert_unsealed_path(book)
    assert_unsealed_path(trades)
    return book, trades


def load_exp003_day(
    feature_dir: Path,
    external_root: Path,
    symbol: str,
    day: date,
    *,
    delay_us: int = PRIMARY_DELAY_US,
    canary: bool = False,
) -> Exp003Day:
    assert_unsealed_day(day, allowed=DAYS)
    base_path = feature_dir / symbol / f"{day.isoformat()}_FEATURES250.csv"
    assert_unsealed_path(base_path)
    base = _load_day(base_path, day)
    built: dict[str, ExternalFeatures] = {}
    for source in SOURCE_EXCHANGES:
        book_path, trade_path = external_paths(external_root, source, symbol, day)
        book = load_book_snapshot_5(book_path, exchange=source, symbol=symbol, day=day)
        trades = load_trades(trade_path, exchange=source, symbol=symbol, day=day)
        built[source] = build_external_features(
            base.ts,
            base.mid,
            base.book_valid,
            book,
            trades,
            delay_us=delay_us,
            canary=canary,
        )
    return assemble_tracks(base, built["binance"], built["bybit"])


def executable_outcomes(day: Exp003Day, track: str, horizon_s: int) -> ExecutableOutcomes:
    assert_unsealed_day(day.day, allowed=DAYS)
    if track not in TRACKS:
        raise ValueError(f"unknown track: {track}")
    horizon_steps = int(round(horizon_s * 1_000_000 / GRID_US))
    n = len(day.ts)
    row = np.arange(n, dtype=np.int64)
    entry = row + ENTRY_STEPS
    exit_ = entry + horizon_steps
    safe_entry = np.minimum(entry, max(n - 1, 0))
    safe_exit = np.minimum(exit_, max(n - 1, 0))
    valid = day.valid[track].copy()
    valid &= exit_ < n
    if n:
        valid &= day.book_valid[safe_entry] & day.book_valid[safe_exit]
    long_gross = np.full(n, np.nan, dtype=np.float64)
    short_gross = np.full(n, np.nan, dtype=np.float64)
    selected = np.flatnonzero(valid)
    if len(selected):
        entry_idx = entry[selected]
        exit_idx = exit_[selected]
        long_gross[selected] = 10_000.0 * np.log(day.bid[exit_idx] / day.ask[entry_idx])
        short_gross[selected] = 10_000.0 * np.log(day.bid[entry_idx] / day.ask[exit_idx])
    valid &= np.isfinite(long_gross) & np.isfinite(short_gross)
    return ExecutableOutcomes(
        valid,
        entry,
        exit_,
        long_gross,
        short_gross,
        valid & ((long_gross - PRIMARY_COST_BPS) > 0.0),
        valid & ((short_gross - PRIMARY_COST_BPS) > 0.0),
    )


def split_calibration_selection(
    outcomes: ExecutableOutcomes,
    *,
    horizon_s: int,
    n_rows: int,
) -> tuple[np.ndarray, np.ndarray]:
    midpoint = n_rows // 2
    span = ENTRY_STEPS + int(round(horizon_s * 1_000_000 / GRID_US))
    row = np.arange(n_rows, dtype=np.int64)
    calibration = np.flatnonzero(outcomes.valid & ((row + span) < midpoint))
    selection = np.flatnonzero(outcomes.valid & (row >= midpoint))
    return calibration, selection


def _training_rows(
    days: Sequence[Exp003Day],
    track: str,
    horizon_s: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    features: list[np.ndarray] = []
    long_labels: list[np.ndarray] = []
    short_labels: list[np.ndarray] = []
    for day in days:
        outcomes = executable_outcomes(day, track, horizon_s)
        index = np.flatnonzero(outcomes.valid)[::TRAIN_STRIDE]
        if len(index):
            features.append(day.X[track][index])
            long_labels.append(outcomes.long_positive[index].astype(np.int8))
            short_labels.append(outcomes.short_positive[index].astype(np.int8))
    if not features:
        return (
            np.empty((0, len(days[0].feature_names[track]) if days else 0), dtype=np.float32),
            np.empty(0, dtype=np.int8),
            np.empty(0, dtype=np.int8),
        )
    return np.concatenate(features), np.concatenate(long_labels), np.concatenate(short_labels)


def fit_side(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_calibration: np.ndarray,
    y_calibration: np.ndarray,
    calibration_net_bps: np.ndarray,
    *,
    c_value: float,
) -> CalibratedSideModel:
    if len(np.unique(y_train)) != 2 or len(np.unique(y_calibration)) != 2:
        raise ValueError("training and calibration slices must each contain both classes")
    from sklearn.linear_model import LogisticRegression

    scaler = TrainOnlyStandardizer()
    transformed_train = scaler.fit_transform(X_train)
    base = LogisticRegression(
        C=float(c_value),
        class_weight="balanced",
        max_iter=300,
        random_state=RANDOM_SEED,
        solver="lbfgs",
    )
    base.fit(transformed_train, y_train)
    calibration_logit = base.decision_function(scaler.transform(X_calibration)).reshape(-1, 1)
    calibrator = LogisticRegression(
        C=1_000_000.0,
        max_iter=200,
        random_state=RANDOM_SEED,
        solver="lbfgs",
    )
    calibrator.fit(calibration_logit, y_calibration)
    positive_mean = float(calibration_net_bps[y_calibration == 1].mean())
    nonpositive_mean = float(calibration_net_bps[y_calibration == 0].mean())
    return CalibratedSideModel(
        scaler, base, calibrator, positive_mean, nonpositive_mean
    )


def fit_pair(
    train_days: Sequence[Exp003Day],
    inner_day: Exp003Day,
    track: str,
    horizon_s: int,
    c_value: float,
) -> tuple[ModelPair, ExecutableOutcomes, np.ndarray, np.ndarray]:
    X_train, y_long, y_short = _training_rows(train_days, track, horizon_s)
    outcomes = executable_outcomes(inner_day, track, horizon_s)
    calibration, selection = split_calibration_selection(
        outcomes, horizon_s=horizon_s, n_rows=len(inner_day.ts)
    )
    calibration = calibration[::TRAIN_STRIDE]
    if not len(X_train) or not len(calibration) or not len(selection):
        raise ValueError("empty train, calibration, or selection slice")
    X_calibration = inner_day.X[track][calibration]
    long_net = outcomes.long_gross_bps[calibration] - PRIMARY_COST_BPS
    short_net = outcomes.short_gross_bps[calibration] - PRIMARY_COST_BPS
    long_model = fit_side(
        X_train,
        y_long,
        X_calibration,
        outcomes.long_positive[calibration].astype(np.int8),
        long_net,
        c_value=c_value,
    )
    short_model = fit_side(
        X_train,
        y_short,
        X_calibration,
        outcomes.short_positive[calibration].astype(np.int8),
        short_net,
        c_value=c_value,
    )
    return ModelPair(long_model, short_model), outcomes, calibration, selection


def score_actions(
    day: Exp003Day,
    outcomes: ExecutableOutcomes,
    indices: np.ndarray,
    long_probability: np.ndarray,
    short_probability: np.ndarray,
    long_utility: np.ndarray,
    short_utility: np.ndarray,
    *,
    probability_threshold: float,
    horizon_s: int,
) -> dict[str, Any]:
    arrays = (
        long_probability,
        short_probability,
        long_utility,
        short_utility,
    )
    if any(len(value) != len(indices) for value in arrays):
        raise ValueError("forecast arrays must align")
    finite = np.logical_and.reduce(tuple(np.isfinite(value) for value in arrays))
    long_ok = finite & (long_probability >= probability_threshold) & (long_utility > 0.0)
    short_ok = finite & (short_probability >= probability_threshold) & (short_utility > 0.0)
    direction = np.zeros(len(indices), dtype=np.int8)
    direction[long_ok & (~short_ok | (long_utility > short_utility))] = 1
    direction[short_ok & (~long_ok | (short_utility > long_utility))] = -1
    candidates = np.flatnonzero(direction)
    chosen_global = greedy_nonoverlap(indices[candidates], horizon_s=horizon_s)
    local_by_global = {int(value): position for position, value in enumerate(indices.tolist())}
    chosen_local = np.asarray(
        [local_by_global[int(value)] for value in chosen_global], dtype=np.int64
    )
    chosen_direction = direction[chosen_local]
    gross = np.where(
        chosen_direction > 0,
        outcomes.long_gross_bps[chosen_global],
        outcomes.short_gross_bps[chosen_global],
    )
    costs = {str(int(cost)): _economic_metrics(gross, cost) for cost in COSTS_BPS}
    primary_net = gross - PRIMARY_COST_BPS
    hour_pnl: dict[str, float] = {}
    for timestamp, pnl in zip(day.ts[chosen_global].tolist(), primary_net.tolist()):
        hour = int((timestamp % 86_400_000_000) // 3_600_000_000)
        key = f"{day.day.isoformat()}T{hour:02d}"
        hour_pnl[key] = hour_pnl.get(key, 0.0) + float(pnl)
    return {
        "probability_threshold": probability_threshold,
        "candidate_rows": int(len(candidates)),
        "directions": {
            "long": int(np.sum(chosen_direction > 0)),
            "short": int(np.sum(chosen_direction < 0)),
        },
        "signal_indices": chosen_global.tolist(),
        "signal_timestamp_us": day.ts[chosen_global].astype(np.int64).tolist(),
        "gross_values_bps": gross.tolist(),
        "hour_pnl_8bps": hour_pnl,
        "costs": costs,
    }


def _candidate_score(
    day: Exp003Day,
    track: str,
    horizon_s: int,
    c_value: float,
    models: ModelPair,
    outcomes: ExecutableOutcomes,
    selection: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    X = day.X[track][selection]
    p_long, u_long = models.long.forecast(X)
    p_short, u_short = models.short.forecast(X)
    return score_actions(
        day,
        outcomes,
        selection,
        p_long,
        p_short,
        u_long,
        u_short,
        probability_threshold=threshold,
        horizon_s=horizon_s,
    )


def _selection_key(candidate: dict[str, Any]) -> tuple[float, float, float, int, float, float]:
    primary = candidate["selection_score"]["costs"]["8"]
    return (
        float(primary["net_bps_trade"]),
        float(primary["total_net_bps"]),
        float(primary["profit_factor"]),
        -int(candidate["horizon_s"]),
        float(candidate["probability_threshold"]),
        -float(candidate["c_value"]),
    )


def select_configuration(
    train_days: Sequence[Exp003Day],
    inner_day: Exp003Day,
    track: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Select the best covered inner configuration, even when inner economics are negative.

    Unlike EXP-001, outer observability is not censored by a positive-inner gate.
    Minimum nonoverlapping coverage remains mandatory. This new rule belongs only
    to EXP-003 and does not amend or rerun EXP-001.
    """

    tested = 0
    eligible: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for horizon_s in HORIZONS_S:
        for c_value in REGULARIZATION_C:
            try:
                models, outcomes, calibration, selection = fit_pair(
                    train_days, inner_day, track, horizon_s, c_value
                )
            except ValueError as exc:
                invalid.append(
                    {"horizon_s": horizon_s, "c_value": c_value, "reason": str(exc)}
                )
                continue
            for threshold in PROBABILITY_THRESHOLDS:
                tested += 1
                score = _candidate_score(
                    inner_day,
                    track,
                    horizon_s,
                    c_value,
                    models,
                    outcomes,
                    selection,
                    threshold,
                )
                if score["costs"]["8"]["trades"] >= MIN_INNER_TRADES:
                    eligible.append(
                        {
                            "track": track,
                            "horizon_s": horizon_s,
                            "c_value": c_value,
                            "probability_threshold": threshold,
                            "models": models,
                            "calibration_rows": int(len(calibration)),
                            "selection_rows": int(len(selection)),
                            "selection_score": score,
                        }
                    )
    if not eligible:
        return None, {
            "tested": tested,
            "eligible": 0,
            "invalid_models": invalid,
            "reason": "NO_COVERED_CONFIGURATION",
        }
    selected = max(eligible, key=_selection_key)
    public = {key: value for key, value in selected.items() if key != "models"}
    return selected, {
        "tested": tested,
        "eligible": len(eligible),
        "selected": public,
        "invalid_models": invalid,
    }


def score_outer(day: Exp003Day, selected: dict[str, Any]) -> dict[str, Any]:
    track = str(selected["track"])
    horizon_s = int(selected["horizon_s"])
    outcomes = executable_outcomes(day, track, horizon_s)
    indices = np.flatnonzero(outcomes.valid)
    models: ModelPair = selected["models"]
    p_long, u_long = models.long.forecast(day.X[track][indices])
    p_short, u_short = models.short.forecast(day.X[track][indices])
    score = score_actions(
        day,
        outcomes,
        indices,
        p_long,
        p_short,
        u_long,
        u_short,
        probability_threshold=float(selected["probability_threshold"]),
        horizon_s=horizon_s,
    )
    score["calibration"] = {
        "long": {
            **calibration_metrics(outcomes.long_positive[indices], p_long),
            "roc_auc": roc_auc(outcomes.long_positive[indices], p_long),
        },
        "short": {
            **calibration_metrics(outcomes.short_positive[indices], p_short),
            "roc_auc": roc_auc(outcomes.short_positive[indices], p_short),
        },
    }
    score["configuration"] = {
        "track": track,
        "horizon_s": horizon_s,
        "c_value": float(selected["c_value"]),
        "probability_threshold": float(selected["probability_threshold"]),
    }
    return score


def score_symbol(
    days: Sequence[Exp003Day],
    symbol: str,
    *,
    outer_transform_kind: str | None = None,
) -> dict[str, Any]:
    if tuple(day.day for day in days) != DAYS:
        raise ValueError("days must be the frozen January-July sequence")
    folds: list[dict[str, Any]] = []
    for outer_position in range(2, len(days)):
        train_days = days[: outer_position - 1]
        inner_day = days[outer_position - 1]
        outer_day = days[outer_position]
        track_results: dict[str, Any] = {}
        for track in TRACKS:
            selected, selection_audit = select_configuration(train_days, inner_day, track)
            evaluation_day = (
                diagnostic_transform(outer_day, "XALL", outer_transform_kind)
                if outer_transform_kind is not None and track == "XALL"
                else outer_day
            )
            outer = score_outer(evaluation_day, selected) if selected is not None else None
            track_results[track] = {
                "selection": selection_audit,
                "outer": outer,
            }
        folds.append(
            {
                "symbol": symbol,
                "evaluation_day": outer_day.day.isoformat(),
                "training_days": [day.day.isoformat() for day in train_days],
                "inner_day": inner_day.day.isoformat(),
                "tracks": track_results,
            }
        )
    return {"symbol": symbol, "folds": folds}


def _pool_track(
    symbol_results: Sequence[dict[str, Any]],
    track: str,
) -> dict[str, Any]:
    by_day: dict[str, list[dict[str, Any]]] = {
        day.isoformat(): [] for day in DAYS[2:]
    }
    selection_complete = True
    for symbol_result in symbol_results:
        for fold in symbol_result["folds"]:
            outer = fold["tracks"][track]["outer"]
            if outer is None:
                selection_complete = False
            else:
                by_day[fold["evaluation_day"]].append(outer)
    gross_by_cost: dict[str, list[float]] = {"8": [], "12": []}
    fold_rows: list[dict[str, Any]] = []
    all_hours: dict[str, float] = {}
    auc_values: dict[str, list[float]] = {"long": [], "short": []}
    for evaluation_day, scores in by_day.items():
        fold_net: list[float] = []
        fold_trades = 0
        for score in scores:
            gross = [float(value) for value in score["gross_values_bps"]]
            fold_net.extend(value - PRIMARY_COST_BPS for value in gross)
            fold_trades += len(gross)
            for cost in gross_by_cost:
                gross_by_cost[cost].extend(gross)
            for hour, pnl in score["hour_pnl_8bps"].items():
                all_hours[hour] = all_hours.get(hour, 0.0) + float(pnl)
            for side in ("long", "short"):
                auc = score["calibration"][side].get("roc_auc")
                if auc is not None:
                    auc_values[side].append(float(auc))
        fold_rows.append(
            {
                "evaluation_day": evaluation_day,
                "symbols_scored": len(scores),
                "trades": fold_trades,
                "total_net_bps_8": float(sum(fold_net)),
                "net_bps_trade_8": float(np.mean(fold_net)) if fold_net else None,
            }
        )
    metrics: dict[str, dict[str, Any]] = {}
    for cost, gross_values in gross_by_cost.items():
        metrics[cost] = _economic_metrics(
            np.asarray(gross_values, dtype=np.float64), float(cost)
        )
    primary = metrics["8"]
    primary["active_hours"] = len(all_hours)
    primary["positive_active_hour_fraction"] = (
        float(np.mean(np.asarray(list(all_hours.values())) > 0.0)) if all_hours else 0.0
    )
    positive_fold_profit = [
        max(0.0, float(fold["total_net_bps_8"])) for fold in fold_rows
    ]
    total_positive = sum(positive_fold_profit)
    max_fold_share = (
        max(positive_fold_profit, default=0.0) / total_positive if total_positive > 0.0 else 1.0
    )
    worst_fold = min(
        (float(fold["total_net_bps_8"]) for fold in fold_rows), default=0.0
    )
    return {
        "track": track,
        "selection_complete_all_symbols_all_folds": selection_complete,
        "folds": fold_rows,
        "positive_folds": int(sum(fold["total_net_bps_8"] > 0.0 for fold in fold_rows)),
        "maximum_positive_fold_share": max_fold_share,
        "worst_fold_total_net_bps": worst_fold,
        "positive_fold_profit_bps": total_positive,
        "active_hour_net_bps": all_hours,
        "mean_outer_roc_auc": {
            side: (float(np.mean(values)) if values else None)
            for side, values in auc_values.items()
        },
        "costs": metrics,
    }


def evaluate_gates(pools: dict[str, dict[str, Any]]) -> dict[str, Any]:
    primary_pool = pools[PRIMARY_TRACK]
    comparator = pools["X0"]
    primary = primary_pool["costs"]["8"]
    stress = primary_pool["costs"]["12"]
    x0_primary = comparator["costs"]["8"]
    catastrophic_limit = -0.50 * float(primary_pool["positive_fold_profit_bps"])
    gates = {
        "xall_selection_complete_all_five_folds_both_symbols": primary_pool[
            "selection_complete_all_symbols_all_folds"
        ],
        "x0_comparator_observed_all_five_folds_both_symbols": comparator[
            "selection_complete_all_symbols_all_folds"
        ],
        "at_least_four_of_five_positive_calendar_folds": primary_pool["positive_folds"] >= 4,
        "primary_net_expectancy_at_least_1bps": primary["net_bps_trade"] >= 1.0,
        "primary_total_net_positive": primary["total_net_bps"] > 0.0,
        "primary_profit_factor_at_least_1_25": primary["profit_factor"] >= 1.25,
        "primary_pnl_to_drawdown_at_least_2": primary["pnl_to_drawdown"] >= 2.0,
        "stress_expectancy_positive": stress["net_bps_trade"] > 0.0,
        "stress_total_net_positive": stress["total_net_bps"] > 0.0,
        "at_least_100_nonoverlapping_outer_trades": primary["trades"] >= 100,
        "positive_active_hour_fraction_at_least_0_55": primary[
            "positive_active_hour_fraction"
        ]
        >= 0.55,
        "maximum_positive_fold_share_at_most_0_40": primary_pool[
            "maximum_positive_fold_share"
        ]
        <= 0.40,
        "no_catastrophic_fold": primary_pool["worst_fold_total_net_bps"] >= catastrophic_limit,
        "xall_expectancy_strictly_beats_x0": primary["net_bps_trade"]
        > x0_primary["net_bps_trade"],
        "xall_total_net_strictly_beats_x0": primary["total_net_bps"]
        > x0_primary["total_net_bps"],
        "common_support_comparison": True,
    }
    return {"gates": gates, "pass": all(gates.values())}


def diagnostic_transform(day: Exp003Day, track: str, kind: str) -> Exp003Day:
    """Return a diagnostic-only copy; transformed rows can never replace primary."""

    if track not in {"X1", "X2", "XALL"}:
        raise ValueError("diagnostics require an external-information track")
    base_width = len(BLOCKS["L2"])
    values = day.X[track].copy()
    valid = {name: mask.copy() for name, mask in day.valid.items()}
    external = values[:, base_width:]
    if kind == "timestamp_permutation":
        rng = np.random.default_rng(RANDOM_SEED)
        external[:] = external[rng.permutation(len(external))]
    elif kind == "sign_placebo":
        names = day.feature_names[track][base_width:]
        signed = np.asarray(
            [name.split("__", 1)[-1] in SIGNED_SOURCE_FEATURES for name in names], dtype=bool
        )
        external[:, signed] *= -1.0
    elif kind == "time_placebo":
        lag_rows = 60_000_000 // GRID_US
        external[lag_rows:] = external[:-lag_rows]
        external[:lag_rows] = np.nan
        for name in TRACKS:
            valid[name][:lag_rows] = False
    else:
        raise ValueError(f"unknown diagnostic transform: {kind}")
    X = {name: matrix.copy() for name, matrix in day.X.items()}
    X[track] = values
    return Exp003Day(
        day.day,
        day.ts.copy(),
        day.bid.copy(),
        day.ask.copy(),
        day.mid.copy(),
        day.book_valid.copy(),
        valid,
        X,
        dict(day.feature_names),
        {name: value.copy() for name, value in day.source_timestamp_us.items()},
        {name: value.copy() for name, value in day.source_age_us.items()},
        dict(day.source_audits),
    )


def inject_future_leak_canary(day: Exp003Day, track: str = "XALL") -> Exp003Day:
    """Append a diagnostic-only 10 s future target return positive control."""

    if track != "XALL":
        raise ValueError("the frozen future canary is XALL-only")
    horizon_steps = 10_000_000 // GRID_US
    future = np.full(len(day.ts), np.nan, dtype=np.float32)
    rows = np.arange(len(day.ts), dtype=np.int64)
    exit_index = rows + ENTRY_STEPS + horizon_steps
    valid_canary = exit_index < len(day.ts)
    selected = np.flatnonzero(valid_canary)
    future[selected] = (
        10_000.0
        * np.log(day.mid[exit_index[selected]] / day.mid[selected])
    ).astype(np.float32)
    X = {name: matrix.copy() for name, matrix in day.X.items()}
    X[track] = np.column_stack((X[track], future)).astype(np.float32)
    valid = {name: mask.copy() for name, mask in day.valid.items()}
    for name in TRACKS:
        valid[name] &= valid_canary & np.isfinite(future)
    names = dict(day.feature_names)
    names[track] = names[track] + ("CANARY_ONLY__future_target_return_10s_bps",)
    return Exp003Day(
        day.day,
        day.ts.copy(),
        day.bid.copy(),
        day.ask.copy(),
        day.mid.copy(),
        day.book_valid.copy(),
        valid,
        X,
        names,
        {name: value.copy() for name, value in day.source_timestamp_us.items()},
        {name: value.copy() for name, value in day.source_age_us.items()},
        dict(day.source_audits),
    )


def _git(workspace: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=workspace, text=True, capture_output=True, check=True
    )
    return completed.stdout.strip()


def assert_frozen_workspace(workspace: Path, frozen_commit: str) -> None:
    if len(frozen_commit) != 40:
        raise RuntimeError("full 40-character frozen commit required")
    current = _git(workspace, "rev-parse", "HEAD")
    if current != frozen_commit:
        raise RuntimeError(f"frozen commit mismatch: expected {frozen_commit}, current {current}")
    if _git(workspace, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("tracked worktree changes detected after freeze")


def input_manifest(feature_dir: Path, external_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for symbol in SYMBOLS:
        for day in DAYS:
            base = feature_dir / symbol / f"{day.isoformat()}_FEATURES250.csv"
            assert_unsealed_path(base)
            paths = [("binance-futures", "FEATURES250", base)]
            for source in SOURCE_EXCHANGES:
                book, trades = external_paths(external_root, source, symbol, day)
                paths.extend(((source, "book_snapshot_5", book), (source, "trades", trades)))
            for source, data_type, path in paths:
                if not path.exists():
                    raise FileNotFoundError(path)
                records.append(
                    {
                        "symbol": symbol,
                        "day": day.isoformat(),
                        "source": source,
                        "data_type": data_type,
                        "path": str(path),
                        "bytes": path.stat().st_size,
                        "sha256": sha256_file(path),
                    }
                )
    return records


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def run(
    feature_dir: Path,
    external_root: Path,
    output_path: Path,
    workspace: Path,
    frozen_commit: str,
    *,
    delay_us: int = PRIMARY_DELAY_US,
    canary: bool = False,
    transform_kind: str | None = None,
) -> dict[str, Any]:
    assert_frozen_workspace(workspace, frozen_commit)
    if transform_kind in {"timestamp_permutation", "sign_placebo", "time_placebo"}:
        if delay_us != PRIMARY_DELAY_US or canary:
            raise ValueError("placebos use the primary 500 ms source build")
        run_kind = transform_kind.upper()
    elif delay_us == DIAGNOSTIC_DELAY_US and not canary:
        run_kind = "DIAGNOSTIC_250MS"
    elif delay_us == STRESS_DELAY_US and not canary:
        run_kind = "STRESS_1000MS"
    elif delay_us == PRIMARY_DELAY_US and not canary:
        run_kind = "PRIMARY_500MS"
    elif delay_us == -FUTURE_CANARY_LEAD_US and canary:
        run_kind = "FUTURE_LEAK_CANARY"
    else:
        raise ValueError("delay/canary mode is outside the frozen experiment")
    manifest = input_manifest(feature_dir, external_root)
    symbol_results: list[dict[str, Any]] = []
    source_audits: list[dict[str, Any]] = []
    for symbol in SYMBOLS:
        days: list[Exp003Day] = []
        for day in DAYS:
            print(f"loading {run_kind} {symbol} {day}", file=sys.stderr, flush=True)
            loaded = load_exp003_day(
                feature_dir,
                external_root,
                symbol,
                day,
                delay_us=delay_us,
                canary=canary,
            )
            if transform_kind is not None and transform_kind != "sign_placebo":
                loaded = diagnostic_transform(loaded, "XALL", transform_kind)
            if canary:
                loaded = inject_future_leak_canary(loaded)
            days.append(loaded)
            source_audits.append(
                {"symbol": symbol, "day": day.isoformat(), **loaded.source_audits}
            )
        symbol_results.append(
            score_symbol(
                days,
                symbol,
                outer_transform_kind=(
                    "sign_placebo" if transform_kind == "sign_placebo" else None
                ),
            )
        )
    pools = {track: _pool_track(symbol_results, track) for track in TRACKS}
    counterfactual_gate_result = evaluate_gates(pools)
    gate_result = counterfactual_gate_result if run_kind == "PRIMARY_500MS" else None
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "run_kind": run_kind,
        "status": (
            "PASS" if gate_result and gate_result["pass"] else "FAIL"
            if gate_result is not None
            else "DIAGNOSTIC_ONLY"
        ),
        "sandbox_development_only": True,
        "profitability_claim_permitted": False,
        "frozen_commit": frozen_commit,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {"python": sys.version, "platform": platform.platform()},
        "configuration": asdict(ExperimentConfig()),
        "configuration_sha256": canonical_sha256(ExperimentConfig()),
        "input_manifest": manifest,
        "source_audits": source_audits,
        "symbol_results": symbol_results,
        "pools": pools,
        "gate_result": gate_result,
        "diagnostic_counterfactual_gate_result": (
            counterfactual_gate_result if gate_result is None else None
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return payload


def evaluate_diagnostic_suite(
    primary: dict[str, Any],
    diagnostic_runs: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    by_kind = {str(run["run_kind"]): run for run in diagnostic_runs}
    required = {
        "DIAGNOSTIC_250MS",
        "STRESS_1000MS",
        "TIMESTAMP_PERMUTATION",
        "SIGN_PLACEBO",
        "TIME_PLACEBO",
        "FUTURE_LEAK_CANARY",
    }
    missing = sorted(required - set(by_kind))
    primary_auc = primary["pools"]["XALL"]["mean_outer_roc_auc"]
    canary_auc = (
        by_kind["FUTURE_LEAK_CANARY"]["pools"]["XALL"]["mean_outer_roc_auc"]
        if "FUTURE_LEAK_CANARY" in by_kind
        else {"long": None, "short": None}
    )
    gains = [
        float(canary_auc[side]) - float(primary_auc[side])
        for side in ("long", "short")
        if canary_auc.get(side) is not None and primary_auc.get(side) is not None
    ]
    gates = {
        "all_diagnostics_present": not missing,
        "future_canary_auc_gain_at_least_0_02": bool(gains) and max(gains) >= 0.02,
        "timestamp_permutation_does_not_pass_primary_gates": bool(
            "TIMESTAMP_PERMUTATION" in by_kind
            and not by_kind["TIMESTAMP_PERMUTATION"][
                "diagnostic_counterfactual_gate_result"
            ]["pass"]
        ),
        "sign_placebo_does_not_pass_primary_gates": bool(
            "SIGN_PLACEBO" in by_kind
            and not by_kind["SIGN_PLACEBO"][
                "diagnostic_counterfactual_gate_result"
            ]["pass"]
        ),
        "time_placebo_does_not_pass_primary_gates": bool(
            "TIME_PLACEBO" in by_kind
            and not by_kind["TIME_PLACEBO"][
                "diagnostic_counterfactual_gate_result"
            ]["pass"]
        ),
        "optimistic_250ms_is_non_rescuing": True,
        "extra_1000ms_is_non_rescuing": True,
        "source_dropout_is_diagnostic_only": True,
    }
    diagnostic_pass = all(gates.values())
    return {
        "missing": missing,
        "canary_auc_gain": gains,
        "gates": gates,
        "diagnostic_suite_pass": diagnostic_pass,
        "final_pass": bool(primary["gate_result"]["pass"] and diagnostic_pass),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature-dir", type=Path, required=True)
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    parser.add_argument(
        "--mode",
        choices=(
            "primary",
            "diagnostic-250ms",
            "stress-1000ms",
            "timestamp-permutation",
            "sign-placebo",
            "time-placebo",
            "future-canary",
        ),
        default="primary",
    )
    args = parser.parse_args(argv)
    modes = {
        "primary": (PRIMARY_DELAY_US, False, None),
        "diagnostic-250ms": (DIAGNOSTIC_DELAY_US, False, None),
        "stress-1000ms": (STRESS_DELAY_US, False, None),
        "timestamp-permutation": (PRIMARY_DELAY_US, False, "timestamp_permutation"),
        "sign-placebo": (PRIMARY_DELAY_US, False, "sign_placebo"),
        "time-placebo": (PRIMARY_DELAY_US, False, "time_placebo"),
        "future-canary": (-FUTURE_CANARY_LEAD_US, True, None),
    }
    delay, canary, transform_kind = modes[args.mode]
    result = run(
        args.feature_dir,
        args.external_root,
        args.output,
        args.workspace,
        args.frozen_commit,
        delay_us=delay,
        canary=canary,
        transform_kind=transform_kind,
    )
    print(json.dumps({"experiment_id": EXPERIMENT_ID, "status": result["status"]}, indent=2))
    if args.mode == "primary":
        return 0 if result["gate_result"]["pass"] else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
