from __future__ import annotations

from types import SimpleNamespace
import numpy as np

from multimarket import dev030_p6_m2_direction as p6
from multimarket import dev033_g2b_loader as loader
from multimarket import dev033_g2b_runner as runner

def test_r1_identity_and_output_are_distinct():
    assert runner.EXPERIMENT_ID=="DEV033-G2B-R1"
    assert runner.REAL_OUTPUT_DIRECTORY.name=="dev033_g2b_r1_layered_temporal_screen_v1"
    assert runner.ARTIFACT_FILENAME=="DEV033_G2B_R1_LAYERED_TEMPORAL_SCREEN_RESULT.json"

def test_loader_uses_frozen_build_candidate_day_contract(monkeypatch):
    calls=[]

    fake_days=tuple(
        SimpleNamespace(day=d)
        for d in __import__(
            "multimarket.dev030_direction_dataset",
            fromlist=["HISTORICAL_DAYS"]
        ).HISTORICAL_DAYS
    )

    monkeypatch.setattr(loader.dd,"load_authorized_days",lambda:fake_days)

    class FakeDataset:
        pass

    def fake_build(day,*,target,window_seconds,block):
        calls.append((day.day,target,window_seconds,block))
        x=FakeDataset()
        x.key=p6.SELECTED_KEY
        return x

    monkeypatch.setattr(loader.dd,"build_candidate_day",fake_build)
    monkeypatch.setattr(loader.p6,"validate_selected_candidate",lambda dataset:None)

    out=loader._load_p3_days()

    assert len(out)==7
    assert len(calls)==7
    assert all(c[1]==p6.SELECTED_TARGET for c in calls)
    assert all(c[2]==p6.SELECTED_WINDOW_SECONDS for c in calls)
    assert all(c[3]==p6.SELECTED_BLOCK for c in calls)
