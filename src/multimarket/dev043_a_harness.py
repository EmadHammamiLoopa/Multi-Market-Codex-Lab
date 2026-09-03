from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

def _square(x:int)->int:
    return x*x

def process_pool_smoke(max_workers:int=2):
    ctx=mp.get_context("forkserver")
    with ProcessPoolExecutor(max_workers=max_workers,mp_context=ctx) as pool:
        return tuple(pool.map(_square,(1,2,3,4)))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--smoke",action="store_true")
    args=p.parse_args()
    if args.smoke:
        print("PROCESS_POOL_SMOKE=PASS")
        print("PROCESS_POOL_VALUES=",process_pool_smoke(2))
        return
    p.error("--smoke required")

if __name__=="__main__":
    main()
