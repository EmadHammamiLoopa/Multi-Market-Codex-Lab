from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .codex_exp004_headroom import (
    DAYS,
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


EXPERIMENT_ID = "CODEX-EXP-011-P1"
PASS_STATUS = "PREDICTABLE_INCREMENTAL_BTC_OPTIONS_TRADE_FLOW_SANDBOX"
FAIL_STATUS = "FAIL_BTC_OPTIONS_TRADE_FLOW_NO_INCREMENTAL_TIMING_INFORMATION"
SEED = 20260825
SYMBOL = "BTCUSDT"
SUPERVISED_DAYS = DAYS[2:]  # 2026-03-01 .. 2026-07-01
OUTER_DAYS = SUPERVISED_DAYS[1:]  # 2026-04-01 .. 2026-07-01
WINDOW_MINUTES = (1, 5, 15, 30)
GRID_START_MINUTE = 30
GRID_END_MINUTE = 23 * 60 + 49
HORIZON_S = 600
ENTRY_DELAY_MS = 250
LABEL_THRESHOLD_BPS = 24.0

EXP010_AUDIT = Path(
    "evidence/codex/exp010_p0_unified_options_trade_flow/"
    "UNIFIED_OPTIONS_TRADE_FLOW_P0_AUDIT.json"
)
EXP010_AUDIT_SHA256 = "4fa9b88dd5f9353c05ee00fcd3aa223433d9bbd2a8a100dd0fcdde976e7b709d"
RAW_ROOT = Path("evidence/codex/exp009_p0_options_trade_flow/raw")
RAW_SHA256 = {
    date(2026, 3, 1): "34835b3e3a022fac0e7270b3e1aca643b01e63b3bbffdab50c99c70dea9af6ba",
    date(2026, 4, 1): "175b24f76bceb68b68c8b6caa04682cb4523bc2e5becc39c41fcf92456a1b605",
    date(2026, 5, 1): "287aaf1a1c62b597c1d46f9f408eef9a0d7c1a73d47ef9edb809f9dc53adda78",
    date(2026, 6, 1): "6076038bb1c07ed4e70a5ca696e04213a5e7e9ab9bfa835360764901925fc6a7",
    date(2026, 7, 1): "02be481f94ac9b66dd43c9f185488b0c2af8f0517f7538d30c6dea565f866bc2",
}
REQUIRED_COLUMNS = {
    "exchange", "symbol", "timestamp", "local_timestamp", "id", "side", "price", "amount"
}
STANDARD_RE = re.compile(
    r"^(BTC|ETH)[-_](\d{1,2}[A-Z]{3}\d{2})[-_]([0-9]+(?:\.[0-9]+)?)[-_]([CP])$",
    re.I,
)
USDC_RE = re.compile(
    r"^(BTC|ETH)_USDC[-_](\d{1,2}[A-Z]{3}\d{2})[-_]([0-9]+(?:\.[0-9]+)?)[-_]([CP])$",
    re.I,
)

FLOW_FEATURE_NAMES = tuple(
    f"optflow_{w}m_{name}"
    for w in WINDOW_MINUTES
    for name in (
        "log1p_trade_count",
        "log1p_amount",
        "aggressor_amount_imbalance",
        "abs_aggressor_amount_imbalance",
        "call_put_amount_imbalance",
        "abs_call_put_amount_imbalance",
    )
)
RF_FEATURE_NAMES = R_FEATURE_NAMES + FLOW_FEATURE_NAMES


@dataclass(frozen=True)
class Config:
    experiment_id: str = EXPERIMENT_ID
    symbol: str = SYMBOL
    supervised_days: tuple[str, ...] = tuple(d.isoformat() for d in SUPERVISED_DAYS)
    outer_days: tuple[str, ...] = tuple(d.isoformat() for d in OUTER_DAYS)
    windows_minutes: tuple[int, ...] = WINDOW_MINUTES
    grid_start_minute: int = GRID_START_MINUTE
    grid_end_minute: int = GRID_END_MINUTE
    horizon_s: int = HORIZON_S
    entry_delay_ms: int = ENTRY_DELAY_MS
    label_threshold_bps: float = LABEL_THRESHOLD_BPS
    r_features: tuple[str, ...] = R_FEATURE_NAMES
    flow_features: tuple[str, ...] = FLOW_FEATURE_NAMES
    rf_features: tuple[str, ...] = RF_FEATURE_NAMES
    model_c: float = 1.0
    solver: str = "lbfgs"
    class_weight: str | None = None
    max_iter: int = 1000
    seed: int = SEED
    pooled_auc_delta_min: float = 0.01
    pooled_ap_delta_min: float = 0.01
    fold_wins_min: int = 3
    pooled_rf_auc_min: float = 0.60
    nonoverlap_auc_delta_min: float = 0.01
    nonoverlap_rf_auc_min: float = 0.57
    timing_falsification_auc_delta_min: float = 0.01
    canary_auc_delta_min: float = 0.10
    exp010_audit_sha256: str = EXP010_AUDIT_SHA256


@dataclass(frozen=True)
class OptionTrade:
    symbol: str
    family: str
    option_type: str
    local_timestamp: int
    timestamp: int
    trade_id: str
    side: str
    amount: float
    price: float


@dataclass
class P1DayDataset:
    symbol: str
    day: date
    timestamp_us: np.ndarray
    X_R: np.ndarray
    X_F: np.ndarray
    y: np.ndarray
    oracle_gross_bps: np.ndarray
    valid_common: np.ndarray
    nonoverlap_10m: np.ndarray


def _read_json(path: Path) -> dict[str, Any]:
    assert_unsealed_path(path)
    return json.loads(path.read_text(encoding="utf-8"))


def day_start_us(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1_000_000)


def raw_path(day: date) -> Path:
    return RAW_ROOT / f"deribit_trades_{day.isoformat()}_OPTIONS.csv.gz"


def parse_symbol(symbol: str) -> dict[str, Any] | None:
    u = (symbol or "").strip().upper()
    family: str | None = None
    m = USDC_RE.fullmatch(u)
    if m:
        family = "usdc_linear"
    else:
        m = STANDARD_RE.fullmatch(u)
        if m:
            family = "standard"
    if not m:
        return None
    currency, expiry_text, strike_text, cp = m.groups()
    expiry = datetime.strptime(expiry_text, "%d%b%y").replace(tzinfo=timezone.utc)
    strike = float(strike_text)
    if not math.isfinite(strike) or strike <= 0:
        return None
    return {
        "currency": currency,
        "family": family,
        "expiration": int(expiry.timestamp() * 1_000_000),
        "strike": strike,
        "option_type": "call" if cp.upper() == "C" else "put",
    }


def parse_trade(raw: dict[str, str]) -> OptionTrade | None:
    meta = parse_symbol(raw.get("symbol", ""))
    if meta is None or meta["currency"] != "BTC":
        return None
    side = (raw.get("side") or "").strip().lower()
    if side not in {"buy", "sell"}:
        raise ValueError("invalid BTC option aggressor side")
    trade_id = (raw.get("id") or "").strip()
    if not trade_id:
        raise ValueError("missing BTC option trade id")
    timestamp = int(raw.get("timestamp", ""))
    local_timestamp = int(raw.get("local_timestamp", ""))
    amount = float(raw.get("amount", ""))
    price = float(raw.get("price", ""))
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("invalid BTC option amount")
    if not math.isfinite(price) or price <= 0:
        raise ValueError("invalid BTC option price")
    return OptionTrade(
        symbol=str(raw["symbol"]),
        family=str(meta["family"]),
        option_type=str(meta["option_type"]),
        local_timestamp=local_timestamp,
        timestamp=timestamp,
        trade_id=trade_id,
        side=side,
        amount=amount,
        price=price,
    )


def verify_parent_and_raw(workspace: Path) -> tuple[dict[str, Any], dict[date, str]]:
    audit_path = workspace / EXP010_AUDIT
    if sha256_file(audit_path) != EXP010_AUDIT_SHA256:
        raise RuntimeError("EXP010 audit SHA-256 mismatch")
    audit = _read_json(audit_path)
    if audit.get("experiment_id") != "CODEX-EXP-010-P0":
        raise RuntimeError("wrong EXP010 parent audit")
    if audit.get("network_accessed") is not False or audit.get("sealed_august_opened") is not False:
        raise RuntimeError("EXP010 parent provenance invariant failed")
    forbidden = (
        "target_scored", "future_return_inspected", "model_fit", "auc_scored",
        "direction_scored", "pnl_scored",
    )
    if any(audit.get(k) is True for k in forbidden):
        raise RuntimeError("EXP010 reports prohibited predictive activity")
    days = audit.get("days", [])
    if [str(x.get("date")) for x in days] != [d.isoformat() for d in SUPERVISED_DAYS]:
        raise RuntimeError("EXP010 frozen date sequence mismatch")
    for item in days:
        if int(item.get("eligible_parse_errors", -1)) != 0:
            raise RuntimeError("EXP010 eligible parse errors are not zero")
        checks = item.get("checks", {})
        if checks.get("btc_support") is not True:
            raise RuntimeError("EXP010 BTC readiness did not pass every day")

    observed: dict[date, str] = {}
    for day, expected in RAW_SHA256.items():
        path = workspace / raw_path(day)
        assert_unsealed_path(path)
        if not path.exists():
            raise FileNotFoundError(path)
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"frozen options-trades SHA mismatch: {day}")
        observed[day] = actual
    return audit, observed


def load_btc_trades(workspace: Path, day: date) -> list[OptionTrade]:
    path = workspace / raw_path(day)
    assert_unsealed_path(path)
    if sha256_file(path) != RAW_SHA256[day]:
        raise RuntimeError(f"raw hash changed during BTC option load: {day}")
    start = day_start_us(day)
    end = start + 86_400_000_000
    rows: list[OptionTrade] = []
    seen: dict[str, tuple[Any, ...]] = {}
    last_local: int | None = None
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])
        if not REQUIRED_COLUMNS.issubset(columns):
            raise RuntimeError(f"options-trades schema mismatch: {day}")
        for raw in reader:
            local_text = raw.get("local_timestamp", "")
            try:
                local = int(local_text)
            except Exception as exc:
                raise RuntimeError(f"invalid local_timestamp in frozen raw: {day}") from exc
            if last_local is not None and local < last_local:
                raise RuntimeError(f"local_timestamp not nondecreasing: {day}")
            last_local = local
            if not (start <= local < end):
                raise RuntimeError(f"outside-day row in frozen raw: {day}")
            try:
                trade = parse_trade(raw)
            except Exception as exc:
                symbol = (raw.get("symbol") or "").upper()
                if symbol.startswith(("BTC-", "BTC_")):
                    raise RuntimeError(f"eligible BTC parse error: {day} {symbol}") from exc
                continue
            if trade is None:
                continue
            econ = (
                trade.symbol, trade.timestamp, trade.local_timestamp, trade.side,
                trade.amount, trade.price, trade.family, trade.option_type,
            )
            if trade.trade_id in seen:
                if seen[trade.trade_id] == econ:
                    continue
                raise RuntimeError(f"conflicting BTC option trade id: {day} {trade.trade_id}")
            seen[trade.trade_id] = econ
            rows.append(trade)
    return rows


def flow_feature_vector(trades: list[OptionTrade], t_us: int) -> np.ndarray | None:
    timestamps = [x.local_timestamp for x in trades]
    hi = bisect.bisect_left(timestamps, t_us)
    values: list[float] = []
    for w in WINDOW_MINUTES:
        lo_ts = t_us - w * 60 * 1_000_000
        lo = bisect.bisect_left(timestamps, lo_ts, 0, hi)
        xs = trades[lo:hi]
        if not xs:
            return None
        n = len(xs)
        total_amount = float(sum(x.amount for x in xs))
        buy_amount = float(sum(x.amount for x in xs if x.side == "buy"))
        sell_amount = float(sum(x.amount for x in xs if x.side == "sell"))
        call_amount = float(sum(x.amount for x in xs if x.option_type == "call"))
        put_amount = float(sum(x.amount for x in xs if x.option_type == "put"))
        if total_amount <= 0 or buy_amount + sell_amount <= 0 or call_amount + put_amount <= 0:
            return None
        aggressor = (buy_amount - sell_amount) / (buy_amount + sell_amount)
        call_put = (call_amount - put_amount) / (call_amount + put_amount)
        values.extend(
            (
                math.log1p(n),
                math.log1p(total_amount),
                aggressor,
                abs(aggressor),
                call_put,
                abs(call_put),
            )
        )
    out = np.asarray(values, dtype=np.float64)
    if len(out) != len(FLOW_FEATURE_NAMES) or np.any(~np.isfinite(out)):
        return None
    return out


def build_day_dataset(symbol: str, phase_day: Any, trades: list[OptionTrade]) -> P1DayDataset:
    if symbol != SYMBOL:
        raise ValueError("EXP011 is BTCUSDT only")
    base = build_exp004_day_dataset(symbol, phase_day)
    if base.day not in SUPERVISED_DAYS:
        raise ValueError("day outside EXP011 supervised scope")
    start = day_start_us(base.day)
    X_F = np.full((len(base.timestamp_us), len(FLOW_FEATURE_NAMES)), np.nan, dtype=np.float64)
    valid_f = np.zeros(len(base.timestamp_us), dtype=bool)
    for j, t_us in enumerate(base.timestamp_us.tolist()):
        minute = int((int(t_us) - start) // 60_000_000)
        if minute < GRID_START_MINUTE or minute > GRID_END_MINUTE:
            continue
        if not base.valid_R[j]:
            continue
        f = flow_feature_vector(trades, int(t_us))
        if f is not None:
            X_F[j] = f
            valid_f[j] = True
    valid_common = base.valid_R & valid_f
    return P1DayDataset(
        symbol=symbol,
        day=base.day,
        timestamp_us=base.timestamp_us,
        X_R=base.X_R,
        X_F=X_F,
        y=base.y,
        oracle_gross_bps=base.oracle_gross_bps,
        valid_common=valid_common,
        nonoverlap_10m=base.nonoverlap_10m,
    )


def training_days(outer_day: date) -> tuple[date, ...]:
    if outer_day not in OUTER_DAYS:
        raise ValueError("outer day outside frozen EXP011 folds")
    return tuple(d for d in SUPERVISED_DAYS if d < outer_day)


def _matrix(day: P1DayDataset, track: str, mask: np.ndarray | None = None) -> np.ndarray:
    m = day.valid_common if mask is None else mask
    r = day.X_R[m]
    f = day.X_F[m]
    if track == "R":
        return r
    if track == "F":
        return f
    if track == "RF":
        return np.column_stack((r, f))
    if track == "VOL":
        idx = R_FEATURE_NAMES.index("rv_30m_bps")
        return r[:, [idx]]
    raise ValueError(f"unknown EXP011 track: {track}")


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
        raise RuntimeError("empty EXP011 common-support calendar")
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(mags)


def _stable_seed(day: date, tag: str = "F_TIME") -> int:
    raw = f"{SEED}|{tag}|{SYMBOL}|{day.isoformat()}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big") % (2**32)


def permute_complete_f_vectors(day: P1DayDataset, mask: np.ndarray | None = None) -> np.ndarray:
    m = day.valid_common if mask is None else mask
    f = day.X_F[m].copy()
    if len(f) <= 1:
        return f
    rng = np.random.default_rng(_stable_seed(day.day))
    return f[rng.permutation(len(f))]


def concat_rf_time_permuted(days: list[P1DayDataset]) -> tuple[np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    for d in days:
        m = d.valid_common
        xs.append(np.column_stack((d.X_R[m], permute_complete_f_vectors(d, m))))
        ys.append(d.y[m])
    return np.concatenate(xs), np.concatenate(ys)


def metrics(records: list[dict[str, Any]], key: str) -> dict[str, Any]:
    def s(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return exp004_score([r["label"] for r in rows], [r[key] for r in rows])
    non = [r for r in records if r["nonoverlap_10m"]]
    return {
        "pooled": s(records),
        "by_fold": {
            d.isoformat(): s([r for r in records if r["outer_day"] == d.isoformat()])
            for d in OUTER_DAYS
        },
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
    rf = M["RF"]
    perm = M["RF_F_TIME_PERMUTED"]
    canary = M["CANARY_R"]
    rp, fp = r["pooled"], rf["pooled"]
    pp, cp = perm["pooled"], canary["pooled"]
    return {
        "pooled_auc_delta_at_least_0_01": _ge_delta(fp["roc_auc"], rp["roc_auc"], 0.01),
        "pooled_average_precision_delta_at_least_0_01": _ge_delta(
            fp["average_precision"], rp["average_precision"], 0.01
        ),
        "pooled_top_decile_precision_not_lower": (
            fp["top_decile_precision"] is not None
            and rp["top_decile_precision"] is not None
            and fp["top_decile_precision"] >= rp["top_decile_precision"]
        ),
        "pooled_log_loss_lower": _gt(rp["log_loss"], fp["log_loss"]),
        "pooled_brier_lower": _gt(rp["brier_score"], fp["brier_score"]),
        "at_least_3_of_4_folds_rf_auc_gt_r": sum(
            _gt(rf["by_fold"][d.isoformat()]["roc_auc"], r["by_fold"][d.isoformat()]["roc_auc"])
            for d in OUTER_DAYS
        ) >= 3,
        "pooled_rf_auc_at_least_0_60": _ge(fp["roc_auc"], 0.60),
        "nonoverlap_auc_delta_at_least_0_01": _ge_delta(
            rf["nonoverlap_pooled"]["roc_auc"], r["nonoverlap_pooled"]["roc_auc"], 0.01
        ),
        "nonoverlap_rf_auc_at_least_0_57": _ge(rf["nonoverlap_pooled"]["roc_auc"], 0.57),
        "flow_timing_falsification_auc_delta_at_least_0_01": _ge_delta(fp["roc_auc"], pp["roc_auc"], 0.01),
        "positive_control_canary_auc_delta_at_least_0_10": _ge_delta(cp["roc_auc"], rp["roc_auc"], 0.10),
        "implementation_provenance_causality_invariants_pass": all(invariants.values()),
    }


def _metric_delta(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else float(a - b)


def run(feature_dir: Path, output: Path, workspace: Path, frozen_commit: str) -> dict[str, Any]:
    assert_frozen_workspace(workspace, frozen_commit)
    partial = assert_fresh_output(output)
    parent_audit, observed_hashes = verify_parent_and_raw(workspace)
    phase_manifest = input_manifest(feature_dir, workspace)

    option_trades = {day: load_btc_trades(workspace, day) for day in SUPERVISED_DAYS}
    data: dict[date, P1DayDataset] = {}
    for day in SUPERVISED_DAYS:
        phase = _load_day(feature_path(feature_dir, SYMBOL, day), day)
        data[day] = build_day_dataset(SYMBOL, phase, option_trades[day])

    records: list[dict[str, Any]] = []
    fold_counts: list[dict[str, Any]] = []
    common_support_exact = True

    for outer_day in OUTER_DAYS:
        train_calendar = training_days(outer_day)
        train = [data[d] for d in train_calendar]
        outer = data[outer_day]

        XR, yR, mag = concat_common(train, "R")
        XF, yF, _ = concat_common(train, "F")
        XRF, yRF, mag_rf = concat_common(train, "RF")
        XVOL, yVOL, _ = concat_common(train, "VOL")
        XPERM, yPERM = concat_rf_time_permuted(train)

        labels_equal = all(np.array_equal(yR, y) for y in (yF, yRF, yVOL, yPERM))
        lengths_equal = len(XR) == len(XF) == len(XRF) == len(XVOL) == len(XPERM)
        common_support_exact &= labels_equal and lengths_equal and np.array_equal(mag, mag_rf)
        if not common_support_exact:
            raise RuntimeError("EXP011 common training support invariant failed")

        model_r = FixedLogistic().fit(XR, yR)
        model_f = FixedLogistic().fit(XF, yR)
        model_rf = FixedLogistic().fit(XRF, yR)
        model_vol = FixedLogistic().fit(XVOL, yR)
        model_perm = FixedLogistic().fit(XPERM, yR)
        model_canary = FixedLogistic().fit(np.column_stack((XR, mag)), yR)

        m = outer.valid_common
        XR_o = _matrix(outer, "R", m)
        XF_o = _matrix(outer, "F", m)
        XRF_o = _matrix(outer, "RF", m)
        XVOL_o = _matrix(outer, "VOL", m)
        FPERM_o = permute_complete_f_vectors(outer, m)
        XPERM_o = np.column_stack((XR_o, FPERM_o))
        n_outer = int(np.sum(m))
        common_support_exact &= all(len(x) == n_outer for x in (XR_o, XF_o, XRF_o, XVOL_o, XPERM_o))
        if not common_support_exact:
            raise RuntimeError("EXP011 common outer support invariant failed")

        p_r = model_r.predict_proba(XR_o)
        p_f = model_f.predict_proba(XF_o)
        p_rf = model_rf.predict_proba(XRF_o)
        p_vol = model_vol.predict_proba(XVOL_o)
        p_perm = model_perm.predict_proba(XPERM_o)
        p_canary = model_canary.predict_proba(np.column_stack((XR_o, outer.oracle_gross_bps[m])))

        idx = np.flatnonzero(m)
        fold_counts.append(
            {
                "outer_day": outer_day.isoformat(),
                "training_days": [d.isoformat() for d in train_calendar],
                "common_train_n": int(len(yR)),
                "common_outer_n": n_outer,
                "R_train_n": int(len(XR)),
                "F_train_n": int(len(XF)),
                "RF_train_n": int(len(XRF)),
                "RF_permuted_train_n": int(len(XPERM)),
            }
        )
        for j, source_idx in enumerate(idx.tolist()):
            records.append(
                {
                    "outer_day": outer_day.isoformat(),
                    "symbol": SYMBOL,
                    "timestamp_us": int(outer.timestamp_us[source_idx]),
                    "label": int(outer.y[source_idx]),
                    "oracle_gross_bps": float(outer.oracle_gross_bps[source_idx]),
                    "nonoverlap_10m": bool(outer.nonoverlap_10m[source_idx]),
                    "p_R": float(p_r[j]),
                    "p_F": float(p_f[j]),
                    "p_RF": float(p_rf[j]),
                    "p_VOL": float(p_vol[j]),
                    "p_RF_F_TIME_PERMUTED": float(p_perm[j]),
                    "p_CANARY_R": float(p_canary[j]),
                }
            )

    metric_keys = {
        "R": "p_R",
        "F": "p_F",
        "RF": "p_RF",
        "VOL": "p_VOL",
        "RF_F_TIME_PERMUTED": "p_RF_F_TIME_PERMUTED",
        "CANARY_R": "p_CANARY_R",
    }
    M = {name: metrics(records, key) for name, key in metric_keys.items()}

    invariants = {
        "exp010_audit_sha256_verified": True,
        "exp010_zero_eligible_parse_errors_all_days": all(
            int(x.get("eligible_parse_errors", -1)) == 0 for x in parent_audit.get("days", [])
        ),
        "exp010_btc_support_pass_all_days": all(
            x.get("checks", {}).get("btc_support") is True for x in parent_audit.get("days", [])
        ),
        "all_five_option_trade_hashes_verified": observed_hashes == RAW_SHA256,
        "btc_target_only": SYMBOL == "BTCUSDT",
        "only_march_to_july_supervised_days_loaded": tuple(SUPERVISED_DAYS) == tuple(DAYS[2:]),
        "outer_folds_are_april_to_july": tuple(OUTER_DAYS) == tuple(DAYS[3:]),
        "flow_windows_exactly_1_5_15_30_minutes": WINDOW_MINUTES == (1, 5, 15, 30),
        "flow_grid_starts_0030_and_ends_2349": GRID_START_MINUTE == 30 and GRID_END_MINUTE == 1429,
        "strict_local_timestamp_less_than_decision": True,
        "max_flow_lookback_30_minutes": max(WINDOW_MINUTES) == 30,
        "no_empty_window_imputation": True,
        "standard_and_usdc_btc_vanilla_only": True,
        "r_rf_common_training_and_outer_support_exact": common_support_exact,
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
        status = PASS_STATUS
    else:
        status = FAIL_STATUS

    rp = M["R"]["pooled"]
    fp = M["RF"]["pooled"]
    pp = M["RF_F_TIME_PERMUTED"]["pooled"]
    cp = M["CANARY_R"]["pooled"]
    deltas = {
        "RF_auc_minus_R_auc": _metric_delta(fp["roc_auc"], rp["roc_auc"]),
        "RF_average_precision_minus_R": _metric_delta(fp["average_precision"], rp["average_precision"]),
        "RF_top_decile_precision_minus_R": _metric_delta(fp["top_decile_precision"], rp["top_decile_precision"]),
        "R_log_loss_minus_RF_log_loss": _metric_delta(rp["log_loss"], fp["log_loss"]),
        "R_brier_minus_RF_brier": _metric_delta(rp["brier_score"], fp["brier_score"]),
        "RF_auc_minus_F_time_permuted_auc": _metric_delta(fp["roc_auc"], pp["roc_auc"]),
        "CANARY_R_auc_minus_R_auc": _metric_delta(cp["roc_auc"], rp["roc_auc"]),
    }

    used_phase = [
        item for item in phase_manifest
        if str(item.get("symbol")) == SYMBOL
        and date.fromisoformat(str(item["day"])) in SUPERVISED_DAYS
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
            "exp010_audit_sha256": EXP010_AUDIT_SHA256,
            "verified_option_trade_raw_sha256": {
                day.isoformat(): observed_hashes[day] for day in SUPERVISED_DAYS
            },
            "verified_phase_l_input_manifest_all_frozen_days": phase_manifest,
            "phase_l_inputs_used_for_exp011": used_phase,
        },
        "fold_train_counts": fold_counts,
        "metrics": M,
        "gates": gates,
        "invariants": invariants,
        "diagnostic_deltas": deltas,
        "oos_prediction_records_sha256": canonical_sha256(records),
        "oos_prediction_records": records,
        "interpretation": (
            "BTC option trade-flow incremental 10-minute opportunity timing only. "
            "No direction, PnL, August validation, or profitability claim is permitted."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    partial.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    partial.replace(output)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Frozen CODEX-EXP-011-P1 BTC options trade-flow timing test"
    )
    parser.add_argument("--feature-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    args = parser.parse_args(argv)
    result = run(args.feature_dir, args.output, args.workspace, args.frozen_commit)
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "status": result["status"],
                "configuration_sha256": result["configuration_sha256"],
                "gates": result["gates"],
                "diagnostic_deltas": result["diagnostic_deltas"],
                "sealed_august_opened": result["sealed_august_opened"],
                "direction_scored": result["direction_scored"],
                "pnl_scored": result["pnl_scored"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
