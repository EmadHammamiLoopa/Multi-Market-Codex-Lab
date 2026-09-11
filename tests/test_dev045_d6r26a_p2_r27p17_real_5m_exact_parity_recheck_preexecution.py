import os

import numpy as np
import pytest

from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p17_real_5m_exact_parity_recheck_preexecution as r27p17


def test_r27p17_contract_is_5m_only_and_closed():
    r27p17.validate_r27p17_contract()
    assert r27p17.PREFIX_ROWS == 5_000_000
    assert r27p17.R27P9_L5_AMENDMENT_REQUIRED is True
    assert r27p17.R27P16_VOLATILITY_AMENDMENT_REQUIRED is True
    assert r27p17.NO_TIMING is True
    assert r27p17.NO_SPEED_GATE is True
    assert r27p17.R27P15_RERUN_AUTHORIZED is False
    assert r27p17.P2_ATTEMPT_CONSUMED is False
    assert r27p17.MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED is False


def test_real_recheck_requires_explicit_authorization(monkeypatch):
    monkeypatch.delenv(r27p17.AUTH_ENV, raising=False)
    with pytest.raises(r27p17.R27P17Error, match="authorization"):
        r27p17._require_authorized()


def test_synthetic_r27p9_plus_r27p16_exactly_matches_r19_reference(monkeypatch):
    events = r20.make_synthetic_dual_context_fixture()
    monkeypatch.setattr(r27p17, "PREFIX_ROWS", int(events.size))
    monkeypatch.setattr(r27p17, "SOURCE_DAY_START_NS", 0)
    monkeypatch.setattr(r27p17, "SOURCE_DAY_END_EXCLUSIVE_NS", 100_000_000_000)
    report = r27p17.diagnose_events(events, prefix_rows=int(events.size))
    assert report.exact_feature_parity is True
    assert report.mismatch_cells == 0
    assert report.mismatch_feature_indices == ()
