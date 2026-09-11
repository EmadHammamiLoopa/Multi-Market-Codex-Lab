import tempfile
from pathlib import Path

import numpy as np

from multimarket import dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19
from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p11_amended_bounded_speed_benchmark_preexecution as r27p11
from multimarket import dev045_d6r26a_p2_r27p16_r10_rolling_volatility_parity_amendment as r27p16


def test_r27p16_contract_is_narrow_and_closed():
    r27p16.validate_r27p16_contract()
    assert r27p16.AMENDED_FEATURE_INDICES == (16, 17, 18)
    assert r27p16.REFERENCE_SEMANTICS == "R10_ROLLING_FEATURE_ACCUMULATOR"
    assert r27p16.SUPERSEDES_R27P14_BATCH_WINDOW_AMENDMENT is True
    assert r27p16.ELIGIBLE_DECISIONS_ONLY is True
    assert r27p16.PREELIGIBLE_ADVANCE_FORBIDDEN is True
    assert r27p16.P2_ATTEMPT_CONSUMED is False
    assert r27p16.REAL_HISTORICAL_DIAGNOSTIC_AUTHORIZED is False
    assert r27p16.MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED is False


def test_r10_rolling_amendment_matches_r19_synthetic_end_to_end_exactly():
    events = r20.make_synthetic_dual_context_fixture()
    nominal_start = 0
    nominal_end = 100_000_000_000

    reference = r19.build_once_day_dense_feature_cache(
        events,
        nominal_day_start_local_ns=nominal_start,
        nominal_day_end_exclusive_local_ns=nominal_end,
    )

    with tempfile.TemporaryDirectory(prefix="r27p16_test_") as root:
        candidate_context, _ = r27p11.build_amended_fused_day_context(
            events,
            nominal_day_start_local_ns=nominal_start,
            nominal_day_end_exclusive_local_ns=nominal_end,
            scratch_root=Path(root),
        )
        try:
            raw = r27p11.r27p6.run_fused_raw_surface(events)
            surface = r27p11._compact_from_raw(raw)
            cache = candidate_context.feature_cache
            base = r27p11.r27p5.CompiledFeatureResult(
                decision_local_ns=cache.decision_local_ns,
                best_bid_tick=cache.best_bid_tick,
                best_ask_tick=cache.best_ask_tick,
                values=cache.values,
                leading_preeligible_count=candidate_context.feature_summary.leading_preeligible_count,
            )
            amended = r27p16.apply_r10_volatility_amendment(surface, base)

            assert np.array_equal(amended.decision_local_ns, reference.cache.decision_local_ns)
            assert np.array_equal(amended.best_bid_tick, reference.cache.best_bid_tick)
            assert np.array_equal(amended.best_ask_tick, reference.cache.best_ask_tick)
            assert np.array_equal(amended.values, reference.cache.values)

            audit = r27p16.audit_amendment(base, amended)
            assert audit.other_feature_bytes_equal is True
            assert set(audit.changed_feature_indices).issubset({16, 17, 18})
        finally:
            if not candidate_context.midpoint_index.closed:
                r20.close_midpoint_index(candidate_context.midpoint_index)


def test_amendment_never_changes_non_volatility_features():
    events = r20.make_synthetic_dual_context_fixture()
    with tempfile.TemporaryDirectory(prefix="r27p16_scope_") as root:
        candidate_context, _ = r27p11.build_amended_fused_day_context(
            events,
            nominal_day_start_local_ns=0,
            nominal_day_end_exclusive_local_ns=100_000_000_000,
            scratch_root=Path(root),
        )
        try:
            raw = r27p11.r27p6.run_fused_raw_surface(events)
            surface = r27p11._compact_from_raw(raw)
            cache = candidate_context.feature_cache
            base = r27p11.r27p5.CompiledFeatureResult(
                decision_local_ns=cache.decision_local_ns,
                best_bid_tick=cache.best_bid_tick,
                best_ask_tick=cache.best_ask_tick,
                values=cache.values,
                leading_preeligible_count=candidate_context.feature_summary.leading_preeligible_count,
            )
            amended = r27p16.apply_r10_volatility_amendment(surface, base)
            keep = [i for i in range(25) if i not in (16, 17, 18)]
            assert np.array_equal(base.values[:, :, keep], amended.values[:, :, keep])
        finally:
            if not candidate_context.midpoint_index.closed:
                r20.close_midpoint_index(candidate_context.midpoint_index)
