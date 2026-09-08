from __future__ import annotations

from collections.abc import Iterable, Mapping
import importlib
from typing import Any

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
    dev045_d6r26a_p2_r15_sequential_lane_real_engine_preexecution as r15,
)


EXPERIMENT_ID = "DEV045-D6R26A-P2-R16"
DESIGN_VERSION = "canonical-row-parquet-serializer-preexecution-v1"
PARENT_R15_HEAD = "3df193741befc801d07da1e732d80366fcb29b73"

CANONICAL_ROW_BUILDER_FROZEN = True
DETERMINISTIC_PARQUET_SERIALIZER_FROZEN = True
R1_EXACT_ROW_SCHEMA_BOUND = True
R8B_FEATURE_LABEL_SEMANTICS_BOUND = True
R15_EOF_CENSORING_BOUND = True

PARQUET_ENGINE = "pyarrow"
PYARROW_VERSION = "25.0.1"
PARQUET_FORMAT_VERSION = "2.6"
PARQUET_DATA_PAGE_VERSION = "1.0"
PARQUET_COMPRESSION = "zstd"
PARQUET_COMPRESSION_LEVEL = 9
PARQUET_USE_DICTIONARY = False
PARQUET_WRITE_STATISTICS = True

# Bound Python row buffer. Final compressed partition bytes are retained only
# because the already-frozen R8A atomic publisher accepts a bytes payload.
ROW_BATCH_SIZE = 1024
FULL_DAY_ROW_MATERIALIZATION_FORBIDDEN = True
ONE_PARTITION_PAYLOAD_AT_A_TIME = True

PREEXECUTION_ONLY = True
HISTORICAL_FILE_IO_AUTHORIZED = False
HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
SIMULATOR_IMPORT_AUTHORIZED = False
CANDIDATE_SIMULATION_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False


class CanonicalSerializerError(RuntimeError):
    pass


def _pyarrow():
    pa = importlib.import_module("pyarrow")
    pq = importlib.import_module("pyarrow.parquet")

    if str(pa.__version__) != PYARROW_VERSION:
        raise CanonicalSerializerError(
            f"pyarrow_version:{pa.__version__}:{PYARROW_VERSION}"
        )

    return pa, pq


def _fill_suffix(horizon_ns: int) -> str:
    mapping = {
        250_000_000: "250ms",
        500_000_000: "500ms",
        1_000_000_000: "1s",
        2_000_000_000: "2s",
        5_000_000_000: "5s",
    }

    try:
        return mapping[int(horizon_ns)]
    except KeyError as exc:
        raise CanonicalSerializerError(
            f"horizon_suffix:{horizon_ns}"
        ) from exc


def _lane_phase(
    *,
    day_start_local_ns: int,
    candidate: p1.CandidateSpec,
) -> int:
    return p1.lane_phase(
        day_start_local_ns=int(day_start_local_ns),
        decision_local_ns=int(candidate.decision_local_ns),
    )


def build_canonical_row(
    *,
    source: r1.FrozenSourceIdentity,
    lane: r1.LaneSpec,
    day_start_local_ns: int,
    candidate: p1.CandidateSpec,
    feature_vector: r8b.FeatureVector,
    labels: r8b.LabelBundle,
    placement_outcome: str,
) -> dict[str, object]:
    phase = _lane_phase(
        day_start_local_ns=day_start_local_ns,
        candidate=candidate,
    )

    if source.day != lane.day:
        raise CanonicalSerializerError("source_lane_day")

    if candidate.side != lane.side:
        raise CanonicalSerializerError("candidate_lane_side")

    if int(candidate.distance_ticks) != int(lane.distance_ticks):
        raise CanonicalSerializerError("candidate_lane_distance")

    if int(phase) != int(lane.phase):
        raise CanonicalSerializerError("candidate_lane_phase")

    if set(feature_vector.values) != set(r8b.FEATURE_NAMES):
        raise CanonicalSerializerError("feature_names")

    if set(feature_vector.observable_local_ns) != set(r8b.FEATURE_NAMES):
        raise CanonicalSerializerError("feature_observable_names")

    p1.validate_feature_observability(
        decision_local_ns=int(candidate.decision_local_ns),
        feature_observable_local_ns=feature_vector.observable_local_ns,
    )

    fill_by_horizon = {
        int(item.horizon_ns): item
        for item in labels.fill_labels
    }

    markout_by_horizon = {
        int(item.horizon_ns): item
        for item in labels.markout_labels
    }

    if set(fill_by_horizon) != set(p0.FILL_HORIZONS_NS):
        raise CanonicalSerializerError("fill_horizon_set")

    if set(markout_by_horizon) != set(p0.MARKOUT_HORIZONS_NS):
        raise CanonicalSerializerError("markout_horizon_set")

    row: dict[str, object] = {
        "experiment_id": r1.EXPERIMENT_ID,
        "design_version": r1.DESIGN_VERSION,
        "data_role": r1.DATA_ROLE,
        "source_day": source.day,
        "source_path": source.path,
        "source_bytes": int(source.bytes),
        "source_sha256": source.sha256,
        "day_start_local_ns": int(day_start_local_ns),
        "decision_local_ns": int(candidate.decision_local_ns),
        "side": candidate.side,
        "distance_ticks": int(candidate.distance_ticks),
        "phase": int(phase),
        "lane_id": lane.lane_id,
        "best_bid_tick": int(candidate.best_bid_tick),
        "best_ask_tick": int(candidate.best_ask_tick),
        "candidate_price_tick": int(candidate.price_tick),
        "candidate_price": float(candidate.price),
        "candidate_qty": float(candidate.qty),
        "candidate_tif": p0.CANDIDATE_TIME_IN_FORCE,
        "label_scenario": p0.PRIMARY_LABEL_SCENARIO,
        "entry_latency_ns": int(p0.ENTRY_LATENCY_NS),
        "response_latency_ns": int(p0.RESPONSE_LATENCY_NS),
        "placement_outcome": placement_outcome,
        "feature_support": feature_vector.support,
        "feature_warmup_complete": True,
    }

    for name in r8b.FEATURE_NAMES:
        row[name] = float(feature_vector.values[name])
        row[f"{name}__observable_local_ns"] = int(
            feature_vector.observable_local_ns[name]
        )

    for horizon in p0.FILL_HORIZONS_NS:
        suffix = _fill_suffix(horizon)
        item = fill_by_horizon[int(horizon)]

        row[f"fill_{suffix}__state"] = item.state
        row[f"fill_{suffix}__any_fill"] = item.any_fill_within_tau
        row[f"fill_{suffix}__fill_fraction"] = item.fill_fraction_at_tau
        row[
            f"fill_{suffix}__fill_fraction_censored"
        ] = item.fill_fraction_censored
        row[
            f"fill_{suffix}__time_to_first_fill_ns"
        ] = item.time_to_first_fill_ns
        row[
            f"fill_{suffix}__time_to_full_fill_ns"
        ] = item.time_to_full_fill_ns
        row[
            f"fill_{suffix}__full_fill_status"
        ] = item.full_fill_status

    for horizon in p0.MARKOUT_HORIZONS_NS:
        suffix = _fill_suffix(horizon)
        item = markout_by_horizon[int(horizon)]

        row[f"markout_{suffix}__status"] = item.status
        row[f"markout_{suffix}__value_bps"] = item.value_bps

    if set(row) != set(r1.ROW_SCHEMA_FIELDS):
        missing = sorted(set(r1.ROW_SCHEMA_FIELDS) - set(row))
        extra = sorted(set(row) - set(r1.ROW_SCHEMA_FIELDS))
        raise CanonicalSerializerError(
            f"row_schema:{missing}:{extra}"
        )

    ordered = {
        field: row[field]
        for field in r1.ROW_SCHEMA_FIELDS
    }

    r1.validate_row_contract(ordered)

    return ordered


def _arrow_type_for_field(
    pa,
    field: str,
):
    string_fields = {
        "experiment_id",
        "design_version",
        "data_role",
        "source_day",
        "source_path",
        "source_sha256",
        "side",
        "lane_id",
        "candidate_tif",
        "label_scenario",
        "placement_outcome",
        "feature_support",
    }

    integer_fields = {
        "source_bytes",
        "day_start_local_ns",
        "decision_local_ns",
        "distance_ticks",
        "phase",
        "best_bid_tick",
        "best_ask_tick",
        "candidate_price_tick",
        "entry_latency_ns",
        "response_latency_ns",
    }

    float_fields = {
        "candidate_price",
        "candidate_qty",
        *r8b.FEATURE_NAMES,
    }

    bool_fields = {
        "feature_warmup_complete",
    }

    if field in string_fields:
        return pa.string()

    if field in integer_fields:
        return pa.int64()

    if field in float_fields:
        return pa.float64()

    if field in bool_fields:
        return pa.bool_()

    if field.endswith("__observable_local_ns"):
        return pa.int64()

    if field.startswith("fill_"):
        if field.endswith("__state"):
            return pa.string()
        if field.endswith("__any_fill"):
            return pa.bool_()
        if field.endswith("__fill_fraction"):
            return pa.float64()
        if field.endswith("__fill_fraction_censored"):
            return pa.bool_()
        if field.endswith("__time_to_first_fill_ns"):
            return pa.int64()
        if field.endswith("__time_to_full_fill_ns"):
            return pa.int64()
        if field.endswith("__full_fill_status"):
            return pa.string()

    if field.startswith("markout_"):
        if field.endswith("__status"):
            return pa.string()
        if field.endswith("__value_bps"):
            return pa.float64()

    raise CanonicalSerializerError(
        f"arrow_type_missing:{field}"
    )


def canonical_arrow_schema():
    pa, _ = _pyarrow()

    fields = [
        pa.field(
            field,
            _arrow_type_for_field(pa, field),
            nullable=True,
        )
        for field in r1.ROW_SCHEMA_FIELDS
    ]

    schema = pa.schema(fields)

    if tuple(schema.names) != tuple(r1.ROW_SCHEMA_FIELDS):
        raise CanonicalSerializerError(
            "arrow_schema_order"
        )

    return schema


def serialize_rows_to_parquet(
    rows: Iterable[Mapping[str, object]],
) -> tuple[bytes, int]:
    pa, pq = _pyarrow()
    schema = canonical_arrow_schema()

    sink = pa.BufferOutputStream()

    writer = pq.ParquetWriter(
        sink,
        schema,
        version=PARQUET_FORMAT_VERSION,
        compression=PARQUET_COMPRESSION,
        compression_level=PARQUET_COMPRESSION_LEVEL,
        use_dictionary=PARQUET_USE_DICTIONARY,
        write_statistics=PARQUET_WRITE_STATISTICS,
        data_page_version=PARQUET_DATA_PAGE_VERSION,
    )

    count = 0
    batch: list[dict[str, object]] = []

    try:
        for raw in rows:
            row = {
                field: raw[field]
                for field in r1.ROW_SCHEMA_FIELDS
            }

            r1.validate_row_contract(row)

            batch.append(row)
            count += 1

            if len(batch) >= ROW_BATCH_SIZE:
                table = pa.Table.from_pylist(
                    batch,
                    schema=schema,
                )
                writer.write_table(
                    table,
                    row_group_size=ROW_BATCH_SIZE,
                )
                batch.clear()

        if batch:
            table = pa.Table.from_pylist(
                batch,
                schema=schema,
            )
            writer.write_table(
                table,
                row_group_size=ROW_BATCH_SIZE,
            )
            batch.clear()

    finally:
        writer.close()

    if count <= 0:
        raise CanonicalSerializerError(
            "empty_partition"
        )

    payload = sink.getvalue().to_pybytes()

    if (
        len(payload) < 8
        or payload[:4] != b"PAR1"
        or payload[-4:] != b"PAR1"
    ):
        raise CanonicalSerializerError(
            "parquet_magic"
        )

    return payload, count


def validate_r16_contract() -> None:
    r1.validate_preauth_contract()
    r8b.validate_r8b_contract()
    r15.validate_r15_contract()

    if PARENT_R15_HEAD != (
        "3df193741befc801d07da1e732d80366fcb29b73"
    ):
        raise CanonicalSerializerError("parent")

    if PYARROW_VERSION != "25.0.1":
        raise CanonicalSerializerError(
            "pyarrow_version_contract"
        )

    if ROW_BATCH_SIZE != 1024:
        raise CanonicalSerializerError(
            "row_batch_size"
        )

    required = (
        CANONICAL_ROW_BUILDER_FROZEN,
        DETERMINISTIC_PARQUET_SERIALIZER_FROZEN,
        R1_EXACT_ROW_SCHEMA_BOUND,
        R8B_FEATURE_LABEL_SEMANTICS_BOUND,
        R15_EOF_CENSORING_BOUND,
        FULL_DAY_ROW_MATERIALIZATION_FORBIDDEN,
        ONE_PARTITION_PAYLOAD_AT_A_TIME,
        PREEXECUTION_ONLY,
        r15.END_OF_SOURCE_CANDIDATES_RETAINED_WITH_CENSORING,
        not r15.CENSORED_MAPS_TO_NO_FILL,
    )

    if not all(required):
        raise CanonicalSerializerError(
            "required_guard"
        )

    forbidden = (
        HISTORICAL_FILE_IO_AUTHORIZED,
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        SIMULATOR_IMPORT_AUTHORIZED,
        CANDIDATE_SIMULATION_AUTHORIZED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
    )

    if any(forbidden):
        raise CanonicalSerializerError(
            "execution_surface_open"
        )


__all__ = [
    "build_canonical_row",
    "canonical_arrow_schema",
    "serialize_rows_to_parquet",
    "validate_r16_contract",
]
