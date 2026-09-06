from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
import unittest

from multimarket import dev045_d6r13_child_launch_successor as s
from multimarket import dev045_d6r13_child_launch_successor_contract as c


class TestD6R13ChildLaunchSuccessor(unittest.TestCase):
    def test_contract_freezes_d6r12_failure_and_blocks_real_execution(self):
        self.assertEqual(c.EXPERIMENT_ID, "DEV045-D6R13")
        self.assertEqual(
            c.PARENT_D6R12_FAILURE_FREEZE_HEAD,
            "c20854aa9fec23ba6d7d0a665ab0f1e4458782d0",
        )
        self.assertEqual(c.D6R12_FAILURE_CLASS, "CHILD_MODULE_RESOLUTION_FAILURE")
        self.assertIs(c.D6R12_RERUN_FORBIDDEN, True)
        self.assertIs(c.DIAGNOSTIC_QUESTION_ANSWERED, False)
        self.assertEqual(
            c.PROHIBITED_EXECUTION_FLAGS,
            (False,) * len(c.PROHIBITED_EXECUTION_FLAGS),
        )

    def test_child_command_uses_fixed_canonical_module_not_runtime_name(self):
        command = s.build_child_command(c.SMOKE_CHILD_FLAG)
        self.assertEqual(
            command,
            [sys.executable, "-m", c.CHILD_MODULE_NAME, c.SMOKE_CHILD_FLAG],
        )
        source = inspect.getsource(s.build_child_command)
        self.assertIn("c.CHILD_MODULE_NAME", source)
        self.assertNotIn("__name__", source)
        self.assertNotEqual(c.CHILD_MODULE_NAME, "__main__")

    def test_smoke_authorization_is_exact(self):
        with self.assertRaisesRegex(
            s.D6R13ChildLaunchError, "smoke_authorization_token"
        ):
            s.require_smoke_authorization({})
        with self.assertRaisesRegex(
            s.D6R13ChildLaunchError, "smoke_authorization_token"
        ):
            s.require_smoke_authorization({c.SMOKE_AUTH_ENV: "wrong"})
        self.assertIsNone(
            s.require_smoke_authorization(
                {c.SMOKE_AUTH_ENV: c.SMOKE_AUTH_TOKEN}
            )
        )

    def test_module_invoked_parent_resolves_real_child_module_name(self):
        completed = subprocess.run(
            [sys.executable, "-m", c.CHILD_MODULE_NAME, c.SMOKE_PARENT_FLAG],
            text=True,
            capture_output=True,
            check=False,
            env=dict(os.environ),
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        self.assertTrue(lines)
        payload = json.loads(lines[-1])
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["resolved_module_name"], c.CHILD_MODULE_NAME)
        self.assertEqual(payload["runtime_name"], "__main__")
        self.assertFalse(payload["source_content_opened"])
        self.assertFalse(payload["attempt_marker_created"])
        self.assertFalse(payload["heartbeat_created"])
        self.assertFalse(payload["hftbacktest_canonical_run"])
        self.assertFalse(payload["real_execution_enabled"])

    def test_real_child_flag_is_fail_closed(self):
        with self.assertRaisesRegex(
            s.D6R13ChildLaunchError, "real_execution_disabled_by_contract"
        ):
            s.run_real_child_disabled()

    def test_design_module_has_no_canonical_execution_dependencies(self):
        source = inspect.getsource(s)
        forbidden = (
            "dev045_d6r12_real_diagnostic_preflight",
            "import hftbacktest",
            "from hftbacktest",
            "SOURCE_PATH",
            "ATTEMPT_STARTED.json",
            "MEMORY_HEARTBEAT.json",
            "calculate_pnl",
            "submit_",
            "cancel_",
        )
        for token in forbidden:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
