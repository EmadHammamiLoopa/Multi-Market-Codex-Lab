from __future__ import annotations

import numpy as np
import pytest

from multimarket import dev044_t0b_raw_adapter as a


def good():
    return {
        "S05":np.zeros((3,7)),
        "S06":np.zeros((3,2)),
        "S21":np.zeros((3,8)),
        "S30":np.zeros((3,6)),
        "S31":np.zeros((3,6)),
        "S32":np.zeros((3,4)),
    }


def test_validate_mapping_good():
    a.validate_mapping(good())


def test_validate_mapping_missing():
    x=good();x.pop("S32")
    with pytest.raises(a.RawAdapterError):
        a.validate_mapping(x)


def test_validate_mapping_width():
    x=good();x["S05"]=np.zeros((3,6))
    with pytest.raises(a.RawAdapterError):
        a.validate_mapping(x)


def test_validate_mapping_row_alignment():
    x=good();x["S31"]=np.zeros((2,6))
    with pytest.raises(a.RawAdapterError):
        a.validate_mapping(x)


def test_raw_row_map():
    r=a.RawAdapterResult(
        day=__import__("datetime").date(2026,4,1),
        timestamps_us=np.asarray([1,2,3],dtype=np.int64),
        values=good(),
        extractor_stderr="",
    )
    assert a.raw_row_map(r)=={1:0,2:1,3:2}
