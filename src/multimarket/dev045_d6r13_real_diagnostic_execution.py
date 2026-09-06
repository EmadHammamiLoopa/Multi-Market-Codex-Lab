from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Mapping, Sequence

from multimarket import dev045_d6r13_real_diagnostic_execution_contract as c


class D6R13ExecutionDesignError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChildResolutionResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def payload(self) -> dict[str, object]:
        if self.returncode != 0:
            raise D6R13ExecutionDesignError(f"child_resolution_return_code:{self.returncode}")
        lines = [line for line in self.stdout.splitlines() if line.strip()]
        if not lines:
            raise D6R13ExecutionDesignError("child_resolution_stdout_empty")
        parsed = json.loads(lines[-1])
        if not isinstance(parsed, dict):
            raise D6R13ExecutionDesignError("child_resolution_payload_type")
        return parsed


def require_execution_authorization(environ: Mapping[str, str] | None = None) -> None:
    env = os.environ if environ is None else environ
    if env.get(c.AUTHORIZATION_ENV) != c.AUTHORIZATION_TOKEN:
        raise D6R13ExecutionDesignError("authorization_token")
    if not c.REAL_EXECUTION_ENABLED:
        raise D6R13ExecutionDesignError("execution_disabled_by_contract")


def child_command(*, smoke: bool = False) -> list[str]:
    flag = c.CHILD_RESOLUTION_SMOKE_FLAG if smoke else c.CHILD_FLAG
    command = [sys.executable, "-m", c.CHILD_MODULE_NAME, flag]
    if "__main__" in command:
        raise D6R13ExecutionDesignError("child_command_uses_main")
    return command


def run_child_resolution_smoke() -> ChildResolutionResult:
    completed = subprocess.run(
        child_command(smoke=True),
        text=True,
        capture_output=True,
        check=False,
        env=dict(os.environ),
    )
    result = ChildResolutionResult(
        returncode=int(completed.returncode),
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    validate_child_resolution_payload(result.payload)
    return result


def validate_child_resolution_payload(payload: Mapping[str, object]) -> None:
    required = {
        "status": "PASS",
        "experiment_id": c.EXPERIMENT_ID,
        "runtime_name": "__main__",
        "resolved_module_name": c.CHILD_MODULE_NAME,
        "canonical_data_opened": False,
        "attempt_marker_created": False,
        "heartbeat_created": False,
        "hftbacktest_canonical_run": False,
        "real_execution_enabled": False,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise D6R13ExecutionDesignError(f"child_resolution_invariant:{key}")


def run_real_parent(environ: Mapping[str, str] | None = None) -> int:
    require_execution_authorization(environ)
    raise D6R13ExecutionDesignError("real_parent_not_materialized_in_design_stage")


def run_real_child(environ: Mapping[str, str] | None = None) -> int:
    require_execution_authorization(environ)
    raise D6R13ExecutionDesignError("real_child_not_materialized_in_design_stage")


def child_resolution_smoke_payload() -> dict[str, object]:
    return {
        "status": "PASS",
        "experiment_id": c.EXPERIMENT_ID,
        "runtime_name": __name__,
        "resolved_module_name": c.CHILD_MODULE_NAME,
        "canonical_data_opened": False,
        "attempt_marker_created": False,
        "heartbeat_created": False,
        "hftbacktest_canonical_run": False,
        "real_execution_enabled": c.REAL_EXECUTION_ENABLED,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(c.CHILD_RESOLUTION_SMOKE_FLAG, action="store_true")
    parser.add_argument(c.CHILD_FLAG, action="store_true")
    parser.add_argument(c.PREFLIGHT_FLAG, action="store_true")
    args = parser.parse_args(argv)

    if args.child_resolution_smoke:
        print(json.dumps(child_resolution_smoke_payload(), sort_keys=True), flush=True)
        return 0
    if args.preflight:
        raise D6R13ExecutionDesignError("preflight_entrypoint_not_materialized_in_design_stage")
    if args.child:
        return run_real_child()
    return run_real_parent()


if __name__ == "__main__":
    raise SystemExit(main())
