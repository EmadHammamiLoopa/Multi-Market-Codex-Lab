from __future__ import annotations

EXPERIMENT_ID = "DEV045-D6R5A"
CONTRACT_ID = "DEV045-D6R5-JAN-MEMMAP-ADAPTER-V1"
SCHEMA_VERSION = "dev045-d6r5-jan-memmap-adapter-contract-v1"

PARENT_HEAD = "cd9cc4aaf7ab873a1b57af2876e3aaadca3aff14"
PARENT_COMMIT_MESSAGE = "research(dev045): freeze D6R4B Jan01 full-day conversion"
PARENT_EVIDENCE_PATH = "evidence/dev045_d6r4b_jan01_full_day_conversion.json"

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

EVENT_DTYPE_DESCR = (
    ("ev", "<u8"),
    ("exch_ts", "<i8"),
    ("local_ts", "<i8"),
    ("px", "<f8"),
    ("qty", "<f8"),
    ("order_id", "<u8"),
    ("ival", "<i8"),
    ("fval", "<f8"),
)
EVENT_FIELDS = tuple(name for name, _ in EVENT_DTYPE_DESCR)
EVENT_ITEMSIZE = 64
EVENT_NDIM = 1

NP_LOAD_MMAP_MODE = "r"
NP_LOAD_ALLOW_PICKLE = False
PRODUCTION_CHUNK_ROWS = 500_000
HASH_BLOCK_BYTES = 8 * 1024 * 1024

OPEN_RAW_CSV_AUTHORIZED = False
RERUN_CONVERTER_AUTHORIZED = False
WRITE_CANONICAL_NPY_AUTHORIZED = False
WHOLE_FILE_MATERIALIZATION_AUTHORIZED = False
SORT_OR_REORDER_AUTHORIZED = False
OTHER_DAY_OPEN_AUTHORIZED = False
FEB_TO_JUL_OPEN_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
POLICY_EXECUTION_AUTHORIZED = False
HISTORICAL_PNL_AUTHORIZED = False
ECONOMIC_ARENA_AUTHORIZED = False
NETWORK_ACQUISITION_AUTHORIZED = False
RAILWAY_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False

REQUIRED_OPEN_SEMANTICS = (
    "np.load(path, mmap_mode='r', allow_pickle=False)",
    "read_only_memmap",
    "exact_file_identity",
    "bounded_slices_only",
    "preserve_physical_row_order",
    "no_converter",
    "no_raw_csv",
)

NEXT_AFTER_CONTRACT_CI = "IMPLEMENT_D6R5B_READ_ONLY_MEMMAP_ADAPTER"
