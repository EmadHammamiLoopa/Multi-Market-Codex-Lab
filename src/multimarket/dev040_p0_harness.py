from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

from .dev040_p0_runner import run

def _square(x:int)->int:
    return x*x

def process_pool_smoke(max_workers:int=2):
    ctx=mp.get_context("forkserver")
    with ProcessPoolExecutor(max_workers=max_workers,mp_context=ctx) as pool:
        return tuple(pool.map(_square,(1,2,3,4)))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--smoke",action="store_true")
    p.add_argument("--execution-commit")
    args=p.parse_args()

    if args.smoke:
        print("PROCESS_POOL_SMOKE=PASS")
        print("PROCESS_POOL_VALUES=",process_pool_smoke(2))
        return

    if not args.execution_commit:
        p.error("--execution-commit required unless --smoke")

    z=run(execution_commit=args.execution_commit)
    print("ARTIFACT_PATH=",z["artifact_path"])
    print("ARTIFACT_SHA256=",z["artifact_sha256"])
    print("ARTIFACT_BYTES=",z["artifact_bytes"])
    print("STATUS=",z["status"])
    print("PRIMARY_ACCEPTED_TRADES=",z["primary_accepted_trades"])

if __name__=="__main__":
    main()
