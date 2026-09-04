from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable


EXPERIMENT_ID = "DEV045-D4"
DESIGN_VERSION = "compressed-byte-provenance-v1"

SYMBOL = "BTCUSDT"

AUTHORIZED_DAYS = (
    "2026-01-01",
    "2026-02-01",
    "2026-03-01",
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)

STREAMS = (
    "trades",
    "incremental_book_L2",
)

RAW_ROOT_BASENAME = "v23_phase0dl_l2_raw"

MANIFEST_RELATIVE_PATH = (
    "evidence/dev045_d4_raw_provenance.tsv"
)

FROZEN_MANIFEST_SHA256 = "7fa6cf76ee8c6da98c5758756c887f0fb7b4d2e5eaf6b0e9f87551dce9981c12"

COMPRESSED_BYTE_HASHING_ENABLED = True

RAW_GZIP_DECOMPRESSION_ENABLED = False
RAW_CSV_HEADER_READ_ENABLED = False
RAW_CSV_ROW_PARSE_ENABLED = False

TARDIS_CONVERTER_EXECUTION_ENABLED = False
HISTORICAL_POLICY_REPLAY_ENABLED = False
HISTORICAL_PNL_ENABLED = False
ECONOMIC_ARENA_EXECUTION_ENABLED = False
CANONICAL_PNL_WRITE_ENABLED = False

NETWORK_MARKET_DATA_ACQUISITION_ENABLED = False
LIVE_TRADING_AUTHORIZED = False


class RawProvenanceError(RuntimeError):
    pass


def expected_relative_path(
    kind: str,
    day: str,
) -> str:
    if kind not in STREAMS:
        raise RawProvenanceError(
            "stream"
        )

    if day not in AUTHORIZED_DAYS:
        raise RawProvenanceError(
            "unauthorized_day"
        )

    return (
        f"{kind}/{SYMBOL}/{day}.csv.gz"
    )


@dataclass(frozen=True)
class RawFileProvenance:
    kind: str
    day: str
    bytes: int
    sha256: str
    relative_path: str

    def __post_init__(self) -> None:
        if self.kind not in STREAMS:
            raise RawProvenanceError(
                "stream"
            )

        if self.day not in AUTHORIZED_DAYS:
            raise RawProvenanceError(
                "unauthorized_day"
            )

        size = int(self.bytes)

        if size <= 0:
            raise RawProvenanceError(
                "nonpositive_size"
            )

        digest = str(self.sha256)

        if (
            len(digest) != 64
            or any(
                c not in "0123456789abcdef"
                for c in digest
            )
        ):
            raise RawProvenanceError(
                "sha256"
            )

        expected = expected_relative_path(
            self.kind,
            self.day,
        )

        if self.relative_path != expected:
            raise RawProvenanceError(
                "relative_path"
            )


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def manifest_path() -> Path:
    return (
        repository_root()
        / MANIFEST_RELATIVE_PATH
    )


def manifest_file_sha256(
    path: Path | None = None,
) -> str:
    target = (
        manifest_path()
        if path is None
        else Path(path)
    )

    return sha256(
        target.read_bytes()
    ).hexdigest()


def load_manifest(
    path: Path | None = None,
) -> tuple[RawFileProvenance, ...]:
    target = (
        manifest_path()
        if path is None
        else Path(path)
    )

    text = target.read_text(
        encoding="utf-8"
    )

    lines = text.splitlines()

    if not lines:
        raise RawProvenanceError(
            "empty_manifest"
        )

    header = (
        "kind\tday\tbytes\tsha256"
        "\trelative_path"
    )

    if lines[0] != header:
        raise RawProvenanceError(
            "manifest_header"
        )

    rows = []

    for line in lines[1:]:
        parts = line.split("\t")

        if len(parts) != 5:
            raise RawProvenanceError(
                "manifest_columns"
            )

        kind, day, size, digest, relative = (
            parts
        )

        rows.append(
            RawFileProvenance(
                kind=kind,
                day=day,
                bytes=int(size),
                sha256=digest,
                relative_path=relative,
            )
        )

    return tuple(rows)


def expected_order() -> tuple[
    tuple[str, str],
    ...
]:
    return tuple(
        (kind, day)
        for day in AUTHORIZED_DAYS
        for kind in STREAMS
    )


def validate_manifest(
    rows: Iterable[
        RawFileProvenance
    ],
) -> tuple[
    RawFileProvenance,
    ...
]:
    xs = tuple(rows)

    if len(xs) != 14:
        raise RawProvenanceError(
            "row_count"
        )

    actual_order = tuple(
        (row.kind, row.day)
        for row in xs
    )

    if actual_order != expected_order():
        raise RawProvenanceError(
            "row_order"
        )

    paths = tuple(
        row.relative_path
        for row in xs
    )

    if len(set(paths)) != 14:
        raise RawProvenanceError(
            "duplicate_path"
        )

    trade_count = sum(
        row.kind == "trades"
        for row in xs
    )

    depth_count = sum(
        row.kind
        == "incremental_book_L2"
        for row in xs
    )

    if trade_count != 7:
        raise RawProvenanceError(
            "trade_count"
        )

    if depth_count != 7:
        raise RawProvenanceError(
            "depth_count"
        )

    return xs


def verify_frozen_manifest() -> tuple[
    RawFileProvenance,
    ...
]:
    if (
        manifest_file_sha256()
        != FROZEN_MANIFEST_SHA256
    ):
        raise RawProvenanceError(
            "manifest_sha256"
        )

    return validate_manifest(
        load_manifest()
    )


def _compressed_sha256(
    path: Path,
) -> str:
    h = sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(
                8 * 1024 * 1024
            )

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def verify_local_compressed_bytes(
    root: str | Path,
    rows: Iterable[
        RawFileProvenance
    ] | None = None,
) -> tuple[
    RawFileProvenance,
    ...
]:
    """
    Verify only the compressed .csv.gz byte identities.

    This function never decompresses gzip content and never parses CSV.
    """
    root_path = Path(root)

    if root_path.name != RAW_ROOT_BASENAME:
        raise RawProvenanceError(
            "raw_root_basename"
        )

    root_resolved = root_path.resolve()

    xs = (
        verify_frozen_manifest()
        if rows is None
        else validate_manifest(rows)
    )

    for row in xs:
        candidate = (
            root_resolved
            / row.relative_path
        )

        if candidate.is_symlink():
            raise RawProvenanceError(
                "symlink"
            )

        if not candidate.is_file():
            raise RawProvenanceError(
                "missing_file"
            )

        resolved = candidate.resolve()

        try:
            resolved.relative_to(
                root_resolved
            )
        except ValueError as exc:
            raise RawProvenanceError(
                "path_escape"
            ) from exc

        if (
            resolved.stat().st_size
            != row.bytes
        ):
            raise RawProvenanceError(
                "byte_size"
            )

        if (
            _compressed_sha256(
                resolved
            )
            != row.sha256
        ):
            raise RawProvenanceError(
                "compressed_sha256"
            )

    return xs


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "SYMBOL",
    "AUTHORIZED_DAYS",
    "STREAMS",
    "RAW_ROOT_BASENAME",
    "MANIFEST_RELATIVE_PATH",
    "FROZEN_MANIFEST_SHA256",
    "COMPRESSED_BYTE_HASHING_ENABLED",
    "RAW_GZIP_DECOMPRESSION_ENABLED",
    "RAW_CSV_HEADER_READ_ENABLED",
    "RAW_CSV_ROW_PARSE_ENABLED",
    "TARDIS_CONVERTER_EXECUTION_ENABLED",
    "HISTORICAL_POLICY_REPLAY_ENABLED",
    "HISTORICAL_PNL_ENABLED",
    "ECONOMIC_ARENA_EXECUTION_ENABLED",
    "CANONICAL_PNL_WRITE_ENABLED",
    "NETWORK_MARKET_DATA_ACQUISITION_ENABLED",
    "LIVE_TRADING_AUTHORIZED",
    "RawProvenanceError",
    "RawFileProvenance",
    "expected_relative_path",
    "manifest_path",
    "manifest_file_sha256",
    "load_manifest",
    "expected_order",
    "validate_manifest",
    "verify_frozen_manifest",
    "verify_local_compressed_bytes",
]
