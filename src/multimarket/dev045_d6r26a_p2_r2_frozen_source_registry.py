from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

from multimarket import dev045_d6r17_real_historical_economic_driver_contract as d6r17
from multimarket import dev045_d6r26a_p2_r1_canonical_label_materializer_preauth as r1

EXPERIMENT_ID = "DEV045-D6R26A-P2-R2"
DESIGN_VERSION = "frozen-jan-jul-source-registry-v1"
PARENT_P2_R1_HEAD = "00c0779b36432e088dc6fd039559ed0095c84b2c"
SOURCE_CONTRACT_EXPERIMENT_ID = "DEV045-D6R17"
SOURCE_CONTRACT_HEAD = "b04a18f8eb5b4689abd15d7cdf6a6c889ee36212"
SOURCE_CONTRACT_PARENT_FREEZE_HEAD = "5411877e3bd1f8fcd9812176bc3dc39dbf18bf88"
DATA_ROLE = "CONSUMED_DEVELOPMENT"

# Frozen lineage defect: D6R17 contains a 63-hex transcription for June.
# The authoritative D6R16 PASS evidence at the witness head records the
# verified adapter SHA256 below. R2 freezes the witness value, never a guess.
JUNE_AUTHORITY_EVIDENCE_PATH = "evidence/dev045_d6r16_2026-06-01.json"
D6R17_JUNE_SHA256_TRANSCRIPTION_DEFECT = "ac97ad27c9d58b3b3e249547b8ae7c74cf2ebfde07965103bd5f6c7b853c26b"
D6R16_JUNE_SHA256_AUTHORITY = "ac97ad27c9d58b3b3e249547b8ae7c74cf2ebfde07965103bd9c8c05d0df1160"

FROZEN_SOURCE_REGISTRY_EMBEDDED = True
REGISTRY_RECOVERED_FROM_FROZEN_LINEAGE = True
REGISTRY_REDISCOVERY_REQUIRED = False
LOCAL_STAT_OR_REHASH_REQUIRED_FOR_REGISTRY_FREEZE = False
HISTORICAL_FILE_IO_AUTHORIZED = False
HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
HISTORICAL_SOURCE_REHASH_AUTHORIZED = False
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

class FrozenSourceRegistryError(RuntimeError):
    pass

@dataclass(frozen=True, order=True)
class FrozenSourceRecord:
    day: str
    path: str
    rows: int
    bytes: int
    sha256: str
    ingestion_witness: str
    witness_head: str

FROZEN_SOURCE_REGISTRY = (
    FrozenSourceRecord("2026-01-01", "/home/emadh/Multi-Market/runtime/dev045_d6r4b/output/BTCUSDT_2026-01-01.npy", 64_314_723, 4_116_142_528, "8f0a4fbd56ecdc261dbe2041ce138a09456423074925d495272716219a1d4da1", "DEV045-D6R7B", "c301e691ae89675f6e244a7b987d3cb0b4488381"),
    FrozenSourceRecord("2026-02-01", "/home/emadh/Multi-Market/runtime/dev045_d6r9a/output/BTCUSDT_2026-02-01.npy", 179_584_138, 11_493_385_088, "d757d2ac32a29b0ac587323e115779c466068c6c0eba4270226b9c4109254cbc", "DEV045-D6R15", "64dfd86079c9ee66956ac5db762306d0d45728de"),
    FrozenSourceRecord("2026-03-01", "/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-03-01.npy", 150_979_263, 9_662_673_088, "9e6a8b61d05e1a4938e17ffa7969241affc7c06c1d0836188e3a882c363f2d99", "DEV045-D6R16", SOURCE_CONTRACT_PARENT_FREEZE_HEAD),
    FrozenSourceRecord("2026-04-01", "/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-04-01.npy", 132_829_759, 8_501_104_832, "de7e0471e63631394981b301bb461d679192c37eb6241d4d8073cf0640eca7f7", "DEV045-D6R16", SOURCE_CONTRACT_PARENT_FREEZE_HEAD),
    FrozenSourceRecord("2026-05-01", "/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-05-01.npy", 108_328_169, 6_933_003_072, "9433dfb498070dd5dd3e8ab1633c2f19551844f2ddf0d451e120119365bb04a3", "DEV045-D6R16", SOURCE_CONTRACT_PARENT_FREEZE_HEAD),
    FrozenSourceRecord("2026-06-01", "/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-06-01.npy", 172_540_697, 11_042_604_864, D6R16_JUNE_SHA256_AUTHORITY, "DEV045-D6R16", SOURCE_CONTRACT_PARENT_FREEZE_HEAD),
    FrozenSourceRecord("2026-07-01", "/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy", 181_084_390, 11_589_401_216, "85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f", "DEV045-D6R16", SOURCE_CONTRACT_PARENT_FREEZE_HEAD),
)

FROZEN_SOURCE_REGISTRY_SHA256 = "97c631d621118d5cd4d294825dec545c92d85c62456403a6974ca38a70ece3f4"

def _record_from_d6r17(spec: d6r17.DaySourceSpec) -> FrozenSourceRecord:
    return FrozenSourceRecord(spec.day, str(spec.path), int(spec.rows), int(spec.bytes), str(spec.sha256), str(spec.ingestion_witness), str(spec.witness_head))

def inherited_registry() -> tuple[FrozenSourceRecord, ...]:
    return tuple(_record_from_d6r17(spec) for spec in d6r17.DAY_SPECS)

def r1_registry() -> dict[str, r1.FrozenSourceIdentity]:
    return {x.day: r1.FrozenSourceIdentity(day=x.day, path=x.path, bytes=x.bytes, sha256=x.sha256) for x in FROZEN_SOURCE_REGISTRY}

def canonical_registry_payload() -> dict[str, object]:
    return {"experiment_id": EXPERIMENT_ID, "design_version": DESIGN_VERSION, "data_role": DATA_ROLE, "source_contract": SOURCE_CONTRACT_EXPERIMENT_ID, "source_contract_head": SOURCE_CONTRACT_HEAD, "records": [asdict(x) for x in FROZEN_SOURCE_REGISTRY]}

def canonical_registry_bytes() -> bytes:
    return json.dumps(canonical_registry_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

def canonical_registry_sha256() -> str:
    return hashlib.sha256(canonical_registry_bytes()).hexdigest()

def _validate_inherited_lineage_with_known_june_defect() -> None:
    inherited = {x.day: x for x in inherited_registry()}
    frozen = {x.day: x for x in FROZEN_SOURCE_REGISTRY}
    if tuple(sorted(inherited)) != tuple(sorted(frozen)):
        raise FrozenSourceRegistryError("d6r17_days")
    for day in frozen:
        if day != "2026-06-01" and inherited[day] != frozen[day]:
            raise FrozenSourceRegistryError(f"d6r17_registry_drift:{day}")
    old = inherited["2026-06-01"]
    new = frozen["2026-06-01"]
    if old.sha256 != D6R17_JUNE_SHA256_TRANSCRIPTION_DEFECT or len(old.sha256) != 63:
        raise FrozenSourceRegistryError("unexpected_d6r17_june_state")
    if new.sha256 != D6R16_JUNE_SHA256_AUTHORITY or len(new.sha256) != 64:
        raise FrozenSourceRegistryError("june_witness_sha")
    if (old.day, old.path, old.rows, old.bytes, old.ingestion_witness, old.witness_head) != (new.day, new.path, new.rows, new.bytes, new.ingestion_witness, new.witness_head):
        raise FrozenSourceRegistryError("june_nonsha_drift")

def validate_frozen_source_registry() -> None:
    r1.validate_preauth_contract()
    d6r17.validate_contract()
    if PARENT_P2_R1_HEAD != "00c0779b36432e088dc6fd039559ed0095c84b2c": raise FrozenSourceRegistryError("parent")
    if SOURCE_CONTRACT_EXPERIMENT_ID != d6r17.EXPERIMENT_ID: raise FrozenSourceRegistryError("source_contract_experiment")
    if SOURCE_CONTRACT_PARENT_FREEZE_HEAD != d6r17.PARENT_FREEZE_HEAD: raise FrozenSourceRegistryError("source_contract_parent")
    if DATA_ROLE != r1.DATA_ROLE or DATA_ROLE != "CONSUMED_DEVELOPMENT": raise FrozenSourceRegistryError("data_role")
    _validate_inherited_lineage_with_known_june_defect()
    if tuple(x.day for x in FROZEN_SOURCE_REGISTRY) != tuple(r1.REAL_DEVELOPMENT_DAYS): raise FrozenSourceRegistryError("day_identity")
    if len(FROZEN_SOURCE_REGISTRY) != 7 or len({x.path for x in FROZEN_SOURCE_REGISTRY}) != 7: raise FrozenSourceRegistryError("registry_identity")
    if any(Path(x.path).suffix != ".npy" or "BTCUSDT_2026-" not in x.path for x in FROZEN_SOURCE_REGISTRY): raise FrozenSourceRegistryError("market_path")
    r1.validate_source_registry(r1_registry())
    if canonical_registry_sha256() != FROZEN_SOURCE_REGISTRY_SHA256: raise FrozenSourceRegistryError("registry_manifest_sha256")
    forbidden = (HISTORICAL_FILE_IO_AUTHORIZED, HISTORICAL_SOURCE_OPEN_AUTHORIZED, HISTORICAL_SOURCE_REHASH_AUTHORIZED, CANDIDATE_SIMULATION_AUTHORIZED, CANONICAL_LABEL_WRITE_AUTHORIZED, MODEL_FIT_AUTHORIZED, MODEL_SELECTION_AUTHORIZED, THRESHOLD_TUNING_AUTHORIZED, PNL_AUTHORIZED, ECONOMIC_ARENA_AUTHORIZED, FEE_RESCUE_AUTHORIZED, SIZE_TUNING_AUTHORIZED, LEVERAGE_AUTHORIZED, LIVE_TRADING_AUTHORIZED, AUG_OPEN_AUTHORIZED, SEP_PLUS_OPEN_AUTHORIZED, NON_BTC_OPEN_AUTHORIZED, NETWORK_ACQUISITION_AUTHORIZED)
    if any(forbidden): raise FrozenSourceRegistryError("closed_surface_open")
