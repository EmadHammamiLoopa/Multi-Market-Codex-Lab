from __future__ import annotations

import inspect
import unittest

from multimarket import dev045_d6r13_real_diagnostic_execution as execution
from multimarket import dev045_d6r13_real_diagnostic_execution_contract as c


class TestD6R13RealDiagnosticExecutionDesign(unittest.TestCase):
    def test_contract_remains_closed(self):
        self.assertIs(c.REAL_EXECUTION_ENABLED, False)
        self.assertEqual(c.PROHIBITED_EXECUTION_FLAGS, (False,) * len(c.PROHIBITED_EXECUTION_FLAGS))
        self.assertIs(c.D6R12_RERUN_FORBIDDEN, True)
        self.assertIs(c.D6R12_DIAGNOSTIC_QUESTION_ANSWERED, False)

    def test_child_command_uses_fixed_module_name(self):
        command = execution.child_command(smoke=False)
        self.assertEqual(command[1:3], ["-m", c.CHILD_MODULE_NAME])
        self.assertNotIn("__main__", command)
        self.assertEqual(command[-1], c.CHILD_FLAG)

    def test_smoke_command_uses_same_fixed_module_name(self):
        command = execution.child_command(smoke=True)
        self.assertEqual(command[1:3], ["-m", c.CHILD_MODULE_NAME])
        self.assertNotIn("__main__", command)
        self.assertEqual(command[-1], c.CHILD_RESOLUTION_SMOKE_FLAG)

    def test_module_level_child_resolution_smoke(self):
        result = execution.run_child_resolution_smoke()
        self.assertEqual(result.returncode, 0)
        payload = result.payload
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["runtime_name"], "__main__")
        self.assertEqual(payload["resolved_module_name"], c.CHILD_MODULE_NAME)
        self.assertFalse(payload["canonical_data_opened"])
        self.assertFalse(payload["attempt_marker_created"])
        self.assertFalse(payload["heartbeat_created"])
        self.assertFalse(payload["hftbacktest_canonical_run"])
        self.assertFalse(payload["real_execution_enabled"])

    def test_authorization_cannot_open_execution_in_design_stage(self):
        with self.assertRaisesRegex(execution.D6R13ExecutionDesignError, "authorization_token"):
            execution.require_execution_authorization({})
        with self.assertRaisesRegex(execution.D6R13ExecutionDesignError, "execution_disabled_by_contract"):
            execution.require_execution_authorization({c.AUTHORIZATION_ENV: c.AUTHORIZATION_TOKEN})

    def test_design_stage_has_no_canonical_open_or_hftbacktest_binding(self):
        source = inspect.getsource(execution)
        self.assertNotIn("_open_verified_file", source)
        self.assertNotIn("_build_lifetime_safe_binding", source)
        self.assertNotIn("wait_next_feed", source)
        self.assertNotIn("MEMORY_HEARTBEAT_PATH.write", source)
        self.assertNotIn("ATTEMPT_MARKER_PATH", source)


if __name__ == "__main__":
    unittest.main()
