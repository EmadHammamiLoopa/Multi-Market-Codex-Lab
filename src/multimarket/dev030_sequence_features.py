"""Pure causal sequence features for DEV030-P2A.

The module accepts only explicitly supplied in-memory arrays.  It performs no
filesystem access, data loading, network access, artifact writing, model
fitting, normalization, label construction, or performance evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

import numpy as np


GRID_US = 250_000
GRID_NS = 250_000_000
GRID_SECONDS = 0.25
LATENCY_MS = 250
LATENCY_US = 250_000
LATENCY_NS = 250_000_000

FROZEN_WINDOWS_SECONDS = (8, 16, 32, 60)
WINDOW_ROW_COUNTS = {seconds: seconds * 4 + 1 for seconds in FROZEN_WINDOWS_SECONDS}

PRICE = "PRICE"
PRICE_BOOK = "PRICE_BOOK"
PRICE_BOOK_FLOW = "PRICE_BOOK_FLOW"
PRICE_BOOK_FLOW_DYNAMICS = "PRICE_BOOK_FLOW_DYNAMICS"
FULL = PRICE_BOOK_FLOW_DYNAMICS
BLOCK_ORDER = (PRICE, PRICE_BOOK, PRICE_BOOK_FLOW, PRICE_BOOK_FLOW_DYNAMICS)

DERIVED_MID_RETURN = "mid_log_return_250ms_bps"

PRICE_STORED_FEATURES = (
    "spread_bps",
    "microprice_minus_mid_bps",
)

BOOK_ADDITIONS = (
    "obi_l1",
    "obi_l5",
    "obi_l10",
    "log_bid_qty_l1",
    "log_ask_qty_l1",
    "log_bid_depth_l5",
    "log_ask_depth_l5",
    "log_bid_depth_l10",
    "log_ask_depth_l10",
)

FLOW_ADDITIONS = (
    "ofi_l1_250ms",
    "ofi_l1_1s",
    "ofi_l1_3s",
    "mlofi_l5_250ms",
    "mlofi_l5_1s",
    "mlofi_l5_3s",
    "mlofi_l10_250ms",
    "mlofi_l10_1s",
    "mlofi_l10_3s",
    "trade_qty_imbalance_250ms",
    "trade_qty_imbalance_1s",
    "trade_qty_imbalance_3s",
    "trade_count_imbalance_250ms",
    "trade_count_imbalance_1s",
    "trade_count_imbalance_3s",
)

DYNAMICS_ADDITIONS = (
    "d_obi_l1_250ms",
    "d_obi_l1_1s",
    "d_obi_l5_250ms",
    "d_obi_l5_1s",
    "d_obi_l10_250ms",
    "d_obi_l10_1s",
    "d_spread_bps_250ms",
    "d_spread_bps_1s",
    "d_microprice_minus_mid_bps_250ms",
    "d_microprice_minus_mid_bps_1s",
    "bid_replenish_l5_1s",
    "ask_replenish_l5_1s",
    "bid_deplete_l5_1s",
    "ask_deplete_l5_1s",
    "trade_qty_imbalance_1s_x_obi_l5",
    "trade_qty_imbalance_1s_x_microprice_minus_mid_bps",
    "mlofi_l5_1s_x_spread_bps",
)

ALLOWED_STORED_FEATURES = (
    PRICE_STORED_FEATURES + BOOK_ADDITIONS + FLOW_ADDITIONS + DYNAMICS_ADDITIONS
)
SOURCE_ONLY_FIELDS = ("mid",)

BLOCK_STORED_FEATURES = {
    PRICE: PRICE_STORED_FEATURES,
    PRICE_BOOK: PRICE_STORED_FEATURES + BOOK_ADDITIONS,
    PRICE_BOOK_FLOW: PRICE_STORED_FEATURES + BOOK_ADDITIONS + FLOW_ADDITIONS,
    PRICE_BOOK_FLOW_DYNAMICS: ALLOWED_STORED_FEATURES,
}
BLOCK_FEATURES = {
    block: stored + (DERIVED_MID_RETURN,)
    for block, stored in BLOCK_STORED_FEATURES.items()
}
ALLOWED_FEATURES = BLOCK_FEATURES[FULL]

# The nested Phase0DL masks establish the validity of each cumulative stored
# block.  book_valid is also required because every derived return endpoint
# must have a valid book state.
BLOCK_VALIDITY_MASKS = {
    PRICE: ("book_valid", "l0_valid"),
    PRICE_BOOK: ("book_valid", "l0_valid"),
    PRICE_BOOK_FLOW: ("book_valid", "l1_valid"),
    PRICE_BOOK_FLOW_DYNAMICS: ("book_valid", "l2_valid"),
}

NATURALLY_SIGNED_FEATURES = frozenset(
    (
        DERIVED_MID_RETURN,
        "microprice_minus_mid_bps",
        "obi_l1",
        "obi_l5",
        "obi_l10",
        *FLOW_ADDITIONS,
        "d_obi_l1_250ms",
        "d_obi_l1_1s",
        "d_obi_l5_250ms",
        "d_obi_l5_1s",
        "d_obi_l10_250ms",
        "d_obi_l10_1s",
        "d_spread_bps_250ms",
        "d_spread_bps_1s",
        "d_microprice_minus_mid_bps_250ms",
        "d_microprice_minus_mid_bps_1s",
        "trade_qty_imbalance_1s_x_obi_l5",
        "trade_qty_imbalance_1s_x_microprice_minus_mid_bps",
        "mlofi_l5_1s_x_spread_bps",
    )
)


def _lookback_manifest() -> dict[str, int]:
    lookbacks = {name: 0 for name in PRICE_STORED_FEATURES + BOOK_ADDITIONS}

    for name in (
        "ofi_l1_250ms",
        "mlofi_l5_250ms",
        "mlofi_l10_250ms",
        "trade_qty_imbalance_250ms",
        "trade_count_imbalance_250ms",
    ):
        lookbacks[name] = GRID_NS
    for name in (
        "ofi_l1_1s",
        "mlofi_l5_1s",
        "mlofi_l10_1s",
        "trade_qty_imbalance_1s",
        "trade_count_imbalance_1s",
    ):
        lookbacks[name] = 1_000_000_000
    for name in (
        "ofi_l1_3s",
        "mlofi_l5_3s",
        "mlofi_l10_3s",
        "trade_qty_imbalance_3s",
        "trade_count_imbalance_3s",
    ):
        lookbacks[name] = 3_000_000_000

    for name in (
        "d_obi_l1_250ms",
        "d_obi_l5_250ms",
        "d_obi_l10_250ms",
        "d_spread_bps_250ms",
        "d_microprice_minus_mid_bps_250ms",
    ):
        lookbacks[name] = GRID_NS
    for name in (
        "d_obi_l1_1s",
        "d_obi_l5_1s",
        "d_obi_l10_1s",
        "d_spread_bps_1s",
        "d_microprice_minus_mid_bps_1s",
        "bid_replenish_l5_1s",
        "ask_replenish_l5_1s",
        "bid_deplete_l5_1s",
        "ask_deplete_l5_1s",
        "trade_qty_imbalance_1s_x_obi_l5",
        "trade_qty_imbalance_1s_x_microprice_minus_mid_bps",
        "mlofi_l5_1s_x_spread_bps",
    ):
        lookbacks[name] = 1_000_000_000

    lookbacks[DERIVED_MID_RETURN] = GRID_NS
    return lookbacks


INTERNAL_LOOKBACK_NS = _lookback_manifest()


class SequenceFeatureError(ValueError):
    """Deterministic fail-closed rejection of an in-memory representation."""

    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = str(reason)
        message = self.reason if detail is None else f"{self.reason}: {detail}"
        super().__init__(message)


@dataclass(frozen=True)
class SequenceFeatureInput:
    """Explicit arrays consumed by the pure P2A feature engine."""

    timestamps_us: Any
    features: Mapping[str, Any]
    mid: Any
    validity_masks: Mapping[str, Any]


@dataclass(frozen=True)
class InformationIntervals:
    representation_start_us: int
    representation_end_us: int
    raw_source_start_us: int
    raw_source_end_us: int
    window_seconds: int
    block_internal_lookback_ns: int
    target_horizon_seconds: int
    latency_ms: int
    total_information_span_ns: int


@dataclass(frozen=True)
class CommonSupport:
    mask: np.ndarray
    indices: np.ndarray
    decision_timestamps_us: np.ndarray


@dataclass(frozen=True)
class _Arrays:
    timestamps_us: np.ndarray
    features: dict[str, np.ndarray]
    mid: np.ndarray
    validity_masks: dict[str, np.ndarray]


def _block(block: str) -> str:
    if block not in BLOCK_ORDER:
        raise SequenceFeatureError("unsupported_block", str(block))
    return block


def block_feature_names(block: str) -> tuple[str, ...]:
    """Return the exact cumulative predictor order for a frozen block."""

    return BLOCK_FEATURES[_block(block)]


def feature_internal_lookback_ns(feature_name: str) -> int:
    """Return the audited causal source lookback for one allowed feature."""

    if feature_name not in INTERNAL_LOOKBACK_NS:
        raise SequenceFeatureError("unsupported_feature", str(feature_name))
    return int(INTERNAL_LOOKBACK_NS[feature_name])


def block_internal_lookback_ns(block: str) -> int:
    """Return the maximum exact internal lookback in a cumulative block."""

    names = block_feature_names(block)
    return int(max(INTERNAL_LOOKBACK_NS[name] for name in names))


def window_observation_count(window_seconds: int) -> int:
    if isinstance(window_seconds, (bool, np.bool_)) or window_seconds not in (
        FROZEN_WINDOWS_SECONDS
    ):
        raise SequenceFeatureError("unsupported_window", str(window_seconds))
    return int(WINDOW_ROW_COUNTS[int(window_seconds)])


def _exact_integer(value: Any, *, reason: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, np.integer)
    ):
        raise SequenceFeatureError(reason)
    return int(value)


def information_intervals(
    *,
    decision_timestamp_us: int,
    window_seconds: int,
    block: str,
    target_horizon_seconds: int,
) -> InformationIntervals:
    """Return stored-row and full raw-source intervals without making labels."""

    decision_us = _exact_integer(
        decision_timestamp_us, reason="decision_timestamp_must_be_integer_us"
    )
    window_rows = window_observation_count(window_seconds)
    del window_rows
    horizon = _exact_integer(
        target_horizon_seconds, reason="target_horizon_must_be_integer_seconds"
    )
    if horizon <= 0:
        raise SequenceFeatureError("target_horizon_must_be_positive")

    window_us = int(window_seconds) * 1_000_000
    lookback_ns = block_internal_lookback_ns(block)
    lookback_us = lookback_ns // 1_000
    horizon_us = horizon * 1_000_000
    representation_start = decision_us - window_us
    raw_start = representation_start - lookback_us
    raw_end = decision_us + LATENCY_US + horizon_us
    total_span_ns = (
        int(window_seconds) * 1_000_000_000
        + lookback_ns
        + LATENCY_NS
        + horizon * 1_000_000_000
    )
    return InformationIntervals(
        representation_start_us=int(representation_start),
        representation_end_us=int(decision_us),
        raw_source_start_us=int(raw_start),
        raw_source_end_us=int(raw_end),
        window_seconds=int(window_seconds),
        block_internal_lookback_ns=int(lookback_ns),
        target_horizon_seconds=int(horizon),
        latency_ms=int(LATENCY_MS),
        total_information_span_ns=int(total_span_ns),
    )


def _as_arrays(data: SequenceFeatureInput) -> _Arrays:
    try:
        raw_timestamps = np.asarray(data.timestamps_us)
        mid = np.asarray(data.mid, dtype=np.float64)
    except (AttributeError, TypeError, ValueError) as exc:
        raise SequenceFeatureError("invalid_input_arrays") from exc

    if raw_timestamps.ndim != 1 or mid.ndim != 1:
        raise SequenceFeatureError("arrays_must_be_one_dimensional")
    if len(raw_timestamps) == 0:
        raise SequenceFeatureError("timestamps_must_not_be_empty")
    if raw_timestamps.dtype.kind not in "iu":
        raise SequenceFeatureError("timestamps_must_be_integer_us")
    if len(mid) != len(raw_timestamps):
        raise SequenceFeatureError("mismatched_array_lengths", "mid")

    timestamps = raw_timestamps.astype(np.int64, copy=False)
    differences = np.diff(timestamps)
    if bool(np.any(differences == 0)):
        raise SequenceFeatureError("duplicate_timestamps")
    if bool(np.any(differences < 0)):
        raise SequenceFeatureError("non_monotonic_timestamps")
    if bool(np.any(timestamps % GRID_US != 0)):
        raise SequenceFeatureError("off_grid_timestamp")

    if not isinstance(data.features, Mapping):
        raise SequenceFeatureError("features_must_be_mapping")
    feature_arrays: dict[str, np.ndarray] = {}
    for name, values in data.features.items():
        try:
            array = np.asarray(values, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise SequenceFeatureError("invalid_feature_array", str(name)) from exc
        if array.ndim != 1:
            raise SequenceFeatureError("arrays_must_be_one_dimensional", str(name))
        if len(array) != len(timestamps):
            raise SequenceFeatureError("mismatched_array_lengths", str(name))
        feature_arrays[str(name)] = array

    if not isinstance(data.validity_masks, Mapping):
        raise SequenceFeatureError("validity_masks_must_be_mapping")
    mask_arrays: dict[str, np.ndarray] = {}
    for name, values in data.validity_masks.items():
        array = np.asarray(values)
        if array.ndim != 1:
            raise SequenceFeatureError("arrays_must_be_one_dimensional", str(name))
        if len(array) != len(timestamps):
            raise SequenceFeatureError("mismatched_array_lengths", str(name))
        if array.dtype.kind != "b":
            raise SequenceFeatureError("validity_mask_must_be_boolean", str(name))
        mask_arrays[str(name)] = array.astype(bool, copy=False)

    return _Arrays(
        timestamps_us=timestamps,
        features=feature_arrays,
        mid=mid,
        validity_masks=mask_arrays,
    )


def _exact_position(timestamps: np.ndarray, timestamp_us: int) -> int | None:
    position = int(np.searchsorted(timestamps, timestamp_us, side="left"))
    if position >= len(timestamps) or int(timestamps[position]) != timestamp_us:
        return None
    return position


def _snapshot_indices(arrays: _Arrays, decision_timestamp_us: int) -> np.ndarray:
    decision_us = _exact_integer(
        decision_timestamp_us, reason="decision_timestamp_must_be_integer_us"
    )
    position = _exact_position(arrays.timestamps_us, decision_us)
    if position is None:
        raise SequenceFeatureError("decision_timestamp_missing")
    return np.asarray([position], dtype=np.int64)


def _window_indices(
    arrays: _Arrays, decision_timestamp_us: int, window_seconds: int
) -> np.ndarray:
    decision_us = _exact_integer(
        decision_timestamp_us, reason="decision_timestamp_must_be_integer_us"
    )
    expected_count = window_observation_count(window_seconds)
    start_us = decision_us - int(window_seconds) * 1_000_000
    start = _exact_position(arrays.timestamps_us, start_us)
    end = _exact_position(arrays.timestamps_us, decision_us)
    if start is None or end is None:
        raise SequenceFeatureError("window_grid_missing")
    indices = np.arange(start, end + 1, dtype=np.int64)
    expected = start_us + np.arange(expected_count, dtype=np.int64) * GRID_US
    if len(indices) != expected_count or not bool(
        np.array_equal(arrays.timestamps_us[indices], expected)
    ):
        raise SequenceFeatureError("window_grid_missing")
    return indices


def _required_values(
    arrays: _Arrays, *, block: str, indices: np.ndarray
) -> dict[str, np.ndarray]:
    selected: dict[str, np.ndarray] = {}
    for name in BLOCK_STORED_FEATURES[_block(block)]:
        if name not in arrays.features:
            raise SequenceFeatureError("missing_required_feature", name)
        values = arrays.features[name][indices]
        if not bool(np.all(np.isfinite(values))):
            raise SequenceFeatureError("non_finite_required_feature", name)
        selected[name] = values

    for mask_name in BLOCK_VALIDITY_MASKS[block]:
        if mask_name not in arrays.validity_masks:
            raise SequenceFeatureError("missing_required_validity_mask", mask_name)
        if not bool(np.all(arrays.validity_masks[mask_name][indices])):
            raise SequenceFeatureError("invalid_required_mask", mask_name)
    return selected


def _derived_mid_returns(arrays: _Arrays, indices: np.ndarray) -> np.ndarray:
    first_timestamp = int(arrays.timestamps_us[int(indices[0])])
    prior_timestamp = first_timestamp - GRID_US
    prior_position = _exact_position(arrays.timestamps_us, prior_timestamp)
    if prior_position is None or prior_position + 1 != int(indices[0]):
        raise SequenceFeatureError("missing_prior_mid_endpoint")

    prior_indices = np.concatenate(
        (np.asarray([prior_position], dtype=np.int64), indices[:-1])
    )
    current_mid = arrays.mid[indices]
    prior_mid = arrays.mid[prior_indices]
    if not bool(
        np.all(np.isfinite(current_mid))
        and np.all(np.isfinite(prior_mid))
        and np.all(current_mid > 0.0)
        and np.all(prior_mid > 0.0)
    ):
        raise SequenceFeatureError("invalid_mid_for_derived_return")

    if "book_valid" not in arrays.validity_masks:
        raise SequenceFeatureError("missing_required_validity_mask", "book_valid")
    book_valid = arrays.validity_masks["book_valid"]
    if not bool(np.all(book_valid[indices]) and np.all(book_valid[prior_indices])):
        raise SequenceFeatureError("invalid_required_mask", "book_valid")

    returns = 10_000.0 * np.log(current_mid / prior_mid)
    if not bool(np.all(np.isfinite(returns))):
        raise SequenceFeatureError("non_finite_derived_return")
    return returns.astype(np.float64, copy=False)


def extract_snapshot(
    data: SequenceFeatureInput, *, decision_timestamp_us: int, block: str
) -> dict[str, float]:
    """Extract S0 at exactly ``t`` with the derived causal 250 ms return."""

    arrays = _as_arrays(data)
    indices = _snapshot_indices(arrays, decision_timestamp_us)
    selected = _required_values(arrays, block=_block(block), indices=indices)
    selected[DERIVED_MID_RETURN] = _derived_mid_returns(arrays, indices)
    return {
        name: float(selected[name][0])
        for name in BLOCK_FEATURES[block]
    }


def summarize_series(
    values: Any, *, naturally_signed: bool = False
) -> dict[str, float]:
    """Compute only the frozen deterministic S1 statistics."""

    try:
        series = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise SequenceFeatureError("invalid_summary_series") from exc
    if series.ndim != 1 or len(series) == 0:
        raise SequenceFeatureError("summary_series_must_be_nonempty_1d")
    if not bool(np.all(np.isfinite(series))):
        raise SequenceFeatureError("non_finite_summary_series")

    elapsed = np.arange(len(series), dtype=np.float64) * GRID_SECONDS
    if len(series) == 1 or bool(np.all(series == series[0])):
        slope = 0.0
    else:
        centered_time = elapsed - float(np.mean(elapsed))
        denominator = float(np.dot(centered_time, centered_time))
        centered_values = series - float(np.mean(series))
        slope = float(np.dot(centered_time, centered_values) / denominator)

    result = {
        "last": float(series[-1]),
        "mean": float(np.mean(series)),
        "std": float(np.std(series, ddof=0)),
        "minimum": float(np.min(series)),
        "maximum": float(np.max(series)),
        "last_minus_first": float(series[-1] - series[0]),
        "ols_slope": float(slope),
    }
    if naturally_signed:
        result["sign_persistence"] = float(abs(float(np.mean(np.sign(series)))))
    if not all(math.isfinite(value) for value in result.values()):
        raise SequenceFeatureError("non_finite_summary_result")
    return result


def extract_sequence_summaries(
    data: SequenceFeatureInput,
    *,
    decision_timestamp_us: int,
    window_seconds: int,
    block: str,
) -> dict[str, float]:
    """Extract S1 summaries from the exact inclusive interval ``[t-W, t]``."""

    arrays = _as_arrays(data)
    indices = _window_indices(arrays, decision_timestamp_us, window_seconds)
    selected = _required_values(arrays, block=_block(block), indices=indices)
    selected[DERIVED_MID_RETURN] = _derived_mid_returns(arrays, indices)

    summaries: dict[str, float] = {}
    for name in BLOCK_FEATURES[block]:
        values = summarize_series(
            selected[name], naturally_signed=name in NATURALLY_SIGNED_FEATURES
        )
        for statistic, value in values.items():
            summaries[f"{name}__{statistic}"] = float(value)
    return summaries


def matched_common_support(
    decision_timestamps_us: Any, s0_valid: Any, s1_valid: Any
) -> CommonSupport:
    """Return the exact S0/S1 intersection without labels or metrics."""

    raw_timestamps = np.asarray(decision_timestamps_us)
    raw_s0 = np.asarray(s0_valid)
    raw_s1 = np.asarray(s1_valid)
    if raw_timestamps.ndim != 1 or raw_timestamps.dtype.kind not in "iu":
        raise SequenceFeatureError("support_timestamps_must_be_integer_1d")
    if raw_s0.ndim != 1 or raw_s1.ndim != 1:
        raise SequenceFeatureError("support_masks_must_be_one_dimensional")
    if len(raw_timestamps) != len(raw_s0) or len(raw_s0) != len(raw_s1):
        raise SequenceFeatureError("mismatched_support_lengths")
    if raw_s0.dtype.kind != "b" or raw_s1.dtype.kind != "b":
        raise SequenceFeatureError("support_masks_must_be_boolean")

    timestamps = raw_timestamps.astype(np.int64, copy=False)
    if bool(np.any(np.diff(timestamps) <= 0)):
        raise SequenceFeatureError("support_timestamps_not_unique_chronological")
    mask = np.logical_and(raw_s0, raw_s1)
    indices = np.flatnonzero(mask).astype(np.int64, copy=False)
    return CommonSupport(
        mask=mask.astype(bool, copy=False),
        indices=indices,
        decision_timestamps_us=timestamps[indices].astype(np.int64, copy=False),
    )
