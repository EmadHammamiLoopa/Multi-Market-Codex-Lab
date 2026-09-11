import numpy as np
import pytest

from multimarket import dev045_d6r26a_p2_r27p8_real_prefix_parity_localization_preexecution as r27p8
from multimarket import dev045_d6r26a_p2_r27p12_real_5m_feature_parity_localization_preexecution as r27p12


def test_r27p12_contract_is_bounded_and_historical_only_by_explicit_auth():
    r27p12.validate_r27p12_contract()
    assert r27p12.PREFIX_ROWS == 5_000_000
    assert r27p12.NO_TIMING is True
    assert r27p12.NO_SPEED_GATE is True
    assert r27p12.P2_ATTEMPT_CONSUMED is False
    assert r27p12.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r27p12.MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED is False
    assert r27p12.real_diagnostic_authorized({}) is False
    assert r27p12.real_diagnostic_authorized({r27p12.AUTH_ENV: r27p12.AUTH_TOKEN}) is True


def test_localize_values_identifies_only_changed_feature():
    a = np.zeros((3, 8, 25), dtype=np.float64)
    b = a.copy()
    b[2, 4, 6] = 1e-12
    diffs = r27p12.localize_values(a, b)
    changed = [x for x in diffs if x.mismatch_count]
    assert len(changed) == 1
    item = changed[0]
    assert item.feature_index == 6
    assert item.first_decision_index == 2
    assert item.first_case_index == 4
    assert item.mismatch_count == 1
    assert item.expected_value == 0.0
    assert item.observed_value == 1e-12


def test_localize_values_rejects_wrong_surface():
    with pytest.raises(r27p12.R27P12Error, match="feature_values_surface"):
        r27p12.localize_values(np.zeros((2, 3)), np.zeros((2, 3)))
