from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
import subprocess
import sys
from typing import Mapping, Sequence

from multimarket import dev045_d6r13_child_launch_successor_contract as c


class D6R13ChildLaunchError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChildLaunchSmokeResult:
    returncode: int
    stdout: str
    stderr: str
    payload: dict[str, object]


def build_child_command(flag: str) -> list[str]:
    if flag not in (c.SMOKE_CHILD_FLAG, c.REAL_CHILD_FLAG):
        raise D6R13ChildLaunchError(f"unsupported_child_flag:{flag}")
    return [sys.executable, "-m", c.CHILD_MODULE_NAME, flag]


def require_smoke_authorization(
    environ: Mapping[str, str] | None = None,
) -> None:
    env = os.environ if environ is None else environ
    if env.get(c.SMOKE_AUTH_ENV) != c.SMOKE_AUTH_TOKEN:
        raise D6R13ChildLaunchError("smoke_authorization_token")


def resolved_main_module_name() -> str | None:
    main_module = sys.modules.get("__main__")
    spec = None if main_module is None else getattr(main_module, "__spec__", None)
    return None if spec is None else getattr(spec, "name", None)


def child_launch_smoke_payload() -> dict[str, object]:
    resolved = resolved_main_module_name()
    if resolved != c.CHILD_MODULE_NAME:
        raise D6R13ChildLaunchError(f"module_resolution:{resolved}")
    return {
        "experiment_id": c.EXPERIMENT_ID,
        "schema_version": c.SCHEMA_VERSION,
        "status": "PASS",
        "resolved_module_name": resolved,
        "runtime_name": __name__,
        "source_content_opened": False,
        "attempt_marker_created": False,
        "heartbeat_created": False,
        "hftbacktest_canonical_run": False,
        "real_execution_enabled": c.REAL_EXECUTION_ENABLED,
    }


def run_child_launch_smoke(
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    require_smoke_authorization(environ)
    return child_launch_smoke_payload()


def validate_smoke_payload(payload: Mapping[str, object]) -> None:
    expected = {
        "experiment_id": c.EXPERIMENT_ID,
        "schema_version": c.SCHEMA_VERSION,
        "status": "PASS",
        "resolved_module_name": c.CHILD_MODULE_NAME,
        "runtime_name": "__main__",
        "source_content_opened": False,
        "attempt_marker_created": False,
        "heartbeat_created": False,
        "hftbacktest_canonical_run": False,
        "real_execution_enabled": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise D6R13ChildLaunchError(f"smoke_payload:{key}")


def run_smoke_parent() -> ChildLaunchSmokeResult:
    env = dict(os.environ)
    env[c.SMOKE_AUTH_ENV] = c.SMOKE_AUTH_TOKEN
    completed = subprocess.run(
        build_child_command(c.SMOKE_CHILD_FLAG),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if completed.returncode != 0:
        raise D6R13ChildLaunchError(
            f"smoke_child_return_code:{completed.returncode}:{completed.stderr[-2000:]}"
        )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise D6R13ChildLaunchError("smoke_child_stdout_empty")
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise D6R13ChildLaunchError("smoke_child_json") from exc
    if not isinstance(payload, dict):
        raise D6R13ChildLaunchError("smoke_child_payload_type")
    validate_smoke_payload(payload)
    return ChildLaunchSmokeResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        payload=payload,
    )


def run_real_child_disabled() -> int:
    if not c.REAL_EXECUTION_ENABLED:
        raise D6R13ChildLaunchError("real_execution_disabled_by_contract")
    raise D6R13ChildLaunchError("real_child_not_implemented_in_design")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(c.SMOKE_PARENT_FLAG, action="store_true")
    group.add_argument(c.SMOKE_CHILD_FLAG, action="store_true")
    group.add_argument(c.REAL_CHILD_FLAG, action="store_true")
    args = parser.parse_args(argv)

    if getattr(args, c.SMOKE_PARENT_FLAG.lstrip("-").replace("-", "_")):
        result = run_smoke_parent()
        print(json.dumps(result.payload, sort_keys=True), flush=True)
        return 0
    if getattr(args, c.SMOKE_CHILD_FLAG.lstrip("-").replace("-", "_")):
        payload = run_child_launch_smoke()
        print(json.dumps(payload, sort_keys=True), flush=True)
        return 0
    return run_real_child_disabled()


if __name__ == "__main__":
    raise SystemExit(main())
