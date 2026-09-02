from __future__ import annotations

from pathlib import Path

from multimarket import dev032_e1b_r1_harness as h

def test_r1_output_is_distinct_from_parent():
    assert h.R1_OUTPUT_DIRECTORY != Path(
        "/home/emadh/Multi-Market/evidence/dev032_e1b_broad_predictive_screen_v1"
    )
    assert h.R1_OUTPUT_DIRECTORY.name == "dev032_e1b_r1_broad_predictive_screen_v1"

def test_process_pool_smoke_real_module():
    assert h.process_pool_smoke(max_workers=2) == (1,4,9,16)
