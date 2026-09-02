from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
from pathlib import Path

from .dev032_e1b_runner import run_e1b

R1_OUTPUT_DIRECTORY = Path(
    "/home/emadh/Multi-Market/evidence/dev032_e1b_r1_broad_predictive_screen_v1"
)

def _square(x: int) -> int:
    return int(x) * int(x)

def process_pool_smoke(*, max_workers: int = 2) -> tuple[int, ...]:
    ctx = mp.get_context("forkserver")
    with ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx) as pool:
        values = tuple(pool.map(_square, (1, 2, 3, 4)))
    if values != (1, 4, 9, 16):
        raise RuntimeError(f"process_pool_smoke_mismatch:{values}")
    return values

def run_recovery(
    *,
    execution_commit: str,
    max_workers: int = 20,
) -> dict:
    return run_e1b(
        execution_commit=execution_commit,
        output_directory=R1_OUTPUT_DIRECTORY,
        require_canonical_output=False,
        max_workers=max_workers,
    )

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--execution-commit")
    parser.add_argument("--max-workers", type=int, default=20)
    args = parser.parse_args()

    if args.smoke:
        values = process_pool_smoke(max_workers=min(args.max_workers, 4))
        print("PROCESS_POOL_SMOKE=PASS")
        print("PROCESS_POOL_VALUES=", values)
        return

    if not args.execution_commit:
        parser.error("--execution-commit is required unless --smoke is used")

    result = run_recovery(
        execution_commit=args.execution_commit,
        max_workers=args.max_workers,
    )
    print("ARTIFACT_PATH=", result["artifact_path"])
    print("ARTIFACT_SHA256=", result["artifact_sha256"])
    print("ARTIFACT_BYTES=", result["artifact_bytes"])
    print("STRONG_SCREENING_SURVIVORS=", result["strong_screening_survivors"])
    print("ADVANCED_MECHANISMS=", result["advanced_mechanisms"])

if __name__ == "__main__":
    main()
