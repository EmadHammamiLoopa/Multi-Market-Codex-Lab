from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from urllib.parse import quote

import httpx

from .codex_research import ResearchSealError, assert_unsealed_day, assert_unsealed_path


EXPERIMENT_ID = "CODEX-EXP-003"
DAYS = tuple(date(2026, month, 1) for month in range(1, 8))
EXCHANGES = ("binance", "bybit")
DATA_TYPES = ("book_snapshot_5", "trades")
SYMBOLS = ("BTCUSDT", "ETHUSDT")
DATASET_ORIGIN = "https://datasets.tardis.dev"


@dataclass(frozen=True)
class DatasetRequest:
    exchange: str
    data_type: str
    symbol: str
    day: date

    def validate(self) -> None:
        if self.exchange not in EXCHANGES:
            raise ValueError(f"unfrozen exchange: {self.exchange}")
        if self.data_type not in DATA_TYPES:
            raise ValueError(f"unfrozen data type: {self.data_type}")
        if self.symbol not in SYMBOLS:
            raise ValueError(f"unfrozen symbol: {self.symbol}")
        assert_unsealed_day(self.day, allowed=DAYS)

    @property
    def url(self) -> str:
        self.validate()
        return (
            f"{DATASET_ORIGIN}/v1/{quote(self.exchange, safe='')}/"
            f"{quote(self.data_type, safe='')}/{self.day:%Y/%m/%d}/"
            f"{quote(self.symbol, safe='')}.csv.gz"
        )

    def output_path(self, root: Path) -> Path:
        self.validate()
        target = root / self.exchange / self.data_type / self.symbol / f"{self.day.isoformat()}.csv.gz"
        assert_unsealed_path(target)
        return target


def frozen_requests() -> tuple[DatasetRequest, ...]:
    return tuple(
        DatasetRequest(exchange, data_type, symbol, day)
        for exchange in EXCHANGES
        for data_type in DATA_TYPES
        for symbol in SYMBOLS
        for day in DAYS
    )


def _git(workspace: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=workspace, text=True, capture_output=True, check=True
    )
    return result.stdout.strip()


def assert_frozen_workspace(workspace: Path, frozen_commit: str) -> None:
    if not frozen_commit or len(frozen_commit) != 40:
        raise RuntimeError("a full 40-character frozen commit is required")
    head = _git(workspace, "rev-parse", "HEAD")
    if head != frozen_commit:
        raise RuntimeError(f"frozen commit mismatch: expected {frozen_commit}, current {head}")
    tracked = _git(workspace, "status", "--porcelain", "--untracked-files=no")
    if tracked:
        raise RuntimeError("tracked worktree changes detected after freeze")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_gzip_csv(path: Path) -> tuple[int, str]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        header = handle.readline().rstrip("\r\n")
        if not header:
            raise RuntimeError(f"empty dataset: {path}")
        rows = sum(1 for _ in handle)
    if rows <= 0:
        raise RuntimeError(f"dataset contains no records: {path}")
    return rows, header


def download_one(
    request: DatasetRequest,
    output_root: Path,
    *,
    client: httpx.Client,
) -> dict[str, object]:
    """Download one frozen sample file. Call only after the pre-score commit is frozen."""

    target = request.output_path(output_root)
    if target.exists():
        rows, header = _validate_gzip_csv(target)
        return {
            **asdict(request),
            "day": request.day.isoformat(),
            "url": request.url,
            "path": str(target),
            "status": "EXISTING_VALID",
            "rows": rows,
            "header": header,
            "sha256": _sha256(target),
        }
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    if partial.exists():
        raise RuntimeError(f"partial file requires manual review: {partial}")
    with client.stream("GET", request.url, follow_redirects=True) as response:
        response.raise_for_status()
        with partial.open("xb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)
    try:
        rows, header = _validate_gzip_csv(partial)
        partial.replace(target)
    except Exception:
        # Preserve a failed download for forensic review; do not silently retry or overwrite it.
        raise
    return {
        **asdict(request),
        "day": request.day.isoformat(),
        "url": request.url,
        "path": str(target),
        "status": "DOWNLOADED",
        "rows": rows,
        "header": header,
        "sha256": _sha256(target),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Post-freeze downloader for the frozen CODEX-EXP-003 Tardis sample set."
    )
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--acknowledge-post-freeze-acquisition",
        action="store_true",
        help="Required acknowledgement that the pre-score review is complete.",
    )
    args = parser.parse_args(argv)
    if not args.acknowledge_post_freeze_acquisition:
        raise ResearchSealError("post-freeze acquisition acknowledgement is required")
    assert_frozen_workspace(args.workspace, args.frozen_commit)
    records: list[dict[str, object]] = []
    with httpx.Client(timeout=120.0) as client:
        for request in frozen_requests():
            records.append(download_one(request, args.output_root, client=client))
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "frozen_commit": args.frozen_commit,
        "post_freeze_acquisition": True,
        "sealed_august_opened": False,
        "files": records,
    }
    args.manifest.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"files": len(records), "manifest": str(args.manifest)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
