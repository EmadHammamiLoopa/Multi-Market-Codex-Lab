from __future__ import annotations

import argparse
from .dev034_g3a_runner import run_g3a

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--execution-commit",required=True)
    args=p.parse_args()
    z=run_g3a(execution_commit=args.execution_commit)
    print("ARTIFACT_PATH=",z["artifact_path"])
    print("ARTIFACT_SHA256=",z["artifact_sha256"])
    print("ARTIFACT_BYTES=",z["artifact_bytes"])
    print("ROWS=",z["rows"])
    print("CANDIDATE_COUNT=",z["candidate_count"])

if __name__=="__main__":
    main()
