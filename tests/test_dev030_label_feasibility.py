from __future__ import annotations

import ast
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

from multimarket import dev030_label_feasibility as lf
from multimarket.dev030_first_passage import LONG_FIRST, NONE, SHORT_FIRST


def _valid_record(label: str, *, touch_ms: float | None = None) -> dict:
    return {
        "label": label,
        "target_valid": True,
        "invalid_reason": None,
        "same_row_ambiguous": False,
        "time_to_first_barrier_ms": touch_ms,
        "entry_spread_bps": 1.25,
        "long_max_favorable_excursion_bps": 9.0,
        "long_max_adverse_excursion_bps": 3.0,
        "short_max_favorable_excursion_bps": 2.0,
        "short_max_adverse_excursion_bps": 10.0,
    }


def _invalid_record(reason: str, *, same_row: bool = False) -> dict:
    return {
        "label": None,
        "target_valid": False,
        "invalid_reason": reason,
        "same_row_ambiguous": same_row,
    }


def _support_metrics(
    *,
    horizon: int = 60,
    barrier: int = 16,
    valid_fraction: float = 0.99,
    touches: int = 200,
    minority: int = 80,
    touch_days: int = 7,
    both_days: int = 7,
    balance: float = 0.67,
    median_touch_ms: float = 2_000.0,
) -> dict:
    return {
        "horizon_seconds": horizon,
        "barrier_bps": barrier,
        "valid_fraction": valid_fraction,
        "invalid_fraction": 1.0 - valid_fraction,
        "invalid_counts_by_reason": {},
        "directional_touch_count": touches,
        "minority_direction_count": minority,
        "days_with_any_directional_touch": touch_days,
        "days_with_both_long_and_short": both_days,
        "direction_balance_ratio": balance,
        "time_to_first_barrier_ms": {"median": median_touch_ms},
        "cost_plausibility": lf.cost_plausibility(barrier),
    }


class AggregationTests(unittest.TestCase):
    def test_long_short_none_invalid_accounting_and_fractions(self) -> None:
        records = [
            _valid_record(LONG_FIRST, touch_ms=250.0),
            _valid_record(SHORT_FIRST, touch_ms=500.0),
            _valid_record(NONE),
            _invalid_record("path_quote_invalid"),
        ]
        result = lf.summarize_records(records)

        self.assertEqual(result["candidate_decisions"], 4)
        self.assertEqual(result["valid_targets"], 3)
        self.assertEqual(result["invalid_targets"], 1)
        self.assertEqual(result["LONG_FIRST_count"], 1)
        self.assertEqual(result["SHORT_FIRST_count"], 1)
        self.assertEqual(result["NONE_count"], 1)
        self.assertEqual(result["valid_fraction"], 0.75)
        self.assertEqual(result["invalid_fraction"], 0.25)
        self.assertEqual(result["directional_touch_fraction_of_valid"], 2 / 3)
        self.assertEqual(result["direction_balance_ratio"], 1.0)

    def test_same_row_ambiguous_is_invalid_and_never_none(self) -> None:
        result = lf.summarize_records(
            [_invalid_record("same_row_ambiguous", same_row=True)]
        )
        self.assertEqual(result["invalid_targets"], 1)
        self.assertEqual(result["same_row_ambiguous_count"], 1)
        self.assertEqual(
            result["invalid_counts_by_reason"], {"same_row_ambiguous": 1}
        )
        self.assertEqual(result["NONE_count"], 0)

    def test_invalid_target_cannot_become_none(self) -> None:
        record = _invalid_record("path_grid_missing")
        record["label"] = NONE
        with self.assertRaises(lf.AuditProtocolError):
            lf.summarize_records([record])

    def test_negative_valid_record_diagnostics_are_rejected(self) -> None:
        fields = (
            "entry_spread_bps",
            "long_max_favorable_excursion_bps",
            "long_max_adverse_excursion_bps",
            "short_max_favorable_excursion_bps",
            "short_max_adverse_excursion_bps",
            "time_to_first_barrier_ms",
        )
        for field in fields:
            with self.subTest(field=field):
                record = _valid_record(LONG_FIRST, touch_ms=250.0)
                record[field] = -0.01
                with self.assertRaisesRegex(
                    lf.AuditProtocolError,
                    rf"{field} must be non-negative",
                ):
                    lf.summarize_records([record])

    def test_zero_denominators_are_json_safe_nulls(self) -> None:
        result = lf.summarize_records([])
        for key in (
            "valid_fraction",
            "invalid_fraction",
            "directional_touch_fraction_of_valid",
            "LONG_fraction_of_directional",
            "SHORT_fraction_of_directional",
            "direction_balance_ratio",
        ):
            self.assertIsNone(result[key])
        json.dumps(result, allow_nan=False)

    def test_percentile_summaries_are_deterministic(self) -> None:
        records = [
            _valid_record(LONG_FIRST, touch_ms=100.0),
            _valid_record(SHORT_FIRST, touch_ms=200.0),
            _valid_record(LONG_FIRST, touch_ms=300.0),
            _valid_record(SHORT_FIRST, touch_ms=400.0),
        ]
        result = lf.summarize_records(records)
        touch = result["time_to_first_barrier_ms"]
        self.assertEqual(touch["p10"], 130.0)
        self.assertEqual(touch["p25"], 175.0)
        self.assertEqual(touch["median"], 250.0)
        self.assertEqual(touch["p75"], 325.0)
        self.assertEqual(touch["p90"], 370.0)
        self.assertEqual(result["LONG_FIRST_time_to_touch_median_ms"], 200.0)
        self.assertEqual(result["SHORT_FIRST_time_to_touch_median_ms"], 300.0)

    def test_pooled_aggregation_and_cross_day_minima(self) -> None:
        day_one_records = [
            _valid_record(LONG_FIRST, touch_ms=100.0),
            _valid_record(SHORT_FIRST, touch_ms=200.0),
            _valid_record(NONE),
        ]
        day_two_records = [
            _valid_record(LONG_FIRST, touch_ms=300.0),
            _valid_record(NONE),
            _invalid_record("path_quote_invalid"),
        ]
        first = lf.RecordAccumulator()
        second = lf.RecordAccumulator()
        first.extend(day_one_records)
        second.extend(day_two_records)
        pooled = lf.RecordAccumulator()
        pooled.merge(first)
        pooled.merge(second)

        result = lf.pooled_day_metrics(
            pooled.summary(), [first.summary(), second.summary()]
        )
        self.assertEqual(result["candidate_decisions"], 6)
        self.assertEqual(result["days_with_any_valid_target"], 2)
        self.assertEqual(result["days_with_any_directional_touch"], 2)
        self.assertEqual(result["days_with_both_long_and_short"], 1)
        self.assertEqual(result["minimum_valid_targets_across_days"], 2)
        self.assertEqual(result["minimum_directional_touches_across_days"], 1)
        self.assertEqual(result["minimum_minority_direction_count_across_days"], 0)
        self.assertAlmostEqual(
            result["median_directional_touch_fraction_across_days"],
            (2 / 3 + 1 / 2) / 2,
        )

    def test_identical_inputs_produce_identical_outputs(self) -> None:
        records = [
            _valid_record(LONG_FIRST, touch_ms=250.0),
            _valid_record(NONE),
            _invalid_record("path_grid_missing"),
        ]
        first = json.dumps(lf.summarize_records(records), sort_keys=True)
        second = json.dumps(lf.summarize_records(records), sort_keys=True)
        self.assertEqual(first, second)


class DecisionGridTests(unittest.TestCase):
    def test_exact_sixty_second_grid_is_deterministic(self) -> None:
        timestamps = np.asarray(
            [0, 250_000, 59_750_000, 60_000_000, 60_250_000, 120_000_000],
            dtype=np.int64,
        )
        expected = np.asarray([0, 3, 5], dtype=np.int64)
        np.testing.assert_array_equal(
            lf.minute_decision_indices(timestamps), expected
        )
        np.testing.assert_array_equal(
            lf.minute_decision_indices(timestamps), expected
        )

    def test_missing_minute_is_not_created_filled_or_shifted(self) -> None:
        timestamps = np.asarray(
            [0, 250_000, 59_750_000, 60_250_000, 119_750_000, 120_000_000],
            dtype=np.int64,
        )
        indices = lf.minute_decision_indices(timestamps)
        np.testing.assert_array_equal(indices, np.asarray([0, 5]))
        np.testing.assert_array_equal(
            timestamps[indices], np.asarray([0, 120_000_000])
        )

    def test_non_chronological_timestamps_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            lf.minute_decision_indices(np.asarray([0, 60_000_000, 0]))


class CostAndSupportTests(unittest.TestCase):
    def test_exact_cost_plausibility_boundaries(self) -> None:
        at_eight = lf.cost_plausibility(8)
        self.assertEqual(at_eight["cost_plausibility_class"], lf.COST_CHALLENGED)
        self.assertEqual(at_eight["margin_after_8bps"], 0.0)
        self.assertEqual(at_eight["margin_after_12bps"], -4.0)

        at_twelve = lf.cost_plausibility(12)
        self.assertEqual(
            at_twelve["cost_plausibility_class"], lf.POSITIVE_AFTER_8_ONLY
        )
        self.assertEqual(at_twelve["margin_after_8bps"], 4.0)
        self.assertEqual(at_twelve["margin_after_12bps"], 0.0)

        above_twelve = lf.cost_plausibility(16)
        self.assertEqual(
            above_twelve["cost_plausibility_class"], lf.POSITIVE_AFTER_12
        )
        self.assertEqual(above_twelve["margin_after_8bps"], 8.0)
        self.assertEqual(above_twelve["margin_after_12bps"], 4.0)

    def test_cost_plausibility_does_not_change_support_class(self) -> None:
        classes = {
            lf.classify_support(_support_metrics(barrier=barrier))
            for barrier in (4, 8, 12, 16, 24, 36)
        }
        self.assertEqual(classes, {lf.ROBUST_SUPPORT})

    def test_support_classification_boundary_cases(self) -> None:
        self.assertEqual(lf.classify_support(_support_metrics()), lf.ROBUST_SUPPORT)
        self.assertEqual(
            lf.classify_support(
                _support_metrics(
                    valid_fraction=0.90,
                    touches=75,
                    minority=25,
                    touch_days=5,
                    both_days=0,
                )
            ),
            lf.USABLE_SUPPORT,
        )
        self.assertEqual(
            lf.classify_support(
                _support_metrics(touches=25, minority=1, touch_days=1, both_days=0)
            ),
            lf.THIN_SUPPORT,
        )
        self.assertEqual(
            lf.classify_support(
                _support_metrics(touches=24, minority=1, touch_days=1, both_days=0)
            ),
            lf.NOT_USABLE,
        )
        self.assertEqual(
            lf.classify_support(_support_metrics(valid_fraction=0.899)),
            lf.NOT_USABLE,
        )

    def test_shortlist_is_diverse_and_reasons_are_complete(self) -> None:
        rows = [
            _support_metrics(horizon=10, barrier=4, touches=1000, minority=300),
            _support_metrics(horizon=30, barrier=8, touches=900, minority=280),
            _support_metrics(horizon=60, barrier=4, touches=850, minority=260),
            _support_metrics(horizon=60, barrier=12, touches=300, minority=100),
            _support_metrics(horizon=120, barrier=16, touches=220, minority=80),
            _support_metrics(horizon=300, barrier=24, touches=180, minority=60),
        ]
        ranked, shortlist, _ = lf.rank_and_shortlist(rows)
        self.assertEqual(len(ranked), 6)
        classes = {row["cost_plausibility_class"] for row in shortlist}
        self.assertIn(lf.COST_CHALLENGED, classes)
        self.assertIn(lf.POSITIVE_AFTER_8_ONLY, classes)
        self.assertIn(lf.POSITIVE_AFTER_12, classes)
        self.assertNotEqual(classes, {lf.COST_CHALLENGED})

        required_reason_fields = (
            "support_class=",
            "directional_touch_count=",
            "minority_direction_count=",
            "days_with_any_directional_touch=",
            "days_with_both_long_and_short=",
            "direction_balance_ratio=",
            "median_time_to_first_barrier_ms=",
            "gross_barrier_bps=",
            "margin_after_8bps=",
            "margin_after_12bps=",
            "cost_plausibility_class=",
        )
        for row in shortlist:
            for field in required_reason_fields:
                self.assertIn(field, row["reason"])

    def test_tiny_barriers_cannot_fill_shortlist_when_alternatives_qualify(self) -> None:
        rows = [
            _support_metrics(
                horizon=10 + i, barrier=4, touches=1000 - i, minority=300
            )
            for i in range(8)
        ]
        rows.extend(
            [
                _support_metrics(horizon=120, barrier=12, touches=180, minority=60),
                _support_metrics(horizon=300, barrier=24, touches=160, minority=55),
            ]
        )
        _, shortlist, _ = lf.rank_and_shortlist(rows)
        classes = [row["cost_plausibility_class"] for row in shortlist]
        self.assertIn(lf.POSITIVE_AFTER_8_ONLY, classes)
        self.assertIn(lf.POSITIVE_AFTER_12, classes)
        self.assertLess(classes.count(lf.COST_CHALLENGED), len(classes))


class JsonAndStaticSafetyTests(unittest.TestCase):
    def test_analytical_output_is_json_safe_with_allow_nan_false(self) -> None:
        summary = lf.summarize_records(
            [_valid_record(NONE), _invalid_record("path_quote_invalid")]
        )
        encoded = lf._assert_json_safe({"summary": summary})
        self.assertEqual(json.loads(encoded)["summary"], summary)

    def test_json_rejects_nan(self) -> None:
        with self.assertRaises(ValueError):
            lf._assert_json_safe({"bad": float("nan")})

    def test_no_predictive_or_model_training_import(self) -> None:
        tree = ast.parse(Path(lf.__file__).read_text(encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        forbidden = ("sklearn", "xgboost", "lightgbm", "catboost", "codex_exp024")
        self.assertFalse(
            [name for name in imported if any(token in name for token in forbidden)]
        )

    def test_configuration_has_exact_grid_and_no_model_scope(self) -> None:
        config = lf.scientific_configuration()
        self.assertEqual(config["horizons_seconds"], [10, 30, 60, 120, 300, 600])
        self.assertEqual(config["barriers_bps"], [4, 8, 12, 16, 24, 36])
        self.assertEqual(config["total_target_geometries"], 36)
        self.assertIn("no spread double subtraction", config["economic_scope"])


class WorkspaceProvenanceTests(unittest.TestCase):
    def _git_values(self, root: Path, overrides=None):
        values = {
            ("rev-parse", "--show-toplevel"): str(root.resolve()),
            ("remote", "get-url", "origin"): lf.EXPECTED_ORIGIN,
            ("rev-parse", "HEAD"): "f" * 40,
            ("branch", "--show-current"): lf.EXPECTED_BRANCH,
            ("status", "--porcelain", "--untracked-files=no"): "",
        }
        values.update(overrides or {})

        def fake(_workspace, *args):
            return values[args]

        return fake

    def _verify_with_mocks(
        self,
        root: Path,
        *,
        git_mock=None,
        ancestor: bool = True,
        tracked=True,
    ):
        git_mock = git_mock or self._git_values(root)
        tracked_patch = (
            mock.patch.object(
                lf, "_tracked_at_execution_head", side_effect=tracked
            )
            if callable(tracked)
            else mock.patch.object(
                lf, "_tracked_at_execution_head", return_value=tracked
            )
        )
        with (
            mock.patch.object(lf, "_git", side_effect=git_mock),
            mock.patch.object(lf, "_is_ancestor", return_value=ancestor),
            tracked_patch,
            mock.patch.object(
                lf,
                "verify_exp029_artifact",
                return_value={
                    "exp029_artifact_path": lf.EXP029_REL,
                    "exp029_artifact_sha256": lf.EXPECTED_EXP029_SHA256,
                    "exp029_artifact_sha256_verified": True,
                },
            ),
        ):
            return lf.verify_workspace(root)

    def test_wrong_repository_origin_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            fake = self._git_values(
                root, {("remote", "get-url", "origin"): "wrong-origin"}
            )
            with self.assertRaisesRegex(lf.AuditProtocolError, "origin"):
                self._verify_with_mocks(root, git_mock=fake)

    def test_wrong_branch_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            fake = self._git_values(
                root, {("branch", "--show-current"): "wrong-branch"}
            )
            with self.assertRaisesRegex(lf.AuditProtocolError, "branch"):
                self._verify_with_mocks(root, git_mock=fake)

    def test_parent_baseline_must_be_ancestor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            with self.assertRaisesRegex(lf.AuditProtocolError, "ancestor"):
                self._verify_with_mocks(root, ancestor=False)

    def test_tracked_tree_modification_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            fake = self._git_values(
                root,
                {
                    ("status", "--porcelain", "--untracked-files=no"): " M file.py"
                },
            )
            with self.assertRaisesRegex(lf.AuditProtocolError, "tracked worktree"):
                self._verify_with_mocks(root, git_mock=fake)

    def test_untracked_implementation_or_test_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()

            def tracked(_workspace, relative_path):
                return relative_path not in (lf.SOURCE_REL, lf.TEST_REL)

            with self.assertRaisesRegex(lf.AuditProtocolError, "untracked"):
                self._verify_with_mocks(root, tracked=tracked)

    def test_valid_committed_descendant_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            result = self._verify_with_mocks(root)
        self.assertTrue(result["parent_baseline_is_ancestor"])
        self.assertTrue(result["tracked_tree_clean"])
        self.assertEqual(result["exp029_artifact_path"], lf.EXP029_REL)
        self.assertEqual(
            result["exp029_artifact_sha256"], lf.EXPECTED_EXP029_SHA256
        )
        self.assertIs(result["exp029_artifact_sha256_verified"], True)

    def test_wrong_exp029_digest_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / lf.EXP029_REL
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b"wrong frozen bytes")
            with self.assertRaisesRegex(lf.AuditProtocolError, "SHA-256"):
                lf.verify_exp029_artifact(root)

    def test_exp029_provenance_payload_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / lf.EXP029_REL
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b"synthetic opaque artifact")
            with mock.patch.object(
                lf, "_sha256_file", return_value=lf.EXPECTED_EXP029_SHA256
            ):
                result = lf.verify_exp029_artifact(root)
        self.assertEqual(
            set(result),
            {
                "exp029_artifact_path",
                "exp029_artifact_sha256",
                "exp029_artifact_sha256_verified",
            },
        )
        self.assertEqual(result["exp029_artifact_path"], lf.EXP029_REL)
        self.assertEqual(
            result["exp029_artifact_sha256"], lf.EXPECTED_EXP029_SHA256
        )
        self.assertIs(result["exp029_artifact_sha256_verified"], True)

    def test_wrong_exp029_digest_stops_before_market_loader(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            artifact = root / lf.EXP029_REL
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b"wrong frozen bytes")
            output = root / "future-output"
            fake_git = self._git_values(root)
            with (
                mock.patch.object(lf, "_git", side_effect=fake_git),
                mock.patch.object(lf, "_is_ancestor", return_value=True),
                mock.patch.object(
                    lf, "_tracked_at_execution_head", return_value=True
                ),
                mock.patch.object(lf, "_load_day") as loader,
                mock.patch.object(lf, "verify_input_manifest") as manifest,
            ):
                with self.assertRaisesRegex(
                    lf.AuditProtocolError, "EXP029.*SHA-256"
                ):
                    lf.run_label_feasibility(
                        workspace=root,
                        output_directory=output,
                        argv=["synthetic"],
                    )
            loader.assert_not_called()
            manifest.assert_not_called()
            self.assertFalse(output.exists())


class OutputSafetyTests(unittest.TestCase):
    def test_existing_output_directory_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp) / "existing"
            existing.mkdir()
            with self.assertRaises(FileExistsError):
                lf._assert_output_absent(existing)

    def test_atomic_write_refuses_existing_final(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            final = Path(tmp) / "artifact.json"
            final.write_bytes(b"preserve")
            with self.assertRaises(FileExistsError):
                lf._write_file_once(final, b"new")
            self.assertEqual(final.read_bytes(), b"preserve")

    def test_atomic_write_refuses_existing_part(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            final = Path(tmp) / "artifact.json"
            part = Path(str(final) + ".part")
            part.write_bytes(b"preserve-part")
            with self.assertRaises(FileExistsError):
                lf._write_file_once(final, b"new")
            self.assertFalse(final.exists())
            self.assertEqual(part.read_bytes(), b"preserve-part")

    def test_atomic_write_creates_once_and_removes_part(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            final = Path(tmp) / "artifact.json"
            digest = lf._write_file_once(final, b"payload")
            self.assertEqual(final.read_bytes(), b"payload")
            self.assertFalse(Path(str(final) + ".part").exists())
            self.assertEqual(
                digest,
                "239f59ed55e737c77147cf55ad0c1b030b6d7ee748a7426952f9b852d5a935e5",
            )


class FrozenIdentityTests(unittest.TestCase):
    def test_exact_frozen_exp029_identity(self) -> None:
        self.assertEqual(
            lf.EXP029_REL,
            "evidence/codex/exp029_p0_causal_rank_opportunity_readiness/"
            "HISTORICAL_SELECTION.json",
        )
        self.assertEqual(
            lf.EXPECTED_EXP029_SHA256,
            "86a5c29c977ee325dc37d3a3c0d2f9b3366360fcf46734785fd25fa45f1a75ee",
        )

    def test_exact_jan_jul_allowlist_and_hash_manifest(self) -> None:
        self.assertEqual(
            lf.HISTORICAL_DAYS,
            tuple(date(2026, month, 1) for month in range(1, 8)),
        )
        self.assertEqual(set(lf.EXPECTED_INPUT_SHA256), set(lf.HISTORICAL_DAYS))
        lowercase_hex = set("0123456789abcdef")
        for day, digest in lf.EXPECTED_INPUT_SHA256.items():
            with self.subTest(day=day):
                self.assertIs(type(digest), str)
                self.assertEqual(len(digest), 64)
                self.assertFalse(set(digest) - lowercase_hex)
        self.assertEqual(
            lf.EXPECTED_INPUT_SHA256[date(2026, 3, 1)],
            "076067a4731047dd992004d936d962567c1d7ceed864bb6e778db05bc8c59420",
        )
        with self.assertRaises(lf.AuditProtocolError):
            lf.authorized_feature_path(date(2026, 8, 1))


if __name__ == "__main__":
    unittest.main()
