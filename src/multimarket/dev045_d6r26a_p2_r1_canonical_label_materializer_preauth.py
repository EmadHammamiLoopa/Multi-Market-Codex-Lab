from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re
from typing import Mapping, Sequence

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p1_synthetic_candidate_labeler as p1
from multimarket import dev045_d6r26a_p2_jan_jul_consumed_development_label_design as p2

EXPERIMENT_ID = "DEV045-D6R26A-P2-R1"
DESIGN_VERSION = "canonical-label-materializer-preauth-v1"
PARENT_P2_HEAD = "a0e22b680c59c4ba26cb1dddc902182fcc962bda"
D6R24_EXECUTION_HEAD = "b04a18f8eb5b4689abd15d7cdf6a6c889ee36212"
D6R24_FREEZE_HEAD = "06eff337e4a039cf47c8b10a41aa91e52df4c792"
Q8_EXECUTION_HEAD = "bc6b66fdf2634cdacf04f2738722b36a9f1619d8"
Q8_FREEZE_HEAD = "fc7733a776cff8fc726be630dae4d389abd00e8c"
HFTBACKTEST_UPSTREAM_HEAD = "a244a14250b42d97fc305569c93c4117cd5e1dff"
HFTBACKTEST_FROZEN_BINARY_SHA256 = "5174f486abc4b29cfef565672548798ea68ec54c0f6c04077bcbdf43f5033752"

AUTH_ENV_NAME = "DEV045_D6R26A_P2_AUTHORIZE"
AUTH_TOKEN = "YES_FROZEN_JAN_JUL_CONSUMED_DEVELOPMENT_CANDIDATE_LABEL_MATERIALIZATION"

PREAUTH_ONLY = True
FROZEN_SOURCE_REGISTRY_REQUIRED = True
FROZEN_SOURCE_REGISTRY_EMBEDDED = False
HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
HISTORICAL_SOURCE_HASH_AUTHORIZED = False
CANDIDATE_SIMULATION_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
MODEL_SELECTION_AUTHORIZED = False
THRESHOLD_TUNING_AUTHORIZED = False
PNL_AUTHORIZED = False
ECONOMIC_ARENA_AUTHORIZED = False
FEE_RESCUE_AUTHORIZED = False
SIZE_TUNING_AUTHORIZED = False
LEVERAGE_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
NETWORK_ACQUISITION_AUTHORIZED = False

REAL_DEVELOPMENT_DAYS = p2.REAL_DEVELOPMENT_DAYS
DATA_ROLE = p2.DATA_ROLE
FEATURE_WARMUP_NS = p2.FEATURE_WARMUP_NS
DECISION_STEP_NS = p0.DECISION_STEP_NS
LANE_PHASE_OFFSETS_S = p0.LANE_PHASE_OFFSETS_S
LANES_PER_DAY = p2.LANES_PER_DAY
TOTAL_LANES = p2.TOTAL_LANES
MAX_PARALLEL_LANES = p2.MAX_PARALLEL_LANES
OUTPUT_ROOT = p2.OUTPUT_ROOT
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PreauthMaterializerError(RuntimeError):
    pass


@dataclass(frozen=True, order=True)
class FrozenSourceIdentity:
    day: str
    path: str
    bytes: int
    sha256: str

    def __post_init__(self) -> None:
        if self.day not in REAL_DEVELOPMENT_DAYS:
            raise PreauthMaterializerError("source_day")
        if not self.path or not self.path.strip():
            raise PreauthMaterializerError("source_path")
        if isinstance(self.bytes, bool) or int(self.bytes) <= 0:
            raise PreauthMaterializerError("source_bytes")
        if not _SHA256_RE.fullmatch(str(self.sha256)):
            raise PreauthMaterializerError("source_sha256")


@dataclass(frozen=True, order=True)
class LaneSpec:
    day: str
    side: str
    distance_ticks: int
    phase: int
    lane_id: str
    partition_relpath: str


@dataclass(frozen=True, order=True)
class PartitionArtifactIdentity:
    lane_id: str
    relpath: str
    bytes: int
    sha256: str
    row_count: int

    def __post_init__(self) -> None:
        if not self.lane_id or not self.relpath:
            raise PreauthMaterializerError("partition_identity")
        if isinstance(self.bytes, bool) or int(self.bytes) < 0:
            raise PreauthMaterializerError("partition_bytes")
        if isinstance(self.row_count, bool) or int(self.row_count) < 0:
            raise PreauthMaterializerError("partition_rows")
        if not _SHA256_RE.fullmatch(str(self.sha256)):
            raise PreauthMaterializerError("partition_sha256")


@dataclass(frozen=True)
class DayManifest:
    experiment_id: str
    design_version: str
    day: str
    data_role: str
    source: FrozenSourceIdentity
    partitions: tuple[PartitionArtifactIdentity, ...]
    partition_count: int
    row_count: int


@dataclass(frozen=True)
class AtomicPublishPlan:
    temp_relpath: str
    final_relpath: str
    publish_rule: str = "WRITE_TEMP_FSYNC_HASH_VERIFY_ATOMIC_RENAME_ONCE"


def validate_authorization_value(value: str | None) -> None:
    # Pure validator only; P2-R1 never reads process environment.
    if value != AUTH_TOKEN:
        raise PreauthMaterializerError("authorization_denied")


def validate_source_registry(registry: Mapping[str, FrozenSourceIdentity]) -> tuple[FrozenSourceIdentity, ...]:
    if tuple(sorted(registry)) != tuple(sorted(REAL_DEVELOPMENT_DAYS)):
        raise PreauthMaterializerError("source_registry_days")
    out = []
    seen_paths: set[str] = set()
    for day in REAL_DEVELOPMENT_DAYS:
        item = registry[day]
        if item.day != day:
            raise PreauthMaterializerError("source_registry_day_binding")
        if item.path in seen_paths:
            raise PreauthMaterializerError("source_registry_duplicate_path")
        seen_paths.add(item.path)
        out.append(item)
    return tuple(out)


def require_exact_source_identity(expected: FrozenSourceIdentity, observed: FrozenSourceIdentity) -> None:
    if observed != expected:
        raise PreauthMaterializerError("source_identity_mismatch")


def lane_id(day: str, side: str, distance_ticks: int, phase: int) -> str:
    if day not in REAL_DEVELOPMENT_DAYS:
        raise PreauthMaterializerError("lane_day")
    if side not in p0.CANDIDATE_SIDES:
        raise PreauthMaterializerError("lane_side")
    if int(distance_ticks) not in p0.CANDIDATE_DISTANCE_TICKS:
        raise PreauthMaterializerError("lane_distance")
    if int(phase) not in LANE_PHASE_OFFSETS_S:
        raise PreauthMaterializerError("lane_phase")
    return f"{day}_{side}_D{int(distance_ticks):02d}_P{int(phase)}"


def partition_relpath(day: str, side: str, distance_ticks: int, phase: int) -> str:
    lane_id(day, side, distance_ticks, phase)
    return f"day={day}/side={side}/distance_ticks={int(distance_ticks)}/phase={int(phase)}/part-000.parquet"


def build_materialization_plan() -> tuple[LaneSpec, ...]:
    lanes = tuple(
        LaneSpec(day, side, int(distance), int(phase), lane_id(day, side, distance, phase), partition_relpath(day, side, distance, phase))
        for day in REAL_DEVELOPMENT_DAYS
        for side in p0.CANDIDATE_SIDES
        for distance in p0.CANDIDATE_DISTANCE_TICKS
        for phase in LANE_PHASE_OFFSETS_S
    )
    if len(lanes) != TOTAL_LANES or len({x.lane_id for x in lanes}) != TOTAL_LANES:
        raise PreauthMaterializerError("materialization_plan_cardinality")
    return lanes


def decision_epochs_for_lane(*, day_start_local_ns: int, day_end_local_ns: int, phase: int) -> tuple[int, ...]:
    start, end = int(day_start_local_ns), int(day_end_local_ns)
    if start < 0 or end <= start:
        raise PreauthMaterializerError("day_bounds")
    if phase not in LANE_PHASE_OFFSETS_S:
        raise PreauthMaterializerError("lane_phase")
    first_valid = start + FEATURE_WARMUP_NS
    if first_valid >= end:
        return ()
    first_index = (first_valid - start + DECISION_STEP_NS - 1) // DECISION_STEP_NS
    nph = len(LANE_PHASE_OFFSETS_S)
    first_index += (phase - (first_index % nph)) % nph
    first = start + first_index * DECISION_STEP_NS
    if first >= end:
        return ()
    epochs = tuple(range(first, end, nph * DECISION_STEP_NS))
    p1.assert_lane_isolation(epochs)
    return epochs


def assert_phase_cover_exactly_once(*, day_start_local_ns: int, day_end_local_ns: int) -> None:
    start, end = int(day_start_local_ns), int(day_end_local_ns)
    expected = tuple(range(start + FEATURE_WARMUP_NS, end, DECISION_STEP_NS))
    actual = tuple(sorted(t for phase in LANE_PHASE_OFFSETS_S for t in decision_epochs_for_lane(day_start_local_ns=start, day_end_local_ns=end, phase=phase)))
    if actual != expected or len(set(actual)) != len(actual):
        raise PreauthMaterializerError("phase_coverage")


FEATURE_NAMES = tuple(feature for family in p0.LOCAL_FEATURE_FAMILIES.values() for feature in family)
FEATURE_OBS_FIELDS = tuple(f"{name}__observable_local_ns" for name in FEATURE_NAMES)
_BASE_ROW_FIELDS = (
    "experiment_id", "design_version", "data_role", "source_day", "source_path", "source_bytes", "source_sha256",
    "day_start_local_ns", "decision_local_ns", "side", "distance_ticks", "phase", "lane_id", "best_bid_tick", "best_ask_tick",
    "candidate_price_tick", "candidate_price", "candidate_qty", "candidate_tif", "label_scenario", "entry_latency_ns", "response_latency_ns",
    "placement_outcome", "feature_support", "feature_warmup_complete",
)
_FILL_SUFFIX = {250_000_000: "250ms", 500_000_000: "500ms", 1_000_000_000: "1s", 2_000_000_000: "2s", 5_000_000_000: "5s"}
_FILL_FIELDS_PER_HORIZON = ("state", "any_fill", "fill_fraction", "fill_fraction_censored", "time_to_first_fill_ns", "time_to_full_fill_ns", "full_fill_status")
_MARKOUT_FIELDS_PER_HORIZON = ("status", "value_bps")
FILL_ROW_FIELDS = tuple(f"fill_{_FILL_SUFFIX[h]}__{name}" for h in p0.FILL_HORIZONS_NS for name in _FILL_FIELDS_PER_HORIZON)
MARKOUT_ROW_FIELDS = tuple(f"markout_{_FILL_SUFFIX[h]}__{name}" for h in p0.MARKOUT_HORIZONS_NS for name in _MARKOUT_FIELDS_PER_HORIZON)
ROW_SCHEMA_FIELDS = _BASE_ROW_FIELDS + FEATURE_NAMES + FEATURE_OBS_FIELDS + FILL_ROW_FIELDS + MARKOUT_ROW_FIELDS


def validate_row_contract(row: Mapping[str, object]) -> None:
    if set(row) != set(ROW_SCHEMA_FIELDS) or len(row) != len(ROW_SCHEMA_FIELDS):
        raise PreauthMaterializerError("row_schema")
    if row["experiment_id"] != EXPERIMENT_ID or row["design_version"] != DESIGN_VERSION or row["data_role"] != DATA_ROLE:
        raise PreauthMaterializerError("row_identity")
    source = FrozenSourceIdentity(str(row["source_day"]), str(row["source_path"]), int(row["source_bytes"]), str(row["source_sha256"]))
    day_start, decision = int(row["day_start_local_ns"]), int(row["decision_local_ns"])
    side, distance, phase = str(row["side"]), int(row["distance_ticks"]), int(row["phase"])
    if phase != p1.lane_phase(day_start_local_ns=day_start, decision_local_ns=decision):
        raise PreauthMaterializerError("row_phase")
    if row["lane_id"] != lane_id(source.day, side, distance, phase):
        raise PreauthMaterializerError("row_lane_id")
    candidate = p1.CandidateSpec(side=side, distance_ticks=distance, decision_local_ns=decision, best_bid_tick=int(row["best_bid_tick"]), best_ask_tick=int(row["best_ask_tick"]), qty=float(row["candidate_qty"]))
    if int(row["candidate_price_tick"]) != candidate.price_tick:
        raise PreauthMaterializerError("row_candidate_price_tick")
    if not math.isclose(float(row["candidate_price"]), candidate.price, rel_tol=0.0, abs_tol=1e-12):
        raise PreauthMaterializerError("row_candidate_price")
    if decision < day_start + FEATURE_WARMUP_NS or row["feature_warmup_complete"] is not True:
        raise PreauthMaterializerError("row_feature_warmup")
    p1.validate_feature_observability(decision_local_ns=decision, feature_observable_local_ns={name: int(row[f"{name}__observable_local_ns"]) for name in FEATURE_NAMES})
    if row["candidate_tif"] != p0.CANDIDATE_TIME_IN_FORCE or row["label_scenario"] != p0.PRIMARY_LABEL_SCENARIO:
        raise PreauthMaterializerError("row_execution_identity")
    if int(row["entry_latency_ns"]) != p0.ENTRY_LATENCY_NS or int(row["response_latency_ns"]) != p0.RESPONSE_LATENCY_NS:
        raise PreauthMaterializerError("row_latency")
    if row["placement_outcome"] not in p0.PLACEMENT_OUTCOMES:
        raise PreauthMaterializerError("row_placement_outcome")
    for h in p0.FILL_HORIZONS_NS:
        s = _FILL_SUFFIX[h]
        state = row[f"fill_{s}__state"]
        any_fill = row[f"fill_{s}__any_fill"]
        censored_fraction = row[f"fill_{s}__fill_fraction_censored"]
        if state not in p0.FILL_LABEL_STATES:
            raise PreauthMaterializerError("row_fill_state")
        if state == p1.CENSORED and any_fill is False:
            raise PreauthMaterializerError("row_censor_collapsed_to_no_fill")
        if state == p1.CENSORED and censored_fraction is not True:
            raise PreauthMaterializerError("row_censor_flag")
        status = row[f"markout_{s}__status"]
        value = row[f"markout_{s}__value_bps"]
        if status not in (p1.MARKOUT_OBSERVED, p1.MARKOUT_CENSORED, p1.MARKOUT_NOT_APPLICABLE_NO_FILL):
            raise PreauthMaterializerError("row_markout_status")
        if status != p1.MARKOUT_OBSERVED and value is not None:
            raise PreauthMaterializerError("row_markout_nonobserved_value")


def sha256_bytes(payload: bytes) -> str:
    if not isinstance(payload, bytes):
        raise PreauthMaterializerError("payload_not_bytes")
    return hashlib.sha256(payload).hexdigest()


def partition_identity_from_bytes(*, lane: LaneSpec, payload: bytes, row_count: int) -> PartitionArtifactIdentity:
    return PartitionArtifactIdentity(lane.lane_id, lane.partition_relpath, len(payload), sha256_bytes(payload), int(row_count))


def build_day_manifest(*, day: str, source: FrozenSourceIdentity, partitions: Sequence[PartitionArtifactIdentity]) -> DayManifest:
    if day not in REAL_DEVELOPMENT_DAYS or source.day != day:
        raise PreauthMaterializerError("manifest_day")
    expected = {x.lane_id for x in build_materialization_plan() if x.day == day}
    ordered = tuple(sorted(partitions))
    if len(ordered) != LANES_PER_DAY or {x.lane_id for x in ordered} != expected:
        raise PreauthMaterializerError("manifest_partition_identity")
    return DayManifest(EXPERIMENT_ID, DESIGN_VERSION, day, DATA_ROLE, source, ordered, len(ordered), sum(x.row_count for x in ordered))


def canonical_manifest_bytes(manifest: DayManifest) -> bytes:
    return json.dumps(asdict(manifest), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def manifest_sha256(manifest: DayManifest) -> str:
    return sha256_bytes(canonical_manifest_bytes(manifest))


def atomic_publish_plan(final_relpath: str) -> AtomicPublishPlan:
    if not final_relpath or final_relpath.startswith("/"):
        raise PreauthMaterializerError("publish_relpath")
    return AtomicPublishPlan(f"{final_relpath}.tmp", final_relpath)


def validate_preauth_contract() -> None:
    p0.validate_design_contract(); p1.validate_p1_contract(); p2.validate_design_contract()
    if EXPERIMENT_ID != "DEV045-D6R26A-P2-R1" or PARENT_P2_HEAD != "a0e22b680c59c4ba26cb1dddc902182fcc962bda":
        raise RuntimeError("identity")
    if DATA_ROLE != "CONSUMED_DEVELOPMENT" or tuple(REAL_DEVELOPMENT_DAYS) != tuple(p0.AUTHORIZED_DAYS):
        raise RuntimeError("data_role")
    if LANES_PER_DAY != 40 or TOTAL_LANES != 280 or MAX_PARALLEL_LANES != 8:
        raise RuntimeError("lane_contract")
    if FROZEN_SOURCE_REGISTRY_EMBEDDED or not FROZEN_SOURCE_REGISTRY_REQUIRED:
        raise RuntimeError("registry_contract")
    if len(FEATURE_NAMES) != 25 or len(set(FEATURE_NAMES)) != 25:
        raise RuntimeError("feature_identity")
    if p0.CENSORED_MAPS_TO_NO_FILL or p0.CANDIDATE_TIME_IN_FORCE != "GTX_POST_ONLY":
        raise RuntimeError("label_contract")
    forbidden = (HISTORICAL_SOURCE_OPEN_AUTHORIZED, HISTORICAL_SOURCE_HASH_AUTHORIZED, CANDIDATE_SIMULATION_AUTHORIZED, CANONICAL_LABEL_WRITE_AUTHORIZED, MODEL_FIT_AUTHORIZED, MODEL_SELECTION_AUTHORIZED, THRESHOLD_TUNING_AUTHORIZED, PNL_AUTHORIZED, ECONOMIC_ARENA_AUTHORIZED, FEE_RESCUE_AUTHORIZED, SIZE_TUNING_AUTHORIZED, LEVERAGE_AUTHORIZED, LIVE_TRADING_AUTHORIZED, AUG_OPEN_AUTHORIZED, SEP_PLUS_OPEN_AUTHORIZED, NON_BTC_OPEN_AUTHORIZED, NETWORK_ACQUISITION_AUTHORIZED)
    if any(forbidden):
        raise RuntimeError("forbidden_authorization")
    if len(build_materialization_plan()) != 280:
        raise RuntimeError("plan_count")
