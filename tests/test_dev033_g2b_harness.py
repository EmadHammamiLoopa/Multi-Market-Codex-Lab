from multimarket import dev033_g2b_harness as h

def test_process_pool_smoke():
    assert h.process_pool_smoke(2)==(1,4,9,16)
