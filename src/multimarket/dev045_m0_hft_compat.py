from __future__ import annotations

HFTBACKTEST_VERSION="2.4.4"

REQUIRED_BACKTEST_ASSET_METHODS=(
    "data",
    "initial_snapshot",
    "linear_asset",
    "constant_order_latency",
    "risk_adverse_queue_model",
    "log_prob_queue_model",
    "no_partial_fill_exchange",
    "partial_fill_exchange",
    "trading_value_fee_model",
    "tick_size",
    "lot_size",
)

class HftCompatError(RuntimeError):
    pass

def audit_api()->dict:
    import hftbacktest
    from hftbacktest import BacktestAsset

    version=getattr(hftbacktest,"__version__",None)
    methods={
        name:bool(hasattr(BacktestAsset,name))
        for name in REQUIRED_BACKTEST_ASSET_METHODS
    }
    if not all(methods.values()):
        missing=[k for k,v in methods.items() if not v]
        raise HftCompatError("missing_api:"+",".join(missing))

    # Exercise the fluent configuration API without loading market data or
    # starting a backtest.
    asset=(
        BacktestAsset()
        .linear_asset(1.0)
        .constant_order_latency(250_000_000,250_000_000)
        .risk_adverse_queue_model()
        .partial_fill_exchange()
        .trading_value_fee_model(0.0,0.0)
        .tick_size(0.1)
        .lot_size(0.001)
    )
    if asset is None:
        raise HftCompatError("asset_builder_none")

    prob=(
        BacktestAsset()
        .linear_asset(1.0)
        .constant_order_latency(250_000_000,250_000_000)
        .log_prob_queue_model()
        .no_partial_fill_exchange()
        .trading_value_fee_model(0.0,0.0)
        .tick_size(0.1)
        .lot_size(0.001)
    )
    if prob is None:
        raise HftCompatError("prob_asset_builder_none")

    return {
        "package":"hftbacktest",
        "version":version,
        "required_version":HFTBACKTEST_VERSION,
        "methods":methods,
        "risk_adverse_builder_pass":True,
        "prob_queue_builder_pass":True,
        "partial_fill_hook_pass":True,
        "no_partial_fill_hook_pass":True,
        "constant_order_latency_hook_pass":True,
        "fee_hook_pass":True,
    }
