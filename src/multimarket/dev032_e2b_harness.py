from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

from .dev032_e2b_runner import run_e2b

def _square(x:int)->int:
    return x*x

def process_pool_smoke(max_workers:int=2)->tuple[int,...]:
    ctx=mp.get_context("forkserver")
    with ProcessPoolExecutor(max_workers=max_workers,mp_context=ctx) as pool:
        return tuple(pool.map(_square,(1,2,3,4)))

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--smoke",action="store_true")
    p.add_argument("--execution-commit")
    p.add_argument("--max-workers",type=int,default=10)
    args=p.parse_args()

    if args.smoke:
        vals=process_pool_smoke(min(max(args.max_workers,1),2))
        print("PROCESS_POOL_SMOKE=PASS")
        print("PROCESS_POOL_VALUES=",vals)
        return

    if not args.execution_commit:
        p.error("--execution-commit is required unless --smoke is used")

    out=run_e2b(
        execution_commit=args.execution_commit,
        max_workers=args.max_workers,
    )
    print("ARTIFACT_PATH=",out["artifact_path"])
    print("ARTIFACT_SHA256=",out["artifact_sha256"])
    print("ARTIFACT_BYTES=",out["artifact_bytes"])
    print("ADAPTIVE_REFINEMENT_SURVIVORS=",out["adaptive_refinement_survivors"])
    print("ADVANCED_MECHANISMS=",out["advanced_mechanisms"])

if __name__=="__main__":
    main()
