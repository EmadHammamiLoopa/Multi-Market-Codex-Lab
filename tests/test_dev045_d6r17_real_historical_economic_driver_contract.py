from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from multimarket import (
    dev045_d6r17_real_historical_economic_driver_contract as c,
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def test_contract_validates():
    c.validate_contract()


def test_exact_parent_and_selection():
    assert c.PARENT_FREEZE_HEAD == (
        "5411877e3bd1f8fcd9812176bc3dc39dbf18bf88"
    )

    assert c.SELECTION_ARTIFACT_PATH.is_file()

    assert (
        _sha256(c.SELECTION_ARTIFACT_PATH)
        == c.SELECTION_ARTIFACT_SHA256
    )

    d = json.loads(
        c.SELECTION_ARTIFACT_PATH.read_text(
            encoding="utf-8"
        )
    )

    assert d["status"] == (
        "EXACT_M6_ECONOMIC_LINEAGE_SELECTED_NO_PNL"
    )

    assert d["canonical_ingestion"][
        "jan_to_jul_complete"
    ] is True

    assert d["economic_family"][
        "policy_day_scenario_replays"
    ] == 112


def test_exact_family_and_matrix():
    assert c.POLICY_IDS == (
        "M01",
        "M02",
        "M03",
        "M04",
        "M05",
        "M06",
        "M07",
        "M08",
    )

    assert c.SCENARIOS == (
        "Q0_PRIMARY_250_250",
        "Q0_STRESS_500_500",
    )

    assert c.AUTHORIZED_DAYS == (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
        "2026-07-01",
    )

    assert c.TOTAL_POLICY_DAY_SCENARIO_REPLAYS == 112
    assert c.EXPECTED_TOTAL_REPLAYS == 112
    assert c.BLOCKS_PER_DAY == 6


def test_exact_source_specs():
    expected = {
        "2026-01-01": (
            64_314_723,
            4_116_142_528,
            "8f0a4fbd56ecdc261dbe2041ce138a094"
            "56423074925d495272716219a1d4da1",
        ),
        "2026-02-01": (
            179_584_138,
            11_493_385_088,
            "d757d2ac32a29b0ac587323e115779c466"
            "068c6c0eba4270226b9c4109254cbc",
        ),
        "2026-03-01": (
            150_979_263,
            9_662_673_088,
            "9e6a8b61d05e1a4938e17ffa7969241aff"
            "c7c06c1d0836188e3a882c363f2d99",
        ),
        "2026-04-01": (
            132_829_759,
            8_501_104_832,
            "de7e0471e63631394981b301bb461d679"
            "192c37eb6241d4d8073cf0640eca7f7",
        ),
        "2026-05-01": (
            108_328_169,
            6_933_003_072,
            "9433dfb498070dd5dd3e8ab1633c2f195"
            "51844f2ddf0d451e120119365bb04a3",
        ),
        "2026-06-01": (
            172_540_697,
            11_042_604_864,
            "ac97ad27c9d58b3b3e249547b8ae7c74c"
            "f2ebfde07965103bd5f6c7b853c26b",
        ),
        "2026-07-01": (
            181_084_390,
            11_589_401_216,
            "85f9a0a168420ce924fc9e1b746fbd9bb"
            "54bec390205c9ed9e65469ad489a83f",
        ),
    }

    assert len(c.DAY_SPECS) == 7

    for spec in c.DAY_SPECS:
        rows, size, sha = expected[spec.day]

        assert spec.rows == rows
        assert spec.bytes == size
        assert spec.sha256 == sha
        assert spec.path.suffix == ".npy"


def test_frozen_fee_and_latency_contract():
    assert c.PRIMARY_QUEUE_MODEL == "risk_adverse"

    assert c.PRIMARY_ENTRY_LATENCY_NS == 250_000_000
    assert c.PRIMARY_RESPONSE_LATENCY_NS == 250_000_000

    assert c.STRESS_ENTRY_LATENCY_NS == 500_000_000
    assert c.STRESS_RESPONSE_LATENCY_NS == 500_000_000

    assert c.PRIMARY_MAKER_RATE == 0.0002
    assert c.PRIMARY_TAKER_RATE == 0.0005

    assert c.STRESS_MAKER_RATE == 0.0003
    assert c.STRESS_TAKER_RATE == 0.00075


def test_frozen_code_blobs_still_exact():
    for path, expected in c.FROZEN_CODE_BLOBS.items():
        observed = subprocess.check_output(
            ["git", "hash-object", "--", path],
            text=True,
        ).strip()

        assert observed == expected, path


def test_all_execution_surfaces_closed():
    assert c.HISTORICAL_FILE_IO_ENABLED is False
    assert c.HISTORICAL_REPLAY_EXECUTION_ENABLED is False
    assert c.HISTORICAL_PNL_ENABLED is False
    assert c.ECONOMIC_ARENA_EXECUTION_ENABLED is False
    assert c.CANONICAL_PNL_WRITE_ENABLED is False
    assert c.ORDER_SUBMISSION_ENABLED is False
    assert c.POLICY_EXECUTION_ENABLED is False
    assert c.NETWORK_ACQUISITION_ENABLED is False
    assert c.RAILWAY_ENABLED is False
    assert c.LIVE_TRADING_AUTHORIZED is False

    assert c.AUG_OPEN_AUTHORIZED is False
    assert c.SEP_PLUS_OPEN_AUTHORIZED is False
    assert c.NON_BTC_OPEN_AUTHORIZED is False

    assert c.CANONICAL_EXECUTION_AUTHORIZED is False


def test_future_one_shot_guards():
    assert c.AUTOMATIC_RETRY is False
    assert c.RERUN_AFTER_ATTEMPT_CONSUMPTION is False

    assert (
        c.STOP_ON_EXECUTION_INTEGRITY_FAILURE
        is True
    )

    # Negative economics are evidence; they must not
    # prematurely terminate the frozen multiplicity family.
    assert c.STOP_ON_ECONOMIC_NONPASS is False

    assert c.ALL_112_REPLAYS_REQUIRED is True
    assert c.RANKING_BEFORE_COMPLETE_MATRIX is False

    assert c.FIRST_HISTORICAL_OUTPUT_IS_EVIDENCE is True

    assert (
        c.TUNING_AFTER_FIRST_OUTPUT_AUTHORIZED
        is False
    )

    assert c.PROCESS_ONE_DAY_AT_A_TIME is True

    assert (
        c.VERIFY_FULL_SOURCE_SHA256_BEFORE_REPLAY
        is True
    )

    assert c.SOURCE_MUST_REMAIN_READ_ONLY is True


def test_contract_module_has_no_market_execution_code():
    text = Path(c.__file__).read_text(
        encoding="utf-8"
    )

    forbidden = (
        "np.load(",
        "numpy.load(",
        "HashMapMarketDepthBacktest(",
        "wait_next_feed(",
        ".submit_buy_order(",
        ".submit_sell_order(",
        "open_canonical_jan(",
    )

    for token in forbidden:
        assert token not in text
