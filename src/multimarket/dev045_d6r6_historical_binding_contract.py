from __future__ import annotations

EXPERIMENT_ID = "DEV045-D6R6A"
CONTRACT_ID = "DEV045-D6R6-HISTORICAL-MEMMAP-BINDING-V1"
SCHEMA_VERSION = "dev045-d6r6-historical-memmap-binding-contract-v1"

PARENT_BRANCH = "research/dev045-m6-jan-memmap-validation"
PARENT_HEAD = "4be133e52d8392da1e91fce4b72fc69995545c58"

D6R5C_EVIDENCE_PATH = (
    "evidence/dev045_d6r5c_jan_memmap_validation.json"
)
D6R5C_EVIDENCE_SHA256 = (
    "79fa94de273c1ced6bf3a6a752331c8026056cbe5dabf22299f43b229cdeddf3"
)
D6R5C_STATUS = "PASS"
D6R5C_CANONICAL_ATTEMPT = 1
D6R5C_OBSERVED_ROWS = 64_314_723
D6R5C_OBSERVED_CHUNKS = 129

HISTORICAL_ORCHESTRATION_PATH = (
    "src/multimarket/dev045_m6_historical_orchestration.py"
)
HISTORICAL_ORCHESTRATION_GIT_BLOB = (
    "b12069072d95d4c2b4a4c788f988501a96dbceb1"
)

EVENT_LOOP_KERNEL_PATH = (
    "src/multimarket/dev045_m6_event_loop_kernel.py"
)
EVENT_LOOP_KERNEL_GIT_BLOB = (
    "93a865b5a7a81da139b60fe220f5106f98832c7e"
)

MEMMAP_ADAPTER_PATH = (
    "src/multimarket/dev045_d6r5_memmap_adapter.py"
)
MEMMAP_ADAPTER_GIT_BLOB = (
    "ff60660affbf85af2b3c35f2ee167f3f9519de2e"
)

MEMMAP_CONTRACT_PATH = (
    "src/multimarket/dev045_d6r5_memmap_contract.py"
)
MEMMAP_CONTRACT_GIT_BLOB = (
    "613ea56130b2f6e846ec82e084cc6a8d56ea340b"
)

HFTBACKTEST_VERSION = "2.4.4"
HFTBACKTEST_UPSTREAM_COMMIT = (
    "a244a14250b42d97fc305569c93c4117cd5e1dff"
)

HFTBACKTEST_PY_INIT_GIT_BLOB = (
    "d7f992d6fe3f53dcdd708fefc4ecddfb49abdd4e"
)
HFTBACKTEST_PY_RUST_LIB_GIT_BLOB = (
    "28dec6993318a7e887a465e2d0ed7adf93ce9889"
)
HFTBACKTEST_DATA_MOD_GIT_BLOB = (
    "da0cedb55931555569bf1053d36b508597d87356"
)
HFTBACKTEST_READER_GIT_BLOB = (
    "4507ebf68aa5a2682542bbdca9b9c9e5eab84e11"
)
HFTBACKTEST_DERIVE_GIT_BLOB = (
    "db6b5a17606b2c4ff346896342a9f2ce68e4961f"
)

EXCHANGE = "binance-futures"
SYMBOL = "BTCUSDT"
DAY = "2026-01-01"

CANONICAL_NPY_PATH = (
    "/home/emadh/Multi-Market/runtime/dev045_d6r4b/output/"
    "BTCUSDT_2026-01-01.npy"
)
CANONICAL_NPY_SHA256 = (
    "8f0a4fbd56ecdc261dbe2041ce138a09456423074925d495272716219a1d4da1"
)
CANONICAL_NPY_BYTES = 4_116_142_528
CANONICAL_NPY_ROWS = 64_314_723

SOURCE_ENTRYPOINT = (
    "multimarket.dev045_d6r5_memmap_adapter."
    "open_canonical_jan"
)
SOURCE_DATA_TYPE = "numpy.memmap"
SOURCE_MMAP_MODE = "r"
SOURCE_ALLOW_PICKLE = False
SOURCE_PUBLIC_PATH_ARGUMENT_COUNT = 0

HFT_ASSET_BINDING = "BacktestAsset.data(source.data)"
HFT_NDARRAY_REGISTRATION = "data.ctypes.data + len(data)"
HFT_RUST_REGISTRATION = (
    "Data::<Event>::from_data_ptr(DataPtr::from_ptr(arr), 0)"
)
HFT_BINDING_OWNERSHIP = "caller_owned_non_owning_raw_pointer"

ZERO_COPY_REGISTRATION_REQUIRED = True
DATA_PTR_MANAGED_BY_HFTBACKTEST = False
READER_DATA_CLONES_SHARE_UNDERLYING_POINTER = True

MEMMAP_OWNER_MUST_OUTLIVE_BACKTEST = True
BACKTEST_MUST_CLOSE_BEFORE_MEMMAP_CLOSE = True

PARALLEL_LOAD = False
FEED_LATENCY_OFFSET_NS = 0
FEED_PREPROCESSOR_AUTHORIZED = False
FEED_DATA_MUTATION_AUTHORIZED = False

PHYSICAL_ROW_ORDER_MUST_BE_PRESERVED = True
SORT_OR_REORDER_AUTHORIZED = False
WHOLE_FILE_MATERIALIZATION_AUTHORIZED = False
ARRAY_COPY_OR_CONCATENATION_AUTHORIZED = False

PRODUCTION_VALIDATION_CHUNK_ROWS = 500_000

IMPLEMENTATION_PATH = (
    "src/multimarket/dev045_d6r6_historical_driver.py"
)

D6R6B_SYNTHETIC_MEMMAP_INGESTION_AUTHORIZED_AFTER_CI = True
D6R6B_CANONICAL_JAN_OPEN_AUTHORIZED = False
D6R6B_CANONICAL_JAN_HFTBACKTEST_INGESTION_AUTHORIZED = False
D6R6B_POLICY_EXECUTION_AUTHORIZED = False

OPEN_RAW_CSV_AUTHORIZED = False
RERUN_CONVERTER_AUTHORIZED = False
WRITE_CANONICAL_NPY_AUTHORIZED = False

OTHER_DAY_OPEN_AUTHORIZED = False
FEB_TO_JUL_OPEN_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False

HISTORICAL_POLICY_REPLAY_AUTHORIZED = False
HISTORICAL_PNL_AUTHORIZED = False
ECONOMIC_ARENA_AUTHORIZED = False
CANONICAL_PNL_WRITE_AUTHORIZED = False

NETWORK_ACQUISITION_AUTHORIZED = False
RAILWAY_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False

REQUIRED_LIFETIME_ORDER = (
    "open_verified_memmap",
    "build_asset_from_same_live_memmap",
    "build_backtest",
    "use_backtest_only_in_later_authorized_gate",
    "close_backtest",
    "close_memmap",
)

REQUIRED_BINDING_SEMANTICS = (
    "exact_d6r5_public_entrypoint_only",
    "no_arbitrary_path_argument",
    "read_only_numpy_memmap",
    "exact_canonical_identity_remains_frozen",
    "zero_copy_raw_pointer_registration",
    "caller_owns_memmap_memory",
    "memmap_outlives_asset_and_backtest",
    "backtest_closes_before_memmap",
    "parallel_load_false",
    "feed_latency_offset_zero",
    "no_feed_preprocessor",
    "no_feed_data_mutation",
    "preserve_physical_row_order",
    "no_sort_or_reorder",
    "no_whole_file_materialization",
    "no_array_copy_or_concatenation",
    "d6r6b_uses_synthetic_memmap_only",
    "canonical_jan_hftbacktest_ingestion_stays_closed",
    "historical_policy_replay_stays_closed",
    "historical_pnl_stays_closed",
)

NEXT_AFTER_CONTRACT_CI = (
    "IMPLEMENT_D6R6B_SYNTHETIC_LIFETIME_SAFE_HISTORICAL_BINDING"
)
