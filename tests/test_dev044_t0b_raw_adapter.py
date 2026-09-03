from __future__ import annotations

import numpy as np
import pytest

from multimarket import dev044_t0b_raw_adapter as a


def good():
    return {
        "S05":np.zeros((3,7)),
        "S06":np.zeros((3,2)),
        "S21":np.zeros((3,8)),
        "S30":np.zeros((3,6)),
        "S31":np.zeros((3,6)),
        "S32":np.zeros((3,4)),
    }


def test_validate_mapping_good():
    a.validate_mapping(good())


def test_validate_mapping_missing():
    x=good();x.pop("S32")
    with pytest.raises(a.RawAdapterError):
        a.validate_mapping(x)


def test_validate_mapping_width():
    x=good();x["S05"]=np.zeros((3,6))
    with pytest.raises(a.RawAdapterError):
        a.validate_mapping(x)


def test_validate_mapping_row_alignment():
    x=good();x["S31"]=np.zeros((2,6))
    with pytest.raises(a.RawAdapterError):
        a.validate_mapping(x)


def test_raw_row_map():
    r=a.RawAdapterResult(
        day=__import__("datetime").date(2026,4,1),
        timestamps_us=np.asarray([1,2,3],dtype=np.int64),
        values=good(),
        extractor_stderr="",
    )
    assert a.raw_row_map(r)=={1:0,2:1,3:2}


def test_adapter_build_directory_is_not_worktree_build(monkeypatch,tmp_path):
    from datetime import date
    import numpy as np
    from pathlib import Path

    day=date(2026,4,1)
    raw_root=tmp_path/"raw"
    raw_file=raw_root/"2026-04-01.csv.gz"
    raw_root.mkdir(parents=True)
    raw_file.write_bytes(b"placeholder")

    monkeypatch.setattr(a.p1a,"RAW_ROOT",raw_root)

    seen={}
    def fake_compile(workspace,build_dir):
        seen["workspace"]=Path(workspace)
        seen["build_dir"]=Path(build_dir)
        exe=Path(build_dir)/"dev032_e1a_raw_features"
        exe.parent.mkdir(parents=True,exist_ok=True)
        exe.write_text("")
        return exe

    def fake_run(cmd,capture_output,text):
        output=Path(cmd[-1])
        output.write_text("local_timestamp_us,S05_0,S05_1,S05_2,S05_3,S05_4,S05_5,S05_6,S06_0,S06_1,S21_0,S21_1,S21_2,S21_3,S21_4,S21_5,S21_6,S21_7,S30_0,S30_1,S30_2,S30_3,S30_4,S30_5,S31_0,S31_1,S31_2,S31_3,S31_4,S31_5,S32_0,S32_1,S32_2,S32_3\n1," + ",".join(["0"]*33) + "\n")
        class P:
            returncode=0
            stderr=""
        return P()

    def fake_parse(path,ts):
        return {
            "S05":np.zeros((1,7)),
            "S06":np.zeros((1,2)),
            "S21":np.zeros((1,8)),
            "S30":np.zeros((1,6)),
            "S31":np.zeros((1,6)),
            "S32":np.zeros((1,4)),
        }

    monkeypatch.setattr(a.e1run,"_compile_tool",fake_compile)
    monkeypatch.setattr(a.subprocess,"run",fake_run)
    monkeypatch.setattr(a.e1mat,"parse_raw_extractor_csv",fake_parse)
    monkeypatch.setattr(a.dd,"HISTORICAL_DAYS",(day,))

    workspace=tmp_path/"repo"
    workspace.mkdir()
    result=a.materialize_raw_adapter(
        workspace=workspace,
        day=day,
        timestamps_us=np.asarray([1],dtype=np.int64),
    )
    assert result.day==day
    assert seen["workspace"]==workspace
    assert workspace not in seen["build_dir"].parents
    assert seen["build_dir"].name=="dev032_e1a_build"
