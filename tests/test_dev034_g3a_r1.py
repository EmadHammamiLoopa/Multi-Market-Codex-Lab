from __future__ import annotations

from types import SimpleNamespace
from datetime import date

import numpy as np
import pytest

from multimarket import dev034_g3a_core as g3
from multimarket import dev034_g3a_r1_core as r1
from multimarket import dev034_g3a_r1_runner as runner

def test_r1_frozen_counts_and_reasons():
    assert r1.EXPECTED_ROWS==1341
    assert r1.EXPECTED_LONG==665
    assert r1.EXPECTED_SHORT==676
    assert r1.EXPECTED_EXCLUDED==33
    assert r1.EXPECTED_REASON_COUNTS=={
        "START_OF_DAY_30M_BOUNDARY":30,
        "BOOK_INVALID_IN_30M_HISTORY":3,
    }

def test_r1_exact_nonboundary_rows():
    assert r1.EXPECTED_NONBOUNDARY_UTC=={
        "2026-02-01T00:30:00+00:00",
        "2026-06-01T00:30:00+00:00",
        "2026-07-01T00:30:00+00:00",
    }

def test_r1_day_and_outer_counts():
    assert r1.EXPECTED_DAY_COUNTS=={
        "2026-01-01":4,"2026-02-01":422,"2026-03-01":356,
        "2026-04-01":156,"2026-05-01":64,"2026-06-01":121,
        "2026-07-01":218,
    }
    assert r1.EXPECTED_OUTER_COUNTS["2026-04-01"]==(156,85,71)
    assert r1.EXPECTED_OUTER_COUNTS["2026-05-01"]==(64,40,24)
    assert r1.EXPECTED_OUTER_COUNTS["2026-06-01"]==(121,55,66)
    assert r1.EXPECTED_OUTER_COUNTS["2026-07-01"]==(218,122,96)

def test_boundary_reason():
    raw=SimpleNamespace(
        book_valid=np.ones(100,dtype=bool),
        mid=np.ones(100,dtype=float),
    )
    spread=np.zeros(100,dtype=float)
    assert r1._reason(raw,1,spread)=="START_OF_DAY_30M_BOUNDARY"

def test_book_invalid_reason(monkeypatch):
    n=8000
    raw=SimpleNamespace(
        book_valid=np.ones(n,dtype=bool),
        mid=np.ones(n,dtype=float),
    )
    raw.book_valid[5]=False
    spread=np.zeros(n,dtype=float)
    assert r1._reason(raw,7200,spread)=="BOOK_INVALID_IN_30M_HISTORY"

def test_validate_frozen_common_support(monkeypatch):
    def ed(day,n,l,s,ex=()):
        y=np.asarray([1]*l+[0]*s,dtype=np.int8)
        return r1.EligibleDay(
            day=day,
            timestamps_us=np.arange(n,dtype=np.int64),
            labels=y,
            full_r=np.zeros((n,22),dtype=float),
            exclusions=tuple(ex),
        )
    days={
        "2026-01-01":ed("2026-01-01",4,3,1),
        "2026-02-01":ed("2026-02-01",422,200,222),
        "2026-03-01":ed("2026-03-01",356,160,196),
        "2026-04-01":ed("2026-04-01",156,85,71),
        "2026-05-01":ed("2026-05-01",64,40,24),
        "2026-06-01":ed("2026-06-01",121,55,66),
        "2026-07-01":ed("2026-07-01",218,122,96),
    }
    ex=[]
    for i in range(30):
        ex.append(r1.Exclusion("2026-02-01",i,f"2026-02-01T00:{i:02d}:00+00:00",0,"START_OF_DAY_30M_BOUNDARY"))
    for utc in sorted(r1.EXPECTED_NONBOUNDARY_UTC):
        day=utc[:10]
        ex.append(r1.Exclusion(day,999,utc,1,"BOOK_INVALID_IN_30M_HISTORY"))
    # distribute exclusions without changing eligible arrays
    days["2026-02-01"]=r1.EligibleDay(**{**days["2026-02-01"].__dict__,"exclusions":tuple(ex)})
    r1.validate_frozen_common_support(days)

def test_forward_guards_false():
    assert not any(r1.FORWARD_GUARDS.values())

def test_runner_identity():
    assert runner.EXPERIMENT_ID=="DEV034-G3A-R1"
    assert runner.REAL_OUTPUT_DIRECTORY.name=="dev034_g3a_r1_common_support_context_v1"
    assert runner.ARTIFACT_FILENAME=="DEV034_G3A_R1_COMMON_SUPPORT_CONTEXT.json"
    assert len(g3.CANDIDATE_IDS)==16


def test_verify_parent_p3_uses_frozen_artifact(monkeypatch):
    seen={}
    payload={"selected_for_next_development_stage":{
        "target":{"target_id":"A","horizon_seconds":120,"barrier_bps":16},
        "window_seconds":32,
        "block":"PRICE",
    }}
    def fake_load(path,sha):
        seen["path"]=path
        seen["sha"]=sha
        return payload
    def fake_validate(value):
        seen["validated"]=value
    monkeypatch.setattr(runner.p4,"load_verified_json_artifact",fake_load)
    monkeypatch.setattr(runner.p4,"validate_p3_selected_survivor",fake_validate)
    got=runner._verify_parent_p3()
    assert seen["path"]==runner.p6.P3_ARTIFACT_PATH
    assert seen["sha"]==runner.p6.P3_ARTIFACT_SHA256
    assert seen["validated"] is payload
    assert got=={
        "path":str(runner.p6.P3_ARTIFACT_PATH),
        "sha256":runner.p6.P3_ARTIFACT_SHA256,
    }

def test_verify_parent_p3_propagates_identity_failure(monkeypatch):
    def fail(path,sha):
        raise runner.p4.P4Error("frozen_artifact_sha256_mismatch")
    monkeypatch.setattr(runner.p4,"load_verified_json_artifact",fail)
    with pytest.raises(runner.p4.P4Error,match="frozen_artifact_sha256_mismatch"):
        runner._verify_parent_p3()
