from __future__ import annotations

import numpy as np

from multimarket import dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17
from multimarket import dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19
from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
from multimarket import dev045_d6r26a_p2_r27p9_cpython313_float_sum_parity_amendment as r27p9


def test_contract_is_one_feature_arithmetic_amendment_only() -> None:
    r27p9.validate_r27p9_contract()
    assert r27p9.CPYTHON_REFERENCE_VERSION == "3.13"
    assert r27p9.CPYTHON_FLOAT_SUM_ALGORITHM == "NEUMAIER_COMPENSATED_SUM"
    assert r27p9.AMENDED_FEATURE_NAME == "l5_obi"
    assert r27p9.AMENDED_FEATURE_INDEX == 5
    assert r27p9.AMENDED_FEATURE_COUNT == 1
    assert r27p9.EXACT_OTHER_FEATURE_BYTES_REQUIRED is True
    assert r27p9.REAL_HISTORICAL_BENCHMARK_AUTHORIZED is False
    assert r27p9.REAL_HISTORICAL_DIAGNOSTIC_AUTHORIZED is False
    assert r27p9.P2_ATTEMPT_CONSUMED is False


def test_cpython313_sum5_matches_builtin_sum_exactly() -> None:
    vectors = (
        (1.0, 1e-16, 1e-16, 1e-16, 1e-16),
        (0.1, 0.2, 0.3, 0.4, 0.5),
        (12.3456789012345, 0.0000000000007, 8.7654321098765, 0.3333333333333, 4.2),
        (1000000000000000.0, 0.125, 0.125, 0.125, 0.125),
    )
    for vector in vectors:
        values = np.asarray(vector, dtype=np.float64)
        expected = sum(float(x) for x in values)
        observed = r27p9.cpython313_sum5(values)
        assert observed == expected
        assert np.float64(observed).tobytes() == np.float64(expected).tobytes()


def test_numba_amendment_changes_only_l5_obi_and_uses_builtin_sum_semantics() -> None:
    book_ns = np.asarray([123], dtype="<i8")
    bid_qty = np.asarray([[12.3456789012345, 0.0000000000007, 8.7654321098765, 0.3333333333333, 4.2]], dtype="<f8")
    ask_qty = np.asarray([[3.1415926535897, 2.7182818284590, 1.4142135623731, 0.5772156649015, 6.02214076]], dtype="<f8")
    decisions = np.asarray([123], dtype="<i8")
    values = np.arange(1 * 8 * 25, dtype=np.float64).reshape(1, 8, 25)

    kernel = r27p9.build_l5_obi_amendment_kernel()
    out, error = kernel(book_ns, bid_qty, ask_qty, decisions, values)
    assert int(error) == 0

    bid5 = sum(float(x) for x in bid_qty[0])
    ask5 = sum(float(x) for x in ask_qty[0])
    expected_l5 = (bid5 - ask5) / (bid5 + ask5)

    assert np.all(out[0, :, 5] == expected_l5)
    assert np.array_equal(np.delete(out, 5, axis=2), np.delete(values, 5, axis=2))


def test_synthetic_end_to_end_exact_feature_parity_is_preserved() -> None:
    events = r20.make_synthetic_dual_context_fixture()
    bounds = r17.derive_feed_bounds(
        events,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
    )
    requested = np.asarray(r17.build_shared_decision_grid(bounds=bounds), dtype="<i8")
    surface = r27p5.build_compact_reference_surface(events)
    reference = r19.build_once_day_dense_feature_cache(
        events,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
    )
    before = r27p5.run_compiled_feature_kernel(surface, requested)
    after = r27p9.run_amended_feature_kernel(surface, requested)

    assert after.leading_preeligible_count == reference.summary.leading_preeligible_count
    assert np.array_equal(after.decision_local_ns, reference.cache.decision_local_ns)
    assert np.array_equal(after.best_bid_tick, reference.cache.best_bid_tick)
    assert np.array_equal(after.best_ask_tick, reference.cache.best_ask_tick)
    assert np.array_equal(after.values, reference.cache.values)

    audit = r27p9.audit_amendment(before, after)
    assert audit.other_feature_bytes_equal is True
    assert set(audit.changed_feature_indices).issubset({5})
