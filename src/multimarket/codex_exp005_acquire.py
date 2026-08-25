from __future__ import annotations

import argparse
import gzip
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from urllib.parse import quote

import httpx

from .codex_exp004_headroom import assert_frozen_workspace
from .codex_research import ResearchSealError, assert_unsealed_day, assert_unsealed_path, sha256_file

EXPERIMENT_ID = "CODEX-EXP-005-P0"
DAYS = tuple(date(2026, month, 1) for month in range(1, 8))
SYMBOLS = ("BTCUSDT", "ETHUSDT")
EXCHANGE = "binance-futures"
DATA_TYPE = "derivative_ticker"
DATASET_ORIGIN = "https://datasets.tardis.dev"


@dataclass(frozen=True)
class DatasetRequest:
    symbol: str
    day: date
    exchange: str = EXCHANGE
    data_type: str = DATA_TYPE

    def validate(self) -> None:
        if self.exchange != EXCHANGE:
            raise ValueError(f"unfrozen exchange: {self.exchange}")
        if self.data_type != DATA_TYPE:
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
    return tuple(DatasetRequest(symbol, day) for symbol in SYMBOLS for day in DAYS)


def _inspect_gzip(path: Path) -> tuple[int, str]:
    assert_unsealed_path(path)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        header = handle.readline().rstrip("\r\n")
        if not header:
            raise RuntimeError(f"empty dataset: {path}")
        rows = sum(1 for _ in handle)
    if rows <= 0:
        raise RuntimeError(f"dataset contains no records: {path}")
    return rows, header


def request_plan(output_root: Path) -> list[dict[str, object]]:
    plan: list[dict[str, object]] = []
    for request in frozen_requests():
        target = request.output_path(output_root)
        plan.append({
            "exchange": request.exchange,
            "data_type": request.data_type,
            "symbol": request.symbol,
            "day": request.day.isoformat(),
            "url": request.url,
            "destination": str(target),
            "exists": target.exists(),
        })
    return plan


def download_one(request: DatasetRequest, output_root: Path, *, client: httpx.Client) -> dict[str, object]:
    request.validate()
    target = request.output_path(output_root)
    if target.exists():
        rows, header = _inspect_gzip(target)
        return {
            **asdict(request),
            "day": request.day.isoformat(),
            "url": request.url,
            "path": str(target),
            "status": "EXISTING_VALID",
            "rows": rows,
            "header": header,
            "bytes": target.stat().st_size,
            "sha256": sha256_file(target),
        }

    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    assert_unsealed_path(partial)
    if partial.exists():
        raise RuntimeError(f"partial file requires manual review: {partial}")

    with client.stream("GET", request.url, follow_redirects=True) as response:
        response.raise_for_status()
        with partial.open("xb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)

    try:
        rows, header = _inspect_gzip(partial)
        partial.replace(target)
    except Exception:
        raise

    return {
        **asdict(request),
        "day": request.day.isoformat(),
        "url": request.url,
        "path": str(target),
        "status": "DOWNLOADED",
        "rows": rows,
        "header": header,
        "bytes": target.stat().st_size,
        "sha256": sha256_file(target),
    }


def _assert_fresh_manifest(path: Path) -> Path:
    assert_unsealed_path(path)
    partial = path.with_name(path.name + ".part")
    if path.exists():
        raise FileExistsError(f"refusing to overwrite acquisition manifest: {path}")
    if partial.exists():
        raise FileExistsError(f"partial acquisition manifest exists: {partial}")
    return partial


def build_manifest_payload(frozen_commit: str, records: list[dict[str, object]]) -> dict[str, object]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "frozen_commit": frozen_commit,
        "source": "Tardis downloadable CSV",
        "exchange": EXCHANGE,
        "data_type": DATA_TYPE,
        "post_freeze_acquisition": True,
        "sealed_august_opened": False,
        "file_count": len(records),
        "files": records,
    }


def run(workspace: Path, frozen_commit: str, output_root: Path, manifest: Path) -> dict[str, object]:
    assert_frozen_workspace(workspace, frozen_commit)
    partial_manifest = _assert_fresh_manifest(manifest)
    plan = request_plan(output_root)
    if len(plan) != 14:
        raise RuntimeError("frozen acquisition set must contain exactly 14 files")
    print(json.dumps({"frozen_request_plan": plan}, indent=2))

    records: list[dict[str, object]] = []
    with httpx.Client(timeout=120.0) as client:
        for request in frozen_requests():
            record = download_one(request, output_root, client=client)
            records.append(record)
            print(json.dumps({"acquired": record}, default=str))

    payload = build_manifest_payload(frozen_commit, records)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    partial_manifest.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    partial_manifest.replace(manifest)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Frozen post-review acquisition for CODEX-EXP-005-P0.")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--acknowledge-post-freeze-acquisition", action="store_true")
    args = parser.parse_args(argv)
    if not args.acknowledge_post_freeze_acquisition:
        raise ResearchSealError("post-freeze acquisition acknowledgement is required")
    result = run(args.workspace, args.frozen_commit, args.output_root, args.manifest)
    print(json.dumps({"experiment_id": result["experiment_id"], "files": result["file_count"], "manifest": str(args.manifest)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
