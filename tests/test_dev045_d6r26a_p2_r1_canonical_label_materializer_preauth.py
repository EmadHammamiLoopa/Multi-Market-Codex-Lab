from __future__ import annotations

import pytest

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p1_synthetic_candidate_labeler as p1
from multimarket import dev045_d6r26a_p2_r1_canonical_label_materializer_preauth as p


def _sources():
    return {day: p.FrozenSourceIdentity(day, f"/frozen/{day}.npz", 1000 + i, f"{i + 1:064x}") for i, day in enumerate(p.REAL_DEVELOPMENT_DAYS)}


def _row():
    day = p.REAL_DEVELOPMENT_DAYS[0]
    lane = next(x for x in p.build_materialization_plan() if x.day == day and x.side == "BID" and x.distance_ticks == 0 and x.phase == 1)
    decision = 31_000_000_000
    row = {name: None for name in p.ROW_SCHEMA_FIELDS}
    row.update(
        experiment_id=p.EXPERIMENT_ID,
        design_version=p.DESIGN_VERSION,
        data_role=p.DATA_ROLE,
        source_day=day,
        source_path=f"/frozen/{day}.npz",
        source_bytes=1000,
        source_sha256="1" * 64,
        day_start_local_ns=0,
        decision_local_ns=decision,
        side="BID",
        distance_ticks=0,
        phase=1,
        lane_id=lane.lane_id,
        best_bid_tick=1000,
        best_ask_tick=1001,
        candidate_price_tick=1000,
        candidate_price=100.0,
        candidate_qty=p0.CANDIDATE_ORDER_QTY,
        candidate_tif=p0.CANDIDATE_TIME_IN_FORCE,
        label_scenario=p0.PRIMARY_LABEL_SCENARIO,
        entry_latency_ns=p0.ENTRY_LATENCY_NS,
        response_latency_ns=p0.RESPONSE_LATENCY_NS,
        placement_outcome=p1.POST_ONLY_ACCEPTED,
        feature_support="SUPPORTED",
        feature_warmup_complete=True,
    )
    for name in p.FEATURE_NAMES:
        row[name] = 0.0
        row[f"{name}__observable_local_ns"] = decision
    for h in p0.FILL_HORIZONS_NS:
        s = p._FILL_SUFFIX[h]
        row[f"fill_{s}__state"] = p1.NOT_FILLED_WITHIN_TAU
        row[f"fill_{s}__any_fill"] = False
        row[f"fill_{s}__fill_fraction"] = 0.0
        row[f"fill_{s}__fill_fraction_censored"] = False
        row[f"fill_{s}__time_to_first_fill_ns"] = None
        row[f"fill_{s}__time_to_full_fill_ns"] = None
        row[f"fill_{s}__full_fill_status"] = p1.NOT_FULL_WITHIN_TAU
        row[f"markout_{s}__status"] = p1.MARKOUT_NOT_APPLICABLE_NO_FILL
        row[f"markout_{s}__value_bps"] = None
    return row


def test_preauth_contract_closes_all_execution_surfaces():
    p.validate_preauth_contract()
    assert p.PREAUTH_ONLY is True
    assert p.FROZEN_SOURCE_REGISTRY_REQUIRED is True
    assert p.FROZEN_SOURCE_REGISTRY_EMBEDDED is False
    assert p.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert p.CANDIDATE_SIMULATION_AUTHORIZED is False
    assert p.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert p.MODEL_FIT_AUTHORIZED is False
    assert p.PNL_AUTHORIZED is False
    assert p.LIVE_TRADING_AUTHORIZED is False


def test_authorization_validator_is_exact_and_pure():
    with pytest.raises(p.PreauthMaterializerError, match="authorization_denied"):
        p.validate_authorization_value(None)
    with pytest.raises(p.PreauthMaterializerError, match="authorization_denied"):
        p.validate_authorization_value(p.AUTH_TOKEN + "_WRONG")
    p.validate_authorization_value(p.AUTH_TOKEN)


def test_source_registry_requires_exact_jan_jul_identity_shape():
    registry = _sources()
    validated = p.validate_source_registry(registry)
    assert tuple(x.day for x in validated) == p.REAL_DEVELOPMENT_DAYS
    missing = dict(registry); missing.pop(p.REAL_DEVELOPMENT_DAYS[-1])
    with pytest.raises(p.PreauthMaterializerError, match="source_registry_days"):
        p.validate_source_registry(missing)
    expected = validated[0]
    p.require_exact_source_identity(expected, expected)
    altered = p.FrozenSourceIdentity(expected.day, expected.path, expected.bytes + 1, expected.sha256)
    with pytest.raises(p.PreauthMaterializerError, match="source_identity_mismatch"):
        p.require_exact_source_identity(expected, altered)


def test_materialization_plan_is_exactly_7_by_40_and_deterministic():
    a = p.build_materialization_plan(); b = p.build_materialization_plan()
    assert a == b and len(a) == 280 and len({x.lane_id for x in a}) == 280
    for day in p.REAL_DEVELOPMENT_DAYS:
        lanes = [x for x in a if x.day == day]
        assert len(lanes) == 40
        assert {x.side for x in lanes} == {"BID", "ASK"}
        assert {x.distance_ticks for x in lanes} == {0, 1, 2, 4}
        assert {x.phase for x in lanes} == {0, 1, 2, 3, 4}


def test_phase_lanes_cover_each_post_warmup_second_exactly_once():
    p.assert_phase_cover_exactly_once(day_start_local_ns=0, day_end_local_ns=45_000_000_000)
    epochs = [t for phase in p.LANE_PHASE_OFFSETS_S for t in p.decision_epochs_for_lane(day_start_local_ns=0, day_end_local_ns=45_000_000_000, phase=phase)]
    assert sorted(epochs) == list(range(30_000_000_000, 45_000_000_000, 1_000_000_000))
    for phase in p.LANE_PHASE_OFFSETS_S:
        lane_epochs = p.decision_epochs_for_lane(day_start_local_ns=0, day_end_local_ns=45_000_000_000, phase=phase)
        assert all(b - a == 5_000_000_000 for a, b in zip(lane_epochs, lane_epochs[1:]))


def test_row_contract_is_causal_and_self_consistent():
    row = _row(); p.validate_row_contract(row)
    bad = dict(row); bad[f"{p.FEATURE_NAMES[0]}__observable_local_ns"] = int(row["decision_local_ns"]) + 1
    with pytest.raises(Exception, match="future_feature"):
        p.validate_row_contract(bad)
    bad = dict(row); bad["phase"] = 0
    with pytest.raises(p.PreauthMaterializerError, match="row_phase"):
        p.validate_row_contract(bad)
    bad = dict(row); bad["lane_id"] = "WRONG"
    with pytest.raises(p.PreauthMaterializerError, match="row_lane_id"):
        p.validate_row_contract(bad)
    bad = dict(row); bad["candidate_price_tick"] = 999
    with pytest.raises(p.PreauthMaterializerError, match="row_candidate_price_tick"):
        p.validate_row_contract(bad)
    bad = dict(row); bad["fill_1s__state"] = p1.CENSORED; bad["fill_1s__any_fill"] = False; bad["fill_1s__fill_fraction_censored"] = True
    with pytest.raises(p.PreauthMaterializerError, match="row_censor_collapsed_to_no_fill"):
        p.validate_row_contract(bad)


def test_manifest_is_canonical_and_sha_stable():
    day = p.REAL_DEVELOPMENT_DAYS[0]; source = _sources()[day]
    lanes = [x for x in p.build_materialization_plan() if x.day == day]
    parts = [p.partition_identity_from_bytes(lane=lane, payload=lane.lane_id.encode(), row_count=i) for i, lane in enumerate(reversed(lanes), start=1)]
    m1 = p.build_day_manifest(day=day, source=source, partitions=parts)
    m2 = p.build_day_manifest(day=day, source=source, partitions=list(reversed(parts)))
    assert m1 == m2 and m1.partition_count == 40 and m1.row_count == sum(range(1, 41))
    assert p.canonical_manifest_bytes(m1) == p.canonical_manifest_bytes(m2)
    assert p.manifest_sha256(m1) == p.manifest_sha256(m2)
    assert len(p.manifest_sha256(m1)) == 64


def test_atomic_publish_and_lineage_contracts():
    plan = p.atomic_publish_plan("day=2026-01-01/manifest.json")
    assert plan.temp_relpath.endswith(".tmp") and plan.publish_rule == "WRITE_TEMP_FSYNC_HASH_VERIFY_ATOMIC_RENAME_ONCE"
    with pytest.raises(p.PreauthMaterializerError, match="publish_relpath"):
        p.atomic_publish_plan("/absolute/not/allowed")
    assert p.PARENT_P2_HEAD == "a0e22b680c59c4ba26cb1dddc902182fcc962bda"
    assert p.D6R24_EXECUTION_HEAD == "b04a18f8eb5b4689abd15d7cdf6a6c889ee36212"
    assert p.Q8_EXECUTION_HEAD == "bc6b66fdf2634cdacf04f2738722b36a9f1619d8"
    assert p.HFTBACKTEST_UPSTREAM_HEAD == "a244a14250b42d97fc305569c93c4117cd5e1dff"
    assert p.DATA_ROLE == "CONSUMED_DEVELOPMENT"
