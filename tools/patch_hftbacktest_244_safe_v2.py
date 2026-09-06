from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess


BASE_COMMIT = "a244a14250b42d97fc305569c93c4117cd5e1dff"
PATCHSET = (
    "ISSUE_312_EXACT_QTY_CLEANUP",
    "ISSUE_316_PARTIAL_LOCAL_ACCOUNTING",
    "TAKER_MULTILEVEL_INTERMEDIATE_RESPONSE_ACCOUNTING",
)


@dataclass(frozen=True)
class FillFalseCallSite:
    name: str
    side: str
    order_type: str
    time_in_force: str
    role: str


FILL_FALSE_CALL_SITES = (
    FillFalseCallSite(
        "BUY_LIMIT_FOK_DEPTH_SWEEP",
        "BUY",
        "LIMIT_MARKETABLE",
        "FOK",
        "IMMEDIATE_LIQUIDITY_TAKING_LOOP",
    ),
    FillFalseCallSite(
        "BUY_LIMIT_IOC_DEPTH_SWEEP",
        "BUY",
        "LIMIT_MARKETABLE",
        "IOC",
        "IMMEDIATE_LIQUIDITY_TAKING_LOOP",
    ),
    FillFalseCallSite(
        "BUY_LIMIT_GTC_DEPTH_SWEEP",
        "BUY",
        "LIMIT_MARKETABLE",
        "GTC",
        "IMMEDIATE_LIQUIDITY_TAKING_LOOP",
    ),
    FillFalseCallSite(
        "BUY_LIMIT_GTC_REMAINDER",
        "BUY",
        "LIMIT_MARKETABLE",
        "GTC",
        "IMMEDIATE_LIQUIDITY_TAKING_FINAL_REMAINDER",
    ),
    FillFalseCallSite(
        "BUY_MARKET_DEPTH_SWEEP",
        "BUY",
        "MARKET",
        "ANY_M4_USES_GTC",
        "IMMEDIATE_LIQUIDITY_TAKING_LOOP",
    ),
    FillFalseCallSite(
        "SELL_LIMIT_FOK_DEPTH_SWEEP",
        "SELL",
        "LIMIT_MARKETABLE",
        "FOK",
        "IMMEDIATE_LIQUIDITY_TAKING_LOOP",
    ),
    FillFalseCallSite(
        "SELL_LIMIT_IOC_DEPTH_SWEEP",
        "SELL",
        "LIMIT_MARKETABLE",
        "IOC",
        "IMMEDIATE_LIQUIDITY_TAKING_LOOP",
    ),
    FillFalseCallSite(
        "SELL_LIMIT_GTC_DEPTH_SWEEP",
        "SELL",
        "LIMIT_MARKETABLE",
        "GTC",
        "IMMEDIATE_LIQUIDITY_TAKING_LOOP",
    ),
    FillFalseCallSite(
        "SELL_LIMIT_GTC_REMAINDER",
        "SELL",
        "LIMIT_MARKETABLE",
        "GTC",
        "IMMEDIATE_LIQUIDITY_TAKING_FINAL_REMAINDER",
    ),
    FillFalseCallSite(
        "SELL_MARKET_DEPTH_SWEEP",
        "SELL",
        "MARKET",
        "ANY_M4_USES_GTC",
        "IMMEDIATE_LIQUIDITY_TAKING_LOOP",
    ),
)

V1_REPLACEMENTS = {
    "hftbacktest/src/backtest/proc/local.rs": [
        (
            "if order.status == Status::Filled {\n"
            "                self.state.apply_fill(&order);\n"
            "            }",
            "if order.status == Status::Filled || order.status == Status::PartiallyFilled {\n"
            "                self.state.apply_fill(&order);\n"
            "            }",
            1,
        ),
    ],
    "hftbacktest/src/backtest/proc/l3_local.rs": [
        (
            "if order.status == Status::Filled {\n"
            "                self.state.apply_fill(&order);\n"
            "            }",
            "if order.status == Status::Filled || order.status == Status::PartiallyFilled {\n"
            "                self.state.apply_fill(&order);\n"
            "            }",
            1,
        ),
    ],
    "hftbacktest/src/backtest/proc/partialfillexchange.rs": [
        (
            "let exec_qty = if filled_qty > order.leaves_qty {",
            "let exec_qty = if filled_qty >= order.leaves_qty {",
            2,
        ),
    ],
}

TAKER_RESPONSE_OLD = """        self.state.apply_fill(order);

        if MAKE_RESPONSE {
            self.order_e2l.respond(order.clone());
        }"""

TAKER_RESPONSE_NEW = """        self.state.apply_fill(order);

        if MAKE_RESPONSE || order.status == Status::PartiallyFilled {
            self.order_e2l.respond(order.clone());
        }"""

V2_REPLACEMENT = (
    TAKER_RESPONSE_OLD,
    TAKER_RESPONSE_NEW,
    1,
)


def _git_output(root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ("git", "-C", str(root), *args),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"REFUSE_PATCH git_{args[0]}") from exc

    return completed.stdout.rstrip("\n")


def require_exact_clean_base(root: Path) -> None:
    if not (root / ".git").exists():
        raise SystemExit("REFUSE_PATCH source_root is not a git checkout")

    head = _git_output(root, "rev-parse", "HEAD")

    if head != BASE_COMMIT:
        raise SystemExit(f"REFUSE_PATCH base_commit {head}")

    status = _git_output(root, "status", "--porcelain=v1", "--untracked-files=all")

    if status:
        raise SystemExit("REFUSE_PATCH source_worktree_not_clean")


def audit_fill_false_call_sites(text: str) -> None:
    expected_count = len(FILL_FALSE_CALL_SITES)
    actual_count = text.count("self.fill::<false>")

    if actual_count != expected_count:
        raise SystemExit(
            "REFUSE_PATCH fill_false_count "
            f"expected={expected_count} actual={actual_count}"
        )

    ack_new_start = text.count("fn ack_new(")
    ack_cancel_start = text.count("fn ack_cancel(")

    if ack_new_start != 1 or ack_cancel_start != 1:
        raise SystemExit("REFUSE_PATCH ack_new_boundaries")

    before_ack_new, ack_and_after = text.split("fn ack_new(", 1)
    ack_new_body, after_ack_new = ack_and_after.split("fn ack_cancel(", 1)

    if "self.fill::<false>" in before_ack_new or "self.fill::<false>" in after_ack_new:
        raise SystemExit("REFUSE_PATCH fill_false_outside_ack_new")

    if ack_new_body.count("self.fill::<false>") != expected_count:
        raise SystemExit("REFUSE_PATCH fill_false_ack_new_count")


def _replace_exact(path: Path, replacement: tuple[str, str, int]) -> None:
    old, new, expected_count = replacement
    text = path.read_text(encoding="utf-8")
    count = text.count(old)

    if count != expected_count:
        raise SystemExit(
            f"REFUSE_PATCH {path}: expected {expected_count} occurrences, found {count}"
        )

    path.write_text(text.replace(old, new), encoding="utf-8")


def _verify_exact(path: Path, replacement: tuple[str, str, int]) -> None:
    old, new, expected_count = replacement
    text = path.read_text(encoding="utf-8")

    if old in text:
        raise SystemExit(f"PATCH_VERIFY_OLD_REMAINS {path}")

    count = text.count(new)

    if count != expected_count:
        raise SystemExit(
            f"PATCH_VERIFY_NEW_COUNT {path}: expected {expected_count}, found {count}"
        )


def apply_patchset(root: Path) -> None:
    partial_path = root / "hftbacktest/src/backtest/proc/partialfillexchange.rs"

    if not partial_path.is_file():
        raise SystemExit("REFUSE_PATCH missing partialfillexchange.rs")

    audit_fill_false_call_sites(partial_path.read_text(encoding="utf-8"))

    for relative_path, replacements in V1_REPLACEMENTS.items():
        path = root / relative_path

        if not path.is_file():
            raise SystemExit(f"REFUSE_PATCH missing {relative_path}")

        for replacement in replacements:
            _replace_exact(path, replacement)

    _replace_exact(partial_path, V2_REPLACEMENT)

    for relative_path, replacements in V1_REPLACEMENTS.items():
        path = root / relative_path

        for replacement in replacements:
            _verify_exact(path, replacement)

    _verify_exact(partial_path, V2_REPLACEMENT)
    patched_partial = partial_path.read_text(encoding="utf-8")
    audit_fill_false_call_sites(patched_partial)

    if patched_partial.count(TAKER_RESPONSE_NEW) != 1:
        raise SystemExit("PATCH_VERIFY_TAKER_RESPONSE_COUNT")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()

    require_exact_clean_base(root)
    apply_patchset(root)

    print("DEV045_HFT244_SAFE_PATCH_V2=PASS")
    print(f"BASE_COMMIT={BASE_COMMIT}")
    print(f"FILL_FALSE_CALL_SITES={len(FILL_FALSE_CALL_SITES)}")
    print("PATCHES=" + ",".join(PATCHSET))


if __name__ == "__main__":
    main()
