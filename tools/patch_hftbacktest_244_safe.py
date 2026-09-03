from __future__ import annotations

import argparse
from pathlib import Path

BASE_COMMIT = "a244a14250b42d97fc305569c93c4117cd5e1dff"

REPLACEMENTS = {
    "hftbacktest/src/backtest/proc/local.rs": [
        (
            "if order.status == Status::Filled {\n                self.state.apply_fill(&order);\n            }",
            "if order.status == Status::Filled || order.status == Status::PartiallyFilled {\n                self.state.apply_fill(&order);\n            }",
            1,
        ),
    ],
    "hftbacktest/src/backtest/proc/l3_local.rs": [
        (
            "if order.status == Status::Filled {\n                self.state.apply_fill(&order);\n            }",
            "if order.status == Status::Filled || order.status == Status::PartiallyFilled {\n                self.state.apply_fill(&order);\n            }",
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


def patch_file(path: Path, replacements: list[tuple[str, str, int]]) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new, expected_count in replacements:
        count = text.count(old)
        if count != expected_count:
            raise SystemExit(
                f"REFUSE_PATCH {path}: expected {expected_count} occurrences, found {count}"
            )
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def verify_file(path: Path, replacements: list[tuple[str, str, int]]) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new, expected_count in replacements:
        if old in text:
            raise SystemExit(f"PATCH_VERIFY_OLD_REMAINS {path}")
        count = text.count(new)
        if count != expected_count:
            raise SystemExit(
                f"PATCH_VERIFY_NEW_COUNT {path}: expected {expected_count}, found {count}"
            )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source_root", type=Path)
    ns = ap.parse_args()
    root = ns.source_root.resolve()
    if not (root / ".git").exists():
        raise SystemExit("REFUSE_PATCH source_root is not a git checkout")

    for rel, replacements in REPLACEMENTS.items():
        path = root / rel
        if not path.is_file():
            raise SystemExit(f"REFUSE_PATCH missing {rel}")
        patch_file(path, replacements)

    for rel, replacements in REPLACEMENTS.items():
        verify_file(root / rel, replacements)

    print("DEV045_HFT244_SAFE_PATCH=PASS")
    print(f"BASE_COMMIT={BASE_COMMIT}")
    print("PATCHES=ISSUE_312_EXACT_QTY_CLEANUP,ISSUE_316_PARTIAL_LOCAL_ACCOUNTING")


if __name__ == "__main__":
    main()
