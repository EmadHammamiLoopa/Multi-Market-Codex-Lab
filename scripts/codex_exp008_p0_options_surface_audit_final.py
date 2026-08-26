#!/usr/bin/env python3

"""Final frozen entry point for CODEX-EXP-008-P0.

This wrapper reuses the acquisition/streaming machinery in the preregistered
candidate runner while replacing only the surface-support diagnostic with the
fully decomposed preregistered support accounting: anchors, ATM, 25-delta,
OI, and all-nine.
"""

import importlib.util
import math
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE / "codex_exp008_p0_options_surface_audit.py"
SPEC = importlib.util.spec_from_file_location("exp008_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load EXP008 base runner")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)


def _expiry_components(rows):
    under = [
        r["underlying_price"]
        for r in rows
        if r["underlying_price"] is not None
        and r["underlying_price"] > 0
    ]
    if not under:
        return {
            "atm": None,
            "delta_pair": None,
            "oi": None,
        }

    s = median(under)
    strikes = sorted({r["strike"] for r in rows if r["strike"] > 0})
    if not strikes:
        return {"atm": None, "delta_pair": None, "oi": None}

    atm_strike = min(
        strikes,
        key=lambda k: (abs(math.log(k / s)), k),
    )
    calls = [
        r for r in rows
        if r["strike"] == atm_strike and r["type"] == "call"
    ]
    puts = [
        r for r in rows
        if r["strike"] == atm_strike and r["type"] == "put"
    ]

    atm = None
    if calls and puts:
        c_iv = calls[0]["mark_iv"]
        p_iv = puts[0]["mark_iv"]
        if c_iv is not None and p_iv is not None:
            atm = 0.5 * (c_iv + p_iv)

    def pick_delta(typ, target):
        candidates = []
        for r in rows:
            if r["type"] != typ or r["delta"] is None:
                continue
            dist = abs(r["delta"] - target)
            if dist <= 0.05:
                candidates.append(
                    (
                        dist,
                        abs(math.log(r["strike"] / s)),
                        r["strike"],
                        r,
                    )
                )
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[0], x[1], x[2]))
        return candidates[0][3]

    c25 = pick_delta("call", 0.25)
    p25 = pick_delta("put", -0.25)
    delta_pair = None
    if (
        c25 is not None
        and p25 is not None
        and c25["mark_iv"] is not None
        and p25["mark_iv"] is not None
    ):
        delta_pair = (c25["mark_iv"], p25["mark_iv"])

    put_oi = sum(
        r["open_interest"]
        for r in rows
        if r["type"] == "put"
        and r["open_interest"] is not None
        and r["open_interest"] > 0
    )
    call_oi = sum(
        r["open_interest"]
        for r in rows
        if r["type"] == "call"
        and r["open_interest"] is not None
        and r["open_interest"] > 0
    )
    denom = put_oi + call_oi
    oi = None if denom <= 0 else (put_oi - call_oi) / denom

    return {
        "atm": atm,
        "delta_pair": delta_pair,
        "oi": oi,
    }


def surface_at(state, currency, t_us):
    fresh = [
        r
        for r in state[currency].values()
        if t_us - base.STALE_US <= r["local_timestamp"] < t_us
    ]
    by_exp = {}
    for r in fresh:
        if r["expiration"] > t_us:
            by_exp.setdefault(r["expiration"], []).append(r)

    e7 = base.choose_expiry(by_exp, t_us, 7, 5, 9)
    e30 = base.choose_expiry(by_exp, t_us, 30, 25, 35)
    anchors = e7 is not None and e30 is not None
    if not anchors:
        return {
            "anchors": False,
            "atm": False,
            "delta": False,
            "oi": False,
            "all": False,
        }

    x7 = _expiry_components(by_exp[e7])
    x30 = _expiry_components(by_exp[e30])

    atm = x7["atm"] is not None and x30["atm"] is not None
    delta = (
        x7["delta_pair"] is not None
        and x30["delta_pair"] is not None
    )
    oi = x7["oi"] is not None and x30["oi"] is not None

    all_ok = atm and delta and oi
    if all_ok:
        c7, p7 = x7["delta_pair"]
        c30, p30 = x30["delta_pair"]
        vals = [
            x7["atm"],
            c7 - p7,
            0.5 * (c7 + p7) - x7["atm"],
            x7["oi"],
            x30["atm"],
            c30 - p30,
            0.5 * (c30 + p30) - x30["atm"],
            x30["oi"],
            x30["atm"] - x7["atm"],
        ]
        all_ok = all(math.isfinite(float(v)) for v in vals)

    return {
        "anchors": anchors,
        "atm": atm,
        "delta": delta,
        "oi": oi,
        "all": all_ok,
    }


base.surface_at = surface_at

# Re-export frozen constants/helpers for tests.
DATES = base.DATES
GRID_COUNT = base.GRID_COUNT
MIN_SUPPORT = base.MIN_SUPPORT
MIN_RUN = base.MIN_RUN
STALE_US = base.STALE_US
choose_expiry = base.choose_expiry
grid_times = base.grid_times
classify_currency = base.classify_currency
source_url = base.source_url


def main():
    base.main()


if __name__ == "__main__":
    main()
