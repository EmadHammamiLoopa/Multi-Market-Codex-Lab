from __future__ import annotations

import ast
import inspect
import math

import numpy as np
import pytest

from multimarket import dev030_sequence_features as sf


DECISION_US = 60_000_000


def synthetic_input(*, end_us: int = 62_000_000) -> sf.SequenceFeatureInput:
    timestamps = np.arange(
        -sf.GRID_US, end_us + sf.GRID_US, sf.GRID_US, dtype=np.int64
    )
    rows = len(timestamps)
    features = {
        name: np.full(rows, float(position + 1), dtype=np.float64)
        for position, name in enumerate(sf.ALLOWED_STORED_FEATURES)
    }
    mid = 100.0 * np.exp(np.arange(rows, dtype=np.float64) * 1e-6)
    validity_masks = {
        "book_valid": np.ones(rows, dtype=bool),
        "l0_valid": np.ones(rows, dtype=bool),
        "l1_valid": np.ones(rows, dtype=bool),
        "l2_valid": np.ones(rows, dtype=bool),
    }
    return sf.SequenceFeatureInput(timestamps, features, mid, validity_masks)


def copied_input(data: sf.SequenceFeatureInput) -> sf.SequenceFeatureInput:
    return sf.SequenceFeatureInput(
        np.asarray(data.timestamps_us).copy(),
        {name: np.asarray(values).copy() for name, values in data.features.items()},
        np.asarray(data.mid).copy(),
        {
            name: np.asarray(values).copy()
            for name, values in data.validity_masks.items()
        },
    )


def remove_row(
    data: sf.SequenceFeatureInput, timestamp_us: int
) -> sf.SequenceFeatureInput:
    keep = np.asarray(data.timestamps_us) != timestamp_us
    return sf.SequenceFeatureInput(
        np.asarray(data.timestamps_us)[keep],
        {name: np.asarray(values)[keep] for name, values in data.features.items()},
        np.asarray(data.mid)[keep],
        {name: np.asarray(values)[keep] for name, values in data.validity_masks.items()},
    )


def index_at(data: sf.SequenceFeatureInput, timestamp_us: int) -> int:
    positions = np.flatnonzero(np.asarray(data.timestamps_us) == timestamp_us)
    assert len(positions) == 1
    return int(positions[0])


def assert_reason(reason: str, callable_, *args, **kwargs) -> None:
    with pytest.raises(sf.SequenceFeatureError) as caught:
        callable_(*args, **kwargs)
    assert caught.value.reason == reason


def test_exact_allowed_feature_manifest_and_block_order() -> None:
    assert sf.BLOCK_ORDER == (
        "PRICE",
        "PRICE_BOOK",
        "PRICE_BOOK_FLOW",
        "PRICE_BOOK_FLOW_DYNAMICS",
    )
    assert sf.PRICE_STORED_FEATURES == (
        "spread_bps",
        "microprice_minus_mid_bps",
    )
    assert sf.BOOK_ADDITIONS == (
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
    assert len(sf.FLOW_ADDITIONS) == 15
    assert len(sf.DYNAMICS_ADDITIONS) == 17
    assert len(sf.ALLOWED_STORED_FEATURES) == 43
    assert len(sf.ALLOWED_FEATURES) == 44
    assert sf.SOURCE_ONLY_FIELDS == ("mid",)
    assert sf.block_feature_names(sf.PRICE) == (
        "spread_bps",
        "microprice_minus_mid_bps",
        sf.DERIVED_MID_RETURN,
    )
    assert sf.block_feature_names(sf.FULL) == sf.ALLOWED_FEATURES


def test_exact_naturally_signed_manifest() -> None:
    expected = {
        sf.DERIVED_MID_RETURN,
        "microprice_minus_mid_bps",
        "obi_l1",
        "obi_l5",
        "obi_l10",
        *sf.FLOW_ADDITIONS,
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
    }
    assert sf.NATURALLY_SIGNED_FEATURES == expected
    assert len(sf.NATURALLY_SIGNED_FEATURES) == 33
    assert "spread_bps" not in sf.NATURALLY_SIGNED_FEATURES
    assert "bid_replenish_l5_1s" not in sf.NATURALLY_SIGNED_FEATURES


def test_exact_internal_lookback_manifest() -> None:
    assert set(sf.INTERNAL_LOOKBACK_NS) == set(sf.ALLOWED_FEATURES)
    assert sf.feature_internal_lookback_ns("spread_bps") == 0
    assert sf.feature_internal_lookback_ns("obi_l10") == 0
    assert sf.feature_internal_lookback_ns(sf.DERIVED_MID_RETURN) == sf.GRID_NS
    assert sf.feature_internal_lookback_ns("ofi_l1_250ms") == sf.GRID_NS
    assert sf.feature_internal_lookback_ns("trade_count_imbalance_250ms") == sf.GRID_NS
    assert sf.feature_internal_lookback_ns("ofi_l1_1s") == 1_000_000_000
    assert sf.feature_internal_lookback_ns("bid_replenish_l5_1s") == 1_000_000_000
    assert (
        sf.feature_internal_lookback_ns("mlofi_l5_1s_x_spread_bps")
        == 1_000_000_000
    )
    assert sf.feature_internal_lookback_ns("mlofi_l10_3s") == 3_000_000_000
    assert (
        sf.feature_internal_lookback_ns("trade_qty_imbalance_3s")
        == 3_000_000_000
    )


def test_cumulative_block_internal_lookbacks() -> None:
    assert sf.block_internal_lookback_ns(sf.PRICE) == 250_000_000
    assert sf.block_internal_lookback_ns(sf.PRICE_BOOK) == 250_000_000
    assert sf.block_internal_lookback_ns(sf.PRICE_BOOK_FLOW) == 3_000_000_000
    assert sf.block_internal_lookback_ns(sf.FULL) == 3_000_000_000


@pytest.mark.parametrize(
    ("window_seconds", "rows"), ((8, 33), (16, 65), (32, 129), (60, 241))
)
def test_frozen_inclusive_window_row_counts(window_seconds: int, rows: int) -> None:
    assert sf.window_observation_count(window_seconds) == rows


@pytest.mark.parametrize("window_seconds", sf.FROZEN_WINDOWS_SECONDS)
def test_exact_grid_window_extraction_includes_both_endpoints(
    window_seconds: int,
) -> None:
    data = copied_input(synthetic_input())
    start = DECISION_US - window_seconds * 1_000_000
    timestamps = np.asarray(data.timestamps_us)
    values = (timestamps - start) / sf.GRID_US
    data.features["spread_bps"][:] = values
    result = sf.extract_sequence_summaries(
        data,
        decision_timestamp_us=DECISION_US,
        window_seconds=window_seconds,
        block=sf.PRICE,
    )
    last = float(window_seconds * 4)
    assert result["spread_bps__last"] == last
    assert result["spread_bps__minimum"] == 0.0
    assert result["spread_bps__maximum"] == last
    assert result["spread_bps__mean"] == last / 2.0


def test_missing_required_grid_row_is_rejected_without_imputation() -> None:
    data = remove_row(synthetic_input(), DECISION_US - 4_000_000)
    assert_reason(
        "window_grid_missing",
        sf.extract_sequence_summaries,
        data,
        decision_timestamp_us=DECISION_US,
        window_seconds=8,
        block=sf.PRICE,
    )


def test_off_grid_timestamp_is_rejected() -> None:
    data = copied_input(synthetic_input())
    position = index_at(data, DECISION_US - 4_000_000)
    data.timestamps_us[position] += 1
    assert_reason(
        "off_grid_timestamp",
        sf.extract_sequence_summaries,
        data,
        decision_timestamp_us=DECISION_US,
        window_seconds=8,
        block=sf.PRICE,
    )


def test_duplicate_timestamp_is_rejected_distinctly() -> None:
    data = copied_input(synthetic_input())
    data.timestamps_us[10] = data.timestamps_us[9]
    assert_reason(
        "duplicate_timestamps",
        sf.extract_snapshot,
        data,
        decision_timestamp_us=DECISION_US,
        block=sf.PRICE,
    )


def test_non_monotonic_timestamp_is_rejected_distinctly() -> None:
    data = copied_input(synthetic_input())
    data.timestamps_us[10] = data.timestamps_us[9] - sf.GRID_US
    assert_reason(
        "non_monotonic_timestamps",
        sf.extract_snapshot,
        data,
        decision_timestamp_us=DECISION_US,
        block=sf.PRICE,
    )


def test_future_mutation_after_t_does_not_change_s0_or_s1() -> None:
    original = synthetic_input()
    changed = copied_input(original)
    after = np.asarray(changed.timestamps_us) > DECISION_US
    changed.mid[after] = -1.0
    for values in changed.features.values():
        values[after] = np.nan
    for mask in changed.validity_masks.values():
        mask[after] = False

    original_s0 = sf.extract_snapshot(
        original, decision_timestamp_us=DECISION_US, block=sf.FULL
    )
    changed_s0 = sf.extract_snapshot(
        changed, decision_timestamp_us=DECISION_US, block=sf.FULL
    )
    original_s1 = sf.extract_sequence_summaries(
        original,
        decision_timestamp_us=DECISION_US,
        window_seconds=8,
        block=sf.FULL,
    )
    changed_s1 = sf.extract_sequence_summaries(
        changed,
        decision_timestamp_us=DECISION_US,
        window_seconds=8,
        block=sf.FULL,
    )
    assert changed_s0 == original_s0
    assert changed_s1 == original_s1


def test_derived_mid_return_uses_exact_prior_250ms_endpoint() -> None:
    data = copied_input(synthetic_input())
    current = index_at(data, DECISION_US)
    prior = index_at(data, DECISION_US - sf.GRID_US)
    data.mid[prior] = 100.0
    data.mid[current] = 101.0
    result = sf.extract_snapshot(
        data, decision_timestamp_us=DECISION_US, block=sf.PRICE
    )
    assert result[sf.DERIVED_MID_RETURN] == pytest.approx(10_000.0 * math.log(1.01))


def test_missing_prior_mid_endpoint_rejects_derived_return() -> None:
    data = remove_row(synthetic_input(), DECISION_US - 8_000_000 - sf.GRID_US)
    assert_reason(
        "missing_prior_mid_endpoint",
        sf.extract_sequence_summaries,
        data,
        decision_timestamp_us=DECISION_US,
        window_seconds=8,
        block=sf.PRICE,
    )


@pytest.mark.parametrize("bad_mid", (0.0, -1.0, np.nan, np.inf))
def test_invalid_mid_endpoint_rejects_derived_return(bad_mid: float) -> None:
    data = copied_input(synthetic_input())
    data.mid[index_at(data, DECISION_US - sf.GRID_US)] = bad_mid
    assert_reason(
        "invalid_mid_for_derived_return",
        sf.extract_snapshot,
        data,
        decision_timestamp_us=DECISION_US,
        block=sf.PRICE,
    )


def test_invalid_required_mask_anywhere_rejects_full_window() -> None:
    data = copied_input(synthetic_input())
    data.validity_masks["l2_valid"][index_at(data, DECISION_US - 2_000_000)] = False
    assert_reason(
        "invalid_required_mask",
        sf.extract_sequence_summaries,
        data,
        decision_timestamp_us=DECISION_US,
        window_seconds=8,
        block=sf.FULL,
    )


def test_missing_prior_book_validity_rejects_without_fill() -> None:
    data = copied_input(synthetic_input())
    prior = index_at(data, DECISION_US - 8_000_000 - sf.GRID_US)
    data.validity_masks["book_valid"][prior] = False
    assert_reason(
        "invalid_required_mask",
        sf.extract_sequence_summaries,
        data,
        decision_timestamp_us=DECISION_US,
        window_seconds=8,
        block=sf.PRICE,
    )


def test_exact_summary_statistics() -> None:
    values = np.asarray([1.0, 2.0, 4.0, 8.0])
    result = sf.summarize_series(values)
    assert result == {
        "last": 8.0,
        "mean": float(np.mean(values)),
        "std": float(np.std(values, ddof=0)),
        "minimum": 1.0,
        "maximum": 8.0,
        "last_minus_first": 7.0,
        "ols_slope": pytest.approx(9.2),
    }


def test_exact_ols_slope_uses_quarter_second_spacing() -> None:
    elapsed = np.arange(33, dtype=np.float64) * 0.25
    values = 7.0 + 2.5 * elapsed
    assert sf.summarize_series(values)["ols_slope"] == pytest.approx(2.5)


def test_constant_series_slope_is_exact_zero() -> None:
    assert sf.summarize_series(np.full(33, 4.0))["ols_slope"] == 0.0


def test_sign_persistence_and_zero_semantics_are_exact() -> None:
    result = sf.summarize_series(
        np.asarray([-2.0, 0.0, 3.0, 4.0]), naturally_signed=True
    )
    assert result["sign_persistence"] == 0.25
    zeros = sf.summarize_series(np.zeros(4), naturally_signed=True)
    assert zeros["sign_persistence"] == 0.0


def test_unsigned_series_has_no_sign_persistence() -> None:
    result = sf.summarize_series(np.asarray([-1.0, 1.0]), naturally_signed=False)
    assert "sign_persistence" not in result
    data = synthetic_input()
    summaries = sf.extract_sequence_summaries(
        data,
        decision_timestamp_us=DECISION_US,
        window_seconds=8,
        block=sf.PRICE,
    )
    assert "spread_bps__sign_persistence" not in summaries
    assert "microprice_minus_mid_bps__sign_persistence" in summaries


def test_snapshot_is_exactly_t_and_contains_no_extra_features() -> None:
    data = copied_input(synthetic_input())
    decision_position = index_at(data, DECISION_US)
    data.features["spread_bps"][decision_position] = 12.5
    result = sf.extract_snapshot(
        data, decision_timestamp_us=DECISION_US, block=sf.PRICE_BOOK
    )
    assert tuple(result) == sf.block_feature_names(sf.PRICE_BOOK)
    assert result["spread_bps"] == 12.5
    assert set(result) == set(sf.PRICE_STORED_FEATURES + sf.BOOK_ADDITIONS) | {
        sf.DERIVED_MID_RETURN
    }


def test_matched_common_support_returns_exact_intersection() -> None:
    timestamps = np.asarray([0, 60_000_000, 120_000_000, 180_000_000])
    result = sf.matched_common_support(
        timestamps,
        np.asarray([True, True, False, True]),
        np.asarray([True, False, True, True]),
    )
    np.testing.assert_array_equal(result.mask, [True, False, False, True])
    np.testing.assert_array_equal(result.indices, [0, 3])
    np.testing.assert_array_equal(result.decision_timestamps_us, [0, 180_000_000])


def test_information_intervals_are_exact_and_block_specific() -> None:
    price = sf.information_intervals(
        decision_timestamp_us=100_000_000,
        window_seconds=60,
        block=sf.PRICE,
        target_horizon_seconds=300,
    )
    assert price.representation_start_us == 40_000_000
    assert price.representation_end_us == 100_000_000
    assert price.raw_source_start_us == 39_750_000
    assert price.raw_source_end_us == 400_250_000
    assert price.block_internal_lookback_ns == 250_000_000

    full = sf.information_intervals(
        decision_timestamp_us=100_000_000,
        window_seconds=60,
        block=sf.FULL,
        target_horizon_seconds=300,
    )
    assert full.representation_start_us == 40_000_000
    assert full.representation_end_us == 100_000_000
    assert full.raw_source_start_us == 37_000_000
    assert full.raw_source_end_us == 400_250_000
    assert full.window_seconds == 60
    assert full.block_internal_lookback_ns == 3_000_000_000
    assert full.target_horizon_seconds == 300
    assert full.latency_ms == 250
    assert full.total_information_span_ns == 363_250_000_000


def test_mismatched_feature_array_length_is_rejected() -> None:
    data = copied_input(synthetic_input())
    data.features["spread_bps"] = data.features["spread_bps"][:-1]
    assert_reason(
        "mismatched_array_lengths",
        sf.extract_snapshot,
        data,
        decision_timestamp_us=DECISION_US,
        block=sf.PRICE,
    )


def test_non_finite_required_feature_is_rejected_only_when_used() -> None:
    data = copied_input(synthetic_input())
    inside = index_at(data, DECISION_US - 1_000_000)
    data.features["spread_bps"][inside] = np.nan
    assert_reason(
        "non_finite_required_feature",
        sf.extract_sequence_summaries,
        data,
        decision_timestamp_us=DECISION_US,
        window_seconds=8,
        block=sf.PRICE,
    )


def test_missing_required_feature_is_rejected() -> None:
    data = copied_input(synthetic_input())
    del data.features["obi_l10"]
    assert_reason(
        "missing_required_feature",
        sf.extract_snapshot,
        data,
        decision_timestamp_us=DECISION_US,
        block=sf.PRICE_BOOK,
    )


def test_missing_required_validity_mask_is_rejected() -> None:
    data = copied_input(synthetic_input())
    del data.validity_masks["l1_valid"]
    assert_reason(
        "missing_required_validity_mask",
        sf.extract_snapshot,
        data,
        decision_timestamp_us=DECISION_US,
        block=sf.PRICE_BOOK_FLOW,
    )


def test_output_is_deterministic_and_builtin_finite() -> None:
    data = synthetic_input()
    first = sf.extract_sequence_summaries(
        data,
        decision_timestamp_us=DECISION_US,
        window_seconds=16,
        block=sf.FULL,
    )
    second = sf.extract_sequence_summaries(
        data,
        decision_timestamp_us=DECISION_US,
        window_seconds=16,
        block=sf.FULL,
    )
    assert first == second
    assert all(type(value) is float and math.isfinite(value) for value in first.values())


def test_module_has_no_filesystem_network_loader_or_model_behavior() -> None:
    source = inspect.getsource(sf)
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called_names.add(node.func.id)

    assert imported_roots <= {"__future__", "dataclasses", "math", "typing", "numpy"}
    assert called_names.isdisjoint(
        {
            "open",
            "glob",
            "loadtxt",
            "read_csv",
            "urlopen",
            "request",
            "fit",
            "predict",
            "dump",
        }
    )
    assert not hasattr(sf, "_load_day")
