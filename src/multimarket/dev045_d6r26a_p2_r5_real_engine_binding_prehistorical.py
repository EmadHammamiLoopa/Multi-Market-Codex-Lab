from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata as importlib_metadata

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p1_synthetic_candidate_labeler as p1
from multimarket import dev045_d6r26a_p2_r4_canonical_materialization_runner_preexec as r4
from multimarket import dev045_m4_adapter as m4


EXPERIMENT_ID = "DEV045-D6R26A-P2-R5"
DESIGN_VERSION = "real-engine-binding-prehistorical-v1"
PARENT_P2_R4_HEAD = "af961cd3404529873aea8b066da11e55eaaf918e"

HFTBACKTEST_VERSION = "2.4.4"
HFTBACKTEST_UPSTREAM_HEAD = "a244a14250b42d97fc305569c93c4117cd5e1dff"
HFTBACKTEST_FROZEN_BINARY_SHA256 = "5174f486abc4b29cfef565672548798ea68ec54c0f6c04077bcbdf43f5033752"

REAL_ENGINE_PROBE_AUTHORIZED = True
SYNTHETIC_FIXTURE_ONLY = True
HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
HISTORICAL_FILE_IO_AUTHORIZED = False
CANONICAL_RUNNER_BINDING_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
NETWORK_ACQUISITION_AUTHORIZED = False

GTX_ACCEPT_ORDER_ID = 5201
GTX_CROSS_ORDER_ID = 5202
PROBE_TIMEOUT_NS = 10_000_000_000
RESPONSE_TIMEOUT_NS = 600_000_000


class RealEngineBindingError(RuntimeError):
    pass


@dataclass(frozen=True)
class EngineIdentity:
    version: str
    gtx: int
    none: int
    new: int
    expired: int
    filled: int
    canceled: int
    partially_filled: int
    rejected: int


@dataclass(frozen=True)
class GtxAcceptedFillProbe:
    accepted_status: int
    accepted_placement: str
    post_trade10_status: int
    terminal_status: int
    terminal_placement: str
    exec_qty: float
    position: float
    fill_response_rc: int


@dataclass(frozen=True)
class GtxCrossProbe:
    terminal_status: int
    placement: str
    position: float


def verify_engine_identity() -> EngineIdentity:
    import hftbacktest as h
    from hftbacktest.order import (
        GTX,
        NONE,
        NEW,
        EXPIRED,
        FILLED,
        CANCELED,
        PARTIALLY_FILLED,
        REJECTED,
    )

    version = importlib_metadata.version("hftbacktest")
    identity = EngineIdentity(
        version=version,
        gtx=int(GTX),
        none=int(NONE),
        new=int(NEW),
        expired=int(EXPIRED),
        filled=int(FILLED),
        canceled=int(CANCELED),
        partially_filled=int(PARTIALLY_FILLED),
        rejected=int(REJECTED),
    )
    if identity.version != HFTBACKTEST_VERSION:
        raise RealEngineBindingError("hftbacktest_version")
    if identity.gtx != 1:
        raise RealEngineBindingError("gtx_identity")
    expected = (
        p1.HFT_NONE,
        p1.HFT_NEW,
        p1.HFT_EXPIRED,
        p1.HFT_FILLED,
        p1.HFT_CANCELED,
        p1.HFT_PARTIALLY_FILLED,
        p1.HFT_REJECTED,
    )
    observed = (
        identity.none,
        identity.new,
        identity.expired,
        identity.filled,
        identity.canceled,
        identity.partially_filled,
        identity.rejected,
    )
    if observed != expected:
        raise RealEngineBindingError("order_status_identity")
    if int(h.LIMIT) <= 0:
        raise RealEngineBindingError("limit_identity")
    return identity


def _new_synthetic_backtest(data):
    import hftbacktest as h

    m4.validate_events(data)
    asset = m4.build_asset(
        data,
        queue_model="risk_adverse",
        entry_latency_ns=p0.ENTRY_LATENCY_NS,
        response_latency_ns=p0.RESPONSE_LATENCY_NS,
        maker_fee=0.0,
        taker_fee=0.0,
    )
    return h, h.HashMapMarketDepthBacktest([asset])


def _next_market(bt) -> int:
    rc = int(bt.wait_next_feed(False, PROBE_TIMEOUT_NS))
    if rc != 2:
        raise RealEngineBindingError(f"market_feed_rc:{rc}")
    return int(bt.current_timestamp)


def _response_or_timeout(bt) -> int:
    rc = int(bt.wait_next_feed(True, RESPONSE_TIMEOUT_NS))
    if rc not in (0, 3):
        raise RealEngineBindingError(f"response_rc:{rc}")
    return rc


def run_gtx_accept_fill_probe() -> GtxAcceptedFillProbe:
    """Real hftbacktest engine, in-memory synthetic fixture only."""
    identity = verify_engine_identity()
    h, bt = _new_synthetic_backtest(m4.make_fill_fixture())
    try:
        _next_market(bt)
        depth = bt.depth(0)
        price = float(depth.best_bid)
        rc = int(
            bt.submit_buy_order(
                0,
                GTX_ACCEPT_ORDER_ID,
                price,
                float(p0.CANDIDATE_ORDER_QTY),
                h.GTX,
                h.LIMIT,
                True,
            )
        )
        if rc != 0:
            raise RealEngineBindingError(f"gtx_submit_rc:{rc}")
        order = bt.orders(0).get(GTX_ACCEPT_ORDER_ID)
        if order is None:
            raise RealEngineBindingError("accepted_order_missing")
        accepted_status = int(order.status)
        accepted_placement = p1.classify_gtx_placement_status(accepted_status)
        if accepted_placement != p1.POST_ONLY_ACCEPTED:
            raise RealEngineBindingError("gtx_passive_not_accepted")

        _next_market(bt)
        _response_or_timeout(bt)
        order = bt.orders(0).get(GTX_ACCEPT_ORDER_ID)
        if order is None:
            raise RealEngineBindingError("post_trade10_order_missing")
        post_trade10_status = int(order.status)
        if post_trade10_status != identity.new:
            raise RealEngineBindingError("unexpected_fill_after_queue_depletion_only")

        _next_market(bt)
        fill_response_rc = _response_or_timeout(bt)
        order = bt.orders(0).get(GTX_ACCEPT_ORDER_ID)
        if order is None:
            raise RealEngineBindingError("terminal_order_missing")
        terminal_status = int(order.status)
        terminal_placement = p1.classify_gtx_placement_status(terminal_status)
        if terminal_status != identity.filled:
            raise RealEngineBindingError(f"gtx_not_filled:{terminal_status}")
        if terminal_placement != p1.POST_ONLY_ACCEPTED:
            raise RealEngineBindingError("filled_gtx_not_accepted")
        exec_qty = float(order.exec_qty)
        position = float(bt.position(0))
        if abs(exec_qty - float(p0.CANDIDATE_ORDER_QTY)) > 1e-12:
            raise RealEngineBindingError("gtx_exec_qty")
        if abs(position - exec_qty) > 1e-12:
            raise RealEngineBindingError("gtx_position_binding")
        if fill_response_rc != 3:
            raise RealEngineBindingError("fill_response_missing")
        return GtxAcceptedFillProbe(
            accepted_status=accepted_status,
            accepted_placement=accepted_placement,
            post_trade10_status=post_trade10_status,
            terminal_status=terminal_status,
            terminal_placement=terminal_placement,
            exec_qty=exec_qty,
            position=position,
            fill_response_rc=fill_response_rc,
        )
    finally:
        rc = int(bt.close())
        if rc != 0:
            raise RealEngineBindingError(f"bt_close_rc:{rc}")


def run_gtx_cross_probe() -> GtxCrossProbe:
    """Proves PartialFillExchange expresses GTX crossing refusal as EXPIRED."""
    identity = verify_engine_identity()
    h, bt = _new_synthetic_backtest(m4.make_cancel_replace_fixture())
    try:
        _next_market(bt)
        depth = bt.depth(0)
        crossing_price = float(depth.best_ask)
        rc = int(
            bt.submit_buy_order(
                0,
                GTX_CROSS_ORDER_ID,
                crossing_price,
                float(p0.CANDIDATE_ORDER_QTY),
                h.GTX,
                h.LIMIT,
                True,
            )
        )
        if rc != 0:
            raise RealEngineBindingError(f"gtx_cross_submit_rc:{rc}")
        order = bt.orders(0).get(GTX_CROSS_ORDER_ID)
        if order is None:
            raise RealEngineBindingError("cross_order_missing")
        status = int(order.status)
        placement = p1.classify_gtx_placement_status(status)
        if status != identity.expired:
            raise RealEngineBindingError(f"gtx_cross_not_expired:{status}")
        if placement != p1.POST_ONLY_REJECTED_AT_ARRIVAL:
            raise RealEngineBindingError("gtx_cross_classification")
        position = float(bt.position(0))
        if abs(position) > 1e-15:
            raise RealEngineBindingError("gtx_cross_position")
        return GtxCrossProbe(
            terminal_status=status,
            placement=placement,
            position=position,
        )
    finally:
        rc = int(bt.close())
        if rc != 0:
            raise RealEngineBindingError(f"bt_close_rc:{rc}")


def validate_r5_contract() -> None:
    r4.validate_runner_contract()
    p1.validate_p1_contract()
    if PARENT_P2_R4_HEAD != "af961cd3404529873aea8b066da11e55eaaf918e":
        raise RealEngineBindingError("parent")
    if HFTBACKTEST_VERSION != "2.4.4":
        raise RealEngineBindingError("version")
    if HFTBACKTEST_UPSTREAM_HEAD != "a244a14250b42d97fc305569c93c4117cd5e1dff":
        raise RealEngineBindingError("upstream")
    if not REAL_ENGINE_PROBE_AUTHORIZED or not SYNTHETIC_FIXTURE_ONLY:
        raise RealEngineBindingError("probe_surface")
    forbidden = (
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        HISTORICAL_FILE_IO_AUTHORIZED,
        CANONICAL_RUNNER_BINDING_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
        NETWORK_ACQUISITION_AUTHORIZED,
    )
    if any(forbidden):
        raise RealEngineBindingError("closed_surface_open")


__all__ = [
    "EngineIdentity",
    "GtxAcceptedFillProbe",
    "GtxCrossProbe",
    "verify_engine_identity",
    "run_gtx_accept_fill_probe",
    "run_gtx_cross_probe",
    "validate_r5_contract",
]
