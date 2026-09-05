from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from multimarket import dev045_d6r8ed_semantic_real_parity_contract as c
from multimarket import dev045_d6r8ef_semantic_real_parity_runner as r


TRADE_HEADER = (
    "exchange",
    "symbol",
    "timestamp",
    "local_timestamp",
    "id",
    "side",
    "price",
    "amount",
)
DEPTH_HEADER = (
    "exchange",
    "symbol",
    "timestamp",
    "local_timestamp",
    "is_snapshot",
    "side",
    "price",
    "amount",
)


def _write_csv_gzip(
    path: Path,
    header: tuple[str, ...],
    rows: list[tuple[str, ...]],
) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


class TestD6R8EFSemanticRealParityRunner(unittest.TestCase):
    def _capacity_fixture(self, root: Path) -> tuple[Path, Path]:
        trades = root / "trades_capacity.csv.gz"
        depth = root / "incremental_book_L2_capacity.csv.gz"
        trade_rows = [
            (
                "binance-futures",
                "BTCUSDT",
                str(1_000 + index),
                str(1_000 + index),
                str(index + 1),
                "buy" if index % 2 == 0 else "sell",
                "100.0",
                "0.1",
            )
            for index in range(129)
        ]
        depth_rows = [
            (
                "binance-futures",
                "BTCUSDT",
                "2000",
                "2000",
                "true",
                "bid",
                str(99.9 - index / 10_000),
                "1.0",
            )
            for index in range(65)
        ]
        depth_rows.extend(
            (
                "binance-futures",
                "BTCUSDT",
                "2000",
                "2000",
                "true",
                "ask",
                str(100.1 + index / 10_000),
                "1.0",
            )
            for index in range(65)
        )
        depth_rows.append(
            (
                "binance-futures",
                "BTCUSDT",
                "2100",
                "2100",
                "false",
                "bid",
                "99.8",
                "2.0",
            )
        )
        _write_csv_gzip(trades, TRADE_HEADER, trade_rows)
        _write_csv_gzip(depth, DEPTH_HEADER, depth_rows)
        return trades, depth

    def test_authorization_commit_still_requires_explicit_one_shot_env(self) -> None:
        self.assertTrue(r.EXECUTION_AUTHORIZED)
        self.assertEqual(r.PREAUTHORIZATION_HEAD, "0a204b479fd7c66b54824914be408f233a53e18e")
        old = os.environ.pop("DEV045_D6R8EF_AUTHORIZE", None)
        try:
            with tempfile.TemporaryDirectory() as td:
                with self.assertRaisesRegex(r.D6R8EFError, "real_execution_not_authorized"):
                    r.run(Path(td) / "evidence.json")
        finally:
            if old is not None:
                os.environ["DEV045_D6R8EF_AUTHORIZE"] = old

    def test_runtime_and_evidence_are_new_not_d6r8eb(self) -> None:
        self.assertIn("dev045_d6r8ef", str(r.RUNTIME_ROOT))
        self.assertIn("d6r8ef", str(r.DEFAULT_EVIDENCE))
        self.assertNotIn("d6r8eb", str(r.RUNTIME_ROOT))
        self.assertNotIn("d6r8eb", str(r.DEFAULT_EVIDENCE))
        self.assertEqual(str(r.ATTEMPT_MARKER), c.SUCCESSOR_ATTEMPT_MARKER_PATH)

    def test_exact_raw_lineage_is_contract_bound(self) -> None:
        self.assertEqual(r.TRADE_RAW, Path(c.RAW_ROOT) / c.TRADE_RELATIVE_PATH)
        self.assertEqual(r.DEPTH_RAW, Path(c.RAW_ROOT) / c.DEPTH_RELATIVE_PATH)
        self.assertEqual(c.TRADE_RAW_SHA256, "e4aaee2b9f85016a5198e0cace5755dbd789c0f6f47ac0fc802c8f4b533833f6")
        self.assertEqual(c.DEPTH_RAW_SHA256, "0488a2204c9070b1e6a8769af48d54fb36e6a5658613267e2615cd3228002ded")

    def test_semantic_identity_uses_decompressed_payload_not_container_hash(self) -> None:
        self.assertFalse(c.COMPRESSED_GZIP_SHA_IS_PARITY_GATE)
        self.assertEqual(c.TRADE_DECOMPRESSED_SHA256, "cb6a1d37e4422fa99e563969b3750487a3ca3d01956a45973085f26352a220fe")
        self.assertEqual(c.DEPTH_DECOMPRESSED_SHA256, "5c5d8de09c1a38083f151f632fce568fb80b9df1485f5688d2dab20431869f93")

    def test_three_converters_and_pairwise_parity_are_frozen(self) -> None:
        self.assertEqual(c.CONVERTER_EXECUTION_ORDER, ("upstream_oracle", "old_converter", "v2_converter"))
        self.assertEqual(c.PAIRWISE_PARITY_REQUIRED, ("upstream_vs_old", "upstream_vs_v2", "old_vs_v2"))
        self.assertEqual(c.PARITY_MODE, "FIELDWISE_EXACT_NAN_EQUAL")
        self.assertEqual(c.PARITY_ITEMSIZE_REQUIRED, 64)

    def test_all_later_surfaces_remain_closed(self) -> None:
        self.assertFalse(c.JAN_FULL_DAY_OPEN_AUTHORIZED)
        self.assertFalse(c.RAW_FEB_TO_JUL_OPEN_AUTHORIZED)
        self.assertFalse(c.RUN_112_REPLAYS_AUTHORIZED)
        self.assertFalse(c.HISTORICAL_PNL_AUTHORIZED)
        self.assertFalse(c.AUG_OPEN_AUTHORIZED)
        self.assertFalse(c.SEP_PLUS_OPEN_AUTHORIZED)
        self.assertFalse(c.NON_BTC_OPEN_AUTHORIZED)
        self.assertFalse(c.RAILWAY_AUTHORIZED)
        self.assertFalse(c.LIVE_TRADING_AUTHORIZED)

    def test_source_does_not_reuse_old_attempt_marker(self) -> None:
        source = Path(r.__file__).read_text(encoding="utf-8")
        self.assertNotIn("runtime/dev045_d6r8eb", source)
        self.assertNotIn("dev045_d6r8eb_v2_real_10min_parity.json", source)

    def test_upstream_capacity_is_derived_from_frozen_slice_counts(self) -> None:
        sizes = r._upstream_buffer_sizes()
        d6r2 = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "evidence/dev045_d6r2b_real_10min_parity.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(sizes.event_rows, 496_256)
        self.assertEqual(sizes.snapshot_rows, 1_024)
        self.assertEqual(d6r2["oracle"]["buffer_size"], sizes.event_rows)
        self.assertEqual(
            d6r2["oracle"]["ss_buffer_size"], sizes.snapshot_rows
        )
        self.assertEqual(d6r2["slice"]["depth"]["max_snapshot_side_rows"], 1_002)
        self.assertGreater(sizes.event_rows, c.TRADE_SEMANTIC_ROWS)
        self.assertGreater(
            sizes.snapshot_rows,
            d6r2["slice"]["depth"]["max_snapshot_side_rows"],
        )

    def test_exact_128_row_root_cause_and_fixed_actual_upstream_path(self) -> None:
        if importlib.util.find_spec("hftbacktest") is None:
            self.skipTest("hftbacktest not installed in generic environment")
        import hftbacktest
        from hftbacktest.data.utils import tardis

        self.assertEqual(hftbacktest.__version__, "2.4.4")
        with tempfile.TemporaryDirectory() as td:
            trades, depth = self._capacity_fixture(Path(td))
            with self.assertRaisesRegex(
                ValueError,
                r"shape \(129,\) into shape \(128,\)",
            ):
                tardis.convert(
                    [str(trades), str(depth)],
                    output_filename=None,
                    buffer_size=128,
                    ss_buffer_size=64,
                    base_latency=c.UPSTREAM_BASE_LATENCY,
                    snapshot_mode=c.UPSTREAM_SNAPSHOT_MODE,
                )

            result = r._convert_upstream(trades, depth)
            self.assertEqual(len(result), 262)
            self.assertEqual(result.dtype.itemsize, 64)

    def test_failed_child_diagnostics_are_bounded_and_recorded(self) -> None:
        stderr = "prefix\n" + "traceback-line\n" * 1000
        completed = subprocess.CompletedProcess(
            args=["python"],
            returncode=1,
            stdout="child stdout\n",
            stderr=stderr,
        )
        evidence: dict[str, object] = {}
        with mock.patch.object(r.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(
                r.D6R8EFError,
                "upstream_return_code:1",
            ):
                r._execute_child("upstream", evidence)

        self.assertEqual(evidence["upstream_return_code"], 1)
        self.assertEqual(
            evidence["upstream_stdout_sha256"],
            hashlib.sha256(completed.stdout.encode()).hexdigest(),
        )
        self.assertEqual(
            evidence["upstream_stderr_sha256"],
            hashlib.sha256(completed.stderr.encode()).hexdigest(),
        )
        self.assertEqual(
            evidence["upstream_stdout_tail"], completed.stdout
        )
        self.assertEqual(
            evidence["upstream_stderr_tail"],
            completed.stderr[-r.CHILD_DIAGNOSTIC_TAIL_CHARS :],
        )
        self.assertLessEqual(
            len(str(evidence["upstream_stderr_tail"])),
            r.CHILD_DIAGNOSTIC_TAIL_CHARS,
        )

    def test_successful_upstream_progress_precedes_final_json(self) -> None:
        stdout = (
            "Reading trades.csv.gz\n"
            "Reading incremental_book_L2.csv.gz\n"
            "Correcting the latency\n"
            "Correcting the event order\n"
            '{"itemsize": 64, "rows": 262}\n'
        )
        completed = subprocess.CompletedProcess(
            args=["python"],
            returncode=0,
            stdout=stdout,
            stderr="",
        )
        evidence: dict[str, object] = {}
        with mock.patch.object(r.subprocess, "run", return_value=completed):
            payload = r._execute_child("upstream", evidence)

        self.assertEqual(payload["rows"], 262)
        self.assertEqual(payload["itemsize"], 64)
        self.assertEqual(evidence["upstream_return_code"], 0)
        self.assertEqual(evidence["upstream_stdout_tail"], stdout)


if __name__ == "__main__":
    unittest.main()
