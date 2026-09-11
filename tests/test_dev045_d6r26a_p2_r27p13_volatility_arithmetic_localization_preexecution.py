import numpy as np

from multimarket import dev045_d6r26a_p2_r27p13_volatility_arithmetic_localization_preexecution as r27p13


def test_contract_is_bounded_and_safe():
    r27p13.validate_r27p13_contract()
    assert r27p13.PREFIX_ROWS == 5_000_000
    assert r27p13.REFERENCE_CONTEXT_REBUILD is False
    assert r27p13.NO_TIMING is True
    assert r27p13.NO_SPEED_GATE is True
    assert r27p13.P2_ATTEMPT_CONSUMED is False
    assert r27p13.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r27p13.MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED is False
    assert r27p13.real_diagnostic_authorized({}) is False
    assert r27p13.real_diagnostic_authorized({r27p13.AUTH_ENV: r27p13.AUTH_TOKEN}) is True


def test_diff_localizes_first_float_mismatch():
    a = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    b = a.copy()
    b[1] = np.nextafter(b[1], 3.0)
    d = r27p13._diff(a, b)
    assert d.mismatch_count == 1
    assert d.first_index == 1
    assert d.expected == 2.0
    assert d.observed == b[1]
    assert d.max_abs_diff > 0.0


def test_python_transform_is_finite_and_deterministic():
    x = np.array([0.0, 1e-12, 4e-12], dtype=np.float64)
    a = r27p13._python_transform(x)
    b = r27p13._python_transform(x)
    assert np.array_equal(a, b)
    assert np.isfinite(a).all()
