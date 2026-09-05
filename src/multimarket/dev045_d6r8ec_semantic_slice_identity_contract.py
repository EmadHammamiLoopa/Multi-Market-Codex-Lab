from __future__ import annotations

EXPERIMENT_ID = "DEV045-D6R8EC"
CONTRACT_ID = "DEV045-D6R8EC-SEMANTIC-SLICE-IDENTITY-LINEAGE-AMENDMENT-V1"
SCHEMA_VERSION = "dev045-d6r8ec-semantic-slice-identity-lineage-amendment-v1"
STATUS = "FROZEN_CONTRACT_ONLY"

PARENT_BRANCH = "research/dev045-m6-d6r8eb-slice-identity-forensics"
PARENT_HEAD = "4390605f0050bdbbf49058f41a52e954fbc3af7a"
FORENSIC_ROOT_CAUSE_REQUIRED = "FROZEN_D6R2_SLICE_HASH_SEMANTICS_UNRECOVERABLE"

# Historical results are preserved exactly; this contract does not reinterpret
# or rescue either result.
D6R2B_COMMIT = "4ff70ec50e39da432a70bf0444907f536586ed3e"
D6R2B_HISTORICAL_STATUS = "PASS"
D6R2B_REMAINS_HISTORICAL_PASS = True
D6R8EB_EXECUTION_COMMIT = "014e7580b476ec8031a0e36980567884c396f819"
D6R8EB_CANONICAL_STATUS = "FAIL"
D6R8EB_REMAINS_FROZEN_FAIL = True
D6R8EB_RERUN_AUTHORIZED = False
D6R2B_COMPRESSED_HASH_REINTERPRETED = False

# Frozen raw lineage from D4. These identify the immutable source files before
# any successor slice extraction is allowed.
D4_MANIFEST_PATH = "evidence/dev045_d4_raw_provenance.tsv"
D4_MANIFEST_SHA256 = "7fa6cf76ee8c6da98c5758756c887f0fb7b4d2e5eaf6b0e9f87551dce9981c12"
RAW_ROOT = "/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw"
TRADE_RELATIVE_PATH = "trades/BTCUSDT/2026-01-01.csv.gz"
DEPTH_RELATIVE_PATH = "incremental_book_L2/BTCUSDT/2026-01-01.csv.gz"
TRADE_RAW_BYTES = 9_691_108
TRADE_RAW_SHA256 = "e4aaee2b9f85016a5198e0cace5755dbd789c0f6f47ac0fc802c8f4b533833f6"
DEPTH_RAW_BYTES = 347_513_061
DEPTH_RAW_SHA256 = "0488a2204c9070b1e6a8769af48d54fb36e6a5658613267e2615cd3228002ded"

EXCHANGE = "binance-futures"
SYMBOL = "BTCUSDT"
DAY = "2026-01-01"
SELECTION_FIELD = "local_timestamp"
WINDOW_START_LOCAL_TIMESTAMP_US = 1_767_225_600_000_000
WINDOW_END_LOCAL_TIMESTAMP_US = 1_767_226_200_000_000
SELECTION_LEFT_INCLUSIVE = True
SELECTION_RIGHT_EXCLUSIVE = True
WINDOW_EXTENSION_ALLOWED = False
WINDOW_SHRINK_ALLOWED = False

# These semantic payload identities were measured from the already-created
# D6R8EB slices after the canonical D6R8EB run had frozen FAIL, but V2 was never
# executed. Therefore they were not selected or tuned using a V2 parity output.
FORENSIC_EVIDENCE_PATH = "evidence/dev045_d6r8eb_slice_identity_forensics.json"
FORENSIC_LOGICAL_PAYLOAD_IDENTITY_WITH_D6R2B_PROVEN = False
FORENSIC_GZIP_ONLY_MISMATCH_PROVEN = False
V2_WAS_EXECUTED_IN_D6R8EB = False
NO_V2_OUTCOME_WAS_AVAILABLE_WHEN_SEMANTIC_DIGESTS_WERE_FROZEN = True

TRADE_SEMANTIC_ROWS = 13_073
TRADE_SEMANTIC_BYTES = 1_137_750
TRADE_DECOMPRESSED_SHA256 = "cb6a1d37e4422fa99e563969b3750487a3ca3d01956a45973085f26352a220fe"
TRADE_FIRST_LOCAL_TIMESTAMP_US = 1_767_225_601_822_030
TRADE_LAST_LOCAL_TIMESTAMP_US = 1_767_226_198_170_130
TRADE_HEADER_HEX = "65786368616e67652c73796d626f6c2c74696d657374616d702c6c6f63616c5f74696d657374616d702c69642c736964652c70726963652c616d6f756e740a"

DEPTH_SEMANTIC_ROWS = 483_149
DEPTH_SEMANTIC_BYTES = 39_147_846
DEPTH_DECOMPRESSED_SHA256 = "5c5d8de09c1a38083f151f632fce568fb80b9df1485f5688d2dab20431869f93"
DEPTH_FIRST_LOCAL_TIMESTAMP_US = 1_767_225_601_223_614
DEPTH_LAST_LOCAL_TIMESTAMP_US = 1_767_226_199_978_052
DEPTH_HEADER_HEX = "65786368616e67652c73796d626f6c2c74696d657374616d702c6c6f63616c5f74696d657374616d702c69735f736e617073686f742c736964652c70726963652c616d6f756e740a"
DEPTH_FIRST_SELECTED_IS_SNAPSHOT = True
DEPTH_SNAPSHOT_BATCHES = 1
DEPTH_SNAPSHOT_ROWS = 2_002
DEPTH_ENDS_INSIDE_SNAPSHOT_BATCH = False

# Successor identity semantics. A gzip container hash can be recorded for
# diagnostics, but it is never sufficient or necessary for semantic identity.
COMPRESSED_GZIP_SHA_IS_SEMANTIC_IDENTITY = False
SUCCESSOR_SEMANTIC_IDENTITY_COMPONENTS = (
    "d4_exact_raw_file_sha256_and_bytes",
    "exact_exchange_symbol_day",
    "exact_left_inclusive_right_exclusive_local_timestamp_window",
    "exact_original_header_bytes",
    "exact_selected_row_bytes_and_order",
    "exact_decompressed_payload_sha256_and_length",
    "exact_selected_row_count",
    "exact_first_and_last_local_timestamp",
    "exact_depth_snapshot_structure",
)

# A future successor must reconstruct the slice from the D4-identified raw
# files, verify the semantic digest before converter execution, then feed the
# exact same reconstructed physical slice files to every converter under test.
SUCCESSOR_RECONSTRUCTION_REQUIREMENTS = (
    "verify_raw_sha256_before_content_selection",
    "sequential_selection_by_local_timestamp_only",
    "preserve_original_header_and_selected_row_bytes_exactly",
    "verify_semantic_sha256_before_any_converter_launch",
    "verify_rows_bytes_endpoints_and_snapshot_structure",
    "feed_same_physical_slice_files_to_all_compared_converters",
    "no_alternate_window_or_payload_after_result",
)

# D6R2B's old output SHA cannot be used as the sole successor oracle because its
# exact historical logical slice bytes are unavailable. A new successor parity
# gate must establish parity on the newly defined semantic slice itself.
D6R2B_OUTPUT_SHA_AS_SOLE_SUCCESSOR_ORACLE_ALLOWED = False
SUCCESSOR_PARITY_ARCHITECTURE = "SAME_SEMANTIC_SLICE_V2_VS_FROZEN_OLD_CONVERTER_AND_UPSTREAM_ORACLE"
OLD_CONVERTER_RERUN_AUTHORIZED_NOW = False
UPSTREAM_ORACLE_RERUN_AUTHORIZED_NOW = False
V2_REAL_EXECUTION_AUTHORIZED_NOW = False

# D6R8EC is contract-only. A separate D6R8ED contract is required before any
# source content is reopened or any converter executes.
RAW_FILE_CONTENT_OPEN_AUTHORIZED = False
SEMANTIC_SLICE_REEXTRACTION_AUTHORIZED = False
JAN_FULL_DAY_OPEN_AUTHORIZED = False
RAW_FEB_TO_JUL_OPEN_AUTHORIZED = False
CONVERSION_FEB_TO_JUL_AUTHORIZED = False
RUN_112_REPLAYS_AUTHORIZED = False
POLICY_EXECUTION_AUTHORIZED = False
HISTORICAL_PNL_AUTHORIZED = False
ECONOMIC_ARENA_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
NETWORK_ACQUISITION_AUTHORIZED = False
RAILWAY_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False

NEXT_AFTER_D6R8EC_CI = "FREEZE_D6R8ED_NEW_SEMANTIC_REAL_PARITY_CONTRACT"
