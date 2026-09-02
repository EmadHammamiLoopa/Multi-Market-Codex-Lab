from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

from .dev034_g3b_r1_runner import run_g3b_r1

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
    p.add_argument("--max-workers",type=int,default=12)
    args=p.parse_args()
    if args.smoke:
        print("PROCESS_POOL_SMOKE=PASS")
        print("PROCESS_POOL_VALUES=",process_pool_smoke(min(max(args.max_workers,1),2)))
        return
    if not args.execution_commit:
        p.error("--execution-commit required unless --smoke")
    z=run_g3b_r1(execution_commit=args.execution_commit,max_workers=args.max_workers)
    print("ARTIFACT_PATH=",z["artifact_path"])
    print("ARTIFACT_SHA256=",z["artifact_sha256"])
    print("ARTIFACT_BYTES=",z["artifact_bytes"])
    print("LAYER_SURVIVORS=",z["layer_survivors"])
    print("ADVANCED_LAYERS=",z["advanced_layers"])

if __name__=="__main__":
    main()
