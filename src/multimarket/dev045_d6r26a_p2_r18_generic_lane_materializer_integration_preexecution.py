from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
import hashlib
from pathlib import Path

import numpy as np

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
    dev045_d6r26a_p2_r4_canonical_materialization_runner_preexec as r4,
)
from multimarket import (
    dev045_d6r26a_p2_r8a_real_hooks_writer_preexecution as r8a,
)
from multimarket import (
    dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b,
)
from multimarket import (
    dev045_d6r26a_p2_r14_synthetic_candidate_grid_real_engine_preexecution as r14,
)
from multimarket import (
    dev045_d6r26a_p2_r15_sequential_lane_real_engine_preexecution as r15,
)
from multimarket import (
    dev045_d6r26a_p2_r16_canonical_row_parquet_serializer_preexecution as r16,
)
from multimarket import (
    dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17,
)


EXPERIMENT_ID = "DEV045-D6R26A-P2-R18"
DESIGN_VERSION = "generic-lane-materializer-integration-preexecution-v1"
PARENT_R17_HEAD = "0ec427c4466200d0f14626609e02a535d0738bdf"

GENERIC_LANE_MATERIALIZER_FROZEN = True
R4_LANE_ARTIFACT_SHAPE_BOUND = True
R8A_ATOMIC_PUBLISHER_BOUND = True
R15_SEQUENTIAL_REAL_ENGINE_BOUND = True
R16_CANONICAL_ROW_PARQUET_BOUND = True
R17_SHARED_DENSE_CACHE_BOUND = True
R17_FEED_BOUND_EOF_BOUND = True

# The real campaign RunnerHooks are deliberately NOT wired here.
R4_FULL_RUNNER_BINDING_CREATED = False
EXECUTION_AUTHORIZATION_CREATED = False

# Explicitly repair the ambiguity that was only implicit in prior layers.
P2_ATTEMPT_CONSUMED = False

# Exact-engine probes are synthetic only.
SYNTHETIC_REAL_ENGINE_PROBES_AUTHORIZED = True
SYNTHETIC_TEMP_ARTIFACT_WRITE_AUTHORIZED = True

PREEXECUTION_ONLY = True
HISTORICAL_FILE_IO_AUTHORIZED = False
HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
HISTORICAL_SIMULATOR_IMPORT_AUTHORIZED = False
HISTORICAL_CANDIDATE_SIMULATION_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False

CANDIDATE_GRID = tuple(
    (side, int(distance))
    for side in p0.CANDIDATE_SIDES
    for distance in p0.CANDIDATE_DISTANCE_TICKS
)
CANDIDATE_GRID_CASE_COUNT = 8
FEATURE_COUNT = 25


class GenericLaneMaterializerError(RuntimeError):
    pass


@dataclass(frozen=True)
class DenseFeatureCache:
    """
    R17-compatible dense once/day feature-cache consumer.

    It contains only decision-grid arrays. It never retains the raw event
    source, decoder, book history, flow history, or Python feature objects.
    """

    decision_local_ns: np.ndarray
    best_bid_tick: np.ndarray
    best_ask_tick: np.ndarray
    values: np.ndarray

    @property
    def decision_count(self) -> int:
        return int(self.decision_local_ns.shape[0])

    @property
    def total_bytes(self) -> int:
        return int(
            self.decision_local_ns.nbytes
            + self.best_bid_tick.nbytes
            + self.best_ask_tick.nbytes
            + self.values.nbytes
        )


@dataclass(frozen=True)
class CandidateExecutionRecord:
    candidate: p1.CandidateSpec
    placement_outcome: str
    labels: r8b.LabelBundle


def _case_index(
    side: str,
    distance_ticks: int,
) -> int:
    key = (str(side), int(distance_ticks))

    try:
        return CANDIDATE_GRID.index(key)
    except ValueError as exc:
        raise GenericLaneMaterializerError(
            f"candidate_grid_case:{key}"
        ) from exc


def validate_dense_feature_cache(
    cache: DenseFeatureCache,
) -> None:
    decisions = cache.decision_local_ns
    bids = cache.best_bid_tick
    asks = cache.best_ask_tick
    values = cache.values

    if decisions.ndim != 1:
        raise GenericLaneMaterializerError(
            "cache_decision_ndim"
        )

    n = int(decisions.shape[0])

    if n <= 0:
        raise GenericLaneMaterializerError(
            "cache_empty"
        )

    if decisions.dtype != np.dtype("<i8"):
        raise GenericLaneMaterializerError(
            f"cache_decision_dtype:{decisions.dtype}"
        )

    if bids.dtype != np.dtype("<i8"):
        raise GenericLaneMaterializerError(
            f"cache_bid_dtype:{bids.dtype}"
        )

    if asks.dtype != np.dtype("<i8"):
        raise GenericLaneMaterializerError(
            f"cache_ask_dtype:{asks.dtype}"
        )

    if values.dtype != r17.FEATURE_CACHE_VALUE_DTYPE:
        raise GenericLaneMaterializerError(
            f"cache_value_dtype:{values.dtype}"
        )

    if bids.shape != (n,) or asks.shape != (n,):
        raise GenericLaneMaterializerError(
            "cache_bbo_shape"
        )

    if values.shape != (
        n,
        CANDIDATE_GRID_CASE_COUNT,
        FEATURE_COUNT,
    ):
        raise GenericLaneMaterializerError(
            f"cache_value_shape:{values.shape}"
        )

    if n > 1 and np.any(
        np.diff(decisions) <= 0
    ):
        raise GenericLaneMaterializerError(
            "cache_decision_not_strict"
        )

    if np.any(bids <= 0):
        raise GenericLaneMaterializerError(
            "cache_bid_tick"
        )

    if np.any(asks <= bids):
        raise GenericLaneMaterializerError(
            "cache_crossed_bbo"
        )

    if not bool(np.isfinite(values).all()):
        raise GenericLaneMaterializerError(
            "cache_nonfinite"
        )

    if (
        decisions.flags.writeable
        or bids.flags.writeable
        or asks.flags.writeable
        or values.flags.writeable
    ):
        raise GenericLaneMaterializerError(
            "cache_not_frozen_readonly"
        )

    layout = r17.feature_cache_layout(
        decision_count=n,
    )

    if cache.total_bytes != layout.total_bytes:
        raise GenericLaneMaterializerError(
            f"cache_layout_bytes:"
            f"{cache.total_bytes}:{layout.total_bytes}"
        )

    if cache.total_bytes > r17.FEATURE_CACHE_MAX_BYTES:
        raise GenericLaneMaterializerError(
            "cache_budget"
        )


def lookup_feature_vector(
    *,
    cache: DenseFeatureCache,
    candidate: p1.CandidateSpec,
) -> r8b.FeatureVector:
    decision = int(candidate.decision_local_ns)

    index = int(
        np.searchsorted(
            cache.decision_local_ns,
            decision,
            side="left",
        )
    )

    if (
        index >= cache.decision_count
        or int(cache.decision_local_ns[index]) != decision
    ):
        raise GenericLaneMaterializerError(
            f"cache_decision_missing:{decision}"
        )

    if (
        int(cache.best_bid_tick[index])
        != int(candidate.best_bid_tick)
        or int(cache.best_ask_tick[index])
        != int(candidate.best_ask_tick)
    ):
        raise GenericLaneMaterializerError(
            f"cache_candidate_bbo:{decision}"
        )

    case_index = _case_index(
        candidate.side,
        candidate.distance_ticks,
    )

    raw = cache.values[
        index,
        case_index,
        :,
    ]

    values = {
        name: float(raw[i])
        for i, name in enumerate(r8b.FEATURE_NAMES)
    }

    if values["candidate_side_sign"] != float(
        candidate.side_sign
    ):
        raise GenericLaneMaterializerError(
            "cache_side_sign"
        )

    if values["candidate_distance_ticks"] != float(
        candidate.distance_ticks
    ):
        raise GenericLaneMaterializerError(
            "cache_distance"
        )

    if (
        values["displayed_qty_at_candidate_price"]
        != values[
            "estimated_queue_ahead_qty_from_decision_book"
        ]
    ):
        raise GenericLaneMaterializerError(
            "cache_queue_display_equivalence"
        )

    observable = {
        name: decision
        for name in r8b.FEATURE_NAMES
    }

    p1.validate_feature_observability(
        decision_local_ns=decision,
        feature_observable_local_ns=observable,
    )

    return r8b.FeatureVector(
        values=values,
        observable_local_ns=observable,
        support=p2.CANDIDATE_ELIGIBILITY,
    )


def _synthetic_dense_cache_from_bid_d0(
    *,
    candidates: Sequence[p1.CandidateSpec],
    feature_vectors: Sequence[r8b.FeatureVector],
) -> DenseFeatureCache:
    """
    Synthetic CI helper only.

    The raw event stream was already decoded by R14/R15. This helper merely
    transforms those already-computed BID/D0 vectors into the exact dense R17
    storage shape so R18 can test the cache consumer without another raw pass.

    The production once/day cache builder remains outside R18 and sealed.
    """
    if len(candidates) != len(feature_vectors):
        raise GenericLaneMaterializerError(
            "synthetic_cache_cardinality"
        )

    if not candidates:
        raise GenericLaneMaterializerError(
            "synthetic_cache_empty"
        )

    n = len(candidates)

    decisions = np.asarray(
        [
            int(item.decision_local_ns)
            for item in candidates
        ],
        dtype="<i8",
    )

    bids = np.asarray(
        [
            int(item.best_bid_tick)
            for item in candidates
        ],
        dtype="<i8",
    )

    asks = np.asarray(
        [
            int(item.best_ask_tick)
            for item in candidates
        ],
        dtype="<i8",
    )

    values = np.empty(
        (
            n,
            CANDIDATE_GRID_CASE_COUNT,
            FEATURE_COUNT,
        ),
        dtype=r17.FEATURE_CACHE_VALUE_DTYPE,
    )

    for i, (candidate, feature_vector) in enumerate(
        zip(candidates, feature_vectors)
    ):
        if (
            candidate.side != "BID"
            or int(candidate.distance_ticks) != 0
        ):
            raise GenericLaneMaterializerError(
                "synthetic_cache_base_not_bid_d0"
            )

        if set(feature_vector.values) != set(
            r8b.FEATURE_NAMES
        ):
            raise GenericLaneMaterializerError(
                "synthetic_cache_feature_names"
            )

        if set(feature_vector.observable_local_ns) != set(
            r8b.FEATURE_NAMES
        ):
            raise GenericLaneMaterializerError(
                "synthetic_cache_observable_names"
            )

        if any(
            int(feature_vector.observable_local_ns[name])
            != int(candidate.decision_local_ns)
            for name in r8b.FEATURE_NAMES
        ):
            raise GenericLaneMaterializerError(
                "synthetic_cache_observable_time"
            )

        base = {
            name: float(feature_vector.values[name])
            for name in r8b.FEATURE_NAMES
        }

        bid_depth = base["own_best_depth_qty"]
        ask_depth = base["opposite_best_depth_qty"]

        bid_delta = base[
            "same_side_depth_change_250ms"
        ]
        ask_delta = base[
            "opposite_side_depth_change_250ms"
        ]

        for case_index, (
            side,
            distance,
        ) in enumerate(CANDIDATE_GRID):
            case = dict(base)

            if side == "BID":
                own_depth = bid_depth
                opposite_depth = ask_depth
                own_delta = bid_delta
                opposite_delta = ask_delta
                side_sign = 1.0
            else:
                own_depth = ask_depth
                opposite_depth = bid_depth
                own_delta = ask_delta
                opposite_delta = bid_delta
                side_sign = -1.0

            # For the synthetic cache-shape probe, D0 is exact. Deeper
            # cases are populated only to prove dense 8-case storage;
            # R18 never consumes them unless an exact matching vector is
            # supplied by the future once/day real cache builder.
            displayed = (
                own_depth
                if int(distance) == 0
                else 0.0
            )

            case["candidate_side_sign"] = side_sign
            case["candidate_distance_ticks"] = float(
                distance
            )
            case[
                "displayed_qty_at_candidate_price"
            ] = displayed
            case[
                "estimated_queue_ahead_qty_from_decision_book"
            ] = displayed
            case[
                "own_best_depth_qty"
            ] = own_depth
            case[
                "opposite_best_depth_qty"
            ] = opposite_depth
            case[
                "same_side_depth_change_250ms"
            ] = own_delta
            case[
                "opposite_side_depth_change_250ms"
            ] = opposite_delta

            values[
                i,
                case_index,
                :,
            ] = np.asarray(
                [
                    case[name]
                    for name in r8b.FEATURE_NAMES
                ],
                dtype=r17.FEATURE_CACHE_VALUE_DTYPE,
            )

    decisions.setflags(write=False)
    bids.setflags(write=False)
    asks.setflags(write=False)
    values.setflags(write=False)

    cache = DenseFeatureCache(
        decision_local_ns=decisions,
        best_bid_tick=bids,
        best_ask_tick=asks,
        values=values,
    )

    validate_dense_feature_cache(cache)

    return cache


def materialize_lane_partition(
    *,
    source: r1.FrozenSourceIdentity,
    lane: r1.LaneSpec,
    day_start_local_ns: int,
    feed_bounds: r17.FeedBounds,
    feature_cache: DenseFeatureCache,
    records: Iterable[CandidateExecutionRecord],
    output_root: Path,
) -> r4.LaneArtifact:
    """
    Generic bounded lane-result -> canonical-partition materializer.

    It does not open a source and it does not create an engine. Those are
    deliberately left for the final R4 execution binding.

    R18 only consumes:
      - already-frozen lane execution evidence,
      - the shared once/day dense feature cache,
      - R16 canonical serialization,
      - R8A atomic one-shot publishing.
    """
    validate_dense_feature_cache(feature_cache)

    if P2_ATTEMPT_CONSUMED:
        raise GenericLaneMaterializerError(
            "attempt_already_consumed"
        )

    if source.day != lane.day:
        raise GenericLaneMaterializerError(
            "source_lane_day"
        )

    expected_lane_id = r1.lane_id(
        lane.day,
        lane.side,
        lane.distance_ticks,
        lane.phase,
    )

    expected_relpath = r1.partition_relpath(
        lane.day,
        lane.side,
        lane.distance_ticks,
        lane.phase,
    )

    if lane.lane_id != expected_lane_id:
        raise GenericLaneMaterializerError(
            "lane_id"
        )

    if lane.partition_relpath != expected_relpath:
        raise GenericLaneMaterializerError(
            "lane_relpath"
        )

    if (
        int(day_start_local_ns)
        != int(feed_bounds.nominal_day_start_local_ns)
    ):
        raise GenericLaneMaterializerError(
            "day_start_feed_bound"
        )

    def rows():
        previous_decision: int | None = None

        for record in records:
            candidate = record.candidate
            decision = int(
                candidate.decision_local_ns
            )

            if candidate.side != lane.side:
                raise GenericLaneMaterializerError(
                    "candidate_lane_side"
                )

            if int(candidate.distance_ticks) != int(
                lane.distance_ticks
            ):
                raise GenericLaneMaterializerError(
                    "candidate_lane_distance"
                )

            phase = p1.lane_phase(
                day_start_local_ns=int(
                    day_start_local_ns
                ),
                decision_local_ns=decision,
            )

            if int(phase) != int(lane.phase):
                raise GenericLaneMaterializerError(
                    "candidate_lane_phase"
                )

            if (
                decision
                > int(feed_bounds.last_observed_local_ns)
            ):
                raise GenericLaneMaterializerError(
                    "candidate_after_feed_eof"
                )

            if previous_decision is not None:
                if decision <= previous_decision:
                    raise GenericLaneMaterializerError(
                        "candidate_not_strict"
                    )

                if (
                    decision - previous_decision
                    < p0.MAX_CANDIDATE_LIFETIME_NS
                ):
                    raise GenericLaneMaterializerError(
                        "candidate_lane_overlap"
                    )

            feature_vector = lookup_feature_vector(
                cache=feature_cache,
                candidate=candidate,
            )

            yield r16.build_canonical_row(
                source=source,
                lane=lane,
                day_start_local_ns=int(
                    day_start_local_ns
                ),
                candidate=candidate,
                feature_vector=feature_vector,
                labels=record.labels,
                placement_outcome=(
                    record.placement_outcome
                ),
            )

            previous_decision = decision

    payload, row_count = (
        r16.serialize_rows_to_parquet(
            rows()
        )
    )

    artifact = r8a.write_partition_bytes_impl(
        root=Path(output_root),
        lane=lane,
        payload=payload,
        row_count=row_count,
    )

    r8a.verify_partition_impl(
        root=Path(output_root),
        artifact=artifact,
    )

    if artifact.lane_id != lane.lane_id:
        raise GenericLaneMaterializerError(
            "artifact_lane_id"
        )

    if artifact.relpath != lane.partition_relpath:
        raise GenericLaneMaterializerError(
            "artifact_relpath"
        )

    if int(artifact.row_count) != int(row_count):
        raise GenericLaneMaterializerError(
            "artifact_row_count"
        )

    return artifact


def _synthetic_lane(
    *,
    candidate: p1.CandidateSpec,
    day_start_local_ns: int = 0,
) -> r1.LaneSpec:
    phase = p1.lane_phase(
        day_start_local_ns=int(
            day_start_local_ns
        ),
        decision_local_ns=int(
            candidate.decision_local_ns
        ),
    )

    matches = [
        lane
        for lane in r1.build_materialization_plan()
        if (
            lane.side == candidate.side
            and int(lane.distance_ticks)
            == int(candidate.distance_ticks)
            and int(lane.phase) == int(phase)
        )
    ]

    if not matches:
        raise GenericLaneMaterializerError(
            "synthetic_lane_missing"
        )

    return matches[0]


def _synthetic_source(
    lane: r1.LaneSpec,
) -> r1.FrozenSourceIdentity:
    digest = hashlib.sha256(
        (
            "DEV045-D6R26A-P2-R18-SYNTHETIC:"
            + lane.lane_id
        ).encode("ascii")
    ).hexdigest()

    return r1.FrozenSourceIdentity(
        day=lane.day,
        path="/synthetic/dev045_d6r26a_p2_r18.npy",
        bytes=1,
        sha256=digest,
    )


def run_synthetic_sequential_materialization(
    *,
    output_root: Path,
) -> tuple[
    r4.LaneArtifact,
    DenseFeatureCache,
    r15.SequentialLaneResult,
]:
    """
    Exact patched hftbacktest synthetic no-fill sequential-lane integration.

    The three candidates run on one engine in R15. R18 then proves that their
    feature vectors are consumed from the dense cache and serialized/published
    through the exact R16/R8A path.
    """
    result = r15.run_sequential_lane(
        side="BID",
        distance_ticks=0,
    )

    candidates = tuple(
        item.candidate
        for item in result.candidates
    )

    feature_vectors = tuple(
        item.feature_vector
        for item in result.candidates
    )

    cache = _synthetic_dense_cache_from_bid_d0(
        candidates=candidates,
        feature_vectors=feature_vectors,
    )

    lane = _synthetic_lane(
        candidate=candidates[0],
    )

    if any(
        p1.lane_phase(
            day_start_local_ns=0,
            decision_local_ns=int(
                candidate.decision_local_ns
            ),
        )
        != lane.phase
        for candidate in candidates
    ):
        raise GenericLaneMaterializerError(
            "synthetic_sequential_phase"
        )

    source = _synthetic_source(lane)

    fixture = r15.make_sequential_fixture()

    bounds = r17.derive_feed_bounds(
        fixture,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=(
            100_000_000_000
        ),
    )

    observed_through = int(
        np.max(fixture["exch_ts"])
    )

    records = tuple(
        CandidateExecutionRecord(
            candidate=item.candidate,
            placement_outcome=(
                item.placement_outcome
            ),
            labels=r8b.build_label_bundle(
                candidate=item.candidate,
                fills=(),
                midpoints=(),
                source_exchange_observed_through_ns=(
                    observed_through
                ),
                placement_outcome=(
                    item.placement_outcome
                ),
            ),
        )
        for item in result.candidates
    )

    artifact = materialize_lane_partition(
        source=source,
        lane=lane,
        day_start_local_ns=0,
        feed_bounds=bounds,
        feature_cache=cache,
        records=records,
        output_root=Path(output_root),
    )

    return artifact, cache, result


def run_synthetic_fill_materialization(
    *,
    output_root: Path,
) -> tuple[
    r4.LaneArtifact,
    DenseFeatureCache,
    r14.CandidateGridResult,
]:
    """
    Exact patched hftbacktest BID/D0 fill-path integration.
    """
    result = r14.run_grid_case(
        side="BID",
        distance_ticks=0,
        with_fill=True,
    )

    cache = _synthetic_dense_cache_from_bid_d0(
        candidates=(result.candidate,),
        feature_vectors=(
            result.feature_vector,
        ),
    )

    lane = _synthetic_lane(
        candidate=result.candidate,
    )

    source = _synthetic_source(lane)

    fixture = r14.make_grid_fixture(
        side="BID",
        distance_ticks=0,
        with_fill=True,
    )

    bounds = r17.derive_feed_bounds(
        fixture,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=(
            100_000_000_000
        ),
    )

    record = CandidateExecutionRecord(
        candidate=result.candidate,
        placement_outcome=(
            result.placement_outcome
        ),
        labels=result.labels,
    )

    artifact = materialize_lane_partition(
        source=source,
        lane=lane,
        day_start_local_ns=0,
        feed_bounds=bounds,
        feature_cache=cache,
        records=(record,),
        output_root=Path(output_root),
    )

    return artifact, cache, result


def validate_r18_contract() -> None:
    r4.validate_runner_contract()
    r8a.validate_r8a_contract()
    r8b.validate_r8b_contract()
    r14.validate_r14_contract()
    r15.validate_r15_contract()
    r16.validate_r16_contract()
    r17.validate_r17_contract()

    if PARENT_R17_HEAD != (
        "0ec427c4466200d0f14626609e02a535d0738bdf"
    ):
        raise GenericLaneMaterializerError(
            "parent"
        )

    expected_grid = tuple(
        (side, int(distance))
        for side in ("BID", "ASK")
        for distance in (0, 1, 2, 4)
    )

    if CANDIDATE_GRID != expected_grid:
        raise GenericLaneMaterializerError(
            "candidate_grid"
        )

    if (
        CANDIDATE_GRID_CASE_COUNT != 8
        or FEATURE_COUNT != 25
    ):
        raise GenericLaneMaterializerError(
            "cache_cardinality"
        )

    if r4.EXPECTED_LANES_PER_DAY != 40:
        raise GenericLaneMaterializerError(
            "r4_lanes_per_day"
        )

    if r17.RAW_FEATURE_PASSES_PER_DAY != 1:
        raise GenericLaneMaterializerError(
            "raw_feature_passes"
        )

    if not r17.PER_LANE_RAW_FEATURE_RESCAN_FORBIDDEN:
        raise GenericLaneMaterializerError(
            "raw_feature_rescan_guard"
        )

    if not r17.FEATURE_CACHE_SHARED_ACROSS_ALL_40_LANES:
        raise GenericLaneMaterializerError(
            "shared_cache_guard"
        )

    required = (
        GENERIC_LANE_MATERIALIZER_FROZEN,
        R4_LANE_ARTIFACT_SHAPE_BOUND,
        R8A_ATOMIC_PUBLISHER_BOUND,
        R15_SEQUENTIAL_REAL_ENGINE_BOUND,
        R16_CANONICAL_ROW_PARQUET_BOUND,
        R17_SHARED_DENSE_CACHE_BOUND,
        R17_FEED_BOUND_EOF_BOUND,
        SYNTHETIC_REAL_ENGINE_PROBES_AUTHORIZED,
        SYNTHETIC_TEMP_ARTIFACT_WRITE_AUTHORIZED,
        PREEXECUTION_ONLY,
        not R4_FULL_RUNNER_BINDING_CREATED,
        not EXECUTION_AUTHORIZATION_CREATED,
        P2_ATTEMPT_CONSUMED is False,
        r17.NATURAL_END_OF_DATA_IS_VALID_TERMINAL,
        r17.DECISION_AFTER_LAST_FEED_TIMESTAMP_FORBIDDEN,
        r17.END_OF_SOURCE_CANDIDATES_RETAINED_WITH_CENSORING,
        not r17.CENSORED_MAPS_TO_NO_FILL,
        r16.FULL_DAY_ROW_MATERIALIZATION_FORBIDDEN,
        r16.ONE_PARTITION_PAYLOAD_AT_A_TIME,
        r8a.ATOMIC_WRITER_IMPLEMENTED,
    )

    if not all(required):
        raise GenericLaneMaterializerError(
            "required_guard"
        )

    forbidden = (
        HISTORICAL_FILE_IO_AUTHORIZED,
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        HISTORICAL_SIMULATOR_IMPORT_AUTHORIZED,
        HISTORICAL_CANDIDATE_SIMULATION_AUTHORIZED,
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
        raise GenericLaneMaterializerError(
            "execution_surface_open"
        )


__all__ = [
    "DenseFeatureCache",
    "CandidateExecutionRecord",
    "validate_dense_feature_cache",
    "lookup_feature_vector",
    "materialize_lane_partition",
    "run_synthetic_sequential_materialization",
    "run_synthetic_fill_materialization",
    "validate_r18_contract",
]
