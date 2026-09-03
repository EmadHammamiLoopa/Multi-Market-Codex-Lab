from __future__ import annotations

from multimarket import dev045_m0_hft_compat as c


def test_hftbacktest_api_compatibility():
    r=c.audit_api()
    assert r["package"]=="hftbacktest"
    assert r["required_version"]=="2.4.4"
    assert all(r["methods"].values())
    assert r["risk_adverse_builder_pass"] is True
    assert r["prob_queue_builder_pass"] is True
    assert r["partial_fill_hook_pass"] is True
    assert r["no_partial_fill_hook_pass"] is True
    assert r["constant_order_latency_hook_pass"] is True
    assert r["fee_hook_pass"] is True
