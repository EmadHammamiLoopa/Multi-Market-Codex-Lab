from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from multimarket import dev045_d6r8ed_semantic_real_parity_contract as c
from multimarket import dev045_d6r8ef_semantic_real_parity_runner as r


class TestD6R8EFSemanticRealParityRunner(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
