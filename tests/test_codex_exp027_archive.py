import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import multimarket.codex_exp027_archive as archive
from multimarket.codex_exp025_collect import CollectorIdentity


DAY = date(2026, 1, 2)
COMMIT = "3" * 40


class FakeVerifier:
    def __init__(self, *, fail_key: str | None = None):
        self.fail_key = fail_key
        self.calls: list[tuple[str, int, str]] = []

    def verify_existing(
        self,
        key: str,
        expected_bytes: int,
        expected_sha256: str,
    ):
        self.calls.append((key, expected_bytes, expected_sha256))
        if key == self.fail_key:
            raise RuntimeError("synthetic remote verification failure")
        return {
            "key": key,
            "bytes": expected_bytes,
            "sha256": expected_sha256,
        }


def identity(*, armed_before: bool) -> CollectorIdentity:
    start = datetime(DAY.year, DAY.month, DAY.day, tzinfo=timezone.utc)
    started = start - timedelta(hours=1) if armed_before else start + timedelta(hours=3)
    wall_ns = int(started.timestamp() * 1_000_000_000)
    return CollectorIdentity(
        collector_run_id="synthetic-run",
        process_id=123,
        frozen_implementation_commit=COMMIT,
        collector_started_wall_ns=wall_ns,
        collector_started_utc=started.isoformat(),
    )


def write_hourly(
    root: Path,
    *,
    symbol: str,
    hour_index: int,
    ident: CollectorIdentity,
    digest: str | None = None,
    bytes_: int = 100,
):
    hour = datetime(
        DAY.year,
        DAY.month,
        DAY.day,
        hour_index,
        tzinfo=timezone.utc,
    )
    sha = digest or ("%064x" % (hour_index + 1))
    path = archive.hourly_manifest_path(root, symbol, hour)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment_id": archive.EXPERIMENT_ID,
        "status": "HOURLY_RAW_ARCHIVE_VERIFIED",
        "symbol": symbol,
        "collection_hour_utc": hour.isoformat(),
        "archive_key": archive.expected_archive_key(symbol, hour),
        "local_bytes": bytes_,
        "local_sha256": sha,
        "remote_bytes": bytes_,
        "remote_sha256": sha,
        "frozen_implementation_commit": ident.frozen_implementation_commit,
        "collector_run_id": ident.collector_run_id,
        "archived_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(
        {
            name: False
            for name in (
                "older_august_holdout_opened",
                "historical_aug1_feature_reparsed",
                "features_constructed",
                "target_scored",
                "model_fit",
                "auc_scored",
                "ap_scored",
                "direction_scored",
                "pnl_scored",
                "leverage_scored",
                "automatic_holdout_scoring",
            )
        }
    )
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, sha


class Exp027DailyManifestTests(unittest.TestCase):
    def test_24_verified_chunks_make_full_day_ready(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ident = identity(armed_before=True)
            verifier = FakeVerifier()
            for h in range(24):
                write_hourly(root, symbol="BTCUSDT", hour_index=h, ident=ident)
            payload = archive.finalize_daily_archive_manifest(
                root,
                verifier,
                symbol="BTCUSDT",
                day=DAY,
                identity=ident,
            )
            self.assertEqual(payload["status"], archive.FULL_DAY_STATUS)
            self.assertEqual(payload["verified_hour_count"], 24)
            self.assertEqual(payload["missing_hours"], [])
            self.assertEqual(len(verifier.calls), 24)

    def test_missing_hour_rejected_for_armed_full_day(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ident = identity(armed_before=True)
            verifier = FakeVerifier()
            for h in range(24):
                if h == 7:
                    continue
                write_hourly(root, symbol="ETHUSDT", hour_index=h, ident=ident)
            with self.assertRaises(archive.DailyArchiveIntegrityError):
                archive.finalize_daily_archive_manifest(
                    root,
                    verifier,
                    symbol="ETHUSDT",
                    day=DAY,
                    identity=ident,
                )

    def test_partial_start_day_is_not_full(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ident = identity(armed_before=False)
            verifier = FakeVerifier()
            for h in range(3, 24):
                write_hourly(root, symbol="SOLUSDT", hour_index=h, ident=ident)
            payload = archive.finalize_daily_archive_manifest(
                root,
                verifier,
                symbol="SOLUSDT",
                day=DAY,
                identity=ident,
            )
            self.assertEqual(payload["status"], archive.PARTIAL_DAY_STATUS)
            self.assertNotEqual(payload["verified_hour_count"], 24)

    def test_remote_verification_is_required(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ident = identity(armed_before=True)
            fail_hour = datetime(
                DAY.year, DAY.month, DAY.day, 4, tzinfo=timezone.utc
            )
            fail_key = archive.expected_archive_key("BTCUSDT", fail_hour)
            verifier = FakeVerifier(fail_key=fail_key)
            for h in range(24):
                write_hourly(root, symbol="BTCUSDT", hour_index=h, ident=ident)
            with self.assertRaises(RuntimeError):
                archive.finalize_daily_archive_manifest(
                    root,
                    verifier,
                    symbol="BTCUSDT",
                    day=DAY,
                    identity=ident,
                )

    def test_hourly_sha_mismatch_rejected_before_day_ready(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ident = identity(armed_before=True)
            verifier = FakeVerifier()
            for h in range(24):
                path, _ = write_hourly(
                    root,
                    symbol="BTCUSDT",
                    hour_index=h,
                    ident=ident,
                )
                if h == 12:
                    payload = json.loads(path.read_text())
                    payload["remote_sha256"] = "f" * 64
                    path.write_text(json.dumps(payload))
            with self.assertRaises(archive.DailyArchiveIntegrityError):
                archive.finalize_daily_archive_manifest(
                    root,
                    verifier,
                    symbol="BTCUSDT",
                    day=DAY,
                    identity=ident,
                )

    def test_failure_marker_prevents_ready_status(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ident = identity(armed_before=True)
            verifier = FakeVerifier()
            for h in range(24):
                write_hourly(root, symbol="BTCUSDT", hour_index=h, ident=ident)
            failure_dir = archive.failure_root(root, "BTCUSDT", DAY)
            failure_dir.mkdir(parents=True, exist_ok=True)
            (failure_dir / "05.operational-failure.json").write_text("{}")
            payload = archive.finalize_daily_archive_manifest(
                root,
                verifier,
                symbol="BTCUSDT",
                day=DAY,
                identity=ident,
            )
            self.assertEqual(payload["status"], archive.FAIL_STATUS)


if __name__ == "__main__":
    unittest.main()
