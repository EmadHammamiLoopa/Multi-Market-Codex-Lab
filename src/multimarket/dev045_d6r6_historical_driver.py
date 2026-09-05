from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from multimarket import dev045_d6r5_memmap_adapter as adapter
from multimarket import dev045_d6r5_memmap_contract as m5
from multimarket import dev045_d6r6_historical_binding_contract as c


EXPERIMENT_ID = "DEV045-D6R6B"
DESIGN_VERSION = "synthetic-read-only-memmap-hft-binding-v1"

CANONICAL_JAN_OPEN_ENABLED = False
CANONICAL_JAN_HFTBACKTEST_INGESTION_ENABLED = False
HISTORICAL_POLICY_REPLAY_ENABLED = False
HISTORICAL_PNL_ENABLED = False
ECONOMIC_ARENA_EXECUTION_ENABLED = False
CANONICAL_PNL_WRITE_ENABLED = False
NETWORK_ACQUISITION_ENABLED = False
LIVE_TRADING_AUTHORIZED = False

SYNTHETIC_MEMMAP_ONLY = True


class HistoricalMemmapBindingError(RuntimeError):
    pass


def _imports():
    import hftbacktest as h

    return h


def _expected_dtype() -> np.dtype:
    return np.dtype(list(m5.EVENT_DTYPE_DESCR))


def _validate_verified_source(
    source: adapter.CanonicalJanMemmap,
) -> None:
    if not isinstance(source, adapter.CanonicalJanMemmap):
        raise HistoricalMemmapBindingError("source_type")

    if source._closed:
        raise HistoricalMemmapBindingError("source_closed")

    data = source.data

    if not isinstance(data, np.memmap):
        raise HistoricalMemmapBindingError("source_not_memmap")

    if data.flags.writeable:
        raise HistoricalMemmapBindingError("source_writeable")

    if data.ndim != 1:
        raise HistoricalMemmapBindingError("source_ndim")

    if not data.flags.c_contiguous:
        raise HistoricalMemmapBindingError("source_not_contiguous")

    if data.dtype != _expected_dtype():
        raise HistoricalMemmapBindingError(
            f"source_dtype:{data.dtype}"
        )

    if data.dtype.names != m5.EVENT_FIELDS:
        raise HistoricalMemmapBindingError(
            f"source_fields:{data.dtype.names}"
        )

    if data.dtype.itemsize != m5.EVENT_ITEMSIZE:
        raise HistoricalMemmapBindingError(
            f"source_itemsize:{data.dtype.itemsize}"
        )

    mmap_mode = getattr(data, "mode", None)
    if mmap_mode != "r":
        raise HistoricalMemmapBindingError(
            f"source_mode:{mmap_mode}"
        )


def _build_asset_from_live_memmap(
    source: adapter.CanonicalJanMemmap,
):
    _validate_verified_source(source)

    h = _imports()

    if source.data.dtype != h.event_dtype:
        raise HistoricalMemmapBindingError(
            "hft_event_dtype_mismatch"
        )

    # D6R6A freezes this exact no-copy ndarray registration path:
    # BacktestAsset.data(np.memmap) -> ctypes pointer -> non-owning
    # DataPtr::from_ptr in hftbacktest 2.4.4.
    #
    # Therefore `source` MUST remain alive while the backtest exists.
    asset = (
        h.BacktestAsset()
        .parallel_load(False)
        .latency_offset(0)
        .data(source.data)
        .linear_asset(1.0)
        .constant_order_latency(0, 0)
        .risk_adverse_queue_model()
        .partial_fill_exchange()
        .trading_value_fee_model(0.0, 0.0)
        .tick_size(0.1)
        .lot_size(0.001)
    )

    return asset


@dataclass
class LifetimeSafeHistoricalBinding:
    source: adapter.CanonicalJanMemmap
    bt: Any
    lifecycle: list[str] = field(default_factory=list)
    _closed: bool = False

    def close(self) -> None:
        if self._closed:
            return

        # Contract-critical order:
        # backtest is destroyed first while the caller-owned mmap is
        # guaranteed to remain mapped.
        rc = int(self.bt.close())
        self.lifecycle.append("backtest_closed")

        # Only after hftbacktest has released its non-owning pointer may
        # the underlying mmap be unmapped.
        self.source.close()
        self.lifecycle.append("memmap_closed")

        self._closed = True

        if rc != 0:
            raise HistoricalMemmapBindingError(
                f"backtest_close_rc:{rc}"
            )

    def __enter__(self) -> "LifetimeSafeHistoricalBinding":
        if self._closed:
            raise HistoricalMemmapBindingError(
                "binding_closed"
            )
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def _build_lifetime_safe_binding(
    source: adapter.CanonicalJanMemmap,
) -> LifetimeSafeHistoricalBinding:
    """
    Bind an already-verified read-only memmap to hftbacktest.

    D6R6B is synthetic-only.  This function does not open any path and
    does not invoke the canonical Jan entrypoint.
    """
    _validate_verified_source(source)

    h = _imports()

    lifecycle = ["memmap_opened_verified"]

    asset = _build_asset_from_live_memmap(source)
    lifecycle.append("asset_registered")

    bt = h.HashMapMarketDepthBacktest([asset])
    lifecycle.append("backtest_built")

    return LifetimeSafeHistoricalBinding(
        source=source,
        bt=bt,
        lifecycle=lifecycle,
    )
