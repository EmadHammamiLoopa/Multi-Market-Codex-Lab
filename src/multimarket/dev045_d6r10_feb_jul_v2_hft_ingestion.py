from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import mmap
import os
from pathlib import Path
import resource
import subprocess
import sys

from multimarket import dev045_d6r5_memmap_adapter as adapter
from multimarket import dev045_d6r6_historical_driver as driver

EXPERIMENT_ID = "DEV045-D6R10"
SCHEMA_VERSION = "dev045-d6r10-feb-jul-v2-hft-ingestion-v1"
PARENT_D6R9B_HEAD = "7635f57c0bf4e7c92379bcb1846d5fa105160103"
SYMBOL = "BTCUSDT"
EXCHANGE = "binance-futures"
MODE = "FEED_ONLY_NO_STRATEGY"
HFTBACKTEST_VERSION = "2.4.4"
MIN_MEMAVAILABLE_BYTES = 8_442_945_536
RSS_ABORT_BYTES = 10 * 1024**3
WAIT_NEXT_FEED_TIMEOUT_NS = 86_400_000_000_000
HEARTBEAT_EVERY_WAKEUPS = 100_000
RUNTIME_ROOT = Path("/home/emadh/Multi-Market/runtime/dev045_d6r10")

@dataclass(frozen=True)
class DaySpec:
    day: str
    path: Path
    rows: int
    bytes: int
    sha256: str
    lineage_evidence: Path
    lineage_evidence_sha256: str

DAY_SPECS = (
    DaySpec("2026-02-01", Path("/home/emadh/Multi-Market/runtime/dev045_d6r9a/output/BTCUSDT_2026-02-01.npy"), 179_584_138, 11_493_385_088, "d757d2ac32a29b0ac587323e115779c466068c6c0eba4270226b9c4109254cbc", Path("evidence/dev045_d6r9a_feb01_full_day_v2.json"), "54afd16ca610b76de0658d68764b661335fcda23e3ae3ca4ce4de93c57c199d9"),
    DaySpec("2026-03-01", Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-03-01.npy"), 150_979_263, 9_662_673_088, "9e6a8b61d05e1a4938e17ffa7969241affc7c06c1d0836188e3a882c363f2d99", Path("evidence/dev045_d6r9b_2026-03-01.json"), "dc077571207df728666b147c4c865a51ac40e189b626b0f398585aaaff2ce221"),
    DaySpec("2026-04-01", Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-04-01.npy"), 132_829_759, 8_501_104_832, "de7e0471e63631394981b301bb461d679192c37eb6241d4d8073cf0640eca7f7", Path("evidence/dev045_d6r9b_2026-04-01.json"), "a00918595087e55ae1dcb7d833ee11cdedbed26c6ff9ca06d5caccc36a6eacae"),
    DaySpec("2026-05-01", Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-05-01.npy"), 108_328_169, 6_933_003_072, "9433dfb498070dd5dd3e8ab1633c2f19551844f2ddf0d451e120119365bb04a3", Path("evidence/dev045_d6r9b_2026-05-01.json"), "abdb6a95dd9027a65386b9e4a1218fdcf3be57d94a80945a6c94919ac12a6bd5"),
    DaySpec("2026-06-01", Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-06-01.npy"), 172_540_697, 11_042_604_864, "ac97ad27c9d58b3b3e249547b8ae7c74cf2ebfde07965103bd9c8c05d0df1160", Path("evidence/dev045_d6r9b_2026-06-01.json"), "13821ab6ba2f77820ab43ed9082a249c972a95eb11f282340cd5f6c7b853c26b"),
    DaySpec("2026-07-01", Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy"), 181_084_390, 11_589_401_216, "85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f", Path("evidence/dev045_d6r9b_2026-07-01.json"), "02c59ac113b71c511768724e218249d506ef38962aa3ae28770613f8dc10561c"),
)
DAY_BY_NAME = {x.day: x for x in DAY_SPECS}

class D6R10Error(RuntimeError):
    pass

def _sha256(path: Path) -> str:
    d = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            d.update(block)
    return d.hexdigest()

def _memavailable_bytes() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise D6R10Error("memavailable_missing")

def _rss_bytes() -> int:
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) * 1024
    raise D6R10Error("rss_missing")

def _marker(spec: DaySpec) -> Path:
    return RUNTIME_ROOT / spec.day / "ATTEMPT_STARTED.json"

def _heartbeat(spec: DaySpec) -> Path:
    return RUNTIME_ROOT / spec.day / "HEARTBEAT.json"

def _evidence(spec: DaySpec) -> Path:
    return Path(f"evidence/dev045_d6r10_{spec.day}.json")

def _state(spec: DaySpec) -> str:
    m, e = _marker(spec), _evidence(spec)
    if not m.exists() and not e.exists():
        return "FRESH"
    if m.exists() and e.exists():
        try:
            p = json.loads(e.read_text())
        except Exception:
            return "FROZEN_NONPASS"
        if p.get("experiment_id") == EXPERIMENT_ID and p.get("day") == spec.day and p.get("status") == "PASS":
            return "FROZEN_PASS"
    return "FROZEN_NONPASS"

def _verify_lineage(spec: DaySpec) -> None:
    if not spec.lineage_evidence.is_file():
        raise D6R10Error(f"lineage_missing:{spec.day}")
    if _sha256(spec.lineage_evidence) != spec.lineage_evidence_sha256:
        raise D6R10Error(f"lineage_sha256:{spec.day}")
    p = json.loads(spec.lineage_evidence.read_text())
    if p.get("status") != "PASS":
        raise D6R10Error(f"lineage_status:{spec.day}")
    sha = p.get("output_sha256") or (p.get("v2") or {}).get("output_sha256")
    rows = (p.get("output_header") or {}).get("rows")
    if sha != spec.sha256 or rows != spec.rows:
        raise D6R10Error(f"lineage_output_identity:{spec.day}")

def _preflight(spec: DaySpec) -> dict[str, int]:
    if _state(spec) != "FRESH":
        raise D6R10Error(f"day_not_fresh:{spec.day}")
    _verify_lineage(spec)
    if not spec.path.is_file() or spec.path.stat().st_size != spec.bytes:
        raise D6R10Error(f"source_stat:{spec.day}")
    mem = _memavailable_bytes()
    if mem < MIN_MEMAVAILABLE_BYTES:
        raise D6R10Error(f"memavailable:{spec.day}:{mem}")
    (RUNTIME_ROOT / spec.day).mkdir(parents=True, exist_ok=True)
    return {"memavailable_bytes": mem, "source_bytes": spec.bytes}

def _write_heartbeat(spec: DaySpec, payload: dict[str, object]) -> None:
    path = _heartbeat(spec)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True) + "\n")
    os.replace(tmp, path)

def _ingest(spec: DaySpec, *, heartbeat: bool) -> dict[str, object]:
    import hftbacktest as h
    if h.__version__ != HFTBACKTEST_VERSION:
        raise D6R10Error(f"hftbacktest_version:{h.__version__}")
    source = adapter._open_verified_file(spec.path, expected_sha256=spec.sha256, expected_bytes=spec.bytes, expected_rows=spec.rows)
    binding = None
    wakeups = 0
    first_ts = None
    last_ts = None
    peak_rss = _rss_bytes()
    before = (spec.path.stat().st_dev, spec.path.stat().st_ino, spec.path.stat().st_size, spec.path.stat().st_mtime_ns)
    try:
        mm = getattr(source.data, "_mmap", None)
        if mm is not None and hasattr(mm, "madvise") and hasattr(mmap, "MADV_SEQUENTIAL"):
            mm.madvise(mmap.MADV_SEQUENTIAL)
        binding = driver._build_lifetime_safe_binding(source)
        while True:
            rc = int(binding.bt.wait_next_feed(False, WAIT_NEXT_FEED_TIMEOUT_NS))
            if rc == 1:
                break
            if rc != 2:
                raise D6R10Error(f"feed_rc:{spec.day}:{rc}")
            ts = int(binding.bt.current_timestamp)
            if last_ts is not None and ts < last_ts:
                raise D6R10Error(f"nonmonotonic:{spec.day}")
            first_ts = ts if first_ts is None else first_ts
            last_ts = ts
            wakeups += 1
            if wakeups % HEARTBEAT_EVERY_WAKEUPS == 0:
                rss = _rss_bytes()
                peak_rss = max(peak_rss, rss)
                if rss > RSS_ABORT_BYTES:
                    raise D6R10Error(f"rss_abort:{spec.day}:{rss}")
                if heartbeat:
                    _write_heartbeat(spec, {"day": spec.day, "market_wakeups": wakeups, "current_timestamp_ns": ts, "current_rss_bytes": rss, "updated_at_utc": datetime.now(timezone.utc).isoformat()})
        if wakeups <= 0:
            raise D6R10Error(f"no_wakeup:{spec.day}")
        depth = binding.bt.depth(0)
        bid, ask = int(depth.best_bid_tick), int(depth.best_ask_tick)
        pos, orders = float(binding.bt.position(0)), int(len(binding.bt.orders(0)))
        if bid <= 0 or ask <= 0 or bid >= ask:
            raise D6R10Error(f"terminal_book:{spec.day}:{bid}:{ask}")
        if pos != 0.0 or orders != 0:
            raise D6R10Error(f"terminal_execution_state:{spec.day}")
        result = {"source_sha256": source.sha256, "source_rows": spec.rows, "source_bytes": spec.bytes, "market_wakeups": wakeups, "first_market_wakeup_ns": first_ts, "last_market_wakeup_ns": last_ts, "terminal_rc": 1, "terminal_timestamp_ns": int(binding.bt.current_timestamp), "best_bid_tick": bid, "best_ask_tick": ask, "position": pos, "working_order_count": orders}
    finally:
        if binding is not None:
            binding.close()
            lifecycle = list(binding.lifecycle)
        else:
            if not source._closed:
                source.close()
            lifecycle = ["memmap_closed"]
    after = (spec.path.stat().st_dev, spec.path.stat().st_ino, spec.path.stat().st_size, spec.path.stat().st_mtime_ns)
    if after != before:
        raise D6R10Error(f"source_changed:{spec.day}")
    result["lifecycle"] = lifecycle
    result["peak_rss_bytes"] = max(peak_rss, int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024)
    return result

def _child(spec: DaySpec) -> int:
    print(json.dumps(_ingest(spec, heartbeat=True), sort_keys=True), flush=True)
    return 0

def _run_day(spec: DaySpec) -> bool:
    pre = _preflight(spec)
    attempt = {"experiment_id": EXPERIMENT_ID, "schema_version": SCHEMA_VERSION, "canonical_attempt": 1, "day": spec.day, "symbol": SYMBOL, "exchange": EXCHANGE, "mode": MODE, "parent_d6r9b_head": PARENT_D6R9B_HEAD, "started_at_utc": datetime.now(timezone.utc).isoformat()}
    _marker(spec).write_text(json.dumps(attempt, indent=2, sort_keys=True) + "\n")
    e: dict[str, object] = {**attempt, **pre, "status": "FAIL", "failure_reason": None, "source_content_opened": False, "canonical_npy_written": False, "raw_csv_opened": False, "converter_rerun": False, "order_submission_run": False, "order_cancel_run": False, "policy_execution_run": False, "historical_pnl_computed": False, "economic_arena_executed": False, "aug_opened": False, "sep_plus_opened": False, "non_btc_opened": False, "network_market_data_acquisition": False, "railway_touched": False, "live_trading_authorized": False}
    try:
        e["source_content_opened"] = True
        p = subprocess.run([sys.executable, "-m", "multimarket.dev045_d6r10_feb_jul_v2_hft_ingestion", "--child", spec.day], text=True, capture_output=True, check=False)
        e["child_return_code"] = p.returncode
        e["child_stdout_sha256"] = hashlib.sha256(p.stdout.encode()).hexdigest()
        e["child_stderr_sha256"] = hashlib.sha256(p.stderr.encode()).hexdigest()
        e["child_stderr_tail"] = p.stderr[-8192:]
        if p.returncode != 0:
            raise D6R10Error(f"child_return_code:{spec.day}:{p.returncode}")
        observed = json.loads(p.stdout.splitlines()[-1])
        e["observed"] = observed
        if observed["source_sha256"] != spec.sha256 or int(observed["source_rows"]) != spec.rows or int(observed["source_bytes"]) != spec.bytes:
            raise D6R10Error(f"observed_identity:{spec.day}")
        if int(observed["terminal_rc"]) != 1 or float(observed["position"]) != 0.0 or int(observed["working_order_count"]) != 0:
            raise D6R10Error(f"terminal_state:{spec.day}")
        if int(observed["peak_rss_bytes"]) > RSS_ABORT_BYTES:
            raise D6R10Error(f"peak_rss:{spec.day}")
        e["status"] = "PASS"
    except Exception as exc:
        e["failure_reason"] = f"{type(exc).__name__}:{exc}"
    finally:
        e["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        _evidence(spec).write_text(json.dumps(e, indent=2, sort_keys=True) + "\n")
    return e["status"] == "PASS"

def run_sequence() -> int:
    if os.environ.get("DEV045_D6R10_AUTHORIZE") != "YES_FEED_ONLY_SEQUENCE":
        raise D6R10Error("sequence_not_authorized")
    print(f"{EXPERIMENT_ID}_SEQUENCE_START=YES", flush=True)
    print("ORDER=" + ",".join(x.day for x in DAY_SPECS), flush=True)
    for spec in DAY_SPECS:
        state = _state(spec)
        if state == "FROZEN_PASS":
            print(f"DAY={spec.day} STATUS=FROZEN_PASS ACTION=SKIP", flush=True)
            continue
        if state == "FROZEN_NONPASS":
            print(f"DAY={spec.day} STATUS=FROZEN_NONPASS ACTION=STOP RERUN=FORBIDDEN", flush=True)
            return 1
        print(f"DAY={spec.day} PREFLIGHT=START", flush=True)
        try:
            ok = _run_day(spec)
        except Exception as exc:
            print(f"DAY={spec.day} PRE_MARKER_FAILURE={type(exc).__name__}:{exc}", flush=True)
            print(f"DAY={spec.day} ATTEMPT_CONSUMED=NO", flush=True)
            return 1
        if not ok:
            print(f"DAY={spec.day} RESULT=FAIL RERUN=FORBIDDEN", flush=True)
            return 1
        p = json.loads(_evidence(spec).read_text())["observed"]
        print(f"DAY={spec.day} RESULT=PASS WAKEUPS={p['market_wakeups']} PEAK_RSS_BYTES={p['peak_rss_bytes']} BID_TICK={p['best_bid_tick']} ASK_TICK={p['best_ask_tick']}", flush=True)
    print(f"{EXPERIMENT_ID}_SEQUENCE_RESULT=PASS", flush=True)
    return 0

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", choices=tuple(DAY_BY_NAME))
    args = parser.parse_args()
    return _child(DAY_BY_NAME[args.child]) if args.child else run_sequence()

if __name__ == "__main__":
    raise SystemExit(main())
