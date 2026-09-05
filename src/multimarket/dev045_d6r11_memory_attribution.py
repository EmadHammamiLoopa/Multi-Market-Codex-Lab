from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re

from multimarket import dev045_d6r11_memory_attribution_contract as c


class MemoryAttributionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProcessMemory:
    vm_rss_bytes: int
    rss_anon_bytes: int
    rss_file_bytes: int
    rss_shmem_bytes: int
    vm_size_bytes: int | None
    vm_data_bytes: int | None
    vm_swap_bytes: int | None

    @property
    def resident_components_bytes(self) -> int:
        return self.rss_anon_bytes + self.rss_file_bytes + self.rss_shmem_bytes

    @property
    def rss_decomposition_delta_bytes(self) -> int:
        return self.vm_rss_bytes - self.resident_components_bytes

    @property
    def rss_decomposition_exact(self) -> bool:
        return self.rss_decomposition_delta_bytes == 0

    def to_dict(self) -> dict[str, int | bool | None]:
        return {
            "VmRSS_bytes": self.vm_rss_bytes,
            "RssAnon_bytes": self.rss_anon_bytes,
            "RssFile_bytes": self.rss_file_bytes,
            "RssShmem_bytes": self.rss_shmem_bytes,
            "VmSize_bytes": self.vm_size_bytes,
            "VmData_bytes": self.vm_data_bytes,
            "VmSwap_bytes": self.vm_swap_bytes,
            "resident_components_bytes": self.resident_components_bytes,
            "rss_decomposition_delta_bytes": self.rss_decomposition_delta_bytes,
            "rss_decomposition_exact": self.rss_decomposition_exact,
        }


@dataclass(frozen=True)
class SmapsRollupMemory:
    rss_bytes: int
    pss_bytes: int
    pss_anon_bytes: int | None
    pss_file_bytes: int | None
    private_clean_bytes: int | None
    private_dirty_bytes: int | None
    shared_clean_bytes: int | None
    shared_dirty_bytes: int | None
    anonymous_bytes: int | None
    swap_bytes: int | None

    def to_dict(self) -> dict[str, int | None]:
        return {
            "Rss_bytes": self.rss_bytes,
            "Pss_bytes": self.pss_bytes,
            "Pss_Anon_bytes": self.pss_anon_bytes,
            "Pss_File_bytes": self.pss_file_bytes,
            "Private_Clean_bytes": self.private_clean_bytes,
            "Private_Dirty_bytes": self.private_dirty_bytes,
            "Shared_Clean_bytes": self.shared_clean_bytes,
            "Shared_Dirty_bytes": self.shared_dirty_bytes,
            "Anonymous_bytes": self.anonymous_bytes,
            "Swap_bytes": self.swap_bytes,
        }


@dataclass(frozen=True)
class MemorySnapshot:
    captured_at_utc: str
    pid: int
    process: ProcessMemory
    mem_available_bytes: int
    smaps_rollup: SmapsRollupMemory | None

    @property
    def total_rss_bytes(self) -> int:
        return self.process.vm_rss_bytes

    @property
    def anonymous_resident_bytes(self) -> int:
        return self.process.rss_anon_bytes

    @property
    def file_backed_resident_bytes(self) -> int:
        return self.process.rss_file_bytes

    @property
    def shared_memory_resident_bytes(self) -> int:
        return self.process.rss_shmem_bytes

    def to_dict(self) -> dict[str, object]:
        return {
            "experiment_id": c.EXPERIMENT_ID,
            "schema_version": c.SCHEMA_VERSION,
            "mode": c.MODE,
            "captured_at_utc": self.captured_at_utc,
            "pid": self.pid,
            "unit": "bytes",
            "process": self.process.to_dict(),
            "system": {"MemAvailable_bytes": self.mem_available_bytes},
            "smaps_rollup_available": self.smaps_rollup is not None,
            "smaps_rollup": (
                None if self.smaps_rollup is None else self.smaps_rollup.to_dict()
            ),
            "attribution": {
                "total_rss_bytes": self.total_rss_bytes,
                "anonymous_resident_bytes": self.anonymous_resident_bytes,
                "file_backed_resident_bytes": self.file_backed_resident_bytes,
                "shared_memory_resident_bytes": self.shared_memory_resident_bytes,
                "available_system_memory_bytes": self.mem_available_bytes,
            },
            "canonical_abort_threshold_bytes": c.CANONICAL_ABORT_THRESHOLD_BYTES,
            "canonical_data_opened": False,
            "d6r10_rerun": False,
            "hftbacktest_executed": False,
            "policy_execution_run": False,
            "historical_pnl_computed": False,
            "converter_rerun": False,
        }


@dataclass(frozen=True)
class FileMappingResidency:
    path: str
    mapping_count: int
    rss_bytes: int
    pss_bytes: int
    private_clean_bytes: int
    private_dirty_bytes: int
    shared_clean_bytes: int
    shared_dirty_bytes: int

    @property
    def private_resident_bytes(self) -> int:
        return self.private_clean_bytes + self.private_dirty_bytes

    @property
    def shared_resident_bytes(self) -> int:
        return self.shared_clean_bytes + self.shared_dirty_bytes


_KIB_VALUE_RE = re.compile(r"^(?P<value>[0-9]+)\s+kB$")
_SMAPS_HEADER_RE = re.compile(
    r"^[0-9a-fA-F]+-[0-9a-fA-F]+\s+\S+\s+\S+\s+\S+\s+\d+(?:\s+(?P<path>.*))?$"
)


def kib_to_bytes(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MemoryAttributionError("kib_value")
    return value * c.KIB_TO_BYTES


def _parse_kib_fields(
    text: str,
    *,
    supported: tuple[str, ...],
    required: tuple[str, ...],
    source: str,
) -> dict[str, int]:
    if not isinstance(text, str):
        raise MemoryAttributionError(f"{source}_text")

    wanted = set(supported)
    parsed: dict[str, int] = {}
    for raw_line in text.splitlines():
        if ":" not in raw_line:
            continue
        name, raw_value = raw_line.split(":", 1)
        if name not in wanted:
            continue
        if name in parsed:
            raise MemoryAttributionError(f"{source}_duplicate:{name}")
        match = _KIB_VALUE_RE.fullmatch(raw_value.strip())
        if match is None:
            raise MemoryAttributionError(f"{source}_malformed:{name}")
        parsed[name] = kib_to_bytes(int(match.group("value")))

    missing = [name for name in required if name not in parsed]
    if missing:
        raise MemoryAttributionError(f"{source}_missing:{','.join(missing)}")
    return parsed


def parse_proc_status(text: str) -> ProcessMemory:
    values = _parse_kib_fields(
        text,
        supported=c.STATUS_FIELDS,
        required=c.REQUIRED_STATUS_FIELDS,
        source="status",
    )
    return ProcessMemory(
        vm_rss_bytes=values["VmRSS"],
        rss_anon_bytes=values["RssAnon"],
        rss_file_bytes=values["RssFile"],
        rss_shmem_bytes=values["RssShmem"],
        vm_size_bytes=values.get("VmSize"),
        vm_data_bytes=values.get("VmData"),
        vm_swap_bytes=values.get("VmSwap"),
    )


def parse_proc_meminfo(text: str) -> int:
    values = _parse_kib_fields(
        text,
        supported=c.MEMINFO_FIELDS,
        required=c.REQUIRED_MEMINFO_FIELDS,
        source="meminfo",
    )
    return values["MemAvailable"]


def parse_smaps_rollup(text: str) -> SmapsRollupMemory:
    values = _parse_kib_fields(
        text,
        supported=c.SMAPS_ROLLUP_FIELDS,
        required=c.REQUIRED_SMAPS_ROLLUP_FIELDS,
        source="smaps_rollup",
    )
    return SmapsRollupMemory(
        rss_bytes=values["Rss"],
        pss_bytes=values["Pss"],
        pss_anon_bytes=values.get("Pss_Anon"),
        pss_file_bytes=values.get("Pss_File"),
        private_clean_bytes=values.get("Private_Clean"),
        private_dirty_bytes=values.get("Private_Dirty"),
        shared_clean_bytes=values.get("Shared_Clean"),
        shared_dirty_bytes=values.get("Shared_Dirty"),
        anonymous_bytes=values.get("Anonymous"),
        swap_bytes=values.get("Swap"),
    )


def capture_memory_snapshot(
    *,
    status_path: Path = Path(c.PROC_STATUS_PATH),
    meminfo_path: Path = Path(c.PROC_MEMINFO_PATH),
    smaps_rollup_path: Path | None = Path(c.PROC_SMAPS_ROLLUP_PATH),
    captured_at_utc: str | None = None,
) -> MemorySnapshot:
    try:
        status_text = Path(status_path).read_text(encoding="ascii")
        meminfo_text = Path(meminfo_path).read_text(encoding="ascii")
    except OSError as exc:
        raise MemoryAttributionError(f"required_proc_read:{exc.filename}") from exc

    smaps: SmapsRollupMemory | None = None
    if smaps_rollup_path is not None:
        try:
            smaps_text = Path(smaps_rollup_path).read_text(encoding="ascii")
        except OSError:
            smaps_text = None
        if smaps_text is not None:
            smaps = parse_smaps_rollup(smaps_text)

    timestamp = captured_at_utc
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    return MemorySnapshot(
        captured_at_utc=timestamp,
        pid=os.getpid(),
        process=parse_proc_status(status_text),
        mem_available_bytes=parse_proc_meminfo(meminfo_text),
        smaps_rollup=smaps,
    )


def serialize_snapshot(snapshot: MemorySnapshot) -> str:
    if not isinstance(snapshot, MemorySnapshot):
        raise MemoryAttributionError("snapshot_type")
    return json.dumps(snapshot.to_dict(), indent=2, sort_keys=True) + "\n"


def _decode_smaps_path(value: str) -> str:
    return (
        value.replace(r"\040", " ")
        .replace(r"\011", "\t")
        .replace(r"\012", "\n")
        .replace(r"\134", "\\")
    )


def _mapping_matches(raw_path: str | None, target: Path) -> bool:
    if raw_path is None:
        return False
    decoded = _decode_smaps_path(raw_path.strip())
    if decoded.endswith(" (deleted)"):
        decoded = decoded[: -len(" (deleted)")]
    try:
        return Path(decoded).resolve(strict=False) == target
    except OSError:
        return False


def parse_file_mapping_residency(text: str, path: Path) -> FileMappingResidency:
    if not isinstance(text, str):
        raise MemoryAttributionError("smaps_text")
    target = Path(path).resolve(strict=False)
    metric_names = (
        "Rss",
        "Pss",
        "Private_Clean",
        "Private_Dirty",
        "Shared_Clean",
        "Shared_Dirty",
    )
    totals = {name: 0 for name in metric_names}
    mapping_count = 0
    current_matches = False
    current: dict[str, int] = {}

    def finish_mapping() -> None:
        nonlocal mapping_count, current
        if not current_matches:
            current = {}
            return
        if "Rss" not in current or "Pss" not in current:
            raise MemoryAttributionError("smaps_mapping_missing:Rss,Pss")
        mapping_count += 1
        for name in metric_names:
            totals[name] += current.get(name, 0)
        current = {}

    for raw_line in text.splitlines():
        header = _SMAPS_HEADER_RE.fullmatch(raw_line)
        if header is not None:
            finish_mapping()
            current_matches = _mapping_matches(header.group("path"), target)
            continue
        if not current_matches or ":" not in raw_line:
            continue
        name, raw_value = raw_line.split(":", 1)
        if name not in totals:
            continue
        if name in current:
            raise MemoryAttributionError(f"smaps_mapping_duplicate:{name}")
        match = _KIB_VALUE_RE.fullmatch(raw_value.strip())
        if match is None:
            raise MemoryAttributionError(f"smaps_mapping_malformed:{name}")
        current[name] = kib_to_bytes(int(match.group("value")))
    finish_mapping()

    if mapping_count == 0:
        raise MemoryAttributionError("file_mapping_missing")
    return FileMappingResidency(
        path=str(target),
        mapping_count=mapping_count,
        rss_bytes=totals["Rss"],
        pss_bytes=totals["Pss"],
        private_clean_bytes=totals["Private_Clean"],
        private_dirty_bytes=totals["Private_Dirty"],
        shared_clean_bytes=totals["Shared_Clean"],
        shared_dirty_bytes=totals["Shared_Dirty"],
    )


def capture_file_mapping_residency(
    path: Path,
    *,
    smaps_path: Path = Path(c.PROC_SMAPS_PATH),
) -> FileMappingResidency:
    try:
        text = Path(smaps_path).read_text(encoding="ascii")
    except OSError as exc:
        raise MemoryAttributionError(f"smaps_read:{exc.filename}") from exc
    return parse_file_mapping_residency(text, path)
