from __future__ import annotations

import numpy as np
import pytest

from multimarket import dev045_m5_prereg as m


def test_frozen_family_and_days():
    m.validate_family()
    m.validate_days(m.AUTHORIZED_DAYS)
    assert len(m.POLICY_IDS)==8
    assert m.TOTAL_BLOCKS==42


def test_fee_gate_rejects_unverified_or_missing_source():
    with pytest.raises(m.M5PreregError,match="unverified"):
        m.validate_fee_schedule(m.FeeSchedule(0.0,0.0,"account page",False))
    with pytest.raises(m.M5PreregError,match="source"):
        m.validate_fee_schedule(m.FeeSchedule(0.0,0.0,"",True))


def test_fee_gate_accepts_verified_finite_schedule():
    m.validate_fee_schedule(m.FeeSchedule(0.0002,0.0004,"Binance account fee page",True))


def test_maxstat_family_shape_and_determinism():
    X={}
    for j,cid in enumerate(m.POLICY_IDS):
        X[cid]=np.linspace(-1.0,1.0,m.TOTAL_BLOCKS)+(j*0.01)
    a=m.block_maxstat_test(X,reps=200,seed=123)
    b=m.block_maxstat_test(X,reps=200,seed=123)
    assert a==b
    assert a["total_blocks"]==42
    assert a["policy_ids"]==list(m.POLICY_IDS)


def test_maxstat_rejects_family_or_block_drift():
    bad={cid:[0.0]*m.TOTAL_BLOCKS for cid in m.POLICY_IDS[:-1]}
    with pytest.raises(m.M5PreregError):
        m.block_maxstat_test(bad,reps=10)


def test_eligibility_requires_every_frozen_gate():
    ok=m.evaluate_eligibility(
        policy_id="M01",
        primary_net_expectancy=0.1,
        primary_pf=1.01,
        positive_days=4,
        positive_day_concentration=0.50,
        stress_net_expectancy=0.01,
        execution_integrity_failures=0,
        terminal_flat=True,
        fwer_pvalue=0.05,
    )
    assert ok.passes

    fail=m.evaluate_eligibility(
        policy_id="M01",
        primary_net_expectancy=0.1,
        primary_pf=1.01,
        positive_days=4,
        positive_day_concentration=0.50,
        stress_net_expectancy=-0.01,
        execution_integrity_failures=0,
        terminal_flat=True,
        fwer_pvalue=0.05,
    )
    assert not fail.passes
