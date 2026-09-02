from __future__ import annotations

import argparse
from .dev034_g3a_r1_runner import run_g3a_r1

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--execution-commit",required=True)
    a=p.parse_args()
    z=run_g3a_r1(execution_commit=a.execution_commit)
    print("ARTIFACT_PATH=",z["artifact_path"])
    print("ARTIFACT_SHA256=",z["artifact_sha256"])
    print("ARTIFACT_BYTES=",z["artifact_bytes"])
    print("ROWS=",z["rows"])
    print("EXCLUDED=",z["excluded"])
    print("CANDIDATE_COUNT=",z["candidate_count"])

if __name__=="__main__":
    main()
