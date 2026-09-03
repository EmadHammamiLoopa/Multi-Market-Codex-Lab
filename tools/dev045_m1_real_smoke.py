from __future__ import annotations

import gzip
import importlib.metadata as metadata
import json
import math
from pathlib import Path
import tempfile

import numpy as np

DAY="2026-01-01"
SYMBOL="BTCUSDT"
RAW_ROOT=Path("/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw")
L2=RAW_ROOT/"incremental_book_L2"/SYMBOL/f"{DAY}.csv.gz"
TRADES=RAW_ROOT/"trades"/SYMBOL/f"{DAY}.csv.gz"

MAX_L2_ROWS=100_000
MAX_TRADE_ROWS=25_000

EXPECTED_L2_HEADER="exchange,symbol,timestamp,local_timestamp,is_snapshot,side,price,amount"
EXPECTED_TRADE_HEADER="exchange,symbol,timestamp,local_timestamp,id,side,price,amount"


class SmokeError(RuntimeError):
    pass


def _copy_prefix(src:Path,dst:Path,*,max_rows:int,expected_header:str)->dict:
    if not src.is_file():
        raise SmokeError(f"missing:{src}")
    rows=0
    snapshot_bid=0
    snapshot_ask=0
    buys=0
    sells=0
    with gzip.open(src,"rt",encoding="utf-8",newline="") as r, gzip.open(
        dst,"wt",encoding="utf-8",newline=""
    ) as w:
        header=r.readline().rstrip("\r\n")
        if header!=expected_header:
            raise SmokeError(f"header:{src}:{header}")
        w.write(header+"\n")
        for line in r:
            if rows>=max_rows:
                break
            z=line.rstrip("\r\n")
            if not z:
                continue
            f=z.split(",")
            if len(f)!=8:
                raise SmokeError(f"field_count:{src}:{rows}")
            if src==L2:
                if f[4]=="true" and f[5]=="bid":
                    snapshot_bid+=1
                elif f[4]=="true" and f[5]=="ask":
                    snapshot_ask+=1
            else:
                if f[5]=="buy":
                    buys+=1
                elif f[5]=="sell":
                    sells+=1
            w.write(z+"\n")
            rows+=1
    return {
        "rows":rows,
        "snapshot_bid":snapshot_bid,
        "snapshot_ask":snapshot_ask,
        "buys":buys,
        "sells":sells,
    }


def main()->None:
    if metadata.version("hftbacktest")!="2.4.4":
        raise SmokeError("hftbacktest_version")

    # Hard guards: this smoke is authorized only for the already-audited BTC
    # development day. It writes only temporary prefixes and no evidence/PnL.
    if DAY!="2026-01-01" or SYMBOL!="BTCUSDT":
        raise SmokeError("authorization_guard")
    if "2026-08" in str(L2) or "2026-09" in str(L2):
        raise SmokeError("sealed_date_guard")

    import hftbacktest as h
    from hftbacktest.data.utils.tardis import convert
    from hftbacktest.data.validation import validate_event_order

    with tempfile.TemporaryDirectory(prefix="dev045_m1_real_smoke_") as td:
        td=Path(td)
        l2p=td/"l2.csv.gz"
        trp=td/"trades.csv.gz"
        l2s=_copy_prefix(L2,l2p,max_rows=MAX_L2_ROWS,expected_header=EXPECTED_L2_HEADER)
        trs=_copy_prefix(TRADES,trp,max_rows=MAX_TRADE_ROWS,expected_header=EXPECTED_TRADE_HEADER)

        if l2s["snapshot_bid"]<=0 or l2s["snapshot_ask"]<=0:
            raise SmokeError(f"snapshot_support:{l2s}")
        if trs["buys"]<=0 or trs["sells"]<=0:
            raise SmokeError(f"trade_side_support:{trs}")

        data=convert(
            [str(trp),str(l2p)],
            buffer_size=200_000,
            ss_buffer_size=200_000,
            base_latency=0,
            snapshot_mode="process",
        )

        if data.dtype!=h.event_dtype:
            raise SmokeError("event_dtype")
        if len(data)<=0:
            raise SmokeError("empty_conversion")
        if np.any(data["local_ts"]<data["exch_ts"]):
            raise SmokeError("negative_feed_latency")
        validate_event_order(data)

        base=(data["ev"] & np.uint64(0xff))
        if not np.any(base==h.TRADE_EVENT):
            raise SmokeError("trade_event_missing")
        if not np.any(base==h.DEPTH_SNAPSHOT_EVENT):
            raise SmokeError("snapshot_event_missing")

        asset=(
            h.BacktestAsset()
            .data([data])
            .linear_asset(1.0)
            .constant_order_latency(250_000,250_000)
            .risk_adverse_queue_model()
            .partial_fill_exchange()
            .trading_value_fee_model(0.0,0.0)
            .tick_size(0.1)
            .lot_size(0.001)
        )
        bt=h.HashMapMarketDepthBacktest([asset])
        try:
            constructed=False
            for _ in range(5000):
                rc=bt.wait_next_feed(False,10_000_000_000)
                if rc==1:
                    break
                if rc not in (0,2):
                    raise SmokeError(f"feed_rc:{rc}")
                d=bt.depth(0)
                if math.isfinite(float(d.best_bid)) and math.isfinite(float(d.best_ask)):
                    if float(d.best_bid)>=float(d.best_ask):
                        raise SmokeError("crossed_initial_book")
                    constructed=True
                    break
            if not constructed:
                raise SmokeError("book_not_constructed")
            if float(bt.position(0))!=0.0:
                raise SmokeError("unexpected_position")
        finally:
            bt.close()

    print(json.dumps({
        "status":"DEV045_M1_REAL_DATA_CONVERTER_SMOKE_PASS",
        "day":DAY,
        "symbol":SYMBOL,
        "l2_prefix_rows":l2s["rows"],
        "trade_prefix_rows":trs["rows"],
        "converted_events":int(len(data)),
        "maker_pnl_run":False,
        "strategy_order_submitted":False,
        "sep01_plus_opened":False,
        "non_btc_opened":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
