from __future__ import annotations

import csv
import hashlib
import json
from bisect import bisect_left
from dataclasses import dataclass
from pathlib import Path


EXPERIMENT_ID = "DEV045-D6R17"
DESIGN_VERSION = "direct-frozen-dev044-action-support-v1"

DEV044_T0E_EXECUTION_IDENTITY = (
    "aeaa5c220dbaf936305ebf53d1a70f47dbd6a4d5"
)

ROOT = Path(
    "/home/emadh/Multi-Market/evidence/"
    "dev044_t0e_support_audit_v1"
)

MANIFEST = ROOT / "DEV044_T0E_SUPPORT_AUDIT_RESULT.json"
MANIFEST_BYTES = 23401
MANIFEST_SHA256 = (
    "66864b5e90f3c5ca7d53b5a149cdcb65223eac04c04e68511fc998a0efcb84e8"
)

MANIFEST_STATUS = "DEV044_T0E_ACTION_SUPPORT_AUDIT_PASS"

A0_GATE_THRESHOLD = 0.50

AUTHORIZED_DAYS = (
    "2026-01-01",
    "2026-02-01",
    "2026-03-01",
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)

BASE_ONLY_DAYS = (
    "2026-01-01",
    "2026-02-01",
    "2026-03-01",
)

DIRECT_SUPPORT_DAYS = (
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)

ADAPTER_POLICIES = (
    "M06",
    "M07",
)

POLICY_TO_CORE_COLUMN = {
    "M06": (
        "T10_READY",
        "T10_ACTION",
        "T10A_ACTION",
    ),
    "M07": (
        "T05_READY",
        "T05_ACTION",
        "T05A_ACTION",
    ),
}

# Explicit amendment boundary.
SUPPORT_EVIDENCE_FILE_IO_ENABLED = True
CANONICAL_MARKET_FILE_IO_ENABLED = False
HFTBACKTEST_EXECUTION_ENABLED = False
POLICY_EXECUTION_ENABLED = False
HISTORICAL_PNL_ENABLED = False
ECONOMIC_ARENA_EXECUTION_ENABLED = False
CANONICAL_PNL_WRITE_ENABLED = False
NETWORK_ACQUISITION_ENABLED = False
RAILWAY_ENABLED = False
LIVE_TRADING_AUTHORIZED = False

FORWARD_FILL_ENABLED = False
BACKFILL_ENABLED = False
INTERPOLATION_ENABLED = False
NEAREST_NEIGHBOR_ENABLED = False

A0_REFIT_ENABLED = False
A0_RETRAIN_ENABLED = False
LEGACY_STATE_REMATERIALIZATION_ENABLED = False

AUTOMATIC_RETRY = False


class DirectActionSupportError(RuntimeError):
    pass


@dataclass(frozen=True)
class FrozenDaySpec:
    day: str
    filename: str
    bytes: int
    sha256: str
    a0_support_sha256: str
    rows: int
    t05_ready: int
    t10_ready: int

    @property
    def path(self) -> Path:
        return ROOT / self.filename


DAY_SPECS = (
    FrozenDaySpec(
        day="2026-04-01",
        filename="2026-04-01_DEV044_ACTIONS.csv",
        bytes=268243,
        sha256=(
            "5916f11be83d263ec7a3f54146d7d829"
            "ed41e88eb9d9cf74bdad5768bbb7bed8"
        ),
        a0_support_sha256=(
            "a37f581fdb4c7af3101fc9a3523e438a"
            "4cb9e5943f2c932553f34514bea636c4"
        ),
        rows=1379,
        t05_ready=1379,
        t10_ready=1377,
    ),
    FrozenDaySpec(
        day="2026-05-01",
        filename="2026-05-01_DEV044_ACTIONS.csv",
        bytes=267598,
        sha256=(
            "2bf6f88fb53e55cfd07ba084bd8df6db"
            "1007657da659d2a8bab4d04e79b45356"
        ),
        a0_support_sha256=(
            "3c90ad0394ecc4fb47678f7576b7329a"
            "32c4d8a6c4aaf630cbc804a4f73c329d"
        ),
        rows=1379,
        t05_ready=1379,
        t10_ready=1376,
    ),
    FrozenDaySpec(
        day="2026-06-01",
        filename="2026-06-01_DEV044_ACTIONS.csv",
        bytes=267859,
        sha256=(
            "70535e338a3e84b4dd9add36fbac42e3"
            "13b583842fba7d73245716d55b88505e"
        ),
        a0_support_sha256=(
            "53f5fb58b2bf1b1f19878f42ab5fa0b"
            "f9fd1ebcf6c5dd0278df192d003efa238"
        ),
        rows=1379,
        t05_ready=1379,
        t10_ready=1377,
    ),
    FrozenDaySpec(
        day="2026-07-01",
        filename="2026-07-01_DEV044_ACTIONS.csv",
        bytes=268648,
        sha256=(
            "1fce7c717a744ca8bfb550516ba2baf9"
            "c858916f005ace97f2ed9082b71ccf64"
        ),
        a0_support_sha256=(
            "4025c5a90a0066e468b1bc77f7643a4"
            "e0ac54f5f06ebb95cb82bf90e4ed09ec1"
        ),
        rows=1379,
        t05_ready=1379,
        t10_ready=1376,
    ),
)


@dataclass(frozen=True)
class DirectActionPoint:
    timestamp_us: int
    direction: int
    ready: bool

    def __post_init__(self) -> None:
        if isinstance(self.timestamp_us, bool):
            raise DirectActionSupportError("timestamp")

        if int(self.timestamp_us) < 0:
            raise DirectActionSupportError("timestamp")

        if int(self.direction) not in (-1, 0, 1):
            raise DirectActionSupportError("direction")

        if not bool(self.ready) and int(self.direction) != 0:
            raise DirectActionSupportError(
                "unavailable_nonzero_direction"
            )


@dataclass(frozen=True)
class DirectActionIndex:
    day: str
    policy_id: str
    points: tuple[DirectActionPoint, ...]

    def __post_init__(self) -> None:
        if self.day not in DIRECT_SUPPORT_DAYS:
            raise DirectActionSupportError(
                "direct_support_day"
            )

        if self.policy_id not in ADAPTER_POLICIES:
            raise DirectActionSupportError(
                "adapter_policy"
            )

        ts = tuple(
            int(p.timestamp_us)
            for p in self.points
        )

        if any(
            b <= a
            for a, b in zip(
                ts,
                ts[1:],
            )
        ):
            raise DirectActionSupportError(
                "timestamp_order"
            )

        if any(
            t % 60_000_000 != 0
            for t in ts
        ):
            raise DirectActionSupportError(
                "not_exact_utc_minute"
            )

        object.__setattr__(
            self,
            "_timestamps",
            ts,
        )

    def exact(
        self,
        timestamp_us: int,
    ) -> DirectActionPoint | None:
        """
        Exact lookup only.

        None means there is no frozen support row at this exact
        adapter minute and the future bridge must fall back to M02.

        A returned point with direction=0 is an explicit frozen
        ABSTAIN and is not the same thing as a missing row.
        """
        t = int(timestamp_us)

        ts = getattr(
            self,
            "_timestamps",
        )

        i = bisect_left(
            ts,
            t,
        )

        if (
            i >= len(ts)
            or ts[i] != t
        ):
            return None

        return self.points[i]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def _spec(day: str) -> FrozenDaySpec:
    matches = tuple(
        x
        for x in DAY_SPECS
        if x.day == day
    )

    if len(matches) != 1:
        raise DirectActionSupportError(
            "day_spec"
        )

    return matches[0]


def verify_manifest() -> dict:
    if not MANIFEST.is_file():
        raise DirectActionSupportError(
            "manifest_missing"
        )

    if MANIFEST.stat().st_size != MANIFEST_BYTES:
        raise DirectActionSupportError(
            "manifest_bytes"
        )

    if _sha256(MANIFEST) != MANIFEST_SHA256:
        raise DirectActionSupportError(
            "manifest_sha256"
        )

    obj = json.loads(
        MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    if obj.get("experiment_id") != "DEV044-T0E":
        raise DirectActionSupportError(
            "manifest_experiment"
        )

    if obj.get("status") != MANIFEST_STATUS:
        raise DirectActionSupportError(
            "manifest_status"
        )

    if float(
        obj.get(
            "a0_gate_threshold"
        )
    ) != A0_GATE_THRESHOLD:
        raise DirectActionSupportError(
            "manifest_threshold"
        )

    records = obj.get(
        "day_records"
    )

    if not isinstance(records, list):
        raise DirectActionSupportError(
            "manifest_day_records"
        )

    if tuple(
        r.get("day")
        for r in records
    ) != DIRECT_SUPPORT_DAYS:
        raise DirectActionSupportError(
            "manifest_days"
        )

    by_day = {
        r["day"]: r
        for r in records
    }

    for spec in DAY_SPECS:
        rec = by_day[
            spec.day
        ]

        if rec.get("action_csv") != spec.filename:
            raise DirectActionSupportError(
                f"manifest_filename:{spec.day}"
            )

        if int(
            rec.get(
                "action_csv_bytes"
            )
        ) != spec.bytes:
            raise DirectActionSupportError(
                f"manifest_csv_bytes:{spec.day}"
            )

        if rec.get(
            "action_csv_sha256"
        ) != spec.sha256:
            raise DirectActionSupportError(
                f"manifest_csv_sha:{spec.day}"
            )

        if rec.get(
            "a0_support_sha256"
        ) != spec.a0_support_sha256:
            raise DirectActionSupportError(
                f"manifest_support_sha:{spec.day}"
            )

        if int(
            rec.get(
                "rows"
            )
        ) != spec.rows:
            raise DirectActionSupportError(
                f"manifest_rows:{spec.day}"
            )

    return obj


def _bool(value: str) -> bool:
    s = str(value).strip().lower()

    if s in (
        "1",
        "true",
    ):
        return True

    if s in (
        "0",
        "false",
    ):
        return False

    raise DirectActionSupportError(
        f"boolean:{value!r}"
    )


def load_verified_day(
    *,
    day: str,
    policy_id: str,
) -> DirectActionIndex:
    """
    Read only the already-frozen DEV044-T0E action CSV.

    This function does not touch canonical market NPYs and does
    not execute hftbacktest, policy replay, or PnL.
    """
    if day not in DIRECT_SUPPORT_DAYS:
        raise DirectActionSupportError(
            "load_non_support_day"
        )

    if policy_id not in ADAPTER_POLICIES:
        raise DirectActionSupportError(
            "load_non_adapter_policy"
        )

    spec = _spec(day)

    path = spec.path

    if not path.is_file():
        raise DirectActionSupportError(
            f"csv_missing:{day}"
        )

    if path.stat().st_size != spec.bytes:
        raise DirectActionSupportError(
            f"csv_bytes:{day}"
        )

    if _sha256(path) != spec.sha256:
        raise DirectActionSupportError(
            f"csv_sha256:{day}"
        )

    ready_col, core_col, gated_col = (
        POLICY_TO_CORE_COLUMN[
            policy_id
        ]
    )

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        reader = csv.DictReader(f)

        required = {
            "local_timestamp_us",
            "p_touch",
            ready_col,
            core_col,
            gated_col,
        }

        fields = set(
            reader.fieldnames
            or ()
        )

        if not required.issubset(
            fields
        ):
            raise DirectActionSupportError(
                f"csv_header:{day}:{policy_id}"
            )

        points = []

        ready_count = 0

        for row in reader:
            t = int(
                row[
                    "local_timestamp_us"
                ]
            )

            p_touch = float(
                row[
                    "p_touch"
                ]
            )

            if not (
                0.0
                <= p_touch
                <= 1.0
            ):
                raise DirectActionSupportError(
                    "p_touch"
                )

            ready = _bool(
                row[
                    ready_col
                ]
            )

            core = int(
                row[
                    core_col
                ]
            )

            gated = int(
                row[
                    gated_col
                ]
            )

            if core not in (
                -1,
                0,
                1,
            ):
                raise DirectActionSupportError(
                    "core_direction"
                )

            if gated not in (
                -1,
                0,
                1,
            ):
                raise DirectActionSupportError(
                    "gated_direction"
                )

            expected = (
                core
                if (
                    ready
                    and p_touch
                    >= A0_GATE_THRESHOLD
                )
                else 0
            )

            if gated != expected:
                raise DirectActionSupportError(
                    f"gate_parity:{day}:{t}"
                )

            if ready:
                ready_count += 1

            points.append(
                DirectActionPoint(
                    timestamp_us=t,
                    direction=gated,
                    ready=ready,
                )
            )

    if len(points) != spec.rows:
        raise DirectActionSupportError(
            f"row_count:{day}"
        )

    expected_ready = (
        spec.t10_ready
        if policy_id == "M06"
        else spec.t05_ready
    )

    if ready_count != expected_ready:
        raise DirectActionSupportError(
            f"ready_count:{day}:{policy_id}"
        )

    return DirectActionIndex(
        day=day,
        policy_id=policy_id,
        points=tuple(
            points
        ),
    )


def verify_all_support() -> dict:
    manifest = verify_manifest()

    total_rows = 0
    total_m06_ready = 0
    total_m07_ready = 0
    total_m06_unavailable = 0
    total_m07_unavailable = 0

    for day in DIRECT_SUPPORT_DAYS:
        m06 = load_verified_day(
            day=day,
            policy_id="M06",
        )

        m07 = load_verified_day(
            day=day,
            policy_id="M07",
        )

        if tuple(
            p.timestamp_us
            for p in m06.points
        ) != tuple(
            p.timestamp_us
            for p in m07.points
        ):
            raise DirectActionSupportError(
                f"cross_policy_timestamp_identity:{day}"
            )

        total_rows += len(
            m06.points
        )

        r06 = sum(
            p.ready
            for p in m06.points
        )

        r07 = sum(
            p.ready
            for p in m07.points
        )

        total_m06_ready += r06
        total_m07_ready += r07

        total_m06_unavailable += (
            len(m06.points)
            - r06
        )

        total_m07_unavailable += (
            len(m07.points)
            - r07
        )

    if total_rows != 5516:
        raise DirectActionSupportError(
            "pooled_rows"
        )

    if total_m06_ready != 5506:
        raise DirectActionSupportError(
            "pooled_m06_ready"
        )

    if total_m07_ready != 5516:
        raise DirectActionSupportError(
            "pooled_m07_ready"
        )

    if total_m06_unavailable != 10:
        raise DirectActionSupportError(
            "pooled_m06_unavailable"
        )

    if total_m07_unavailable != 0:
        raise DirectActionSupportError(
            "pooled_m07_unavailable"
        )

    return {
        "manifest": manifest,
        "rows": total_rows,
        "m06_ready": total_m06_ready,
        "m06_unavailable": total_m06_unavailable,
        "m07_ready": total_m07_ready,
        "m07_unavailable": total_m07_unavailable,
    }


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "DEV044_T0E_EXECUTION_IDENTITY",
    "MANIFEST_SHA256",
    "BASE_ONLY_DAYS",
    "DIRECT_SUPPORT_DAYS",
    "ADAPTER_POLICIES",
    "POLICY_TO_CORE_COLUMN",
    "DAY_SPECS",
    "DirectActionPoint",
    "DirectActionIndex",
    "verify_manifest",
    "load_verified_day",
    "verify_all_support",
]
