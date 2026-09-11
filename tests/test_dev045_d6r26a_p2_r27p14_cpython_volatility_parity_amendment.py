import math

import numpy as np

from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
from multimarket import dev045_d6r26a_p2_r27p14_cpython_volatility_parity_amendment as r27p14


def _fixture():
    ns = 1_000_000_000
    book_ns = np.asarray([0, 10*ns, 20*ns, 30*ns, 31*ns, 32*ns], dtype="<i8")
    bid_ticks = np.asarray([[100,99,98,97,96],[101,100,99,98,97],[102,101,100,99,98],[103,102,101,100,99],[104,103,102,101,100],[105,104,103,102,101]], dtype="<i8")
    ask_ticks = bid_ticks + 2
    bid_qty = np.ones((6,5), dtype="<f8")
    ask_qty = np.ones((6,5), dtype="<f8")
    candidate_qty = np.zeros((6,8), dtype="<f8")
    flow_ns = np.asarray([], dtype="<i8")
    flow_code = np.asarray([], dtype=np.int8)
    flow_qty = np.asarray([], dtype="<f8")
    surface = r27p5.CompactFeatureSurface(book_ns, bid_ticks, bid_qty, ask_ticks, ask_qty, candidate_qty, flow_ns, flow_code, flow_qty)
    decisions = np.asarray([31*ns, 32*ns], dtype="<i8")
    values = np.zeros((2,8,25), dtype="<f8")
    base = r27p5.CompiledFeatureResult(decisions, np.asarray([104,105]), np.asarray([106,107]), values, 0)
    return surface, base


def _direct(book_ns, bid_ticks, ask_ticks, decision, window):
    start = decision - window
    anchor = int(np.searchsorted(book_ns, start, side="right")) - 1
    end = int(np.searchsorted(book_ns, decision, side="right")) - 1
    mids = [0.5 * float(int(bid_ticks[i,0]) + int(ask_ticks[i,0])) * 0.01 for i in range(anchor, end+1)]
    squared = 0.0
    for before, after in zip(mids, mids[1:]):
        squared += math.log(after / before) ** 2
    return 10_000.0 * math.sqrt(squared)


def test_r27p14_contract_is_narrow_and_closed():
    r27p14.validate_r27p14_contract()
    assert r27p14.AMENDED_FEATURE_INDICES == (16,17,18)
    assert r27p14.P2_ATTEMPT_CONSUMED is False
    assert r27p14.REAL_HISTORICAL_DIAGNOSTIC_AUTHORIZED is False
    assert r27p14.MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED is False


def test_volatility_amendment_matches_direct_cpython_window_semantics():
    surface, base = _fixture()
    out = r27p14.apply_volatility_amendment(surface, base)
    for di, decision in enumerate(base.decision_local_ns):
        for fi, window in zip((16,17,18), (1_000_000_000,5_000_000_000,30_000_000_000)):
            expected = _direct(surface.book_local_ns, surface.bid_ticks, surface.ask_ticks, int(decision), window)
            assert out.values[di,0,fi] == expected
            assert np.all(out.values[di,:,fi] == expected)


def test_amendment_changes_only_volatility_features():
    surface, base = _fixture()
    out = r27p14.apply_volatility_amendment(surface, base)
    audit = r27p14.audit_amendment(base, out)
    assert audit.other_feature_bytes_equal is True
    assert set(audit.changed_feature_indices).issubset({16,17,18})
    keep = [i for i in range(25) if i not in (16,17,18)]
    assert np.array_equal(base.values[:,:,keep], out.values[:,:,keep])
