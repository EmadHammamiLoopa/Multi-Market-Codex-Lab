"""Pure executable first-passage targets for DEV030.

The module deliberately contains no filesystem, market-data loading, network,
feature, model, opportunity-gating, or economic-evaluation code.  Callers must
provide an in-memory DayData-like object with ``ts``, ``bid``, ``ask``, and
``book_valid`` one-dimensional arrays.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Protocol, Sequence

import numpy as np

GRID_US = 250_000
LATENCY_MS = 250
DAY_US = 86_400_000_000
LOG_BPS = 10_000.0

LONG_FIRST = "LONG_FIRST"
SHORT_FIRST = "SHORT_FIRST"
NONE = "NONE"

INVALID_DAY_BOUNDARY = "day_boundary_crossing"
INVALID_ENTRY_TIMESTAMP = "entry_timestamp_missing"
INVALID_HORIZON_TIMESTAMP = "horizon_timestamp_missing"
INVALID_PATH_GRID = "path_grid_missing"
INVALID_ENTRY_QUOTE = "entry_quote_invalid"
INVALID_PATH_QUOTE = "path_quote_invalid"
INVALID_CROSSED_BOOK = "crossed_book"
INVALID_SAME_ROW_AMBIGUOUS = "same_row_ambiguous"


class DayDataLike(Protocol):
    """Minimum in-memory interface consumed by the labeler."""

    ts: Any
    bid: Any
    ask: Any
    book_valid: Any


JsonScalar = str | int | float | bool | None
FirstPassageRecord = dict[str, JsonScalar]


@dataclass(frozen=True)
class _DayArrays:
    ts: np.ndarray
    bid: np.ndarray
    ask: np.ndarray
    book_valid: np.ndarray


def _as_day_arrays(day: DayDataLike) -> _DayArrays:
    """Validate and borrow the four required arrays without filling data."""

    try:
        raw_ts = np.asarray(day.ts)
        bid = np.asarray(day.bid, dtype=np.float64)
        ask = np.asarray(day.ask, dtype=np.float64)
        raw_book_valid = np.asarray(day.book_valid)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(
            "day must expose numeric ts/bid/ask and boolean book_valid arrays"
        ) from exc

    arrays = (raw_ts, bid, ask, raw_book_valid)
    if any(array.ndim != 1 for array in arrays):
        raise ValueError("day arrays must be one-dimensional")
    if len(raw_ts) == 0:
        raise ValueError("day arrays must not be empty")
    if not (len(raw_ts) == len(bid) == len(ask) == len(raw_book_valid)):
        raise ValueError("day arrays must have equal lengths")
    if raw_ts.dtype.kind not in "iu":
        raise ValueError("timestamps must be exact integers in microseconds")

    ts = raw_ts.astype(np.int64, copy=False)
    if np.any(np.diff(ts) <= 0):
        raise ValueError("timestamps must be unique and strictly chronological")

    if raw_book_valid.dtype.kind == "b":
        book_valid = raw_book_valid.astype(bool, copy=False)
    elif raw_book_valid.dtype.kind in "iu" and bool(
        np.all((raw_book_valid == 0) | (raw_book_valid == 1))
    ):
        book_valid = raw_book_valid.astype(bool, copy=False)
    else:
        raise ValueError("book_valid must contain exact boolean or 0/1 values")

    return _DayArrays(ts=ts, bid=bid, ask=ask, book_valid=book_valid)


def _positive_finite_number(value: Any, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a positive finite number")
    try:
        converted = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive finite number") from exc
    if not math.isfinite(converted) or converted <= 0.0:
        raise ValueError(f"{name} must be a positive finite number")
    return converted


def _configuration(
    *, horizon_seconds: Any, barrier_bps: Any, latency_ms: Any
) -> tuple[float, int, float, int]:
    horizon = _positive_finite_number(horizon_seconds, name="horizon_seconds")
    barrier = _positive_finite_number(barrier_bps, name="barrier_bps")
    latency = _positive_finite_number(latency_ms, name="latency_ms")

    horizon_us_float = horizon * 1_000_000.0
    horizon_us = int(round(horizon_us_float))
    if not math.isclose(horizon_us_float, horizon_us, rel_tol=0.0, abs_tol=1e-7):
        raise ValueError("horizon_seconds must resolve to exact microseconds")
    if horizon_us % GRID_US != 0:
        raise ValueError("horizon_seconds must align to the 250 ms grid")

    latency_us_float = latency * 1_000.0
    latency_us = int(round(latency_us_float))
    if not math.isclose(latency_us_float, latency_us, rel_tol=0.0, abs_tol=1e-7):
        raise ValueError("latency_ms must resolve to exact microseconds")
    if latency_us != GRID_US:
        raise ValueError("DEV030 first-passage latency must be exactly 250 ms")

    return horizon, horizon_us, barrier, latency_us


def _decision_indices(values: Sequence[int] | np.ndarray, *, rows: int) -> np.ndarray:
    raw = np.asarray(values)
    if raw.ndim != 1 or raw.dtype.kind not in "iu":
        raise ValueError("decision_indices must be a one-dimensional integer array")
    indices = raw.astype(np.int64, copy=False)
    if bool(np.any(indices < 0)) or bool(np.any(indices >= rows)):
        raise ValueError("decision index outside supplied in-memory day")
    return indices


def _base_record(
    *,
    decision_timestamp_us: int,
    entry_timestamp_us: int,
    horizon_seconds: float,
    barrier_bps: float,
) -> FirstPassageRecord:
    return {
        "decision_timestamp_us": int(decision_timestamp_us),
        "entry_timestamp_us": int(entry_timestamp_us),
        "label": None,
        "target_valid": False,
        "invalid_reason": None,
        "same_row_ambiguous": False,
        "time_to_first_barrier_ms": None,
        "barrier_reached_timestamp_us": None,
        "long_max_favorable_excursion_bps": None,
        "long_max_adverse_excursion_bps": None,
        "short_max_favorable_excursion_bps": None,
        "short_max_adverse_excursion_bps": None,
        "entry_spread_bps": None,
        "horizon_seconds": float(horizon_seconds),
        "barrier_bps": float(barrier_bps),
        "latency_ms": int(LATENCY_MS),
    }


def _invalid_record(
    base: FirstPassageRecord,
    reason: str,
    *,
    same_row_ambiguous: bool = False,
) -> FirstPassageRecord:
    record = dict(base)
    record["label"] = None
    record["target_valid"] = False
    record["invalid_reason"] = str(reason)
    record["same_row_ambiguous"] = bool(same_row_ambiguous)
    return record


def _exact_position(ts: np.ndarray, timestamp_us: int) -> int | None:
    position = int(np.searchsorted(ts, timestamp_us, side="left"))
    if position >= len(ts) or int(ts[position]) != timestamp_us:
        return None
    return position


def _executable_path_bps(
    bid_path: np.ndarray, ask_path: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Return long-liquidation and short-cover executable log-bps paths."""

    entry_ask = float(ask_path[0])
    entry_bid = float(bid_path[0])
    long_path = LOG_BPS * np.log(bid_path / entry_ask)
    short_path = LOG_BPS * np.log(entry_bid / ask_path)
    return long_path, short_path


def _first_true_index(mask: np.ndarray) -> int | None:
    locations = np.flatnonzero(mask)
    return None if len(locations) == 0 else int(locations[0])


def _label_one(
    arrays: _DayArrays,
    decision_index: int,
    *,
    horizon_seconds: float,
    horizon_us: int,
    barrier_bps: float,
    latency_us: int,
) -> FirstPassageRecord:
    decision_timestamp_us = int(arrays.ts[decision_index])
    entry_timestamp_us = decision_timestamp_us + latency_us
    horizon_timestamp_us = entry_timestamp_us + horizon_us
    base = _base_record(
        decision_timestamp_us=decision_timestamp_us,
        entry_timestamp_us=entry_timestamp_us,
        horizon_seconds=horizon_seconds,
        barrier_bps=barrier_bps,
    )

    day_start_us = (decision_timestamp_us // DAY_US) * DAY_US
    if entry_timestamp_us >= day_start_us + DAY_US or horizon_timestamp_us >= (
        day_start_us + DAY_US
    ):
        return _invalid_record(base, INVALID_DAY_BOUNDARY)

    entry_position = _exact_position(arrays.ts, entry_timestamp_us)
    if entry_position is None:
        return _invalid_record(base, INVALID_ENTRY_TIMESTAMP)
    horizon_position = _exact_position(arrays.ts, horizon_timestamp_us)
    if horizon_position is None:
        return _invalid_record(base, INVALID_HORIZON_TIMESTAMP)

    horizon_steps = horizon_us // GRID_US
    expected_count = horizon_steps + 1
    path_slice = slice(entry_position, horizon_position + 1)
    path_ts = arrays.ts[path_slice]
    expected_ts = entry_timestamp_us + np.arange(
        expected_count, dtype=np.int64
    ) * GRID_US
    if len(path_ts) != expected_count or not bool(np.array_equal(path_ts, expected_ts)):
        return _invalid_record(base, INVALID_PATH_GRID)

    bid_path = arrays.bid[path_slice]
    ask_path = arrays.ask[path_slice]
    valid_path = arrays.book_valid[path_slice]

    entry_quote_ok = bool(valid_path[0]) and bool(
        np.isfinite(bid_path[0])
        and np.isfinite(ask_path[0])
        and bid_path[0] > 0.0
        and ask_path[0] > 0.0
    )
    if not entry_quote_ok:
        return _invalid_record(base, INVALID_ENTRY_QUOTE)

    path_quotes_ok = bool(np.all(valid_path)) and bool(
        np.all(np.isfinite(bid_path))
        and np.all(np.isfinite(ask_path))
        and np.all(bid_path > 0.0)
        and np.all(ask_path > 0.0)
    )
    if not path_quotes_ok:
        return _invalid_record(base, INVALID_PATH_QUOTE)

    long_path, short_path = _executable_path_bps(bid_path, ask_path)
    long_touch = _first_true_index(long_path >= barrier_bps)
    short_touch = _first_true_index(short_path >= barrier_bps)

    # This branch precedes the crossed-book diagnostic deliberately.  With a
    # positive symmetric barrier and uncrossed books it is structurally
    # unreachable; if malformed prices make both first touches appear in one
    # row, the required ambiguity diagnostic must remain explicit rather than
    # allowing arbitrary column order to choose a direction.
    if long_touch is not None and long_touch == short_touch:
        return _invalid_record(
            base,
            INVALID_SAME_ROW_AMBIGUOUS,
            same_row_ambiguous=True,
        )

    if bool(np.any(bid_path > ask_path)):
        return _invalid_record(base, INVALID_CROSSED_BOOK)

    if long_touch is None and short_touch is None:
        label = NONE
        touch_position = None
    elif short_touch is None or (
        long_touch is not None and long_touch < short_touch
    ):
        label = LONG_FIRST
        touch_position = long_touch
    else:
        label = SHORT_FIRST
        touch_position = short_touch

    record = dict(base)
    record["label"] = label
    record["target_valid"] = True
    record["invalid_reason"] = None
    record["same_row_ambiguous"] = False
    if touch_position is not None:
        touch_timestamp_us = int(path_ts[touch_position])
        record["time_to_first_barrier_ms"] = float(
            (touch_timestamp_us - entry_timestamp_us) / 1_000.0
        )
        record["barrier_reached_timestamp_us"] = touch_timestamp_us

    record["long_max_favorable_excursion_bps"] = float(
        max(0.0, float(np.max(long_path)))
    )
    record["long_max_adverse_excursion_bps"] = float(
        max(0.0, -float(np.min(long_path)))
    )
    record["short_max_favorable_excursion_bps"] = float(
        max(0.0, float(np.max(short_path)))
    )
    record["short_max_adverse_excursion_bps"] = float(
        max(0.0, -float(np.min(short_path)))
    )
    record["entry_spread_bps"] = float(
        LOG_BPS * math.log(float(ask_path[0]) / float(bid_path[0]))
    )
    return record


def label_first_passage_targets(
    day: DayDataLike,
    decision_indices: Sequence[int] | np.ndarray,
    *,
    horizon_seconds: float,
    barrier_bps: float,
    latency_ms: int = LATENCY_MS,
) -> list[FirstPassageRecord]:
    """Label explicit decisions using complete executable 250 ms quote paths.

    The input is never mutated.  No interpolation, filling, path discovery,
    filesystem access, or market-data loading is performed.  Results preserve
    input decision order and contain only built-in JSON-compatible scalars.
    """

    arrays = _as_day_arrays(day)
    horizon, horizon_us, barrier, latency_us = _configuration(
        horizon_seconds=horizon_seconds,
        barrier_bps=barrier_bps,
        latency_ms=latency_ms,
    )
    indices = _decision_indices(decision_indices, rows=len(arrays.ts))
    return [
        _label_one(
            arrays,
            int(decision_index),
            horizon_seconds=horizon,
            horizon_us=horizon_us,
            barrier_bps=barrier,
            latency_us=latency_us,
        )
        for decision_index in indices
    ]


__all__ = [
    "GRID_US",
    "LATENCY_MS",
    "LONG_FIRST",
    "SHORT_FIRST",
    "NONE",
    "label_first_passage_targets",
]
