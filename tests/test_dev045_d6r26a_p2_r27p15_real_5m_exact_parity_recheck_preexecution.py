import numpy as np

from multimarket import dev045_d6r26a_p2_r27p15_real_5m_exact_parity_recheck_preexecution as r27p15


def test_r27p15_contract_is_5m_only_and_closed():
    r27p15.validate_r27p15_contract()
    assert r27p15.PREFIX_ROWS == 5_000_000
    assert r27p15.NO_TIMING is True
    assert r27p15.NO_SPEED_GATE is True
    assert r27p15.R27P12_RERUN_AUTHORIZED is False
    assert r27p15.R27P13_RERUN_AUTHORIZED is False
    assert r27p15.P2_ATTEMPT_CONSUMED is False
    assert r27p15.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r27p15.MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED is False
    assert r27p15.real_diagnostic_authorized({}) is False
    assert r27p15.real_diagnostic_authorized({r27p15.AUTH_ENV: r27p15.AUTH_TOKEN}) is True


def test_parity_report_can_represent_exact_pass():
    report = r27p15.ParityReport(
        prefix_rows=5_000_000,
        decision_count=7247,
        leading_preeligible_count=2,
        exact_feature_parity=True,
        mismatch_cells=0,
        mismatch_feature_indices=(),
        l5_changed_cells=320,
        volatility_changed_cells=24,
    )
    assert report.exact_feature_parity is True
    assert report.mismatch_cells == 0
    assert report.mismatch_feature_indices == ()


def test_parity_report_can_represent_localized_failure():
    report = r27p15.ParityReport(
        prefix_rows=5_000_000,
        decision_count=7247,
        leading_preeligible_count=2,
        exact_feature_parity=False,
        mismatch_cells=8,
        mismatch_feature_indices=(17,),
        l5_changed_cells=320,
        volatility_changed_cells=24,
    )
    assert report.exact_feature_parity is False
    assert report.mismatch_cells == 8
    assert report.mismatch_feature_indices == (17,)
