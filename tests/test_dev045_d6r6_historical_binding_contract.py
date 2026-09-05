from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
import subprocess
import unittest

import numpy as np

from multimarket import dev045_d6r5_memmap_adapter as adapter
from multimarket import dev045_d6r6_historical_binding_contract as c


ROOT = Path(__file__).resolve().parents[1]


def _git_blob(path: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / path)],
        cwd=ROOT,
        text=True,
    ).strip()


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with (ROOT / path).open("rb") as fh:
        while True:
            block = fh.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


class TestDev045D6R6HistoricalBindingContract(unittest.TestCase):
    def test_parent_and_d6r5c_identity_are_exact(self):
        self.assertEqual(
            c.PARENT_HEAD,
            "4be133e52d8392da1e91fce4b72fc69995545c58",
        )
        self.assertEqual(c.D6R5C_STATUS, "PASS")
        self.assertEqual(c.D6R5C_CANONICAL_ATTEMPT, 1)
        self.assertEqual(c.D6R5C_OBSERVED_ROWS, 64_314_723)
        self.assertEqual(c.D6R5C_OBSERVED_CHUNKS, 129)
        self.assertEqual(
            _sha256(c.D6R5C_EVIDENCE_PATH),
            c.D6R5C_EVIDENCE_SHA256,
        )

    def test_frozen_local_source_identities_are_exact(self):
        pairs = (
            (
                c.HISTORICAL_ORCHESTRATION_PATH,
                c.HISTORICAL_ORCHESTRATION_GIT_BLOB,
            ),
            (
                c.EVENT_LOOP_KERNEL_PATH,
                c.EVENT_LOOP_KERNEL_GIT_BLOB,
            ),
            (
                c.MEMMAP_ADAPTER_PATH,
                c.MEMMAP_ADAPTER_GIT_BLOB,
            ),
            (
                c.MEMMAP_CONTRACT_PATH,
                c.MEMMAP_CONTRACT_GIT_BLOB,
            ),
        )

        for path, expected in pairs:
            self.assertEqual(_git_blob(path), expected)

    def test_public_memmap_entrypoint_is_canonical_only(self):
        self.assertTrue(issubclass(np.memmap, np.ndarray))
        self.assertEqual(
            len(inspect.signature(adapter.open_canonical_jan).parameters),
            0,
        )
        self.assertEqual(c.SOURCE_PUBLIC_PATH_ARGUMENT_COUNT, 0)
        self.assertEqual(c.SOURCE_MMAP_MODE, "r")
        self.assertIs(c.SOURCE_ALLOW_PICKLE, False)
        self.assertEqual(c.DAY, "2026-01-01")
        self.assertEqual(c.SYMBOL, "BTCUSDT")
        self.assertEqual(c.CANONICAL_NPY_ROWS, 64_314_723)
        self.assertEqual(c.CANONICAL_NPY_BYTES, 4_116_142_528)

    def test_zero_copy_lifetime_contract_is_fail_closed(self):
        self.assertEqual(c.HFTBACKTEST_VERSION, "2.4.4")
        self.assertEqual(
            c.HFTBACKTEST_UPSTREAM_COMMIT,
            "a244a14250b42d97fc305569c93c4117cd5e1dff",
        )
        self.assertIs(c.ZERO_COPY_REGISTRATION_REQUIRED, True)
        self.assertIs(c.DATA_PTR_MANAGED_BY_HFTBACKTEST, False)
        self.assertIs(
            c.READER_DATA_CLONES_SHARE_UNDERLYING_POINTER,
            True,
        )
        self.assertIs(c.MEMMAP_OWNER_MUST_OUTLIVE_BACKTEST, True)
        self.assertIs(
            c.BACKTEST_MUST_CLOSE_BEFORE_MEMMAP_CLOSE,
            True,
        )
        self.assertIs(c.PARALLEL_LOAD, False)
        self.assertEqual(c.FEED_LATENCY_OFFSET_NS, 0)
        self.assertIs(c.FEED_PREPROCESSOR_AUTHORIZED, False)
        self.assertIs(c.FEED_DATA_MUTATION_AUTHORIZED, False)
        self.assertEqual(
            c.REQUIRED_LIFETIME_ORDER,
            (
                "open_verified_memmap",
                "build_asset_from_same_live_memmap",
                "build_backtest",
                "use_backtest_only_in_later_authorized_gate",
                "close_backtest",
                "close_memmap",
            ),
        )

    def test_existing_historical_execution_surfaces_stay_closed(self):
        orchestration = (
            ROOT / c.HISTORICAL_ORCHESTRATION_PATH
        ).read_text(encoding="utf-8")

        kernel = (
            ROOT / c.EVENT_LOOP_KERNEL_PATH
        ).read_text(encoding="utf-8")

        self.assertIn(
            "HISTORICAL_FILE_IO_ENABLED = False",
            orchestration,
        )
        self.assertIn(
            "HISTORICAL_ARENA_EXECUTION_ENABLED = False",
            orchestration,
        )
        self.assertIn(
            "CANONICAL_PNL_WRITE_ENABLED = False",
            orchestration,
        )

        self.assertIn(
            "HISTORICAL_FILE_IO_ENABLED = False",
            kernel,
        )
        self.assertIn(
            "HISTORICAL_REPLAY_EXECUTION_ENABLED = False",
            kernel,
        )
        self.assertIn("SYNTHETIC_ONLY = True", kernel)

    def test_d6r6a_and_d6r6b_dangerous_surfaces_are_closed(self):
        closed = (
            c.D6R6B_CANONICAL_JAN_OPEN_AUTHORIZED,
            c.D6R6B_CANONICAL_JAN_HFTBACKTEST_INGESTION_AUTHORIZED,
            c.D6R6B_POLICY_EXECUTION_AUTHORIZED,
            c.OPEN_RAW_CSV_AUTHORIZED,
            c.RERUN_CONVERTER_AUTHORIZED,
            c.WRITE_CANONICAL_NPY_AUTHORIZED,
            c.OTHER_DAY_OPEN_AUTHORIZED,
            c.FEB_TO_JUL_OPEN_AUTHORIZED,
            c.AUG_OPEN_AUTHORIZED,
            c.SEP_PLUS_OPEN_AUTHORIZED,
            c.NON_BTC_OPEN_AUTHORIZED,
            c.HISTORICAL_POLICY_REPLAY_AUTHORIZED,
            c.HISTORICAL_PNL_AUTHORIZED,
            c.ECONOMIC_ARENA_AUTHORIZED,
            c.CANONICAL_PNL_WRITE_AUTHORIZED,
            c.NETWORK_ACQUISITION_AUTHORIZED,
            c.RAILWAY_AUTHORIZED,
            c.LIVE_TRADING_AUTHORIZED,
            c.SORT_OR_REORDER_AUTHORIZED,
            c.WHOLE_FILE_MATERIALIZATION_AUTHORIZED,
            c.ARRAY_COPY_OR_CONCATENATION_AUTHORIZED,
        )

        self.assertTrue(all(value is False for value in closed))
        self.assertIs(
            c.D6R6B_SYNTHETIC_MEMMAP_INGESTION_AUTHORIZED_AFTER_CI,
            True,
        )


if __name__ == "__main__":
    unittest.main()
