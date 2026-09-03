from __future__ import annotations

from multimarket import dev030_first_passage as fp
from multimarket import dev043_p0_core as core
from multimarket import dev043_p0_harness as harness
from multimarket import dev043_p0_runner as runner

def _r(*,valid=True,label=None,ambiguous=False):
    return {
        "target_valid":valid,
        "label":label,
        "same_row_ambiguous":ambiguous,
    }

def test_none_maps_to_stage_a_only():
    z=core.decompose_record(_r(label=fp.NONE))
    assert z.valid
    assert z.stage_a_event==core.EVENT_NONE
    assert z.stage_b_direction is None

def test_long_touch_maps_to_long_direction():
    z=core.decompose_record(_r(label=fp.LONG_FIRST))
    assert z.valid
    assert z.stage_a_event==core.EVENT_TOUCH
    assert z.stage_b_direction==core.DIR_LONG

def test_short_touch_maps_to_short_direction():
    z=core.decompose_record(_r(label=fp.SHORT_FIRST))
    assert z.valid
    assert z.stage_a_event==core.EVENT_TOUCH
    assert z.stage_b_direction==core.DIR_SHORT

def test_invalid_excluded_from_both_stages():
    z=core.decompose_record(_r(valid=False,label=None))
    assert not z.valid
    assert z.stage_a_event is None
    assert z.stage_b_direction is None

def test_ambiguous_excluded_from_both_stages():
    z=core.decompose_record(_r(valid=True,label=fp.LONG_FIRST,ambiguous=True))
    assert not z.valid
    assert z.stage_a_event is None
    assert z.stage_b_direction is None

def test_factorization_invariants_all_pass_for_frozen_alphabet():
    rows=(
        _r(label=fp.NONE),
        _r(label=fp.LONG_FIRST),
        _r(label=fp.SHORT_FIRST),
        _r(valid=False,label=None),
        _r(valid=True,label=fp.LONG_FIRST,ambiguous=True),
    )
    for r in rows:
        assert all(core.factorization_invariants(r).values())

def test_unknown_valid_label_fails_closed():
    try:
        core.decompose_record(_r(label="BAD"))
    except core.DecompositionError:
        pass
    else:
        raise AssertionError("unknown label must fail closed")

def test_runner_forbidden_result_guards_all_false():
    assert not any(runner.FORWARD_GUARDS.values())
    for k in (
        "model_fit",
        "probabilities_calculated",
        "classification_metrics_calculated",
        "economics_calculated",
        "null_calculated",
        "class_counts_serialized",
        "class_prevalence_serialized",
    ):
        assert runner.FORWARD_GUARDS[k] is False

def test_parent_identities_frozen():
    assert runner.DEV041_BYTES==429239
    assert runner.DEV041_SHA=="542117791966f9049cb49e5b578d7857b3e1178f44be83172c7edfac56244a15"
    assert runner.DEV042_P0_BYTES==12989
    assert runner.DEV042_P0_SHA=="d9259a53d24492f478615c986ed73981f052d483a764935a8dfd68d17212b882"
    assert runner.DEV042_P3_BYTES==155134
    assert runner.DEV042_P3_SHA=="bdb411e8536d94bb21deca5bfb7f31998023dacd727c27c3a67993b0bc07ac3f"

def test_harness_smoke():
    assert harness.process_pool_smoke(2)==(1,4,9,16)
