from multimarket import dev045_d6r26a_p2_r2_frozen_source_registry as r2


def test_registry_matches_frozen_lineage_with_known_june_defect():
    r2.validate_frozen_source_registry()
    inherited = {x.day: x for x in r2.inherited_registry()}
    frozen = {x.day: x for x in r2.FROZEN_SOURCE_REGISTRY}
    for day in frozen:
        if day != '2026-06-01':
            assert inherited[day] == frozen[day]
    assert inherited['2026-06-01'].sha256 == r2.D6R17_JUNE_SHA256_TRANSCRIPTION_DEFECT
    assert len(inherited['2026-06-01'].sha256) == 63
    assert frozen['2026-06-01'].sha256 == r2.D6R16_JUNE_SHA256_AUTHORITY
    assert len(frozen['2026-06-01'].sha256) == 64
    assert len(r2.FROZEN_SOURCE_REGISTRY) == 7
    assert r2.canonical_registry_sha256() == r2.FROZEN_SOURCE_REGISTRY_SHA256


def test_r1_registry_shape_is_exact_and_closed():
    registry = r2.r1_registry()
    assert tuple(sorted(registry)) == tuple(sorted(x.day for x in r2.FROZEN_SOURCE_REGISTRY))
    assert all(x.path.endswith('.npy') for x in registry.values())
    assert all('BTCUSDT_2026-' in x.path for x in registry.values())
    assert all(len(x.sha256) == 64 for x in registry.values())
    assert r2.HISTORICAL_FILE_IO_AUTHORIZED is False
    assert r2.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r2.HISTORICAL_SOURCE_REHASH_AUTHORIZED is False
    assert r2.CANDIDATE_SIMULATION_AUTHORIZED is False
    assert r2.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r2.MODEL_FIT_AUTHORIZED is False
    assert r2.PNL_AUTHORIZED is False
    assert r2.LIVE_TRADING_AUTHORIZED is False


def test_exact_source_witnesses_are_preserved():
    by_day = {x.day: x for x in r2.FROZEN_SOURCE_REGISTRY}
    assert by_day['2026-01-01'].ingestion_witness == 'DEV045-D6R7B'
    assert by_day['2026-02-01'].ingestion_witness == 'DEV045-D6R15'
    for day in ('2026-03-01','2026-04-01','2026-05-01','2026-06-01','2026-07-01'):
        assert by_day[day].ingestion_witness == 'DEV045-D6R16'
    assert by_day['2026-06-01'].witness_head == r2.SOURCE_CONTRACT_PARENT_FREEZE_HEAD
