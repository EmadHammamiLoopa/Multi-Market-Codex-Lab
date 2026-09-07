from __future__ import annotations

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p1_synthetic_candidate_labeler as p1


EXPERIMENT_ID = "DEV045-D6R26A-P2"
DESIGN_VERSION = "jan-jul-consumed-development-canonical-label-materialization-design-v1"

PARENT_P1_HEAD = "e085c2cdfe5e7e1588bb3ce434389b3b014b0403"
PARENT_P0_HEAD = "33c61a4e3904659ea44a0edfe763f31e31c58ba8"
PARENT_D6R25_R1_FREEZE_HEAD = "be9b827d2d4c4ccdeb4ecccf8979e771debd5dd2"

# Protocol amendment: every currently available Jan-Jul real day is development data.
# No day inside this set may be described as fresh replication or final holdout.
REAL_DEVELOPMENT_DAYS = (
    "2026-01-01",
    "2026-02-01",
    "2026-03-01",
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)
DATA_ROLE = "CONSUMED_DEVELOPMENT"
INTERNAL_FRESH_HOLDOUT_DAYS = ()
APR_JUL_ROLE = "CONSUMED_DEVELOPMENT"
FINAL_REAL_BUCKET_ROLE = "UNTOUCHED_ONE_SHOT_HISTORICAL_HOLDOUT"
FINAL_REAL_BUCKET_ASSIGNED = False
FINAL_REAL_BUCKET_OPEN_AUTHORIZED = False
FINAL_REAL_BUCKET_SELECTION_FROM_JAN_JUL_AUTHORIZED = False

# Candidate and label semantics are inherited exactly from frozen P0/P1.
DECISION_STEP_NS = p0.DECISION_STEP_NS
CANDIDATE_SIDES = p0.CANDIDATE_SIDES
CANDIDATE_DISTANCE_TICKS = p0.CANDIDATE_DISTANCE_TICKS
CANDIDATE_ORDER_QTY = p0.CANDIDATE_ORDER_QTY
CANDIDATE_TIME_IN_FORCE = p0.CANDIDATE_TIME_IN_FORCE
QUEUE_MODEL = p0.QUEUE_MODEL
EXCHANGE_MODEL = p0.EXCHANGE_MODEL
PRIMARY_LABEL_SCENARIO = p0.PRIMARY_LABEL_SCENARIO
ENTRY_LATENCY_NS = p0.ENTRY_LATENCY_NS
RESPONSE_LATENCY_NS = p0.RESPONSE_LATENCY_NS
FILL_HORIZONS_NS = p0.FILL_HORIZONS_NS
MARKOUT_HORIZONS_NS = p0.MARKOUT_HORIZONS_NS
FILL_HORIZON_ORIGIN = p1.FILL_HORIZON_ORIGIN
MARKOUT_HORIZON_ORIGIN = p1.MARKOUT_HORIZON_ORIGIN
CENSORED_MAPS_TO_NO_FILL = p0.CENSORED_MAPS_TO_NO_FILL
SPREAD_CAPTURE_ADDED_SEPARATELY = p0.SPREAD_CAPTURE_ADDED_SEPARATELY

LANE_PHASE_OFFSETS_S = p0.LANE_PHASE_OFFSETS_S
LANES_PER_DAY = p0.LANE_COUNT_PER_DAY
TOTAL_LANES = LANES_PER_DAY * len(REAL_DEVELOPMENT_DAYS)
MAX_CANDIDATE_LIFETIME_NS = p0.MAX_CANDIDATE_LIFETIME_NS

# Feature materialization is local-only and causal.
LOCAL_FEATURE_FAMILIES = p0.LOCAL_FEATURE_FAMILIES
FORBIDDEN_FEATURES = p0.FORBIDDEN_FEATURES
FEATURE_OBSERVABILITY_RULE = p0.FEATURE_OBSERVABILITY_RULE
FEATURE_WARMUP_NS = 30_000_000_000
CANDIDATE_ELIGIBILITY = (
    "VALID_LOCAL_BBO_AND_30S_CAUSAL_FEATURE_HISTORY_AT_DECISION_EPOCH"
)
END_OF_SOURCE_CANDIDATES_RETAINED_WITH_CENSORING = True
MISSING_LABELS_DROPPED = False
MISSING_FEATURE_ROWS_DROPPED = False

# Materialization surface: one row per candidate, horizons as columns/structs.
ROW_GRAIN = "ONE_DECISION_EPOCH_X_SIDE_X_DISTANCE"
OUTPUT_FORMAT = "PARQUET_ZSTD"
OUTPUT_PARTITION = "DAY_X_SIDE_X_DISTANCE_X_PHASE"
EXPECTED_PARTITIONS_PER_DAY = LANES_PER_DAY
EXPECTED_TOTAL_PARTITIONS = TOTAL_LANES
OUTPUT_ROOT = "/home/emadh/Multi-Market/evidence/dev045_d6r26a_p2_candidate_labels_v1"
DAY_MANIFEST_FORMAT = "IMMUTABLE_JSON_SHA256_MANIFEST"
PARTITION_IDENTITY = "BYTES_PLUS_SHA256"
ONE_DAY_AT_A_TIME = True
BOUNDED_MEMORY = True

# Independent lanes can be parallelized without changing causal execution semantics.
MAX_PARALLEL_LANES = 8
PARALLELISM_CHANGES_LABEL_SEMANTICS = False

# P2 is label/feature materialization only.
MODEL_FIT_AUTHORIZED = False
MODEL_SELECTION_AUTHORIZED = False
THRESHOLD_TUNING_AUTHORIZED = False
QUOTE_ENGINE_EXECUTION_AUTHORIZED = False
INVENTORY_POLICY_EXECUTION_AUTHORIZED = False
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

# This commit itself is design-only. P2-R1 must explicitly authorize historical
# Jan-Jul source opening under frozen source identities before execution.
P2_DESIGN_ONLY = True
HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
HISTORICAL_SOURCE_HASH_AUTHORIZED = False
CANDIDATE_SIMULATION_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False

# Source identity must be inherited from the already-frozen DEV045 historical
# ingestion/orchestration lineage. P2-R1 must fail closed before opening a source
# if any day path/hash/size differs from that frozen lineage.
SOURCE_IDENTITY_POLICY = "EXACT_FROZEN_DEV045_JAN_JUL_SOURCE_IDENTITY_FAIL_CLOSED"
SOURCE_RECONVERSION_AUTHORIZED = False
SOURCE_REMATERIALIZATION_AUTHORIZED = False
SOURCE_BACKFILL_AUTHORIZED = False

# Development validation after materialization may use all Jan-Jul through
# temporal/blocked OOF. It must never call any Jan-Jul subset independent replication.
ALLOWED_LATER_VALIDATION_ROLE = "BLOCKED_TEMPORAL_OOF_WITHIN_CONSUMED_DEVELOPMENT"
RANDOM_ROW_SPLIT_AUTHORIZED = False
INDEPENDENT_REPLICATION_CLAIM_FROM_JAN_JUL_AUTHORIZED = False

NEXT_PHASE = "D6R26A_P2_R1_CANONICAL_LABEL_MATERIALIZER_IMPLEMENTATION_PREAUTH"


def validate_design_contract() -> None:
    p0.validate_design_contract()
    p1.validate_p1_contract()

    if EXPERIMENT_ID != "DEV045-D6R26A-P2":
        raise RuntimeError("experiment_id")
    if PARENT_P1_HEAD != "e085c2cdfe5e7e1588bb3ce434389b3b014b0403":
        raise RuntimeError("parent_p1")
    if tuple(REAL_DEVELOPMENT_DAYS) != tuple(p0.AUTHORIZED_DAYS):
        raise RuntimeError("jan_jul_identity")
    if DATA_ROLE != "CONSUMED_DEVELOPMENT":
        raise RuntimeError("data_role")
    if INTERNAL_FRESH_HOLDOUT_DAYS:
        raise RuntimeError("internal_holdout_forbidden")
    if APR_JUL_ROLE != "CONSUMED_DEVELOPMENT":
        raise RuntimeError("apr_jul_role")
    if FINAL_REAL_BUCKET_ASSIGNED or FINAL_REAL_BUCKET_OPEN_AUTHORIZED:
        raise RuntimeError("final_bucket_must_remain_sealed")
    if FINAL_REAL_BUCKET_SELECTION_FROM_JAN_JUL_AUTHORIZED:
        raise RuntimeError("final_bucket_from_consumed_data")
    if LANES_PER_DAY != 40 or TOTAL_LANES != 280:
        raise RuntimeError("lane_count")
    if MAX_PARALLEL_LANES < 1 or MAX_PARALLEL_LANES > LANES_PER_DAY:
        raise RuntimeError("parallel_lane_bound")
    if FEATURE_WARMUP_NS != 30_000_000_000:
        raise RuntimeError("feature_warmup")
    if not END_OF_SOURCE_CANDIDATES_RETAINED_WITH_CENSORING:
        raise RuntimeError("end_censoring")
    if MISSING_LABELS_DROPPED or MISSING_FEATURE_ROWS_DROPPED:
        raise RuntimeError("silent_drop")
    if CENSORED_MAPS_TO_NO_FILL:
        raise RuntimeError("censor_to_no_fill")
    if SPREAD_CAPTURE_ADDED_SEPARATELY:
        raise RuntimeError("spread_double_count")
    if ROW_GRAIN != "ONE_DECISION_EPOCH_X_SIDE_X_DISTANCE":
        raise RuntimeError("row_grain")
    if OUTPUT_FORMAT != "PARQUET_ZSTD":
        raise RuntimeError("output_format")
    if not ONE_DAY_AT_A_TIME or not BOUNDED_MEMORY:
        raise RuntimeError("memory_contract")
    if RANDOM_ROW_SPLIT_AUTHORIZED:
        raise RuntimeError("random_split")
    if INDEPENDENT_REPLICATION_CLAIM_FROM_JAN_JUL_AUTHORIZED:
        raise RuntimeError("false_replication_claim")

    forbidden = (
        MODEL_FIT_AUTHORIZED,
        MODEL_SELECTION_AUTHORIZED,
        THRESHOLD_TUNING_AUTHORIZED,
        QUOTE_ENGINE_EXECUTION_AUTHORIZED,
        INVENTORY_POLICY_EXECUTION_AUTHORIZED,
        PNL_AUTHORIZED,
        ECONOMIC_ARENA_AUTHORIZED,
        FEE_RESCUE_AUTHORIZED,
        SIZE_TUNING_AUTHORIZED,
        LEVERAGE_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
        NETWORK_ACQUISITION_AUTHORIZED,
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        HISTORICAL_SOURCE_HASH_AUTHORIZED,
        CANDIDATE_SIMULATION_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        SOURCE_RECONVERSION_AUTHORIZED,
        SOURCE_REMATERIALIZATION_AUTHORIZED,
        SOURCE_BACKFILL_AUTHORIZED,
    )
    if any(forbidden):
        raise RuntimeError("forbidden_authorization")

    if NEXT_PHASE != "D6R26A_P2_R1_CANONICAL_LABEL_MATERIALIZER_IMPLEMENTATION_PREAUTH":
        raise RuntimeError("next_phase")


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "PARENT_P1_HEAD",
    "REAL_DEVELOPMENT_DAYS",
    "DATA_ROLE",
    "APR_JUL_ROLE",
    "FINAL_REAL_BUCKET_ROLE",
    "FINAL_REAL_BUCKET_OPEN_AUTHORIZED",
    "LANES_PER_DAY",
    "TOTAL_LANES",
    "MAX_PARALLEL_LANES",
    "OUTPUT_ROOT",
    "OUTPUT_FORMAT",
    "ROW_GRAIN",
    "SOURCE_IDENTITY_POLICY",
    "ALLOWED_LATER_VALIDATION_ROLE",
    "NEXT_PHASE",
    "validate_design_contract",
]
