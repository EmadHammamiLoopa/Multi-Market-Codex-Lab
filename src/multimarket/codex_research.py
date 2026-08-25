from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, is_dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


EXPERIMENT_ID = "CODEX-EXP-001"
SANDBOX_DAYS = tuple(date(2026, month, 1) for month in range(1, 8))
SEALED_DAYS = frozenset(
    {date(2026, 8, 1), *(date(2026, 8, day) for day in range(4, 24))}
)
_ISO_DATE = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)")


class ResearchSealError(RuntimeError):
    """Raised before any attempt to open a sealed research period."""


def assert_unsealed_day(day: date, *, allowed: Iterable[date] | None = None) -> None:
    if day in SEALED_DAYS:
        raise ResearchSealError(f"sealed research day: {day.isoformat()}")
    if allowed is not None and day not in frozenset(allowed):
        raise ResearchSealError(f"day is outside the frozen experiment set: {day.isoformat()}")


def assert_unsealed_path(path: str | Path) -> None:
    """Reject a path naming a sealed ISO date before the path is opened."""

    value = str(path)
    for match in _ISO_DATE.finditer(value):
        try:
            named_day = date.fromisoformat(match.group(1))
        except ValueError:
            continue
        assert_unsealed_day(named_day)


def canonical_json(value: Any) -> str:
    if is_dataclass(value):
        value = asdict(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    target = Path(path)
    assert_unsealed_path(target)
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()
