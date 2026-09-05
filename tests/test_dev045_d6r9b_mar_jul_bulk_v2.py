from __future__ import annotations

from pathlib import Path
import unittest

from multimarket import dev045_d6r8_structurally_bounded_converter as v2
from multimarket import dev045_d6r8c_bounded_converter_redesign_contract as rc
from multimarket import dev045_d6r9b_mar_jul_bulk_v2 as r


class TestD6R9BMarJulBulkV2(unittest.TestCase):
    def test_frozen_day_order_and_provenance(self) -> None:
        self.assertEqual(
            [x.day for x in r.DAY_SPECS],
            ["2026-03-01", "2026-04-01", "2026-05-01", "2026-06-01", "2026-07-01"],
        )
        expected = {
            "2026-03-01": (50_842_755, "50d3762a883f3f1cddc6869bbc2dbaaacf5bb52637ac0b51b85ae4dfcafdcb50", 737_199_360, "a5468fb97f161b05a89f8dcc39d8c88a58fb6dc60caeb69aa783facff66c27e1", 145_757_298, 110_464_539_904),
            "2026-04-01": (33_823_287, "31959ff7bcf8aae71fe4826987a6cbafc7897c6e881a2d555b89b99ac4def804", 675_132_621, "d1d08211ebcc8b576c4b9d50158ff39971f66dd463cffe1929dacd3d17223cfd", 129_067_640, 99_783_158_784),
            "2026-05-01": (26_110_327, "272f6d8ac29d14098c27d9fdaf95795ac5ed371024a000f279feaa38cf5605e1", 557_562_555, "284b95a8d84d1fdda10f73d80ba8cfb5f1f2ee60db9bd00937f3701e5948faf4", 104_234_425, 83_889_901_184),
            "2026-06-01": (34_960_370, "f1f695bf6ef198f209a115250d1b99194bb21dfa4693cab2dcb4a10a969be53e", 893_502_369, "581361873d3a692362257217e27961332ee25786dca27f280048be2ed150837d", 165_502_465, 123_101_446_784),
            "2026-07-01": (41_982_532, "eefc51c11e55b6d0224e760479bff87fc1f052773ae3c8ae08700395fa229a87", 923_475_379, "b2e8bbed3db89695f055dc3010a0fff074732d82ae18117a1602b5593c90d1f1", 172_067_693, 127_303_192_704),
        }
        for spec in r.DAY_SPECS:
            self.assertEqual(
                (spec.trade_bytes, spec.trade_sha256, spec.depth_bytes, spec.depth_sha256, spec.frozen_raw_rows, spec.required_scratch_bytes),
                expected[spec.day],
            )

    def test_resource_formula_matches_every_day(self) -> None:
        self.assertEqual(v2.PRODUCTION_INITIAL_CHUNK_ROWS, 250_000)
        self.assertEqual(v2.MERGE_FAN_IN, 8)
        self.assertEqual(rc.RUNTIME_RSS_ABORT_BYTES, 6 * 1024**3)
        for spec in r.DAY_SPECS:
            self.assertEqual(rc.required_scratch_bytes(spec.frozen_raw_rows), spec.required_scratch_bytes)

    def test_d6r9a_frozen_pass_binding(self) -> None:
        self.assertEqual(r.D6R9A_MARKER_SHA256, "66ffb16ae49ef37740e51a0e9b3d562ab2724762d4290ecf8e594a62b742d4c7")
        self.assertEqual(r.D6R9A_EVIDENCE_SHA256, "54afd16ca610b76de0658d68764b661335fcda23e3ae3ca4ce4de93c57c199d9")
        self.assertEqual(r.D6R9A_OUTPUT_SHA256, "d757d2ac32a29b0ac587323e115779c466068c6c0eba4270226b9c4109254cbc")
        self.assertEqual(r.D6R9A_OUTPUT_BYTES, 11_493_385_088)
        self.assertEqual(r.D6R9A_FINAL_ROWS, 179_584_138)

    def test_bulk_runner_does_not_use_old_upstream_or_whole_output_load(self) -> None:
        source = Path(r.__file__).read_text(encoding="utf-8")
        self.assertNotIn("dev045_d6r_bounded_converter", source)
        self.assertNotIn("hftbacktest.data.utils.tardis", source)
        self.assertNotIn("np.load(", source)
        self.assertNotIn("mmap_mode", source)

    def test_each_day_has_distinct_marker_evidence_and_output(self) -> None:
        markers = {r._marker_path(x) for x in r.DAY_SPECS}
        evidences = {r._evidence_path(x) for x in r.DAY_SPECS}
        outputs = {r._output_path(x) for x in r.DAY_SPECS}
        self.assertEqual(len(markers), 5)
        self.assertEqual(len(evidences), 5)
        self.assertEqual(len(outputs), 5)
        self.assertTrue(all("dev045_d6r9b" in str(x) for x in markers | outputs))


if __name__ == "__main__":
    unittest.main()
