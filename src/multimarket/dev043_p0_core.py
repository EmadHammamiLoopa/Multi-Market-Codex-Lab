from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from . import dev030_first_passage as fp

EVENT_NONE=0
EVENT_TOUCH=1

DIR_LONG=1
DIR_SHORT=2

class DecompositionError(RuntimeError):
    pass

@dataclass(frozen=True)
class DecomposedTarget:
    valid:bool
    stage_a_event:int|None
    stage_b_direction:int|None

def decompose_record(record:Mapping[str,Any])->DecomposedTarget:
    if record.get("target_valid") is not True:
        return DecomposedTarget(False,None,None)

    if record.get("same_row_ambiguous") is not False:
        return DecomposedTarget(False,None,None)

    label=record.get("label")

    if label==fp.NONE:
        return DecomposedTarget(True,EVENT_NONE,None)

    if label==fp.LONG_FIRST:
        return DecomposedTarget(True,EVENT_TOUCH,DIR_LONG)

    if label==fp.SHORT_FIRST:
        return DecomposedTarget(True,EVENT_TOUCH,DIR_SHORT)

    raise DecompositionError(f"unknown_label:{label!r}")

def factorization_invariants(record:Mapping[str,Any])->dict[str,bool]:
    d=decompose_record(record)

    if not d.valid:
        return {
            "invalid_maps_to_no_stage_a_label":d.stage_a_event is None,
            "invalid_maps_to_no_stage_b_label":d.stage_b_direction is None,
            "none_has_no_direction":True,
            "touch_has_direction":True,
        }

    none_has_no_direction=(
        d.stage_a_event!=EVENT_NONE
        or d.stage_b_direction is None
    )

    touch_has_direction=(
        d.stage_a_event!=EVENT_TOUCH
        or d.stage_b_direction in (DIR_LONG,DIR_SHORT)
    )

    return {
        "invalid_maps_to_no_stage_a_label":True,
        "invalid_maps_to_no_stage_b_label":True,
        "none_has_no_direction":bool(none_has_no_direction),
        "touch_has_direction":bool(touch_has_direction),
    }
