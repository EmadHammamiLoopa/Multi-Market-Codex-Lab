from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from multimarket import dev044_t0a_a0_oof as a


def fold(fid,day,offset=0.0):
    ts=np.asarray([fid*10_000_000+i*60_000_000 for i in range(4)],dtype=np.int64)
    y=np.asarray([0,1,0,1],dtype=np.int8)
    p=np.asarray([0.2,0.8,0.3,0.7],dtype=np.float64)+offset
    return a.A0FoldScores(fid,day,ts,y,p)


def test_fold_validation():
    f=fold(1,"2026-04-01")
    f.validate()


def test_bad_probability_fails():
    f=fold(1,"2026-04-01")
    bad=replace(f,p_touch=np.asarray([0.2,1.2,0.3,0.7]))
    with pytest.raises(a.A0ReplayError):
        bad.validate()


def test_nonchronological_support_fails():
    f=fold(1,"2026-04-01")
    bad=replace(f,timestamps_us=np.asarray([1,3,2,4],dtype=np.int64))
    with pytest.raises(a.A0ReplayError):
        bad.validate()


def test_hashes_are_deterministic_and_score_sensitive():
    fs=(fold(1,"2026-04-01"),fold(2,"2026-05-01"),fold(3,"2026-06-01"),fold(4,"2026-07-01"))
    assert a.support_sha256(fs)==a.support_sha256(fs)
    assert a.score_sha256(fs)==a.score_sha256(fs)
    changed=list(fs)
    changed[0]=fold(1,"2026-04-01",offset=0.01)
    assert a.support_sha256(tuple(changed))==a.support_sha256(fs)
    assert a.score_sha256(tuple(changed))!=a.score_sha256(fs)


def test_frozen_parent_identity_constants():
    assert a.A0_ID=="A0_TOUCH_PRICE_LOGIT"
    assert a.FROZEN_A_BYTES==89918
    assert a.FROZEN_A_SHA256=="38ee159618a1ed13727eb6a86df83b93c92c2aad50251fcfb1618d890efd2eb7"
    assert a.FROZEN_A_STATUS=="DEV043_A_TOUCH_SURVIVOR_A0_TOUCH_PRICE_LOGIT"


def test_expected_frozen_metric_constants():
    assert a.EXPECTED_POOLED["support"]==5516
    assert a.EXPECTED_POOLED["touch_count"]==2683
    assert a.EXPECTED_POOLED["none_count"]==2833
    assert a.EXPECTED_POOLED["touch_average_precision"]==pytest.approx(0.6519588168911605)
    assert len(a.EXPECTED_PER_FOLD_AP_LIFT)==4
    assert len(a.EXPECTED_LOO_AP_LIFT)==4
    assert a.METRIC_ATOL==1e-12
