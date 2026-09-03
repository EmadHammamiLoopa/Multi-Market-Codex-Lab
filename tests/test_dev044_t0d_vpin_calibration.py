from __future__ import annotations

from datetime import date
import numpy as np
import pytest

from multimarket import dev044_t0d_vpin_calibration as c


def make_day(d:date,volume_per_row:float)->c.TradeDay:
    n=c.EXPECTED_ROWS
    ts=np.arange(n,dtype=np.int64)*250_000
    buy=np.full(n,volume_per_row/2.0)
    sell=np.full(n,volume_per_row/2.0)
    return c.TradeDay(d,ts,buy,sell,np.zeros(n),f"synthetic-{d.isoformat()}")


def test_positive_30m_blocks_geometry():
    d=make_day(date(2026,1,1),2.0)
    v=c._positive_30m_volumes(d)
    assert len(v)==48
    assert np.allclose(v,1800*4*2.0)


def test_calibration_exact_formula():
    days=(
        make_day(date(2026,1,1),2.0),
        make_day(date(2026,2,1),4.0),
        make_day(date(2026,3,1),6.0),
    )
    out=c.calibrate_from_days(days)
    expected_median=1800*4*4.0
    assert out["median_30m_directional_qty"]==pytest.approx(expected_median)
    assert out["vpin_bucket_volume"]==pytest.approx(expected_median/50.0)
    assert out["positive_30m_blocks_total"]==144
    assert out["rolling_buckets"]==50
    assert out["calibration_block_seconds"]==1800


def test_calendar_fails_closed():
    days=(
        make_day(date(2026,1,1),2.0),
        make_day(date(2026,3,1),4.0),
        make_day(date(2026,2,1),6.0),
    )
    with pytest.raises(c.T0DCalibrationError):
        c.calibrate_from_days(days)


def test_block_geometry_fails_closed():
    d=make_day(date(2026,1,1),2.0)
    bad=c.TradeDay(d.day,d.timestamps_us[:-1],d.buy_qty[:-1],d.sell_qty[:-1],d.unknown_qty[:-1],d.source_sha256)
    with pytest.raises(c.T0DCalibrationError):
        c._positive_30m_volumes(bad)


def test_constants():
    assert c.CALIBRATION_DAYS==(date(2026,1,1),date(2026,2,1),date(2026,3,1))
    assert c.EXPECTED_ROWS==345_600
    assert c.STATUS_PASS=="DEV044_T0D_VPIN_BUCKET_CALIBRATION_PASS"
