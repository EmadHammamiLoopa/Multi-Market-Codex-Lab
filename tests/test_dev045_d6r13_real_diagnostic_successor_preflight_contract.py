from __future__ import annotations

import unittest

from multimarket import dev045_d6r13_real_diagnostic_successor_preflight_contract as c


class TestD6R13SuccessorPreflightContract(unittest.TestCase):
    def test_frozen_lineage_and_memory_semantics(self):
        self.assertEqual(c.PARENT_FREEZE_HEAD, "4e27c8f9b9403bffcdc866e83ef7b3e79e03ee28")
        self.assertEqual(c.D6R13_DESIGN_HEAD, "7a7e5f00501dec5f808a9b71ac350e3e6946f26f")
        self.assertIs(c.D6R12_RERUN_FORBIDDEN, True)
        self.assertEqual(c.BOUNDED_WAKEUP_TARGET, 7_500_000)
        self.assertEqual(c.WAKEUP_CAPTURE_INTERVAL, 250_000)
        self.assertEqual(c.PREEXEC_MIN_MEMAVAILABLE_BYTES, 8_442_945_536)
        self.assertIsNone(c.RUNTIME_MEMAVAILABLE_ABORT_THRESHOLD_BYTES)
        self.assertIsNone(c.TOTAL_RSS_ABORT_THRESHOLD_BYTES)
        self.assertIsNone(c.ANONYMOUS_RSS_ABORT_THRESHOLD_BYTES)
        self.assertIs(c.RUNTIME_ABORT_ON_PROCESS_SWAP_GROWTH, True)

    def test_launcher_and_authorization_are_frozen_but_execution_disabled(self):
        self.assertEqual(c.CHILD_MODULE_NAME, "multimarket.dev045_d6r13_child_launch_successor")
        self.assertEqual(c.AUTHORIZATION_ENV, "DEV045_D6R13_AUTHORIZE")
        self.assertEqual(c.AUTHORIZATION_TOKEN, "YES_FEB01_BOUNDED_MEMORY_DIAGNOSTIC_SUCCESSOR")
        self.assertIs(c.REAL_EXECUTION_ENABLED, False)
        self.assertEqual(c.PROHIBITED_EXECUTION_FLAGS, (False,) * len(c.PROHIBITED_EXECUTION_FLAGS))


if __name__ == "__main__":
    unittest.main()
