from __future__ import annotations

from dataclasses import asdict, dataclass
import gzip
import hashlib
import os
from pathlib import Path
import struct
import zlib


READ_BLOCK_BYTES = 1024 * 1024


class GzipForensicsError(RuntimeError):
    pass


@dataclass(frozen=True)
class GzipHeader:
    raw_hex: str
    length: int
    compression_method: int
    flags: int
    mtime: int
    xfl: int
    os_byte: int
    filename_hex: str | None


@dataclass(frozen=True)
class GzipSliceInspection:
    path: str
    compressed_sha256: str
    compressed_length: int
    decompressed_sha256: str
    decompressed_length: int
    data_rows: int
    csv_header_hex: str
    first_data_row_hex: str | None
    last_data_row_hex: str | None
    lf_lines: int
    crlf_lines: int
    cr_lines: int
    unterminated_lines: int
    gzip_header: GzipHeader
    trailer_crc32_hex: str
    computed_crc32_hex: str
    trailer_isize: int
    computed_isize: int
    trailer_crc32_valid: bool
    trailer_isize_valid: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _read_c_string(fh: object, raw: bytearray) -> bytes:
    value = bytearray()
    while True:
        byte = fh.read(1)  # type: ignore[attr-defined]
        if not byte:
            raise GzipForensicsError("truncated_gzip_header")
        raw.extend(byte)
        if byte == b"\x00":
            return bytes(value)
        value.extend(byte)


def _parse_gzip_header(path: Path) -> GzipHeader:
    with path.open("rb") as fh:
        fixed = fh.read(10)
        if len(fixed) != 10:
            raise GzipForensicsError("truncated_gzip_header")
        if fixed[:2] != b"\x1f\x8b":
            raise GzipForensicsError("gzip_magic")

        method = fixed[2]
        flags = fixed[3]
        if method != 8:
            raise GzipForensicsError("gzip_compression_method")
        if flags & 0xE0:
            raise GzipForensicsError("gzip_reserved_flags")

        raw = bytearray(fixed)
        if flags & 0x04:
            xlen_raw = fh.read(2)
            if len(xlen_raw) != 2:
                raise GzipForensicsError("truncated_gzip_extra_length")
            raw.extend(xlen_raw)
            xlen = struct.unpack("<H", xlen_raw)[0]
            extra = fh.read(xlen)
            if len(extra) != xlen:
                raise GzipForensicsError("truncated_gzip_extra")
            raw.extend(extra)

        filename = _read_c_string(fh, raw) if flags & 0x08 else None
        if flags & 0x10:
            _read_c_string(fh, raw)
        if flags & 0x02:
            header_crc = fh.read(2)
            if len(header_crc) != 2:
                raise GzipForensicsError("truncated_gzip_header_crc")
            raw.extend(header_crc)

    return GzipHeader(
        raw_hex=bytes(raw).hex(),
        length=len(raw),
        compression_method=method,
        flags=flags,
        mtime=struct.unpack("<I", fixed[4:8])[0],
        xfl=fixed[8],
        os_byte=fixed[9],
        filename_hex=None if filename is None else filename.hex(),
    )


def _compressed_identity(path: Path) -> tuple[str, int, bytes]:
    digest = hashlib.sha256()
    length = 0
    tail = b""
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(READ_BLOCK_BYTES), b""):
            digest.update(block)
            length += len(block)
            tail = (tail + block)[-8:]
    if length < 18 or len(tail) != 8:
        raise GzipForensicsError("truncated_gzip_file")
    return digest.hexdigest(), length, tail


def inspect_gzip_slice(
    path: str | os.PathLike[str],
) -> GzipSliceInspection:
    source = Path(path)
    if not source.is_file():
        raise GzipForensicsError("missing_gzip_file")

    header = _parse_gzip_header(source)
    compressed_sha, compressed_length, trailer = _compressed_identity(source)
    trailer_crc32, trailer_isize = struct.unpack("<II", trailer)

    digest = hashlib.sha256()
    decompressed_length = 0
    crc32 = 0
    line_count = 0
    lf_lines = 0
    crlf_lines = 0
    cr_lines = 0
    unterminated_lines = 0
    csv_header: bytes | None = None
    first_data_row: bytes | None = None
    last_data_row: bytes | None = None

    try:
        with gzip.open(source, "rb") as fh:
            for line in fh:
                digest.update(line)
                decompressed_length += len(line)
                crc32 = zlib.crc32(line, crc32)
                line_count += 1
                if line.endswith(b"\r\n"):
                    crlf_lines += 1
                elif line.endswith(b"\n"):
                    lf_lines += 1
                elif line.endswith(b"\r"):
                    cr_lines += 1
                else:
                    unterminated_lines += 1

                if line_count == 1:
                    csv_header = line
                else:
                    if first_data_row is None:
                        first_data_row = line
                    last_data_row = line
    except (EOFError, OSError, zlib.error) as exc:
        raise GzipForensicsError("gzip_decompression") from exc

    if csv_header is None:
        raise GzipForensicsError("empty_decompressed_payload")

    computed_crc32 = crc32 & 0xFFFFFFFF
    computed_isize = decompressed_length & 0xFFFFFFFF
    return GzipSliceInspection(
        path=os.fspath(source),
        compressed_sha256=compressed_sha,
        compressed_length=compressed_length,
        decompressed_sha256=digest.hexdigest(),
        decompressed_length=decompressed_length,
        data_rows=max(0, line_count - 1),
        csv_header_hex=csv_header.hex(),
        first_data_row_hex=(
            None if first_data_row is None else first_data_row.hex()
        ),
        last_data_row_hex=(
            None if last_data_row is None else last_data_row.hex()
        ),
        lf_lines=lf_lines,
        crlf_lines=crlf_lines,
        cr_lines=cr_lines,
        unterminated_lines=unterminated_lines,
        gzip_header=header,
        trailer_crc32_hex=f"{trailer_crc32:08x}",
        computed_crc32_hex=f"{computed_crc32:08x}",
        trailer_isize=trailer_isize,
        computed_isize=computed_isize,
        trailer_crc32_valid=trailer_crc32 == computed_crc32,
        trailer_isize_valid=trailer_isize == computed_isize,
    )


def logical_payload_equal(
    left: GzipSliceInspection,
    right: GzipSliceInspection,
) -> bool:
    return (
        left.decompressed_length == right.decompressed_length
        and left.decompressed_sha256 == right.decompressed_sha256
    )
