from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

from multimarket import dev045_d6r5_memmap_adapter as adapter
from multimarket import dev045_d6r17_direct_action_driver_bridge as bridge
from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r19_canonical_runner as d6r19_runner
from multimarket import dev045_d6r20_real_engine_qualification as q1
from multimarket import dev045_d6r20_residual_flatten_driver as d6r20
from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m4_m6_binding as binding
from multimarket import dev045_m6_event_loop_contract as d1
from multimarket import dev045_m6_event_loop_kernel as d2
from multimarket.dev044_t0_strategy_contract import LONG, SHORT


EXPERIMENT_ID = "DEV045-D6R20-Q1-FLATTEN-FORENSIC"
DESIGN_VERSION = "flatten-execution-forensic-v1"

FAILED_Q1_HEAD = "692be709f94b05af81dcded4748efdc629032b08"
FAILED_Q1_SHA256 = (
    "03eb0554c1085e6adbe14e1544045edac"
    "4e2c5ee41949912aaeb3f779aed7ac4"
)
D6R20_DRIVER_BLOB = "1cae4584788aab29b409bf985168803759d42b1f"

FORENSIC_DAY = "2026-01-01"
FORENSIC_POLICY = "M01"
FORENSIC_SCENARIO = "Q0_PRIMARY_250_250"
FORENSIC_SCOPE = (
    (FORENSIC_DAY, FORENSIC_POLICY, FORENSIC_SCENARIO),
)

AUTHORIZATION_ENV = "DEV045_D6R20_Q1_FORENSIC_AUTHORIZE"
AUTHORIZATION_TOKEN = "YES_D6R20_Q1_JAN_M01_PRIMARY_FLATTEN_FORENSIC"

EXPECTED_BRANCH = "research/dev045-m6-d6r20-q1-flatten-execution-forensic"
EXPECTED_REMOTE_REF = f"origin/{EXPECTED_BRANCH}"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
D6R20_DRIVER_PATH = Path(d6r20.__file__).resolve()
D6R20_CANONICAL_RUNNER_PATH = (
    REPOSITORY_ROOT / "src/multimarket/dev045_d6r20_canonical_runner.py"
)
FAILED_Q1_EVIDENCE_PATH = (
    REPOSITORY_ROOT / "evidence/dev045_d6r20_q1_real_engine_failure.json"
)
ALLOWED_UNTRACKED_PATHS = (
    "evidence/dev045_d6r9a_feb01_full_day_v2.json",
)

RESULT_ROOT = Path(
    "/home/emadh/Multi-Market/evidence/"
    "dev045_d6r20_q1_flatten_forensic_v1"
)
RESULT_PATH = RESULT_ROOT / "DEV045_D6R20_Q1_FLATTEN_FORENSIC.json"

LOT_TOLERANCE = 1e-12
POSITION_TOLERANCE = 1e-12

MARKET_DEPTH_SWEEP_INSUFFICIENT = "MARKET_DEPTH_SWEEP_INSUFFICIENT"
MARKET_ORDER_UNEXPECTED_PARTIAL = "MARKET_ORDER_UNEXPECTED_PARTIAL"
POSITION_ACCOUNTING_MISMATCH = "POSITION_ACCOUNTING_MISMATCH"
OTHER_EXECUTION_MISMATCH = "OTHER_EXECUTION_MISMATCH"

FORENSIC_EXECUTION_AUTHORIZED_BY_DEFAULT = False
REAL_FORENSIC_REPLAY_EXECUTED = False
CANONICAL_RUNNER_IMPLEMENTED = False
CANONICAL_ECONOMIC_ATTEMPT = False
CANONICAL_ATTEMPT_CONSUMED = False
ECONOMIC_ARENA_CALLED = False
STRATEGY_RANKING_PERFORMED = False
AUTOMATIC_RETRY = False
LIVE_TRADING_AUTHORIZED = False


class FlattenForensicError(base.RealHistoricalDriverError):
    pass


@dataclass(frozen=True)
class ForensicRepositoryIdentity:
    branch: str
    head: str
    remote_ref: str
    remote_head: str
    tracked_worktree_clean: bool
    permitted_untracked_paths: tuple[str, ...]
    d6r20_driver_blob: str
    d6r20_canonical_runner_absent: bool
    result_surface_virgin: bool


@dataclass(frozen=True)
class FlattenAttemptDiagnostics:
    local_timestamp: int
    current_position: float
    requested_direction: str
    requested_direction_code: int
    requested_qty: float
    requested_lots: int
    best_bid_tick: int
    best_ask_tick: int
    best_bid: float
    best_ask: float
    lot_size: float
    market_sweep_lower_tick: int
    market_sweep_upper_tick: int
    market_sweep_tick_count: int
    market_sweep_visible_qty: float
    market_sweep_visible_lots: int
    market_sweep_visible_sufficient: bool
    order_id: int
    status: int
    side: int
    price_tick: int
    exec_price_tick: int
    exec_qty: float
    leaves_qty: float
    exch_timestamp: int
    local_timestamp_after: int
    cumulative_executed_qty: float
    post_position: float
    position_delta: float
    expected_post_position: float
    position_accounting_consistent: bool
    order_status_is_filled: bool
    order_status_is_expired: bool
    residual_abs_position: float
    classification: str


def _require_authorization(
    *,
    authorization_token: str,
    execution_gate: bool,
) -> None:
    if execution_gate is not True:
        raise FlattenForensicError("execution_gate_closed")

    if authorization_token != AUTHORIZATION_TOKEN:
        raise FlattenForensicError("authorization_token")

    if os.environ.get(AUTHORIZATION_ENV) != AUTHORIZATION_TOKEN:
        raise FlattenForensicError("authorization_environment")


def _git_blob(path: Path) -> str:
    data = path.read_bytes()
    payload = f"blob {len(data)}\0".encode("ascii") + data
    return hashlib.sha1(payload).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def _git_output(*args: str) -> str:
    try:
        completed = subprocess.run(
            ("git", *args),
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise FlattenForensicError(
            f"repository_git_command:{args[0]}"
        ) from exc

    return completed.stdout.rstrip("\n")


def _require_virgin_result_surface() -> None:
    if RESULT_PATH.exists():
        raise FlattenForensicError("forensic_result_exists")

    if RESULT_ROOT.exists():
        if not RESULT_ROOT.is_dir():
            raise FlattenForensicError("forensic_root_not_directory")

        if any(RESULT_ROOT.iterdir()):
            raise FlattenForensicError("forensic_surface_not_virgin")


def validate_repository_preflight() -> ForensicRepositoryIdentity:
    branch = _git_output("branch", "--show-current")

    if branch != EXPECTED_BRANCH:
        raise FlattenForensicError(f"repository_branch:{branch}")

    status_output = _git_output(
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    status = tuple(line for line in status_output.splitlines() if line)
    allowed = {f"?? {path}" for path in ALLOWED_UNTRACKED_PATHS}
    unexpected = tuple(line for line in status if line not in allowed)

    if unexpected:
        raise FlattenForensicError(
            f"repository_worktree_dirty_or_unexpected:{unexpected[0]}"
        )

    head = _git_output("rev-parse", "HEAD")
    remote_head = _git_output("rev-parse", EXPECTED_REMOTE_REF)

    if len(head) != 40 or len(remote_head) != 40:
        raise FlattenForensicError("repository_head")

    if head != remote_head:
        raise FlattenForensicError(
            f"repository_remote_mismatch:{head}:{remote_head}"
        )

    driver_blob = _git_blob(D6R20_DRIVER_PATH)

    if driver_blob != D6R20_DRIVER_BLOB:
        raise FlattenForensicError(f"d6r20_driver_blob:{driver_blob}")

    if D6R20_CANONICAL_RUNNER_PATH.exists():
        raise FlattenForensicError("d6r20_canonical_runner_exists")

    _require_virgin_result_surface()

    return ForensicRepositoryIdentity(
        branch=branch,
        head=head,
        remote_ref=EXPECTED_REMOTE_REF,
        remote_head=remote_head,
        tracked_worktree_clean=True,
        permitted_untracked_paths=tuple(
            line[3:] for line in status if line in allowed
        ),
        d6r20_driver_blob=driver_blob,
        d6r20_canonical_runner_absent=True,
        result_surface_virgin=True,
    )


def validate_forensic_contract() -> None:
    if FORENSIC_SCOPE != ((FORENSIC_DAY, FORENSIC_POLICY, FORENSIC_SCENARIO),):
        raise FlattenForensicError("forensic_scope")

    if _git_blob(D6R20_DRIVER_PATH) != D6R20_DRIVER_BLOB:
        raise FlattenForensicError("d6r20_driver_blob")

    if _sha256(FAILED_Q1_EVIDENCE_PATH) != FAILED_Q1_SHA256:
        raise FlattenForensicError("failed_q1_evidence_sha256")

    spec = d6r19_runner._spec_for_day(FORENSIC_DAY)

    if (
        spec.rows != 64_314_723
        or spec.bytes != 4_116_142_528
        or spec.sha256
        != "8f0a4fbd56ecdc261dbe2041ce138a094"
        "56423074925d495272716219a1d4da1"
    ):
        raise FlattenForensicError("january_source_identity")


def _rust_round_nonnegative(value: float) -> int:
    number = float(value)

    if not math.isfinite(number) or number < 0.0:
        raise FlattenForensicError("nonnegative_round_value")

    return int(math.floor(number + 0.5))


def quantity_lots(qty: float, *, lot_size: float = p.LOT_SIZE) -> int:
    quantity = float(qty)
    lot = float(lot_size)

    if not math.isfinite(quantity) or quantity < 0.0:
        raise FlattenForensicError("quantity")

    if not math.isfinite(lot) or lot <= 0.0:
        raise FlattenForensicError("lot_size")

    return _rust_round_nonnegative(quantity / lot)


def market_sweep_ticks(
    *,
    direction: int,
    best_bid_tick: int,
    best_ask_tick: int,
) -> tuple[int, ...]:
    bid = int(best_bid_tick)
    ask = int(best_ask_tick)

    if bid >= ask:
        raise FlattenForensicError("crossed_book")

    if direction == SHORT:
        return tuple(range(bid, bid - 101, -1))

    if direction == LONG:
        return tuple(range(ask, ask + 100))

    raise FlattenForensicError("flatten_direction")


def market_sweep_visible_qty(
    depth,
    *,
    direction: int,
) -> tuple[float, int, int, int]:
    ticks = market_sweep_ticks(
        direction=direction,
        best_bid_tick=int(depth.best_bid_tick),
        best_ask_tick=int(depth.best_ask_tick),
    )
    quantities = []

    for tick in ticks:
        if direction == SHORT:
            qty = float(depth.bid_qty_at_tick(tick))
        else:
            qty = float(depth.ask_qty_at_tick(tick))

        if not math.isfinite(qty) or qty < 0.0:
            raise FlattenForensicError("market_depth_quantity")

        quantities.append(qty)

    return (
        math.fsum(quantities),
        min(ticks),
        max(ticks),
        len(ticks),
    )


def classify_flatten_execution(
    *,
    requested_qty: float,
    market_sweep_visible_qty: float,
    leaves_qty: float,
    post_position: float,
    expected_post_position: float,
    lot_size: float = p.LOT_SIZE,
) -> str:
    requested_lots = quantity_lots(requested_qty, lot_size=lot_size)
    visible_lots = quantity_lots(
        market_sweep_visible_qty,
        lot_size=lot_size,
    )
    leaves = float(leaves_qty)
    post = float(post_position)
    expected = float(expected_post_position)

    if not all(math.isfinite(x) for x in (leaves, post, expected)):
        raise FlattenForensicError("classification_nonfinite")

    leaves_remain = leaves > LOT_TOLERANCE
    post_nonflat = abs(post) > POSITION_TOLERANCE
    accounting_inconsistent = not math.isclose(
        post,
        expected,
        rel_tol=0.0,
        abs_tol=POSITION_TOLERANCE,
    )

    if leaves_remain and visible_lots < requested_lots and post_nonflat:
        return MARKET_DEPTH_SWEEP_INSUFFICIENT

    if leaves_remain and visible_lots >= requested_lots:
        return MARKET_ORDER_UNEXPECTED_PARTIAL

    if not leaves_remain and (post_nonflat or accounting_inconsistent):
        return POSITION_ACCOUNTING_MISMATCH

    return OTHER_EXECUTION_MISMATCH


class FlattenForensicContinuousHistoricalPolicyKernel(
    d6r20.ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel
):
    """D6R20 with read-only observations around its one flatten submission."""

    def __init__(self, *, forensic_sink=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.flatten_forensics = (
            forensic_sink if forensic_sink is not None else []
        )

    def _execute_unique_flatten(
        self,
        *,
        direction: int,
        qty: float,
    ) -> None:
        before = binding.snapshot_state_values(self.bt.state_values(d2.ASSET_NO))
        flatten_order_id = int(self.next_flatten_order_id)

        if flatten_order_id >= int(d2.ORDER_ID_START):
            raise base.RealHistoricalDriverError("flatten_order_id_exhausted")

        depth = self.bt.depth(d2.ASSET_NO)
        pre_position = float(self.bt.position(d2.ASSET_NO))
        request_qty = float(qty)
        request_direction = int(direction)
        visible_qty, lower_tick, upper_tick, tick_count = (
            market_sweep_visible_qty(depth, direction=request_direction)
        )
        requested_lots = quantity_lots(request_qty)
        visible_lots = quantity_lots(visible_qty)
        local_timestamp = int(self.bt.current_timestamp)
        best_bid_tick = int(depth.best_bid_tick)
        best_ask_tick = int(depth.best_ask_tick)
        best_bid = float(depth.best_bid)
        best_ask = float(depth.best_ask)

        view = m4.submit_forced_flatten(
            self.bt,
            self.h,
            direction=request_direction,
            qty=request_qty,
            order_id=flatten_order_id,
            wait=True,
        )

        after = binding.snapshot_state_values(self.bt.state_values(d2.ASSET_NO))
        post_position = float(self.bt.position(d2.ASSET_NO))
        cumulative_executed_qty = request_qty - float(view.leaves_qty)
        side_sign = -1.0 if request_direction == SHORT else 1.0
        expected_post_position = (
            pre_position + side_sign * cumulative_executed_qty
        )
        classification = classify_flatten_execution(
            requested_qty=request_qty,
            market_sweep_visible_qty=visible_qty,
            leaves_qty=float(view.leaves_qty),
            post_position=post_position,
            expected_post_position=expected_post_position,
        )
        attempt = FlattenAttemptDiagnostics(
            local_timestamp=local_timestamp,
            current_position=pre_position,
            requested_direction=(
                "SHORT" if request_direction == SHORT else "LONG"
            ),
            requested_direction_code=request_direction,
            requested_qty=request_qty,
            requested_lots=requested_lots,
            best_bid_tick=best_bid_tick,
            best_ask_tick=best_ask_tick,
            best_bid=best_bid,
            best_ask=best_ask,
            lot_size=float(p.LOT_SIZE),
            market_sweep_lower_tick=lower_tick,
            market_sweep_upper_tick=upper_tick,
            market_sweep_tick_count=tick_count,
            market_sweep_visible_qty=visible_qty,
            market_sweep_visible_lots=visible_lots,
            market_sweep_visible_sufficient=(visible_lots >= requested_lots),
            order_id=int(view.order_id),
            status=int(view.status),
            side=int(view.side),
            price_tick=int(view.price_tick),
            exec_price_tick=int(view.exec_price_tick),
            exec_qty=float(view.exec_qty),
            leaves_qty=float(view.leaves_qty),
            exch_timestamp=int(view.exch_timestamp),
            local_timestamp_after=int(view.local_timestamp),
            cumulative_executed_qty=cumulative_executed_qty,
            post_position=post_position,
            position_delta=post_position - pre_position,
            expected_post_position=expected_post_position,
            position_accounting_consistent=math.isclose(
                post_position,
                expected_post_position,
                rel_tol=0.0,
                abs_tol=POSITION_TOLERANCE,
            ),
            order_status_is_filled=(int(view.status) == int(d2.HFT_FILLED)),
            order_status_is_expired=(int(view.status) == int(d2.HFT_EXPIRED)),
            residual_abs_position=abs(post_position),
            classification=classification,
        )
        self.flatten_forensics.append(attempt)

        # Preserve the inherited path byte-for-byte after the added observation.
        if int(view.order_id) != flatten_order_id:
            raise base.RealHistoricalDriverError("flatten_order_identity")

        self.next_flatten_order_id += 1
        self.flatten_order_ids.append(flatten_order_id)

        event = binding.bind_forced_flatten_from_state_delta(
            view,
            before=before,
            after=after,
            policy_id=self.policy_id,
            day=self.day,
        )

        if event.kind != binding.FILL:
            raise base.RealHistoricalDriverError("flatten_fill_missing")

        self.bound_fills.append(event)
        response_local_ns = int(self.bt.current_timestamp)
        self.inventory_clock = self.inventory_clock.observe_local_position(
            new_position=float(self.bt.position(d2.ASSET_NO)),
            local_response_timestamp_ns=response_local_ns,
        )
        self.flatten_response_local_ns = response_local_ns

    def _maybe_execute_forced_flatten(self) -> None:
        try:
            super()._maybe_execute_forced_flatten()
        except base.RealHistoricalDriverError as exc:
            if str(exc) == "completed_flatten_nonflat":
                raise FlattenForensicError(
                    "completed_flatten_nonflat_forensic"
                ) from exc
            raise


HISTORICAL_KERNEL = FlattenForensicContinuousHistoricalPolicyKernel


def open_verified_january_source(
    *,
    authorization_token: str,
    execution_gate: bool,
) -> adapter.CanonicalJanMemmap:
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )
    spec = d6r19_runner._spec_for_day(FORENSIC_DAY)
    source = adapter._open_verified_file(
        spec.path,
        expected_sha256=spec.sha256,
        expected_bytes=spec.bytes,
        expected_rows=spec.rows,
    )

    try:
        d6r19_runner.validate_canonical_verified_source(
            source,
            day=FORENSIC_DAY,
        )
    except Exception:
        source.close()
        raise

    return source


def _hftbacktest_module():
    import hftbacktest as h

    return h


def run_bound_forensic_replay(
    source: adapter.CanonicalJanMemmap,
    *,
    forensic_sink: list[FlattenAttemptDiagnostics],
) -> None:
    bridge.validate_direct_index(
        policy_id=FORENSIC_POLICY,
        day=FORENSIC_DAY,
        index=None,
    )
    h = _hftbacktest_module()
    asset = base._build_asset_from_verified_source(
        source,
        scenario=FORENSIC_SCENARIO,
        initial_snapshot=None,
    )
    bt = h.HashMapMarketDepthBacktest([asset])
    primary_exception: BaseException | None = None

    try:
        kernel = HISTORICAL_KERNEL(
            bt=bt,
            h=h,
            policy_id=FORENSIC_POLICY,
            day=FORENSIC_DAY,
            scenario=FORENSIC_SCENARIO,
            terminal_source_local_ns=int(source.data[-1]["local_ts"]),
            direct_index=None,
            forensic_sink=forensic_sink,
        )
        kernel.run_full_day()
    except BaseException as exc:
        primary_exception = exc
        raise
    finally:
        try:
            rc = int(bt.close())
        except BaseException:
            if primary_exception is None:
                raise
        else:
            if rc != 0 and primary_exception is None:
                raise FlattenForensicError(f"backtest_close_rc:{rc}")


def _write_json_new(payload: dict) -> Path:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)

    try:
        with RESULT_PATH.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise FlattenForensicError("forensic_result_exists") from exc

    return RESULT_PATH


def run_flatten_execution_forensic(
    *,
    authorization_token: str,
    execution_gate: bool,
) -> dict:
    """Run exactly one authorized real replay and persist its failure facts."""
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )
    repository = validate_repository_preflight()
    validate_forensic_contract()
    runtime = q1.validate_runtime_identity(_hftbacktest_module())
    attempts: list[FlattenAttemptDiagnostics] = []
    spec = d6r19_runner._spec_for_day(FORENSIC_DAY)
    replay_exception: BaseException | None = None

    try:
        with open_verified_january_source(
            authorization_token=authorization_token,
            execution_gate=execution_gate,
        ) as source:
            before = base._stat_identity(source.path)

            try:
                run_bound_forensic_replay(source, forensic_sink=attempts)
            except BaseException as exc:
                replay_exception = exc

            after = base._stat_identity(source.path)

            if before != after and replay_exception is None:
                replay_exception = FlattenForensicError(
                    "source_identity_changed"
                )
    except BaseException as exc:
        if replay_exception is None:
            replay_exception = exc

    if replay_exception is None:
        replay_exception = FlattenForensicError(
            "completed_flatten_nonflat_not_reproduced"
        )

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "schema_version": "dev045-d6r20-q1-flatten-forensic-v1",
        "status": "FORENSIC_EXECUTION_FAILURE_CAPTURED",
        "head": repository.head,
        "repository": asdict(repository),
        "scope": {
            "day": FORENSIC_DAY,
            "policy": FORENSIC_POLICY,
            "scenario": FORENSIC_SCENARIO,
            "replay_count": 1,
        },
        "d6r20_driver_blob": D6R20_DRIVER_BLOB,
        "failed_q1_head": FAILED_Q1_HEAD,
        "failed_q1_sha256": FAILED_Q1_SHA256,
        "hftbacktest": {
            "version": runtime.version,
            "compiled_artifact_sha256": runtime.compiled_artifact_sha256,
            "verified": runtime.verified,
        },
        "exception_type": type(replay_exception).__name__,
        "exception_message": str(replay_exception),
        "flatten_attempt_count": len(attempts),
        "flatten_attempts": [asdict(item) for item in attempts],
        "classifications": [item.classification for item in attempts],
        "automatic_retry": False,
        "canonical_economic_attempt": False,
        "canonical_attempt_consumed": False,
        "economic_arena_called": False,
        "strategy_ranking_performed": False,
        "economic_conclusion": "UNAVAILABLE",
        "live_trading_authorized": False,
    }
    _write_json_new(payload)
    raise replay_exception


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "FAILED_Q1_HEAD",
    "FAILED_Q1_SHA256",
    "D6R20_DRIVER_BLOB",
    "FORENSIC_DAY",
    "FORENSIC_POLICY",
    "FORENSIC_SCENARIO",
    "FORENSIC_SCOPE",
    "AUTHORIZATION_ENV",
    "AUTHORIZATION_TOKEN",
    "RESULT_ROOT",
    "RESULT_PATH",
    "MARKET_DEPTH_SWEEP_INSUFFICIENT",
    "MARKET_ORDER_UNEXPECTED_PARTIAL",
    "POSITION_ACCOUNTING_MISMATCH",
    "OTHER_EXECUTION_MISMATCH",
    "FORENSIC_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "REAL_FORENSIC_REPLAY_EXECUTED",
    "CANONICAL_RUNNER_IMPLEMENTED",
    "CANONICAL_ATTEMPT_CONSUMED",
    "ECONOMIC_ARENA_CALLED",
    "STRATEGY_RANKING_PERFORMED",
    "AUTOMATIC_RETRY",
    "LIVE_TRADING_AUTHORIZED",
    "FlattenForensicError",
    "ForensicRepositoryIdentity",
    "FlattenAttemptDiagnostics",
    "quantity_lots",
    "market_sweep_ticks",
    "market_sweep_visible_qty",
    "classify_flatten_execution",
    "FlattenForensicContinuousHistoricalPolicyKernel",
    "HISTORICAL_KERNEL",
    "validate_forensic_contract",
    "validate_repository_preflight",
    "open_verified_january_source",
    "run_bound_forensic_replay",
    "run_flatten_execution_forensic",
]
