from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


EXPERIMENT_ID = "DEV045-D6R17"

CONTRACT_ID = (
    "DEV045-D6R17-REAL-HISTORICAL-"
    "ECONOMIC-DRIVER-CONTRACT-V1"
)

SCHEMA_VERSION = (
    "dev045-d6r17-real-historical-"
    "economic-driver-contract-v1"
)


# ------------------------------------------------------------------
# Parent / exact lineage selection
# ------------------------------------------------------------------

PARENT_FREEZE_HEAD = (
    "5411877e3bd1f8fcd9812176bc3dc39dbf18bf88"
)

PARENT_FREEZE_BRANCH = (
    "research/dev045-m6-d6r16-mar-jul-pass-frozen"
)

SELECTION_ARTIFACT_PATH = Path(
    "evidence/"
    "dev045_d6r17_exact_economic_lineage_selection.json"
)

SELECTION_ARTIFACT_SHA256 = "8921e161b5f69ebcac6fd14d2ad96328ef0d7f64abdfb1b9eaaa9744bee2bd08"

SELECTED_ECONOMIC_FAMILY = "DEV045_M_MAKER"

LEGACY_TAKER_LINEAGE_REOPENED = False

JAN_THROUGH_JUL_INGESTION_GATE_PASS = True

INGESTION_RERUN_AUTHORIZED = False

RAW_CONVERSION_RERUN_AUTHORIZED = False


# ------------------------------------------------------------------
# Frozen simulator identity
# ------------------------------------------------------------------

HFTBACKTEST_VERSION = "2.4.4"

HFTBACKTEST_UPSTREAM_COMMIT = (
    "a244a14250b42d97fc305569c93c4117cd5e1dff"
)

PATCHED_HFTBACKTEST_REQUIRED = True

UNPATCHED_PYPI_HFTBACKTEST_FORBIDDEN = True


# ------------------------------------------------------------------
# Frozen economic family
# ------------------------------------------------------------------

POLICY_IDS = (
    "M01",
    "M02",
    "M03",
    "M04",
    "M05",
    "M06",
    "M07",
    "M08",
)

PRIMARY_SCENARIO = "Q0_PRIMARY_250_250"
STRESS_SCENARIO = "Q0_STRESS_500_500"

SCENARIOS = (
    PRIMARY_SCENARIO,
    STRESS_SCENARIO,
)

PRIMARY_QUEUE_MODEL = "risk_adverse"

PRIMARY_ENTRY_LATENCY_NS = 250_000_000
PRIMARY_RESPONSE_LATENCY_NS = 250_000_000

STRESS_ENTRY_LATENCY_NS = 500_000_000
STRESS_RESPONSE_LATENCY_NS = 500_000_000

PRIMARY_MAKER_RATE = 0.0002
PRIMARY_TAKER_RATE = 0.0005

STRESS_MAKER_RATE = 0.0003
STRESS_TAKER_RATE = 0.00075

ACCOUNTING_UNIT = (
    "REALIZED_FLAT_TO_FLAT_INVENTORY_CYCLE"
)

BLOCK_HOURS = 4
BLOCKS_PER_DAY = 6


# ------------------------------------------------------------------
# Exact canonical development sources
# ------------------------------------------------------------------

@dataclass(frozen=True)
class DaySourceSpec:
    day: str
    path: Path
    rows: int
    bytes: int
    sha256: str
    ingestion_witness: str
    witness_head: str


DAY_SPECS = (
    DaySourceSpec(
        day="2026-01-01",
        path=Path(
            "/home/emadh/Multi-Market/runtime/"
            "dev045_d6r4b/output/"
            "BTCUSDT_2026-01-01.npy"
        ),
        rows=64_314_723,
        bytes=4_116_142_528,
        sha256=(
            "8f0a4fbd56ecdc261dbe2041ce138a094"
            "56423074925d495272716219a1d4da1"
        ),
        ingestion_witness="DEV045-D6R7B",
        witness_head=(
            "c301e691ae89675f6e244a7b987d3cb0b4488381"
        ),
    ),
    DaySourceSpec(
        day="2026-02-01",
        path=Path(
            "/home/emadh/Multi-Market/runtime/"
            "dev045_d6r9a/output/"
            "BTCUSDT_2026-02-01.npy"
        ),
        rows=179_584_138,
        bytes=11_493_385_088,
        sha256=(
            "d757d2ac32a29b0ac587323e115779c466"
            "068c6c0eba4270226b9c4109254cbc"
        ),
        ingestion_witness="DEV045-D6R15",
        witness_head=(
            "64dfd86079c9ee66956ac5db762306d0d45728de"
        ),
    ),
    DaySourceSpec(
        day="2026-03-01",
        path=Path(
            "/home/emadh/Multi-Market/runtime/"
            "dev045_d6r9b/output/"
            "BTCUSDT_2026-03-01.npy"
        ),
        rows=150_979_263,
        bytes=9_662_673_088,
        sha256=(
            "9e6a8b61d05e1a4938e17ffa7969241aff"
            "c7c06c1d0836188e3a882c363f2d99"
        ),
        ingestion_witness="DEV045-D6R16",
        witness_head=PARENT_FREEZE_HEAD,
    ),
    DaySourceSpec(
        day="2026-04-01",
        path=Path(
            "/home/emadh/Multi-Market/runtime/"
            "dev045_d6r9b/output/"
            "BTCUSDT_2026-04-01.npy"
        ),
        rows=132_829_759,
        bytes=8_501_104_832,
        sha256=(
            "de7e0471e63631394981b301bb461d679"
            "192c37eb6241d4d8073cf0640eca7f7"
        ),
        ingestion_witness="DEV045-D6R16",
        witness_head=PARENT_FREEZE_HEAD,
    ),
    DaySourceSpec(
        day="2026-05-01",
        path=Path(
            "/home/emadh/Multi-Market/runtime/"
            "dev045_d6r9b/output/"
            "BTCUSDT_2026-05-01.npy"
        ),
        rows=108_328_169,
        bytes=6_933_003_072,
        sha256=(
            "9433dfb498070dd5dd3e8ab1633c2f195"
            "51844f2ddf0d451e120119365bb04a3"
        ),
        ingestion_witness="DEV045-D6R16",
        witness_head=PARENT_FREEZE_HEAD,
    ),
    DaySourceSpec(
        day="2026-06-01",
        path=Path(
            "/home/emadh/Multi-Market/runtime/"
            "dev045_d6r9b/output/"
            "BTCUSDT_2026-06-01.npy"
        ),
        rows=172_540_697,
        bytes=11_042_604_864,
        sha256=(
            "ac97ad27c9d58b3b3e249547b8ae7c74c"
            "f2ebfde07965103bd5f6c7b853c26b"
        ),
        ingestion_witness="DEV045-D6R16",
        witness_head=PARENT_FREEZE_HEAD,
    ),
    DaySourceSpec(
        day="2026-07-01",
        path=Path(
            "/home/emadh/Multi-Market/runtime/"
            "dev045_d6r9b/output/"
            "BTCUSDT_2026-07-01.npy"
        ),
        rows=181_084_390,
        bytes=11_589_401_216,
        sha256=(
            "85f9a0a168420ce924fc9e1b746fbd9bb"
            "54bec390205c9ed9e65469ad489a83f"
        ),
        ingestion_witness="DEV045-D6R16",
        witness_head=PARENT_FREEZE_HEAD,
    ),
)

AUTHORIZED_DAYS = tuple(
    spec.day
    for spec in DAY_SPECS
)

TOTAL_POLICY_DAY_SCENARIO_REPLAYS = (
    len(POLICY_IDS)
    * len(DAY_SPECS)
    * len(SCENARIOS)
)

EXPECTED_TOTAL_REPLAYS = 112


# ------------------------------------------------------------------
# Frozen source-code identities inherited from M3-M6
# ------------------------------------------------------------------

FROZEN_CODE_BLOBS = {
    "src/multimarket/dev045_m3_policy.py":
        "256644726f8478d2b76105bce97e5f2c536cabf6",

    "src/multimarket/dev045_m4_adapter.py":
        "7f6a321b4512dd1ec1edf94c79416e176ee75e1c",

    "src/multimarket/dev045_m4_m6_binding.py":
        "7c0673a60c59772b5c187d90b4037693d120d94b",

    "src/multimarket/dev045_m5_prereg.py":
        "4aafd06bc6f9c6b2bcd81e5e1ecf1beacf51186f",

    "src/multimarket/dev045_m5_fee_amendment.py":
        "4c4f4e974f164f4a55e24fa92ee4029c6e47a1f7",

    "src/multimarket/dev045_m6_economic_arena.py":
        "75e2ebe55d830202d3dfeb41382783c2fc670bc8",

    "src/multimarket/dev045_m6_tardis_feed.py":
        "8bf7d620ce54cfa0ef759e9f8a866cea39570bc8",

    "src/multimarket/dev045_m6_historical_orchestration.py":
        "b12069072d95d4c2b4a4c788f988501a96dbceb1",

    "src/multimarket/dev045_m6_event_loop_kernel.py":
        "93a865b5a7a81da139b60fe220f5106f98832c7e",

    "src/multimarket/dev045_m6_policy_integration.py":
        "662dc0ef4380ca9a29cdaea7b6711d87b4082caf",
}


# ------------------------------------------------------------------
# Contract-only safety state
# ------------------------------------------------------------------

HISTORICAL_FILE_IO_ENABLED = False

HISTORICAL_REPLAY_EXECUTION_ENABLED = False

HISTORICAL_PNL_ENABLED = False

ECONOMIC_ARENA_EXECUTION_ENABLED = False

CANONICAL_PNL_WRITE_ENABLED = False

ORDER_SUBMISSION_ENABLED = False

POLICY_EXECUTION_ENABLED = False

NETWORK_ACQUISITION_ENABLED = False

RAILWAY_ENABLED = False

LIVE_TRADING_AUTHORIZED = False

AUG_OPEN_AUTHORIZED = False

SEP_PLUS_OPEN_AUTHORIZED = False

NON_BTC_OPEN_AUTHORIZED = False


# ------------------------------------------------------------------
# Future one-shot execution semantics — contract only
# ------------------------------------------------------------------

AUTHORIZATION_ENV = "DEV045_D6R17_AUTHORIZE"

AUTHORIZATION_TOKEN = (
    "YES_JAN_JUL_M6_MAKER_ECONOMIC_ARENA_ONE_SHOT"
)

CANONICAL_EXECUTION_AUTHORIZED = False

AUTOMATIC_RETRY = False

RERUN_AFTER_ATTEMPT_CONSUMPTION = False

STOP_ON_EXECUTION_INTEGRITY_FAILURE = True

STOP_ON_ECONOMIC_NONPASS = False

ALL_112_REPLAYS_REQUIRED = True

RANKING_BEFORE_COMPLETE_MATRIX = False

FIRST_HISTORICAL_OUTPUT_IS_EVIDENCE = True

TUNING_AFTER_FIRST_OUTPUT_AUTHORIZED = False

PROCESS_ONE_DAY_AT_A_TIME = True

VERIFY_FULL_SOURCE_SHA256_BEFORE_REPLAY = True

SOURCE_MUST_REMAIN_READ_ONLY = True


def validate_contract() -> None:
    if PARENT_FREEZE_HEAD != (
        "5411877e3bd1f8fcd9812176bc3dc39dbf18bf88"
    ):
        raise RuntimeError("parent_head")

    if SELECTED_ECONOMIC_FAMILY != "DEV045_M_MAKER":
        raise RuntimeError("economic_family")

    if LEGACY_TAKER_LINEAGE_REOPENED:
        raise RuntimeError("legacy_taker_reopened")

    if not JAN_THROUGH_JUL_INGESTION_GATE_PASS:
        raise RuntimeError("ingestion_gate")

    if AUTHORIZED_DAYS != (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
        "2026-07-01",
    ):
        raise RuntimeError("authorized_days")

    if POLICY_IDS != (
        "M01",
        "M02",
        "M03",
        "M04",
        "M05",
        "M06",
        "M07",
        "M08",
    ):
        raise RuntimeError("policy_ids")

    if SCENARIOS != (
        "Q0_PRIMARY_250_250",
        "Q0_STRESS_500_500",
    ):
        raise RuntimeError("scenarios")

    if TOTAL_POLICY_DAY_SCENARIO_REPLAYS != 112:
        raise RuntimeError("replay_count")

    if EXPECTED_TOTAL_REPLAYS != 112:
        raise RuntimeError("expected_replay_count")

    if PRIMARY_MAKER_RATE != 0.0002:
        raise RuntimeError("primary_maker_rate")

    if PRIMARY_TAKER_RATE != 0.0005:
        raise RuntimeError("primary_taker_rate")

    if STRESS_MAKER_RATE != 0.0003:
        raise RuntimeError("stress_maker_rate")

    if STRESS_TAKER_RATE != 0.00075:
        raise RuntimeError("stress_taker_rate")

    if CANONICAL_EXECUTION_AUTHORIZED:
        raise RuntimeError("execution_must_remain_closed")

    if any(
        (
            HISTORICAL_FILE_IO_ENABLED,
            HISTORICAL_REPLAY_EXECUTION_ENABLED,
            HISTORICAL_PNL_ENABLED,
            ECONOMIC_ARENA_EXECUTION_ENABLED,
            CANONICAL_PNL_WRITE_ENABLED,
            ORDER_SUBMISSION_ENABLED,
            POLICY_EXECUTION_ENABLED,
            NETWORK_ACQUISITION_ENABLED,
            RAILWAY_ENABLED,
            LIVE_TRADING_AUTHORIZED,
            AUG_OPEN_AUTHORIZED,
            SEP_PLUS_OPEN_AUTHORIZED,
            NON_BTC_OPEN_AUTHORIZED,
            INGESTION_RERUN_AUTHORIZED,
            RAW_CONVERSION_RERUN_AUTHORIZED,
            AUTOMATIC_RETRY,
            RERUN_AFTER_ATTEMPT_CONSUMPTION,
            STOP_ON_ECONOMIC_NONPASS,
            RANKING_BEFORE_COMPLETE_MATRIX,
            TUNING_AFTER_FIRST_OUTPUT_AUTHORIZED,
        )
    ):
        raise RuntimeError("closed_surface_open")

    if not all(
        (
            PATCHED_HFTBACKTEST_REQUIRED,
            UNPATCHED_PYPI_HFTBACKTEST_FORBIDDEN,
            STOP_ON_EXECUTION_INTEGRITY_FAILURE,
            ALL_112_REPLAYS_REQUIRED,
            FIRST_HISTORICAL_OUTPUT_IS_EVIDENCE,
            PROCESS_ONE_DAY_AT_A_TIME,
            VERIFY_FULL_SOURCE_SHA256_BEFORE_REPLAY,
            SOURCE_MUST_REMAIN_READ_ONLY,
        )
    ):
        raise RuntimeError("required_guard_disabled")


__all__ = [
    "EXPERIMENT_ID",
    "CONTRACT_ID",
    "SCHEMA_VERSION",
    "PARENT_FREEZE_HEAD",
    "SELECTION_ARTIFACT_PATH",
    "SELECTION_ARTIFACT_SHA256",
    "HFTBACKTEST_VERSION",
    "HFTBACKTEST_UPSTREAM_COMMIT",
    "POLICY_IDS",
    "SCENARIOS",
    "DAY_SPECS",
    "AUTHORIZED_DAYS",
    "TOTAL_POLICY_DAY_SCENARIO_REPLAYS",
    "FROZEN_CODE_BLOBS",
    "AUTHORIZATION_ENV",
    "AUTHORIZATION_TOKEN",
    "CANONICAL_EXECUTION_AUTHORIZED",
    "validate_contract",
]
