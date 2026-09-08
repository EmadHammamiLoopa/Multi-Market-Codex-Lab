from __future__ import annotations

import io

import pytest

from multimarket import (
    dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0,
)
from multimarket import (
    dev045_d6r26a_p1_synthetic_candidate_labeler as p1,
)
from multimarket import (
    dev045_d6r26a_p2_jan_jul_consumed_development_label_design as p2,
)
from multimarket import (
    dev045_d6r26a_p2_r1_canonical_label_materializer_preauth as r1,
)
from multimarket import (
    dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b,
)
from multimarket import (
    dev045_d6r26a_p2_r16_canonical_row_parquet_serializer_preexecution as r16,
)


def _source():
    return r1.FrozenSourceIdentity(
        day="2026-02-01",
        path="/synthetic/r16/frozen.npy",
        bytes=123_456,
        sha256="0" * 64,
    )


def _lane(
    *,
    side="BID",
    distance=0,
    decision=31_000_000_000,
):
    phase = p1.lane_phase(
        day_start_local_ns=0,
        decision_local_ns=decision,
    )

    return next(
        lane
        for lane in r1.build_materialization_plan()
        if lane.day == "2026-02-01"
        and lane.side == side
        and lane.distance_ticks == distance
        and lane.phase == phase
    )


def _feature_vector(
    *,
    decision,
):
    return r8b.FeatureVector(
        values={
            name: 0.0
            for name in r8b.FEATURE_NAMES
        },
        observable_local_ns={
            name: int(decision)
            for name in r8b.FEATURE_NAMES
        },
        support=p2.CANDIDATE_ELIGIBILITY,
    )


def _row(
    *,
    decision=31_000_000_000,
    source_observed_through=40_000_000_000,
):
    side = "BID"
    distance = 0

    candidate = p1.CandidateSpec(
        side=side,
        distance_ticks=distance,
        decision_local_ns=decision,
        best_bid_tick=1000,
        best_ask_tick=1001,
    )

    labels = r8b.build_label_bundle(
        candidate=candidate,
        fills=(),
        midpoints=(),
        source_exchange_observed_through_ns=source_observed_through,
        placement_outcome=p1.POST_ONLY_ACCEPTED,
    )

    return r16.build_canonical_row(
        source=_source(),
        lane=_lane(
            side=side,
            distance=distance,
            decision=decision,
        ),
        day_start_local_ns=0,
        candidate=candidate,
        feature_vector=_feature_vector(
            decision=decision,
        ),
        labels=labels,
        placement_outcome=p1.POST_ONLY_ACCEPTED,
    )


def test_r16_contract_is_strictly_preexecution():
    r16.validate_r16_contract()

    assert r16.PYARROW_VERSION == "25.0.1"
    assert r16.ROW_BATCH_SIZE == 1024

    assert r16.FULL_DAY_ROW_MATERIALIZATION_FORBIDDEN is True
    assert r16.ONE_PARTITION_PAYLOAD_AT_A_TIME is True

    assert r16.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r16.CANDIDATE_SIMULATION_AUTHORIZED is False
    assert r16.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r16.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r16.MODEL_FIT_AUTHORIZED is False
    assert r16.PNL_AUTHORIZED is False


def test_canonical_row_matches_exact_r1_schema():
    row = _row()

    assert tuple(row) == tuple(r1.ROW_SCHEMA_FIELDS)

    r1.validate_row_contract(row)

    assert row["experiment_id"] == r1.EXPERIMENT_ID
    assert row["design_version"] == r1.DESIGN_VERSION
    assert row["lane_id"] == _lane().lane_id

    assert (
        row["fill_1s__state"]
        == p1.NOT_FILLED_WITHIN_TAU
    )


def test_eof_censoring_survives_row_materialization():
    row = _row(
        decision=46_000_000_000,
        source_observed_through=47_000_000_000,
    )

    assert (
        row["fill_250ms__state"]
        == p1.NOT_FILLED_WITHIN_TAU
    )
    assert (
        row["fill_500ms__state"]
        == p1.NOT_FILLED_WITHIN_TAU
    )
    assert (
        row["fill_1s__state"]
        == p1.NOT_FILLED_WITHIN_TAU
    )

    assert row["fill_2s__state"] == p1.CENSORED
    assert row["fill_5s__state"] == p1.CENSORED

    assert row["fill_2s__any_fill"] is None
    assert row["fill_5s__any_fill"] is None

    assert row["fill_2s__fill_fraction_censored"] is True
    assert row["fill_5s__fill_fraction_censored"] is True


def test_arrow_schema_is_exact_and_stable():
    schema = r16.canonical_arrow_schema()

    assert tuple(schema.names) == tuple(r1.ROW_SCHEMA_FIELDS)
    assert len(schema.names) == len(r1.ROW_SCHEMA_FIELDS)


def test_parquet_bytes_are_deterministic_and_round_trip():
    import pyarrow.parquet as pq

    rows = [
        _row(),
        _row(
            decision=46_000_000_000,
            source_observed_through=47_000_000_000,
        ),
    ]

    payload_a, count_a = r16.serialize_rows_to_parquet(
        iter(rows)
    )
    payload_b, count_b = r16.serialize_rows_to_parquet(
        iter(rows)
    )

    assert count_a == 2
    assert count_b == 2

    assert payload_a == payload_b
    assert payload_a[:4] == b"PAR1"
    assert payload_a[-4:] == b"PAR1"

    table = pq.read_table(
        io.BytesIO(payload_a)
    )

    assert tuple(table.schema.names) == tuple(r1.ROW_SCHEMA_FIELDS)

    restored = table.to_pylist()

    assert restored == rows


def test_serializer_batches_without_full_lane_row_list():
    row = _row()

    generated = 0

    def rows():
        nonlocal generated

        for _ in range(
            2 * r16.ROW_BATCH_SIZE + 3
        ):
            generated += 1
            yield row

    payload, count = r16.serialize_rows_to_parquet(
        rows()
    )

    assert generated == 2051
    assert count == 2051
    assert payload[:4] == b"PAR1"
    assert payload[-4:] == b"PAR1"


def test_empty_partition_fails_closed():
    with pytest.raises(
        r16.CanonicalSerializerError,
        match="empty_partition",
    ):
        r16.serialize_rows_to_parquet(())
