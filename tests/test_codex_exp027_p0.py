import asyncio
import gzip
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import multimarket.codex_exp027_collect as collect
from multimarket.codex_exp025_collect import CollectorIdentity


TEST_COMMIT = "2" * 40
TEST_HOUR = datetime(2026, 1, 2, 3, tzinfo=timezone.utc)


def _identity() -> CollectorIdentity:
    start = int((TEST_HOUR - timedelta(hours=2)).timestamp() * 1_000_000_000)
    return CollectorIdentity(
        collector_run_id="synthetic-exp027",
        process_id=123,
        frozen_implementation_commit=TEST_COMMIT,
        collector_started_wall_ns=start,
        collector_started_utc=collect._iso_from_ns(start),
    )


class FakeArchive:
    def __init__(self, fail_symbol: str | None = None):
        self.fail_symbol = fail_symbol
        self.uploads: dict[str, bytes] = {}

    def put_verified(
        self, path: Path, key: str
    ) -> collect.ArchiveVerification:
        if self.fail_symbol and f"/{self.fail_symbol}/" in f"/{key}":
            raise collect.ArchiveOperationalError("synthetic upload failure")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        self.uploads[key] = data
        return collect.ArchiveVerification(
            key=key,
            byte_size=len(data),
            sha256=digest,
            remote_byte_size=len(data),
            remote_sha256=digest,
        )


class Exp027PureFunctionTests(unittest.TestCase):
    def test_exact_symbols_and_hourly_paths(self):
        self.assertEqual(
            collect.INITIAL_SYMBOLS,
            ("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        )
        self.assertEqual(
            collect.staging_path(Path("/data"), "BTCUSDT", TEST_HOUR),
            Path("/data/staging/bookticker/BTCUSDT/2026-01-02/03.jsonl.gz"),
        )
        self.assertEqual(
            collect.archive_key("ETHUSDT", TEST_HOUR),
            "bookticker/ETHUSDT/2026-01-02/03.jsonl.gz",
        )

    def test_hour_alignment_is_strict(self):
        with self.assertRaises(ValueError):
            collect.archive_key(
                "BTCUSDT",
                TEST_HOUR.replace(minute=1),
            )
        with self.assertRaises(ValueError):
            collect.archive_key(
                "BTCUSDT",
                TEST_HOUR.replace(tzinfo=None),
            )

    def test_floor_utc_hour(self):
        ns = int(
            TEST_HOUR.replace(minute=47, second=12).timestamp()
            * 1_000_000_000
        )
        self.assertEqual(collect.floor_utc_hour_from_ns(ns), TEST_HOUR)

    def test_archive_config_accepts_railway_native_variables(self):
        env = {
            "ENDPOINT": "https://storage.railway.app",
            "ACCESS_KEY_ID": "key",
            "SECRET_ACCESS_KEY": "secret",
            "BUCKET": "global-bucket",
            "REGION": "auto",
        }
        with mock.patch.dict("os.environ", env, clear=True):
            cfg = collect.ArchiveConfig.from_env()
        self.assertEqual(cfg.endpoint, env["ENDPOINT"])
        self.assertEqual(cfg.bucket, env["BUCKET"])
        self.assertEqual(cfg.region, "auto")
        self.assertEqual(cfg.url_style, "virtual")

    def test_archive_config_accepts_aws_style_variables(self):
        env = {
            "AWS_ENDPOINT_URL": "https://storage.railway.app",
            "AWS_ACCESS_KEY_ID": "key",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "AWS_S3_BUCKET_NAME": "global-bucket",
            "AWS_DEFAULT_REGION": "auto",
            "AWS_S3_URL_STYLE": "path",
        }
        with mock.patch.dict("os.environ", env, clear=True):
            cfg = collect.ArchiveConfig.from_env()
        self.assertEqual(cfg.bucket, "global-bucket")
        self.assertEqual(cfg.url_style, "path")

    def test_no_analysis_guards_are_false(self):
        guards = collect.no_analysis_guards()
        self.assertTrue(guards)
        self.assertTrue(all(value is False for value in guards.values()))


class Exp027ArchiveBankTests(unittest.TestCase):
    def _wall_ns(self, hour: datetime = TEST_HOUR) -> int:
        return int(hour.timestamp() * 1_000_000_000)

    def _quote(self, symbol: str, seq: int) -> dict:
        return {
            "record_type": "quote",
            "symbol": symbol,
            "market": collect.MARKET,
            "venue": collect.VENUE,
            "asset_class": collect.ASSET_CLASS,
            "connection_epoch": 1,
            "receive_wall_ns": self._wall_ns() + seq,
            "receive_timestamp_utc": collect._iso_from_ns(
                self._wall_ns() + seq
            ),
            "receive_monotonic_ns": 100 + seq,
            "bid": 100.0,
            "ask": 100.1,
            "bid_size": 1.0,
            "ask_size": 1.0,
            "best_bid": 100.0,
            "best_ask": 100.1,
            "best_bid_qty": 1.0,
            "best_ask_qty": 1.0,
        }

    def test_successful_archive_verification_creates_manifests_then_deletes_local(self):
        async def scenario(root: Path):
            archive = FakeArchive()
            bank = collect.AsyncHourlyArchiveBank(root, _identity(), archive)
            await bank.open_hour(
                TEST_HOUR,
                wall_ns=self._wall_ns(),
                mono_ns=100,
                active_epoch=1,
            )
            for i, symbol in enumerate(collect.INITIAL_SYMBOLS, 1):
                bank.emit(symbol, self._quote(symbol, i))
            verified = await bank.close_archive_and_delete()
            self.assertEqual(set(verified), set(collect.INITIAL_SYMBOLS))
            self.assertEqual(len(archive.uploads), 3)
            for symbol in collect.INITIAL_SYMBOLS:
                raw = collect.staging_path(root, symbol, TEST_HOUR)
                manifest = collect.manifest_path(root, symbol, TEST_HOUR)
                self.assertFalse(raw.exists())
                self.assertTrue(manifest.exists())
                payload = json.loads(manifest.read_text())
                self.assertEqual(
                    payload["status"],
                    "HOURLY_RAW_ARCHIVE_VERIFIED",
                )
                self.assertEqual(payload["symbol"], symbol)
                self.assertFalse(payload["model_fit"])
                self.assertFalse(payload["target_scored"])
                self.assertFalse(payload["pnl_scored"])

        with tempfile.TemporaryDirectory() as td:
            asyncio.run(scenario(Path(td)))

    def test_upload_failure_preserves_all_local_chunks_and_marks_failure(self):
        async def scenario(root: Path):
            archive = FakeArchive(fail_symbol="ETHUSDT")
            bank = collect.AsyncHourlyArchiveBank(root, _identity(), archive)
            await bank.open_hour(
                TEST_HOUR,
                wall_ns=self._wall_ns(),
                mono_ns=100,
                active_epoch=1,
            )
            for i, symbol in enumerate(collect.INITIAL_SYMBOLS, 1):
                bank.emit(symbol, self._quote(symbol, i))
            with self.assertRaises(collect.ArchiveOperationalError):
                await bank.close_archive_and_delete()
            for symbol in collect.INITIAL_SYMBOLS:
                self.assertTrue(
                    collect.staging_path(root, symbol, TEST_HOUR).exists()
                )
                self.assertTrue(
                    collect.operational_failure_path(
                        root, symbol, TEST_HOUR
                    ).exists()
                )
                self.assertFalse(
                    collect.manifest_path(root, symbol, TEST_HOUR).exists()
                )

        with tempfile.TemporaryDirectory() as td:
            asyncio.run(scenario(Path(td)))

    def test_shutdown_preserves_active_partial_hour_and_never_uploads_it(self):
        async def scenario(root: Path):
            archive = FakeArchive()
            bank = collect.AsyncHourlyArchiveBank(root, _identity(), archive)
            await bank.open_hour(
                TEST_HOUR,
                wall_ns=self._wall_ns(),
                mono_ns=100,
                active_epoch=1,
            )
            for i, symbol in enumerate(collect.INITIAL_SYMBOLS, 1):
                bank.emit(symbol, self._quote(symbol, i))
            await bank.close_without_archive()
            self.assertEqual(archive.uploads, {})
            for symbol in collect.INITIAL_SYMBOLS:
                raw = collect.staging_path(root, symbol, TEST_HOUR)
                self.assertTrue(raw.exists())
                self.assertFalse(
                    collect.manifest_path(root, symbol, TEST_HOUR).exists()
                )
                with gzip.open(raw, "rt", encoding="utf-8") as handle:
                    records = [json.loads(line) for line in handle]
                self.assertGreaterEqual(len(records), 2)

        with tempfile.TemporaryDirectory() as td:
            asyncio.run(scenario(Path(td)))

    def test_rollover_requires_exact_next_hour(self):
        async def scenario(root: Path):
            archive = FakeArchive()
            bank = collect.AsyncHourlyArchiveBank(root, _identity(), archive)
            await bank.open_hour(
                TEST_HOUR,
                wall_ns=self._wall_ns(),
                mono_ns=100,
                active_epoch=1,
            )
            with self.assertRaises(RuntimeError):
                await bank.rollover(
                    TEST_HOUR + timedelta(hours=2),
                    wall_ns=self._wall_ns(TEST_HOUR + timedelta(hours=2)),
                    mono_ns=200,
                    active_epoch=1,
                )
            await bank.close_without_archive()

        with tempfile.TemporaryDirectory() as td:
            asyncio.run(scenario(Path(td)))

    def test_rollover_archives_completed_hour_and_opens_next(self):
        async def scenario(root: Path):
            archive = FakeArchive()
            bank = collect.AsyncHourlyArchiveBank(root, _identity(), archive)
            await bank.open_hour(
                TEST_HOUR,
                wall_ns=self._wall_ns(),
                mono_ns=100,
                active_epoch=1,
            )
            for i, symbol in enumerate(collect.INITIAL_SYMBOLS, 1):
                bank.emit(symbol, self._quote(symbol, i))
            next_hour = TEST_HOUR + timedelta(hours=1)
            verified = await bank.rollover(
                next_hour,
                wall_ns=self._wall_ns(next_hour),
                mono_ns=200,
                active_epoch=1,
            )
            self.assertEqual(set(verified), set(collect.INITIAL_SYMBOLS))
            self.assertEqual(bank.current_hour, next_hour)
            for symbol in collect.INITIAL_SYMBOLS:
                self.assertTrue(
                    collect.staging_path(root, symbol, next_hour).exists()
                )
                self.assertFalse(
                    collect.staging_path(root, symbol, TEST_HOUR).exists()
                )
            await bank.close_without_archive()

        with tempfile.TemporaryDirectory() as td:
            asyncio.run(scenario(Path(td)))


if __name__ == "__main__":
    unittest.main()
