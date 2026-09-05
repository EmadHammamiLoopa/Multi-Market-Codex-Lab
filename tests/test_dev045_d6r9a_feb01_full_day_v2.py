from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from multimarket import dev045_d6r8_structurally_bounded_converter as v2
from multimarket import dev045_d6r8c_bounded_converter_redesign_contract as rc
from multimarket import dev045_d6r9a_feb01_full_day_v2 as r


class TestD6R9AFeb01FullDayV2(unittest.TestCase):
    def test_frozen_new_day_raw_provenance(self) -> None:
        self.assertEqual(r.DAY, "2026-02-01")
        self.assertEqual(r.TRADE_RAW_BYTES, 57_631_972)
        self.assertEqual(r.TRADE_RAW_SHA256, "dfd19ab53abbc90118ce3c861521ecb17dbed6ce7bcc7410c07f296460454508")
        self.assertEqual(r.DEPTH_RAW_BYTES, 865_907_076)
        self.assertEqual(r.DEPTH_RAW_SHA256, "a1e9fc0fcc20d309d171ed1b6367ebe17948c84dd025a07a5d13c80f0b023cc4")
        self.assertEqual(r.FROZEN_RAW_ROWS, 172_721_707)

    def test_resource_gate_is_exactly_inherited(self) -> None:
        self.assertEqual(rc.required_scratch_bytes(r.FROZEN_RAW_ROWS), 127_721_761_664)
        self.assertEqual(r.REQUIRED_SCRATCH_BYTES, 127_721_761_664)
        self.assertEqual(rc.MIN_MEMAVAILABLE_BYTES, 8 * 1024**3)
        self.assertEqual(rc.RUNTIME_RSS_ABORT_BYTES, 6 * 1024**3)
        self.assertEqual(v2.PRODUCTION_INITIAL_CHUNK_ROWS, 250_000)
        self.assertEqual(v2.MERGE_FAN_IN, 8)

    def test_successor_is_one_shot_and_distinct(self) -> None:
        self.assertEqual(r.EXPERIMENT_ID, "DEV045-D6R9A")
        self.assertTrue(r.EXECUTION_AUTHORIZED)
        self.assertIn("dev045_d6r9a", str(r.RUNTIME_ROOT))
        self.assertIn("d6r9a", str(r.DEFAULT_EVIDENCE))
        self.assertNotEqual(r.ATTEMPT_MARKER, r.D6R8EG_MARKER)
        self.assertNotEqual(r.DEFAULT_EVIDENCE, r.D6R8EG_EVIDENCE)
        old = os.environ.pop("DEV045_D6R9A_AUTHORIZE", None)
        try:
            with tempfile.TemporaryDirectory() as td:
                with self.assertRaisesRegex(r.D6R9AError, "real_execution_not_authorized"):
                    r.run(Path(td) / "evidence.json")
        finally:
            if old is not None:
                os.environ["DEV045_D6R9A_AUTHORIZE"] = old

    def test_d6r8eg_frozen_pass_hashes_are_bound(self) -> None:
        self.assertEqual(r.D6R8EG_MARKER_SHA256, "ccbf010be8a0493da30e22a8c51bbc98961bd5d11635eadd2a8403f4d7ada95f")
        self.assertEqual(r.D6R8EG_EVIDENCE_SHA256, "c912e7a8233995aed3abfd4d911e35b10097f46e434f56502f09dbb41a5806b9")
        self.assertEqual(r.D6R8EG_OUTPUT_SHA256, "60ebc2aec273976c12526f7c49159d005368388a0f9d5993af269cc9753ffaf7")

    def test_full_day_runner_never_loads_whole_output(self) -> None:
        source = Path(r.__file__).read_text(encoding="utf-8")
        self.assertNotIn("np.load(", source)
        self.assertNotIn("mmap_mode", source)
        self.assertNotIn("dev045_d6r_bounded_converter", source)
        self.assertNotIn("hftbacktest.data.utils.tardis", source)

    def test_failed_v2_child_diagnostics_are_bounded_and_persisted(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["python"],
            returncode=1,
            stdout="progress\n",
            stderr="traceback\n" * 2000,
        )
        evidence: dict[str, object] = {}
        with mock.patch.object(r.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(r.D6R9AError, "v2_return_code:1"):
                r._execute_child(evidence)
        self.assertEqual(evidence["v2_return_code"], 1)
        self.assertEqual(evidence["v2_stdout_sha256"], hashlib.sha256(completed.stdout.encode()).hexdigest())
        self.assertEqual(evidence["v2_stderr_sha256"], hashlib.sha256(completed.stderr.encode()).hexdigest())
        self.assertLessEqual(len(str(evidence["v2_stderr_tail"])), r.CHILD_DIAGNOSTIC_TAIL_CHARS)

    def test_successful_child_parses_final_json_line(self) -> None:
        payload = {
            "base_event_rows": 10,
            "final_event_rows": 12,
            "initial_sort_runs": 2,
            "exchange_merge_levels": 1,
            "local_merge_levels": 1,
            "chunk_rows": 250000,
            "output_sha256": "abc",
            "peak_rss_bytes": 123,
        }
        completed = subprocess.CompletedProcess(
            args=["python"], returncode=0, stdout="progress\n" + json.dumps(payload) + "\n", stderr=""
        )
        evidence: dict[str, object] = {}
        with mock.patch.object(r.subprocess, "run", return_value=completed):
            actual = r._execute_child(evidence)
        self.assertEqual(actual, payload)
        self.assertEqual(evidence["v2_return_code"], 0)


if __name__ == "__main__":
    unittest.main()
