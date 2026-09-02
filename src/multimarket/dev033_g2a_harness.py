from __future__ import annotations

import argparse
from pathlib import Path

from .dev033_g2a_runner import run_g2a

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--workspace",default=".")
    p.add_argument("--execution-commit",required=True)
    p.add_argument("--max-workers",type=int,default=2)
    args=p.parse_args()
    z=run_g2a(
        workspace=Path(args.workspace),
        execution_commit=args.execution_commit,
        max_workers=args.max_workers,
    )
    print("ARTIFACT_PATH=",z.artifact_path)
    print("ARTIFACT_SHA256=",z.artifact_sha256)
    print("ARTIFACT_BYTES=",z.artifact_bytes)

if __name__=="__main__":
    main()
