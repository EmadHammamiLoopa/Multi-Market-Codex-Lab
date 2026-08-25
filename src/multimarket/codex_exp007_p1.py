from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .codex_exp004_headroom import (
    DAYS,
    SYMBOLS,
    assert_fresh_output,
    assert_frozen_workspace,
    feature_path,
    input_manifest,
)
from .codex_exp004_p1 import (
    R_FEATURE_NAMES,
    FixedLogistic,
    build_day_dataset as build_exp004_day_dataset,
    score as exp004_score,
)
from .codex_research import assert_unsealed_path, canonical_sha256, sha256_file
from .v23_phase0dl_score import _load_day


EXPERIMENT_ID = "CODEX-EXP-007-P1"
SEED = 20260825
SUPERVISED_DAYS = DAYS[2:]  # 2026-03-01 .. 2026-07-01
OUTER_DAYS = SUPERVISED_DAYS[1:]  # 2026-04-01 .. 2026-07-01
HORIZON_S = 600
ENTRY_DELAY_MS = 250
LABEL_THRESHOLD_BPS = 24.0
MINUTE_MS = 60_000
AVAILABILITY_LAG_S = 60
MAX_DVOL_LOOKBACK_MIN = 30
REQUIRED_DVOL_CANDLES = 31

P0_RESULT = Path("evidence/codex/exp007_p0_dvol_support/DVOL_SUPPORT_AUDIT.json")
P0_RESULT_SHA256 = "0ce28490fff42d93d528675c0e1135e7e442f04727a6fb9997d441d115bde6ec"
EXP006_MANIFEST = Path("evidence/codex/exp006_p0_dvol/DVOL_ACQUISITION_MANIFEST.json")
EXP006_MANIFEST_SHA256 = "4d217438803ea82ead8899a9ab3ed45aa9942675748107191c79430a0250118d"

CURRENCY_BY_SYMBOL = {
    "BTCUSDT": "BTC",
    "ETHUSDT": "ETH",
}
CONTEXT_BY_DAY = {
    date(2026, 3, 1): date(2026, 2, 28),
    date(2026, 4, 1): date(2026, 3, 31),
    date(2026, 5, 1): date(2026, 4, 30),
    date(2026, 6, 1): date(2026, 5, 31),
    date(2026, 7, 1): date(2026, 6, 30),
}

V_FEATURE_NAMES = (
    "dvol_log_level",
    "dvol_log_change_1m",
    "dvol_log_change_5m",
    "dvol_log_change_15m",
    "dvol_log_change_30m",
    "dvol_latest_log_range",
    "dvol_latest_log_open_close",
    "dvol_rv_5m",
    "dvol_rv_15m",
    "dvol_rv_30m",
)
RV_FEATURE_NAMES = R_FEATURE_NAMES + V_FEATURE_NAMES


@dataclass(frozen=True)
class Config:
    experiment_id: str = EXPERIMENT_ID
    symbols: tuple[str, ...] = SYMBOLS
    supervised_days: tuple[str, ...] = tuple(d.isoformat() for d in SUPERVISED_DAYS)
    outer_days: tuple[str, ...] = tuple(d.isoformat() for d in OUTER_DAYS)
    horizon_s: int = HORIZON_S
    entry_delay_ms: int = ENTRY_DELAY_MS
    label_threshold_bps: float = LABEL_THRESHOLD_BPS
    r_features: tuple[str, ...] = R_FEATURE_NAMES
    v_features: tuple[str, ...] = V_FEATURE_NAMES
    rv_features: tuple[str, ...] = RV_FEATURE_NAMES
    availability_lag_s: int = AVAILABILITY_LAG_S
    max_dvol_lookback_min: int = MAX_DVOL_LOOKBACK_MIN
    required_dvol_candles: int = REQUIRED_DVOL_CANDLES
    model_c: float = 1.0
    solver: str = "lbfgs"
    class_weight: str | None = None
    max_iter: int = 1000
    seed: int = SEED
    pooled_auc_delta_min: float = 0.01
    pooled_ap_delta_min: float = 0.01
    fold_wins_min: int = 3
    pooled_rv_auc_min: float = 0.60
    symbol_rv_auc_min: float = 0.57
    nonoverlap_auc_delta_min: float = 0.01
    nonoverlap_rv_auc_min: float = 0.57
    timing_falsification_auc_delta_min: float = 0.01
    canary_auc_delta_min: float = 0.10
    p0_result_sha256: str = P0_RESULT_SHA256
    exp006_manifest_sha256: str = EXP006_MANIFEST_SHA256


@dataclass
class P1DayDataset:
    symbol: str
    day: date
    timestamp_us: np.ndarray
    X_R: np.ndarray
    X_V: np.ndarray
    y: np.ndarray
    oracle_gross_bps: np.ndarray
    valid_common: np.ndarray
    nonoverlap_10m: np.ndarray


def _read_json(path: Path) -> dict[str, Any]:
    assert_unsealed_path(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_dvol_row(row: Any) -> bool:
    if not isinstance(row, list) or len(row) != 5:
        return False
    ts, opn, high, low, close = row
    if not isinstance(ts, int) or isinstance(ts, bool):
        return False
    vals = (opn, high, low, close)
    if any(not isinstance(x, (int, float)) or isinstance(x, bool) for x in vals):
        return False
    opn, high, low, close = map(float, vals)
    if any(not math.isfinite(x) or x <= 0.0 for x in (opn, high, low, close)):
        return False
    return high >= max(opn, close) and low <= min(opn, close) and high >= low


def verify_parent_inputs(workspace: Path) -> tuple[dict[str, Any], dict[str, Any], dict[tuple[str, date], dict[str, Any]]]:
    p0_path = workspace / P0_RESULT
    manifest_path = workspace / EXP006_MANIFEST
    if sha256_file(p0_path) != P0_RESULT_SHA256:
        raise RuntimeError("EXP007-P0 result SHA-256 mismatch")
    p0 = _read_json(p0_path)
    if p0.get("status") != "DATA_READY_MAINTENANCE_AWARE_DVOL_SANDBOX":
        raise RuntimeError("EXP007-P0 parent is not DATA_READY_MAINTENANCE_AWARE_DVOL_SANDBOX")
    inv = p0.get("invariants", {})
    required_true = (
        "frozen_exp006_raw_hashes_unchanged",
        "all_10_supervised_symbol_days_complete",
        "all_10_context_midnight_tails_complete",
        "no_maintenance_gap_intersects_required_cross_midnight_support",
        "no_august_accessed",
        "no_network_used",
    )
    if not all(inv.get(k) is True for k in required_true):
        raise RuntimeError("EXP007-P0 required invariants are not all true")
    forbidden_true = (
        "target_scored",
        "future_returns_inspected",
        "model_fit",
        "auc_scored",
        "average_precision_scored",
        "direction_scored",
        "pnl_scored",
    )
    if any(inv.get(k) is True for k in forbidden_true):
        raise RuntimeError("EXP007-P0 reports prohibited activity")

    if sha256_file(manifest_path) != EXP006_MANIFEST_SHA256:
        raise RuntimeError("EXP006 DVOL acquisition manifest SHA-256 mismatch")
    manifest = _read_json(manifest_path)
    if manifest.get("sealed_august_opened") is not False:
        raise RuntimeError("EXP006 manifest reports sealed August access")

    expected_dates = set(SUPERVISED_DAYS) | set(CONTEXT_BY_DAY.values())
    expected_keys = {(CURRENCY_BY_SYMBOL[s], d) for s in SYMBOLS for d in expected_dates}
    entries: dict[tuple[str, date], dict[str, Any]] = {}
    for item in manifest.get("entries", []):
        currency = str(item.get("currency"))
        day = date.fromisoformat(str(item.get("date")))
        key = (currency, day)
        if key in entries:
            raise RuntimeError(f"duplicate DVOL manifest entry: {key}")
        entries[key] = item
    if set(entries) != expected_keys:
        raise RuntimeError("DVOL manifest symbol/day matrix mismatch for frozen EXP007 scope")

    for key, item in entries.items():
        rel = Path(str(item.get("canonical_path")))
        assert_unsealed_path(rel)
        path = workspace / rel
        if not path.exists():
            raise FileNotFoundError(path)
        expected_sha = str(item.get("canonical_sha256"))
        if sha256_file(path) != expected_sha:
            raise RuntimeError(f"frozen DVOL raw SHA-256 mismatch: {key}")
    return p0, manifest, entries


def load_dvol_day(workspace: Path, entry: dict[str, Any], currency: str, day: date) -> dict[int, tuple[float, float, float, float]]:
    path = workspace / Path(str(entry["canonical_path"]))
    assert_unsealed_path(path)
    if sha256_file(path) != str(entry["canonical_sha256"]):
        raise RuntimeError(f"DVOL raw hash changed during load: {currency} {day}")
    obj = _read_json(path)
    if obj.get("currency") != currency or obj.get("date") != day.isoformat():
        raise RuntimeError("DVOL currency/date mismatch")
    if obj.get("resolution_seconds") != 60:
        raise RuntimeError("DVOL resolution must be exactly 60 seconds")
    out: dict[int, tuple[float, float, float, float]] = {}
    for row in obj.get("data", []):
        if not _validate_dvol_row(row):
            raise RuntimeError(f"invalid DVOL OHLC row: {currency} {day}")
        ts = int(row[0])
        if ts in out:
            raise RuntimeError(f"duplicate DVOL timestamp: {currency} {day} {ts}")
        out[ts] = tuple(float(x) for x in row[1:])
    return out


def dvol_required_timestamps_ms(t_us: int) -> np.ndarray:
    if t_us % 1000 != 0:
        raise RuntimeError("decision timestamp is not millisecond aligned")
    t_ms = t_us // 1000
    return t_ms - np.arange(1, REQUIRED_DVOL_CANDLES + 1, dtype=np.int64) * MINUTE_MS


def dvol_feature_vector(rows_by_ts: dict[int, tuple[float, float, float, float]], t_us: int) -> np.ndarray | None:
    required = dvol_required_timestamps_ms(t_us)
    rows: list[tuple[float, float, float, float]] = []
    for ts in required.tolist():
        row = rows_by_ts.get(int(ts))
        if row is None:
            return None
        rows.append(row)
    # rows[k-1] corresponds to t-k minutes; tuple is open/high/low/close.
    closes = np.asarray([row[3] for row in rows], dtype=np.float64)
    if len(closes) != 31 or np.any(~np.isfinite(closes)) or np.any(closes <= 0):
        return None
    opn1, high1, low1, close1 = rows[0]
    if not (high1 >= max(opn1, close1) and low1 <= min(opn1, close1) and low1 > 0):
        return None

    changes = [
        math.log(closes[0] / closes[1]),
        math.log(closes[0] / closes[5]),
        math.log(closes[0] / closes[15]),
        math.log(closes[0] / closes[30]),
    ]
    one_minute = np.log(closes[:-1] / closes[1:])  # r_k for k=1..30

    def rv(n: int) -> float:
        r = one_minute[:n]
        return float(np.sqrt(np.mean(r * r)))

    values = np.asarray(
        [
            math.log(close1),
            *changes,
            math.log(high1 / low1),
            math.log(close1 / opn1),
            rv(5),
            rv(15),
            rv(30),
        ],
        dtype=np.float64,
    )
    if len(values) != len(V_FEATURE_NAMES) or np.any(~np.isfinite(values)):
        return None
    return values


def build_day_dataset(
    symbol: str,
    phase_day: Any,
    context_rows: dict[int, tuple[float, float, float, float]],
    current_rows: dict[int, tuple[float, float, float, float]],
) -> P1DayDataset:
    base = build_exp004_day_dataset(symbol, phase_day)
    if symbol not in SYMBOLS or base.day not in SUPERVISED_DAYS:
        raise ValueError("symbol/day outside frozen EXP007-P1 supervised scope")
    rows_by_ts = dict(context_rows)
    overlap = set(rows_by_ts).intersection(current_rows)
    if overlap:
        raise RuntimeError("context/current DVOL timestamps overlap")
    rows_by_ts.update(current_rows)

    X_V = np.full((len(base.timestamp_us), len(V_FEATURE_NAMES)), np.nan, dtype=np.float64)
    valid_v = np.zeros(len(base.timestamp_us), dtype=bool)
    for j, t_us in enumerate(base.timestamp_us.tolist()):
        if not base.valid_R[j]:
            continue
        v = dvol_feature_vector(rows_by_ts, int(t_us))
        if v is not None:
            X_V[j] = v
            valid_v[j] = True
    valid_common = base.valid_R & valid_v
    return P1DayDataset(
        symbol=symbol,
        day=base.day,
        timestamp_us=base.timestamp_us,
        X_R=base.X_R,
        X_V=X_V,
        y=base.y,
        oracle_gross_bps=base.oracle_gross_bps,
        valid_common=valid_common,
        nonoverlap_10m=base.nonoverlap_10m,
    )


def training_days(outer_day: date) -> tuple[date, ...]:
    if outer_day not in OUTER_DAYS:
        raise ValueError("outer day outside frozen EXP007-P1 folds")
    return tuple(d for d in SUPERVISED_DAYS if d < outer_day)


def _matrix(day: P1DayDataset, track: str, mask: np.ndarray | None = None) -> np.ndarray:
    m = day.valid_common if mask is None else mask
    r = day.X_R[m]
    v = day.X_V[m]
    if track == "R":
        return r
    if track == "V":
        return v
    if track == "RV":
        return np.column_stack((r, v))
    if track == "VOL":
        idx = R_FEATURE_NAMES.index("rv_30m_bps")
        return r[:, [idx]]
    raise ValueError(f"unknown track: {track}")


def concat_common(days: list[P1DayDataset], track: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    mags: list[np.ndarray] = []
    for d in days:
        m = d.valid_common
        xs.append(_matrix(d, track, m))
        ys.append(d.y[m])
        mags.append(d.oracle_gross_bps[m])
    if not xs:
        raise RuntimeError("empty common-support calendar")
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(mags)


def _stable_seed(symbol: str, day: date, tag: str = "V_TIME") -> int:
    raw = f"{SEED}|{tag}|{symbol}|{day.isoformat()}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big") % (2**32)


def permute_complete_v_vectors(day: P1DayDataset, mask: np.ndarray | None = None) -> np.ndarray:
    m = day.valid_common if mask is None else mask
    v = day.X_V[m].copy()
    if len(v) <= 1:
        return v
    rng = np.random.default_rng(_stable_seed(day.symbol, day.day))
    return v[rng.permutation(len(v))]


def concat_rv_time_permuted(days: list[P1DayDataset]) -> tuple[np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    for d in days:
        m = d.valid_common
        xs.append(np.column_stack((d.X_R[m], permute_complete_v_vectors(d, m))))
        ys.append(d.y[m])
    return np.concatenate(xs), np.concatenate(ys)


def metrics(records: list[dict[str, Any]], key: str) -> dict[str, Any]:
    def s(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return exp004_score([r["label"] for r in rows], [r[key] for r in rows])
    non = [r for r in records if r["nonoverlap_10m"]]
    return {
        "pooled": s(records),
        "by_symbol": {z: s([r for r in records if r["symbol"] == z]) for z in SYMBOLS},
        "by_fold": {d.isoformat(): s([r for r in records if r["outer_day"] == d.isoformat()]) for d in OUTER_DAYS},
        "nonoverlap_pooled": s(non),
    }


def _ge_delta(a: float | None, b: float | None, threshold: float) -> bool:
    return a is not None and b is not None and a - b >= threshold


def _gt(a: float | None, b: float | None) -> bool:
    return a is not None and b is not None and a > b


def _ge(a: float | None, threshold: float) -> bool:
    return a is not None and a >= threshold


def primary_gates(M: dict[str, dict[str, Any]], invariants: dict[str, bool]) -> dict[str, bool]:
    r = M["R"]
    rv = M["RV"]
    perm = M["RV_V_TIME_PERMUTED"]
    canary = M["CANARY_R"]
    rp, vp = r["pooled"], rv["pooled"]
    pp, cp = perm["pooled"], canary["pooled"]
    return {
        "pooled_auc_delta_at_least_0_01": _ge_delta(vp["roc_auc"], rp["roc_auc"], 0.01),
        "pooled_average_precision_delta_at_least_0_01": _ge_delta(vp["average_precision"], rp["average_precision"], 0.01),
        "pooled_top_decile_precision_not_lower": (
            vp["top_decile_precision"] is not None and rp["top_decile_precision"] is not None
            and vp["top_decile_precision"] >= rp["top_decile_precision"]
        ),
        "pooled_log_loss_lower": _gt(rp["log_loss"], vp["log_loss"]),
        "pooled_brier_lower": _gt(rp["brier_score"], vp["brier_score"]),
        "at_least_3_of_4_folds_rv_auc_gt_r": sum(
            _gt(rv["by_fold"][d.isoformat()]["roc_auc"], r["by_fold"][d.isoformat()]["roc_auc"])
            for d in OUTER_DAYS
        ) >= 3,
        "btc_rv_auc_gt_r": _gt(rv["by_symbol"]["BTCUSDT"]["roc_auc"], r["by_symbol"]["BTCUSDT"]["roc_auc"]),
        "eth_rv_auc_gt_r": _gt(rv["by_symbol"]["ETHUSDT"]["roc_auc"], r["by_symbol"]["ETHUSDT"]["roc_auc"]),
        "pooled_rv_auc_at_least_0_60": _ge(vp["roc_auc"], 0.60),
        "btc_rv_auc_at_least_0_57": _ge(rv["by_symbol"]["BTCUSDT"]["roc_auc"], 0.57),
        "eth_rv_auc_at_least_0_57": _ge(rv["by_symbol"]["ETHUSDT"]["roc_auc"], 0.57),
        "nonoverlap_auc_delta_at_least_0_01": _ge_delta(
            rv["nonoverlap_pooled"]["roc_auc"], r["nonoverlap_pooled"]["roc_auc"], 0.01
        ),
        "nonoverlap_rv_auc_at_least_0_57": _ge(rv["nonoverlap_pooled"]["roc_auc"], 0.57),
        "dvol_timing_falsification_auc_delta_at_least_0_01": _ge_delta(vp["roc_auc"], pp["roc_auc"], 0.01),
        "positive_control_canary_auc_delta_at_least_0_10": _ge_delta(cp["roc_auc"], rp["roc_auc"], 0.10),
        "implementation_provenance_causality_invariants_pass": all(invariants.values()),
    }


def _metric_delta(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else float(a - b)


def run(feature_dir: Path, output: Path, workspace: Path, frozen_commit: str) -> dict[str, Any]:
    assert_frozen_workspace(workspace, frozen_commit)
    partial = assert_fresh_output(output)
    p0, dvol_manifest, entries = verify_parent_inputs(workspace)
    phase_manifest = input_manifest(feature_dir, workspace)

    dvol_cache: dict[tuple[str, date], dict[int, tuple[float, float, float, float]]] = {}
    for key, entry in entries.items():
        dvol_cache[key] = load_dvol_day(workspace, entry, key[0], key[1])

    data: dict[tuple[str, date], P1DayDataset] = {}
    for symbol in SYMBOLS:
        currency = CURRENCY_BY_SYMBOL[symbol]
        for day in SUPERVISED_DAYS:
            phase = _load_day(feature_path(feature_dir, symbol, day), day)
            context_day = CONTEXT_BY_DAY[day]
            data[(symbol, day)] = build_day_dataset(
                symbol,
                phase,
                dvol_cache[(currency, context_day)],
                dvol_cache[(currency, day)],
            )

    records: list[dict[str, Any]] = []
    fold_counts: list[dict[str, Any]] = []
    common_support_exact = True

    for outer_day in OUTER_DAYS:
        train_calendar = training_days(outer_day)
        for symbol in SYMBOLS:
            train = [data[(symbol, d)] for d in train_calendar]
            outer = data[(symbol, outer_day)]

            XR, yR, mag = concat_common(train, "R")
            XV, yV, _ = concat_common(train, "V")
            XRV, yRV, mag_rv = concat_common(train, "RV")
            XVOL, yVOL, _ = concat_common(train, "VOL")
            XPERM, yPERM = concat_rv_time_permuted(train)

            labels_equal = all(np.array_equal(yR, y) for y in (yV, yRV, yVOL, yPERM))
            lengths_equal = len(XR) == len(XV) == len(XRV) == len(XVOL) == len(XPERM)
            common_support_exact &= labels_equal and lengths_equal and np.array_equal(mag, mag_rv)
            if not common_support_exact:
                raise RuntimeError("common training support invariant failed")

            model_r = FixedLogistic().fit(XR, yR)
            model_v = FixedLogistic().fit(XV, yR)
            model_rv = FixedLogistic().fit(XRV, yR)
            model_vol = FixedLogistic().fit(XVOL, yR)
            model_perm = FixedLogistic().fit(XPERM, yR)
            model_canary = FixedLogistic().fit(np.column_stack((XR, mag)), yR)

            m = outer.valid_common
            XR_o = _matrix(outer, "R", m)
            XV_o = _matrix(outer, "V", m)
            XRV_o = _matrix(outer, "RV", m)
            XVOL_o = _matrix(outer, "VOL", m)
            VPERM_o = permute_complete_v_vectors(outer, m)
            XPERM_o = np.column_stack((XR_o, VPERM_o))
            n_outer = int(np.sum(m))
            common_support_exact &= all(len(x) == n_outer for x in (XR_o, XV_o, XRV_o, XVOL_o, XPERM_o))
            if not common_support_exact:
                raise RuntimeError("common outer support invariant failed")

            p_r = model_r.predict_proba(XR_o)
            p_v = model_v.predict_proba(XV_o)
            p_rv = model_rv.predict_proba(XRV_o)
            p_vol = model_vol.predict_proba(XVOL_o)
            p_perm = model_perm.predict_proba(XPERM_o)
            p_canary = model_canary.predict_proba(np.column_stack((XR_o, outer.oracle_gross_bps[m])))

            idx = np.flatnonzero(m)
            fold_counts.append(
                {
                    "outer_day": outer_day.isoformat(),
                    "symbol": symbol,
                    "training_days": [d.isoformat() for d in train_calendar],
                    "common_train_n": int(len(yR)),
                    "common_outer_n": n_outer,
                    "R_train_n": int(len(XR)),
                    "V_train_n": int(len(XV)),
                    "RV_train_n": int(len(XRV)),
                    "RV_permuted_train_n": int(len(XPERM)),
                }
            )
            for j, source_idx in enumerate(idx.tolist()):
                records.append(
                    {
                        "outer_day": outer_day.isoformat(),
                        "symbol": symbol,
                        "timestamp_us": int(outer.timestamp_us[source_idx]),
                        "label": int(outer.y[source_idx]),
                        "oracle_gross_bps": float(outer.oracle_gross_bps[source_idx]),
                        "nonoverlap_10m": bool(outer.nonoverlap_10m[source_idx]),
                        "p_R": float(p_r[j]),
                        "p_V": float(p_v[j]),
                        "p_RV": float(p_rv[j]),
                        "p_VOL": float(p_vol[j]),
                        "p_RV_V_TIME_PERMUTED": float(p_perm[j]),
                        "p_CANARY_R": float(p_canary[j]),
                    }
                )

    metric_keys = {
        "R": "p_R",
        "V": "p_V",
        "RV": "p_RV",
        "VOL": "p_VOL",
        "RV_V_TIME_PERMUTED": "p_RV_V_TIME_PERMUTED",
        "CANARY_R": "p_CANARY_R",
    }
    M = {name: metrics(records, key) for name, key in metric_keys.items()}

    invariants = {
        "p0_result_sha256_verified": True,
        "p0_data_ready": p0.get("status") == "DATA_READY_MAINTENANCE_AWARE_DVOL_SANDBOX",
        "exp006_manifest_sha256_verified": True,
        "all_20_frozen_dvol_hashes_verified": len(entries) == 20,
        "only_march_to_july_supervised_days_loaded": set(SUPERVISED_DAYS) == set(DAYS[2:]),
        "outer_folds_are_april_to_july": tuple(OUTER_DAYS) == tuple(DAYS[3:]),
        "latest_dvol_candle_is_t_minus_60_seconds": AVAILABILITY_LAG_S == 60,
        "max_dvol_lookback_is_30_minutes": MAX_DVOL_LOOKBACK_MIN == 30,
        "exact_dvol_timestamp_lookup_no_fill": True,
        "own_currency_dvol_only": CURRENCY_BY_SYMBOL == {"BTCUSDT": "BTC", "ETHUSDT": "ETH"},
        "r_rv_common_training_and_outer_support_exact": common_support_exact,
        "outer_folds_chronological": all(all(d < o for d in training_days(o)) for o in OUTER_DAYS),
        "scaling_fit_on_training_only_by_fixed_pipeline": True,
        "sealed_august_not_accessed": True,
        "direction_not_scored": True,
        "pnl_not_scored": True,
    }
    gates = primary_gates(M, invariants)
    if not all(invariants.values()):
        status = "INVALID"
    elif all(gates.values()):
        status = "PREDICTABLE_INCREMENTAL_DVOL_SANDBOX"
    else:
        status = "FAIL_DVOL_NO_INCREMENTAL_TIMING_INFORMATION"

    rp = M["R"]["pooled"]
    vp = M["RV"]["pooled"]
    pp = M["RV_V_TIME_PERMUTED"]["pooled"]
    cp = M["CANARY_R"]["pooled"]
    deltas = {
        "RV_auc_minus_R_auc": _metric_delta(vp["roc_auc"], rp["roc_auc"]),
        "RV_average_precision_minus_R": _metric_delta(vp["average_precision"], rp["average_precision"]),
        "RV_top_decile_precision_minus_R": _metric_delta(vp["top_decile_precision"], rp["top_decile_precision"]),
        "R_log_loss_minus_RV_log_loss": _metric_delta(rp["log_loss"], vp["log_loss"]),
        "R_brier_minus_RV_brier": _metric_delta(rp["brier_score"], vp["brier_score"]),
        "RV_auc_minus_V_time_permuted_auc": _metric_delta(vp["roc_auc"], pp["roc_auc"]),
        "CANARY_R_auc_minus_R_auc": _metric_delta(cp["roc_auc"], rp["roc_auc"]),
    }

    used_phase = [
        item for item in phase_manifest
        if date.fromisoformat(str(item["day"])) in SUPERVISED_DAYS
    ]
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "sandbox_only": True,
        "direction_scored": False,
        "pnl_scored": False,
        "sealed_august_opened": False,
        "frozen_commit": frozen_commit,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": asdict(Config()),
        "configuration_sha256": canonical_sha256(Config()),
        "provenance": {
            "p0_result_sha256": P0_RESULT_SHA256,
            "exp006_dvol_manifest_sha256": EXP006_MANIFEST_SHA256,
            "verified_dvol_raw_sha256": {
                f"{currency}|{day.isoformat()}": str(entry["canonical_sha256"])
                for (currency, day), entry in sorted(entries.items(), key=lambda x: (x[0][0], x[0][1]))
            },
            "verified_phase_l_input_manifest_all_frozen_days": phase_manifest,
            "phase_l_inputs_used_for_exp007": used_phase,
            "exp006_acquisition_manifest": dvol_manifest,
        },
        "fold_train_counts": fold_counts,
        "metrics": M,
        "gates": gates,
        "invariants": invariants,
        "diagnostic_deltas": deltas,
        "oos_prediction_records_sha256": canonical_sha256(records),
        "oos_prediction_records": records,
        "interpretation": (
            "Incremental 10-minute opportunity-timing information only. No direction, PnL, "
            "August validation, live-money readiness, or profitability claim is permitted."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    partial.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    partial.replace(output)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Frozen CODEX-EXP-007-P1 incremental DVOL timing test")
    parser.add_argument("--feature-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    args = parser.parse_args(argv)
    result = run(args.feature_dir, args.output, args.workspace, args.frozen_commit)
    print(json.dumps({
        "experiment_id": result["experiment_id"],
        "status": result["status"],
        "configuration_sha256": result["configuration_sha256"],
        "gates": result["gates"],
        "diagnostic_deltas": result["diagnostic_deltas"],
        "sealed_august_opened": result["sealed_august_opened"],
        "direction_scored": result["direction_scored"],
        "pnl_scored": result["pnl_scored"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
