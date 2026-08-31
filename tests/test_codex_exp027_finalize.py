import gzip
import hashlib
import json
import shutil
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import multimarket.codex_exp027_archive as archive
import multimarket.codex_exp027_finalize as finalize


DAY = date(2026, 1, 2)
SYMBOL = "BTCUSDT"


class FakeDownloadClient:
    def __init__(self, objects: dict[str, Path]):
        self.objects = objects
        self.verify_calls: list[str] = []
        self.download_calls: list[str] = []

    def verify_existing(self, key: str, expected_bytes: int, expected_sha256: str):
        path = self.objects[key]
        self.verify_calls.append(key)
        self._verify(path, expected_bytes, expected_sha256)
        return True

    def download_verified(
        self,
        key: str,
        expected_bytes: int,
        expected_sha256: str,
        destination: Path,
    ) -> Path:
        path = self.objects[key]
        self.download_calls.append(key)
        self._verify(path, expected_bytes, expected_sha256)
        shutil.copyfile(path, destination)
        return destination

    @staticmethod
    def _verify(path: Path, expected_bytes: int, expected_sha256: str) -> None:
        data = path.read_bytes()
        if len(data) != expected_bytes:
            raise RuntimeError("synthetic size mismatch")
        if hashlib.sha256(data).hexdigest() != expected_sha256:
            raise RuntimeError("synthetic sha mismatch")


def _chunk_records(hour: datetime) -> list[dict]:
    wall_ns = int(hour.timestamp() * 1_000_000_000)
    return [
        {
            "record_type": "transport",
            "event": "hour_started",
            "connection_epoch": 1,
            "receive_wall_ns": wall_ns,
            "receive_wall_utc": hour.isoformat(),
            "receive_monotonic_ns": 100,
            "collection_hour_utc": hour.isoformat(),
        },
        {
            "record_type": "quote",
            "market": "USD_M_PERPETUAL",
            "symbol": SYMBOL,
            "venue": "BINANCE_USD_M_FUTURES",
            "asset_class": "CRYPTO_PERPETUAL_FUTURES",
            "connection_epoch": 1,
            "receive_wall_ns": wall_ns,
            "receive_timestamp_utc": hour.isoformat(),
            "receive_monotonic_ns": 101,
            "best_bid": 100.0,
            "best_ask": 100.1,
            "best_bid_qty": 1.0,
            "best_ask_qty": 1.0,
            "update_id": 1,
            "exchange_event_time_ms": None,
            "exchange_transaction_time_ms": None,
        },
    ]


def build_fixture(root: Path) -> tuple[Path, dict[str, Path]]:
    manifest_root = root / "manifest-root"
    object_root = root / "objects"
    object_root.mkdir(parents=True, exist_ok=True)

    hours = []
    objects: dict[str, Path] = {}
    for index in range(24):
        hour = datetime(
            DAY.year,
            DAY.month,
            DAY.day,
            index,
            tzinfo=timezone.utc,
        )
        key = archive.expected_archive_key(SYMBOL, hour)
        path = object_root / f"{index:02d}.jsonl.gz"
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            for record in _chunk_records(hour):
                handle.write(json.dumps(record) + "\n")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        objects[key] = path
        hours.append(
            {
                "hour": hour.isoformat(),
                "archive_key": key,
                "bytes": len(data),
                "sha256": digest,
            }
        )

    day_manifest = archive.daily_manifest_path(manifest_root, SYMBOL, DAY)
    day_manifest.parent.mkdir(parents=True, exist_ok=True)
    day_manifest.write_text(
        json.dumps(
            {
                "experiment_id": archive.EXPERIMENT_ID,
                "status": archive.FULL_DAY_STATUS,
                "symbol": SYMBOL,
                "collection_day": DAY.isoformat(),
                "verified_hour_count": 24,
                "missing_hours": [],
                "rollover_observed_after_day": True,
                "hourly_archives": hours,
            }
        ),
        encoding="utf-8",
    )
    return manifest_root, objects


class Exp027ArchiveFinalizerTests(unittest.TestCase):
    def test_finalizer_verifies_all_chunks_and_builds_grid(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_root, objects = build_fixture(root)
            client = FakeDownloadClient(objects)
            output_root = root / "out"
            output_root.mkdir()
            payload = finalize.finalize_archived_day(
                output_root,
                manifest_root,
                client,
                symbol=SYMBOL,
                day=DAY,
                expected_rows=8,
            )
            self.assertEqual(payload["status"], finalize.STATUS_READY)
            self.assertEqual(payload["archive_chunks_verified"], 24)
            self.assertEqual(len(client.verify_calls), 24)
            self.assertEqual(len(client.download_calls), 24)
            self.assertTrue(Path(payload["grid_path"]).exists())
            self.assertFalse(payload["predictive_metrics_calculated"])
            self.assertFalse(payload["model_fit"])
            self.assertFalse(payload["pnl_scored"])

    def test_non_full_day_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_root, objects = build_fixture(root)
            path = archive.daily_manifest_path(manifest_root, SYMBOL, DAY)
            payload = json.loads(path.read_text())
            payload["status"] = archive.PARTIAL_DAY_STATUS
            path.write_text(json.dumps(payload))
            client = FakeDownloadClient(objects)
            output_root = root / "out"
            output_root.mkdir()
            with self.assertRaises(Exception):
                finalize.finalize_archived_day(
                    output_root,
                    manifest_root,
                    client,
                    symbol=SYMBOL,
                    day=DAY,
                    expected_rows=8,
                )

    def test_manifest_hour_order_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_root, objects = build_fixture(root)
            path = archive.daily_manifest_path(manifest_root, SYMBOL, DAY)
            payload = json.loads(path.read_text())
            payload["hourly_archives"][3], payload["hourly_archives"][4] = (
                payload["hourly_archives"][4],
                payload["hourly_archives"][3],
            )
            path.write_text(json.dumps(payload))
            client = FakeDownloadClient(objects)
            output_root = root / "out"
            output_root.mkdir()
            with self.assertRaises(Exception):
                finalize.finalize_archived_day(
                    output_root,
                    manifest_root,
                    client,
                    symbol=SYMBOL,
                    day=DAY,
                    expected_rows=8,
                )


if __name__ == "__main__":
    unittest.main()
