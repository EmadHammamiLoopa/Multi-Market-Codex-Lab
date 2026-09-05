from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from multimarket import dev045_d6r8ed_semantic_real_parity_contract as c
from multimarket import dev045_d6r8ef_semantic_real_parity_runner as fixed
from multimarket import dev045_d6r8eg_semantic_real_parity_successor as r


class TestD6R8EGSemanticRealParitySuccessor(unittest.TestCase):
    def test_successor_is_distinct_and_one_shot_env_is_mandatory(self) -> None:
        self.assertEqual(r.EXPERIMENT_ID, "DEV045-D6R8EG")
        self.assertTrue(r.EXECUTION_AUTHORIZED)
        self.assertEqual(r.FIX_HEAD, "eb0762ca4b3b69fd8966e20ee51d213ea5fcd301")
        self.assertIn("dev045_d6r8eg", str(r.RUNTIME_ROOT))
        self.assertIn("d6r8eg", str(r.DEFAULT_EVIDENCE))
        old = os.environ.pop("DEV045_D6R8EG_AUTHORIZE", None)
        try:
            with tempfile.TemporaryDirectory() as td:
                with self.assertRaisesRegex(r.D6R8EGError, "real_execution_not_authorized"):
                    r.run(Path(td) / "evidence.json")
        finally:
            if old is not None:
                os.environ["DEV045_D6R8EG_AUTHORIZE"] = old

    def test_d6r8ef_frozen_identity_is_bound_not_reused(self) -> None:
        self.assertEqual(r.D6R8EF_MARKER_SHA256, "f022ee78ce82f84a1d7e1fcfff376ff1fbdea988f2be3f79ef2f8886a0944cb6")
        self.assertEqual(r.D6R8EF_EVIDENCE_SHA256, "4d42e51c91bc5950848c14e7f41ca576e5f64749fd512015f485cd14835d164f")
        self.assertNotEqual(r.ATTEMPT_MARKER, r.D6R8EF_MARKER)
        self.assertNotEqual(r.DEFAULT_EVIDENCE, r.D6R8EF_EVIDENCE)

    def test_fixed_upstream_capacity_is_exactly_inherited(self) -> None:
        sizes = fixed._upstream_buffer_sizes()
        self.assertEqual(sizes.event_rows, 496_256)
        self.assertEqual(sizes.snapshot_rows, 1_024)
        self.assertEqual(r._child_convert.__module__, "multimarket.dev045_d6r8eg_semantic_real_parity_successor")

    def test_semantic_and_converter_contract_remains_exact(self) -> None:
        self.assertEqual(c.TRADE_SEMANTIC_ROWS, 13_073)
        self.assertEqual(c.DEPTH_SEMANTIC_ROWS, 483_149)
        self.assertEqual(c.TRADE_DECOMPRESSED_SHA256, "cb6a1d37e4422fa99e563969b3750487a3ca3d01956a45973085f26352a220fe")
        self.assertEqual(c.DEPTH_DECOMPRESSED_SHA256, "5c5d8de09c1a38083f151f632fce568fb80b9df1485f5688d2dab20431869f93")
        self.assertFalse(c.COMPRESSED_GZIP_SHA_IS_PARITY_GATE)
        self.assertEqual(c.PARITY_MODE, "FIELDWISE_EXACT_NAN_EQUAL")
        self.assertEqual(c.PARITY_ITEMSIZE_REQUIRED, 64)
        self.assertEqual(c.CONVERTER_EXECUTION_ORDER, ("upstream_oracle", "old_converter", "v2_converter"))

    def test_child_failure_diagnostics_are_persisted_before_raise(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["python"],
            returncode=1,
            stdout="progress\n",
            stderr="traceback\n" * 1000,
        )
        evidence: dict[str, object] = {}
        with mock.patch.object(r.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(r.D6R8EGError, "upstream_return_code:1"):
                r._execute_child("upstream", evidence)
        self.assertEqual(evidence["upstream_return_code"], 1)
        self.assertEqual(evidence["upstream_stdout_sha256"], hashlib.sha256(completed.stdout.encode()).hexdigest())
        self.assertEqual(evidence["upstream_stderr_sha256"], hashlib.sha256(completed.stderr.encode()).hexdigest())
        self.assertLessEqual(len(str(evidence["upstream_stderr_tail"])), r.CHILD_DIAGNOSTIC_TAIL_CHARS)

    def test_success_child_parses_last_json_line_after_progress(self) -> None:
        payload = {"rows": 503934, "itemsize": 64}
        stdout = "Reading trades\nCorrecting latency\n" + json.dumps(payload) + "\n"
        completed = subprocess.CompletedProcess(args=["python"], returncode=0, stdout=stdout, stderr="")
        evidence: dict[str, object] = {}
        with mock.patch.object(r.subprocess, "run", return_value=completed):
            actual = r._execute_child("upstream", evidence)
        self.assertEqual(actual["rows"], 503934)
        self.assertEqual(actual["itemsize"], 64)
        self.assertEqual(evidence["upstream_return_code"], 0)

    def test_later_surfaces_remain_closed(self) -> None:
        self.assertFalse(c.JAN_FULL_DAY_OPEN_AUTHORIZED)
        self.assertFalse(c.RAW_FEB_TO_JUL_OPEN_AUTHORIZED)
        self.assertFalse(c.HISTORICAL_PNL_AUTHORIZED)
        self.assertFalse(c.AUG_OPEN_AUTHORIZED)
        self.assertFalse(c.SEP_PLUS_OPEN_AUTHORIZED)
        self.assertFalse(c.NON_BTC_OPEN_AUTHORIZED)
        self.assertFalse(c.RAILWAY_AUTHORIZED)
        self.assertFalse(c.LIVE_TRADING_AUTHORIZED)


if __name__ == "__main__":
    unittest.main()
