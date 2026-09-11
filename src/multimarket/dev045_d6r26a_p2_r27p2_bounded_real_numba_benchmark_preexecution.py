from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
from time import perf_counter

import numpy as np

from multimarket import dev045_d6r26a_p2_r27p1_numba_kernel_foundation_preexecution as r27p1

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P2"
DESIGN_VERSION = "bounded-real-numba-benchmark-preexecution-v1"
PARENT_R27P1_HEAD = "10776de703c8534e2a34fd2ddff74766e59c7450"

AUTH_ENV = "DEV045_D6R26A_P2_R27P2_AUTHORIZE"
AUTH_TOKEN = "YES_BOUNDED_JAN_NUMBA_KERNEL_BENCHMARK_PREATTEMPT"

SOURCE_DAY = "2026-01-01"
SOURCE_PATH = Path("/home/emadh/Multi-Market/runtime/dev045_d6r4b/output/BTCUSDT_2026-01-01.npy")
SOURCE_ROWS = 64_314_723
SOURCE_BYTES = 4_116_142_528
SOURCE_SHA256 = "8f0a4fbd56ecdc261dbe2041ce138a09456423074925d495272716219a1d4da1"

PREFIX_ROWS = (100_000, 1_000_000, 5_000_000)
REFERENCE_REPETITIONS = 1
NUMBA_REPETITIONS = 3
MIN_ACCEPTED_SPEEDUP = 10.0
GATE_PREFIX_ROWS = 5_000_000

OUTPUT_ROOT = Path("/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_r27p2_benchmark")
OUTPUT_MANIFEST = OUTPUT_ROOT / "R27P2_NUMBA_KERNEL_BENCHMARK.json"

CANONICAL_OUTPUT_ROOT = Path("/home/emadh/Multi-Market/evidence/dev045_d6r26a_p2_candidate_labels_v1")
ATTEMPT_MARKER = CANONICAL_OUTPUT_ROOT / "DEV045_D6R26A_P2_ATTEMPT_CONSUMED.json"
FAILURE_ARTIFACT = CANONICAL_OUTPUT_ROOT / "DEV045_D6R26A_P2_FAILURE.json"
CANONICAL_MANIFEST = CANONICAL_OUTPUT_ROOT / "DEV045_D6R26A_P2_CANONICAL_MANIFEST.json"

REAL_HISTORICAL_BENCHMARK_AUTHORIZED = True
BENCHMARK_SCOPE_ONE_FROZEN_SOURCE_ONLY = True
BENCHMARK_PREFIX_ONLY = True
FULL_DAY_CONTEXT_BUILD_AUTHORIZED = False
FULL_JAN_JUL_RERUN_AUTHORIZED = False
DURABLE_CONTEXT_WRITE_AUTHORIZED = False
SIMULATOR_LANE_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
P2_ATTEMPT_CONSUMED = False


class R27P2Error(RuntimeError):
    pass


@dataclass(frozen=True)
class PrefixBenchmark:
    prefix_rows: int
    python_seconds: float
    numba_seconds_best: float
    speedup: float
    parity: bool


@dataclass(frozen=True)
class BenchmarkManifest:
    experiment_id: str
    design_version: str
    source_day: str
    source_path: str
    source_rows: int
    source_bytes: int
    source_sha256: str
    prefixes: tuple[PrefixBenchmark, ...]
    gate_prefix_rows: int
    min_accepted_speedup: float
    observed_gate_speedup: float
    gate_pass: bool
    p2_attempt_consumed: bool
    simulator_run: bool
    full_jan_jul_rerun: bool


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb", buffering=0) as handle:
        while True:
            block = handle.read(8 * 1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def validate_r27p2_contract() -> None:
    r27p1.validate_r27p1_contract()
    if PARENT_R27P1_HEAD != "10776de703c8534e2a34fd2ddff74766e59c7450":
        raise R27P2Error("parent")
    if PREFIX_ROWS != (100_000, 1_000_000, 5_000_000):
        raise R27P2Error("prefix_plan")
    if GATE_PREFIX_ROWS != PREFIX_ROWS[-1]:
        raise R27P2Error("gate_prefix")
    if MIN_ACCEPTED_SPEEDUP != r27p1.MIN_ACCEPTED_SPEEDUP or MIN_ACCEPTED_SPEEDUP != 10.0:
        raise R27P2Error("speedup_gate")
    if SOURCE_ROWS <= GATE_PREFIX_ROWS:
        raise R27P2Error("source_not_larger_than_gate")
    required = (
        REAL_HISTORICAL_BENCHMARK_AUTHORIZED,
        BENCHMARK_SCOPE_ONE_FROZEN_SOURCE_ONLY,
        BENCHMARK_PREFIX_ONLY,
        not FULL_DAY_CONTEXT_BUILD_AUTHORIZED,
        not FULL_JAN_JUL_RERUN_AUTHORIZED,
        not DURABLE_CONTEXT_WRITE_AUTHORIZED,
    )
    if not all(required):
        raise R27P2Error("required_guard")
    forbidden = (
        SIMULATOR_LANE_AUTHORIZED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
        P2_ATTEMPT_CONSUMED,
    )
    if any(forbidden):
        raise R27P2Error("execution_surface_open")


def _validate_preattempt_state() -> None:
    for path, reason in (
        (ATTEMPT_MARKER, "attempt_marker_exists"),
        (FAILURE_ARTIFACT, "canonical_failure_exists"),
        (CANONICAL_MANIFEST, "canonical_manifest_exists"),
    ):
        if path.exists():
            raise R27P2Error(reason)


def _verify_source_identity() -> np.memmap:
    if not SOURCE_PATH.is_file():
        raise R27P2Error("source_missing")
    if int(SOURCE_PATH.stat().st_size) != SOURCE_BYTES:
        raise R27P2Error("source_bytes")
    observed_sha = _sha256(SOURCE_PATH)
    if observed_sha != SOURCE_SHA256:
        raise R27P2Error("source_sha256")
    events = np.load(SOURCE_PATH, mmap_mode="r", allow_pickle=False)
    if not isinstance(events, np.memmap):
        raise R27P2Error("source_not_memmap")
    if int(events.size) != SOURCE_ROWS:
        raise R27P2Error("source_rows")
    return events


def _benchmark_prefix(events: np.ndarray, *, prefix_rows: int, kernel) -> PrefixBenchmark:
    n = int(prefix_rows)
    if n <= 0 or n > int(events.size):
        raise R27P2Error("prefix_rows")
    prefix = events[:n]

    expected = r27p1._python_scan(prefix)
    observed = r27p1.numba_scan(prefix, kernel=kernel)
    if observed != expected:
        raise R27P2Error(f"parity:{n}")

    py_times: list[float] = []
    for _ in range(REFERENCE_REPETITIONS):
        t0 = perf_counter()
        current = r27p1._python_scan(prefix)
        elapsed = perf_counter() - t0
        if current != expected:
            raise R27P2Error(f"python_repeat_parity:{n}")
        py_times.append(float(elapsed))

    nb_times: list[float] = []
    for _ in range(NUMBA_REPETITIONS):
        t0 = perf_counter()
        current = r27p1.numba_scan(prefix, kernel=kernel)
        elapsed = perf_counter() - t0
        if current != expected:
            raise R27P2Error(f"numba_repeat_parity:{n}")
        nb_times.append(float(elapsed))

    py_best = min(py_times)
    nb_best = min(nb_times)
    if py_best <= 0.0 or nb_best <= 0.0:
        raise R27P2Error("elapsed")

    return PrefixBenchmark(
        prefix_rows=n,
        python_seconds=float(py_best),
        numba_seconds_best=float(nb_best),
        speedup=float(py_best / nb_best),
        parity=True,
    )


def run_real_benchmark() -> BenchmarkManifest:
    validate_r27p2_contract()
    if os.environ.get(AUTH_ENV) != AUTH_TOKEN:
        raise R27P2Error("authorization")
    _validate_preattempt_state()
    if OUTPUT_MANIFEST.exists():
        raise R27P2Error("benchmark_manifest_exists")

    events = _verify_source_identity()
    kernel = r27p1.build_numba_scan_kernel()
    # Compile/warm on a tiny real read-only prefix; compile time is excluded.
    _ = r27p1.numba_scan(events[:10_000], kernel=kernel)

    results = tuple(
        _benchmark_prefix(events, prefix_rows=n, kernel=kernel)
        for n in PREFIX_ROWS
    )
    gate = next(item for item in results if item.prefix_rows == GATE_PREFIX_ROWS)
    gate_pass = bool(gate.speedup >= MIN_ACCEPTED_SPEEDUP)

    manifest = BenchmarkManifest(
        experiment_id=EXPERIMENT_ID,
        design_version=DESIGN_VERSION,
        source_day=SOURCE_DAY,
        source_path=str(SOURCE_PATH),
        source_rows=SOURCE_ROWS,
        source_bytes=SOURCE_BYTES,
        source_sha256=SOURCE_SHA256,
        prefixes=results,
        gate_prefix_rows=GATE_PREFIX_ROWS,
        min_accepted_speedup=MIN_ACCEPTED_SPEEDUP,
        observed_gate_speedup=float(gate.speedup),
        gate_pass=gate_pass,
        p2_attempt_consumed=False,
        simulator_run=False,
        full_jan_jul_rerun=False,
    )

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    payload = asdict(manifest)
    payload["prefixes"] = [asdict(item) for item in manifest.prefixes]
    temp = OUTPUT_MANIFEST.with_suffix(".json.tmp")
    with temp.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, OUTPUT_MANIFEST)

    print(f"R27P2_SOURCE_IDENTITY=PASS ROWS={SOURCE_ROWS} BYTES={SOURCE_BYTES} SHA256={SOURCE_SHA256}")
    for item in results:
        print(
            f"R27P2_PREFIX={item.prefix_rows} PYTHON_S={item.python_seconds:.6f} "
            f"NUMBA_S={item.numba_seconds_best:.6f} SPEEDUP={item.speedup:.3f} PARITY=PASS"
        )
    print(f"R27P2_GATE_SPEEDUP={gate.speedup:.3f}")
    print(f"R27P2_MIN_REQUIRED_SPEEDUP={MIN_ACCEPTED_SPEEDUP:.1f}")
    print(f"R27P2_KERNEL_GATE={'PASS' if gate_pass else 'FAIL'}")
    print("P2_ATTEMPT_CONSUMED=NO")
    print("SIMULATOR_RUN=NO")
    print("FULL_JAN_JUL_RERUN=NO")
    print(f"BENCHMARK_MANIFEST={OUTPUT_MANIFEST}")
    return manifest


def main() -> int:
    try:
        manifest = run_real_benchmark()
    except Exception as exc:
        print(f"R27P2_RESULT=FAIL TYPE={type(exc).__name__} REASON={exc}")
        print("P2_ATTEMPT_CONSUMED=NO")
        print("SIMULATOR_RUN=NO")
        print("FULL_JAN_JUL_RERUN=NO")
        return 2
    return 0 if manifest.gate_pass else 3


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AUTH_ENV",
    "AUTH_TOKEN",
    "BenchmarkManifest",
    "GATE_PREFIX_ROWS",
    "MIN_ACCEPTED_SPEEDUP",
    "PREFIX_ROWS",
    "PrefixBenchmark",
    "SOURCE_BYTES",
    "SOURCE_DAY",
    "SOURCE_PATH",
    "SOURCE_ROWS",
    "SOURCE_SHA256",
    "run_real_benchmark",
    "validate_r27p2_contract",
]
