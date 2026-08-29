import inspect
import json
import math
import tempfile
import unittest
from dataclasses import asdict
from datetime import date
from pathlib import Path
from unittest import mock

import numpy as np

import multimarket.codex_exp022_p1 as frozen_p1
import multimarket.codex_exp023_p0 as p0
from multimarket.codex_exp004_headroom import executable_fixed_horizon
from multimarket.codex_exp004_p1 import _r_features, _spread
from multimarket.codex_research import canonical_sha256
from multimarket.v23_phase0dl_score import DayData


def _synthetic_historical_day(
    rows: int,
    *,
    day: date = date(2026, 1, 1),
    book_valid: np.ndarray | None = None,
) -> DayData:
    index = np.arange(rows, dtype=np.float64)
    mid = 100.0 * np.exp(index * 1e-6)
    bid = mid - 0.01
    ask = mid + 0.01
    valid = (
        np.ones(rows, dtype=bool)
        if book_valid is None
        else np.asarray(book_valid, dtype=bool)
    )
    start_us = 1_767_225_600_000_000
    return DayData(
        day=day,
        ts=start_us + np.arange(rows, dtype=np.int64) * p0.GRID_US,
        bid=bid,
        ask=ask,
        mid=mid,
        book_valid=valid,
        valid={},
        X={},
    )


def _fake_historical_preflight(*, exact: bool = True) -> dict:
    validation = [
        {
            "day": day.isoformat(),
            "decision_rows": 100,
            "common_support_n": 50,
            "rv_exact_match": exact,
            "target_and_support_exact_match": exact,
        }
        for day in p0.TRAIN_DAYS
    ]
    counts = [
        {
            "day": day.isoformat(),
            "n": 50,
            "positives": 10,
            "negatives": 40,
        }
        for day in p0.TRAIN_DAYS
    ]
    return {
        "historical_input_manifest": [],
        "historical_semantic_validation": validation,
        "historical_training_counts": counts,
        "historical_training_n": 350,
        "historical_feature_columns": 1,
    }


def _fake_references() -> dict[str, str]:
    return {
        f"synthetic-reference-{index}": "0" * 64
        for index in range(len(p0.FROZEN_REFERENCE_SHA256) + 1)
    }


class Exp023P0InvariantCorrectionTests(unittest.TestCase):
    def test_regression_reproduces_frozen_numpy_bool_bug_and_correction(self):
        frozen_value = np.all(np.asarray([True, True], dtype=bool))
        self.assertIs(type(frozen_value), np.bool_)
        self.assertIsNot(frozen_value, True)
        with self.assertRaises(TypeError):
            json.dumps({"invariant": frozen_value}, allow_nan=False)

        checks = p0.frozen_bug_regression()
        self.assertTrue(all(checks.values()))
        self.assertTrue(all(type(value) is bool for value in checks.values()))

    def test_corrected_common_support_invariant_is_always_builtin_bool(self):
        cases = (
            (np.asarray([], dtype=np.int64), True),
            (np.asarray([10], dtype=np.int64), True),
            (np.asarray([10, 20], dtype=np.int64), True),
            (np.asarray([10, 10], dtype=np.int64), False),
            (np.asarray([20, 10], dtype=np.int64), False),
        )
        for timestamps, expected in cases:
            with self.subTest(timestamps=timestamps.tolist()):
                value = p0.common_support_unique_and_chronological(timestamps)
                self.assertIs(type(value), bool)
                self.assertEqual(value, expected)

    def test_invariant_validation_rejects_every_non_builtin_bool(self):
        for value in (np.bool_(True), np.int64(1), 1, 1.0, "true", None):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(p0.InvariantTypeError):
                    p0.validate_builtin_bool_invariants({"gate": value})

    def test_type_safe_adjudication_supports_true_and_false_expectations(self):
        invariants = {"positive_gate": True, "guard": False}
        expected = {"positive_gate": True, "guard": False}
        self.assertTrue(
            p0.adjudicate_invariants(invariants, expected=expected)
        )
        self.assertFalse(
            p0.adjudicate_invariants(
                invariants,
                expected={"positive_gate": True, "guard": True},
            )
        )
        with self.assertRaises(p0.InvariantTypeError):
            p0.adjudicate_invariants(
                {"gate": np.bool_(True)},
                expected={"gate": True},
            )

    def test_every_preflight_invariant_value_is_exact_builtin_bool(self):
        with mock.patch.object(
            p0, "assert_frozen_workspace"
        ), mock.patch.object(
            p0,
            "verify_frozen_references",
            return_value=_fake_references(),
        ), mock.patch.object(
            p0,
            "_is_ancestor",
            return_value=True,
        ), mock.patch.object(
            p0,
            "_historical_preflight",
            return_value=_fake_historical_preflight(),
        ):
            payload = p0._preflight_once(
                feature_dir=Path("synthetic"),
                workspace=Path("synthetic"),
                frozen_commit="0" * 40,
            )
        self.assertEqual(payload["status"], p0.PASS_STATUS)
        self.assertTrue(
            all(type(value) is bool for value in payload["invariants"].values())
        )


class Exp023P0JsonSafetyTests(unittest.TestCase):
    def test_recursive_json_safety_normalizes_numpy_scalars(self):
        payload = {
            "boolean": np.bool_(True),
            "integer": np.int64(7),
            "floating": np.float32(1.25),
            "nested": [np.int8(1), (np.float64(2.5), np.bool_(False))],
        }
        normalized = p0.normalize_json_safe(payload)
        self.assertIs(type(normalized["boolean"]), bool)
        self.assertIs(type(normalized["integer"]), int)
        self.assertIs(type(normalized["floating"]), float)
        self.assertIsInstance(normalized["nested"], list)
        json.dumps(normalized, allow_nan=False)

    def test_nonfinite_builtin_and_numpy_floats_are_rejected(self):
        values = (
            float("nan"),
            float("inf"),
            float("-inf"),
            np.float32("nan"),
            np.float64("inf"),
        )
        for value in values:
            with self.subTest(value=repr(value)):
                with self.assertRaises(p0.JsonSafetyError):
                    p0.normalize_json_safe({"bad": value})

    def test_unsupported_numpy_array_and_nonstring_key_are_rejected(self):
        with self.assertRaises(p0.JsonSafetyError):
            p0.normalize_json_safe({"array": np.asarray([1, 2])})
        with self.assertRaises(p0.JsonSafetyError):
            p0.normalize_json_safe({1: "value"})

    def test_residual_numpy_bool_in_invariants_is_rejected_before_writing(self):
        payload = {"invariants": {"gate": np.bool_(True)}}
        with self.assertRaises(p0.InvariantTypeError):
            p0.normalize_result_payload(payload)

    def test_pass_fail_inconclusive_and_invalid_payloads_serialize(self):
        statuses = (
            frozen_p1.PASS_STATUS,
            frozen_p1.FAIL_STATUS,
            frozen_p1.INCONCLUSIVE_STATUS,
            frozen_p1.INVALID_STATUS,
        )
        for status in statuses:
            with self.subTest(status=status):
                payload = p0.synthetic_result_payload(status)
                normalized = p0.normalize_result_payload(payload)
                json.dumps(normalized, allow_nan=False)
                encoded = p0.encode_result_payload(payload)
                decoded = json.loads(encoded)
                self.assertEqual(decoded["status"], status)
                json.dumps(decoded, allow_nan=False)
        self.assertTrue(p0.synthetic_status_payloads_serialize())

    def test_result_shapes_contain_no_forbidden_scientific_outputs(self):
        forbidden = {
            "long_gross_bps",
            "short_gross_bps",
            "winning_direction",
            "directional_label",
            "directional_score",
            "pnl",
            "leverage",
        }
        payload = p0.normalize_result_payload(
            p0.synthetic_result_payload(frozen_p1.PASS_STATUS)
        )

        def keys(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    yield key
                    yield from keys(item)
            elif isinstance(value, list):
                for item in value:
                    yield from keys(item)

        self.assertTrue(forbidden.isdisjoint(set(keys(payload))))


class Exp023P0FrozenSemanticsTests(unittest.TestCase):
    def test_scientific_configuration_is_exactly_frozen_exp022_p1(self):
        expected = asdict(frozen_p1.Config())
        actual = p0.scientific_configuration()
        self.assertEqual(actual, expected)
        self.assertEqual(actual, p0.FROZEN_SCIENTIFIC_CONFIGURATION)
        self.assertEqual(
            canonical_sha256(actual),
            p0.FROZEN_SCIENTIFIC_CONFIGURATION_SHA256,
        )
        self.assertEqual(
            p0.FROZEN_SCIENTIFIC_CONFIGURATION_SHA256,
            "5592bd41fa4cfc48dd418f0f1920762d8d760ab6bb39ce2000e0114d9603f348",
        )

    def test_fixed_model_parameters_are_unchanged(self):
        params = p0.FixedLogistic().model.get_params()
        expected = {
            "C": 1.0,
            "penalty": "l2",
            "solver": "lbfgs",
            "class_weight": None,
            "max_iter": 1000,
            "random_state": 20260825,
        }
        self.assertEqual({key: params[key] for key in expected}, expected)

    def test_feature_semantics_are_exactly_frozen_31_samples_30_returns(self):
        day = _synthetic_historical_day(10_000)
        corrected = p0.build_historical_adapter_dataset(day)
        frozen = frozen_p1.build_prospective_dataset(day, required_day=None)
        position = int(np.flatnonzero(corrected.decision_indices == 7200)[0])
        expected_return = 240.0e-6
        expected_rv = 10_000.0 * math.sqrt(30.0 * expected_return**2)
        helper = _r_features(day, 7200, _spread(day))

        self.assertTrue(corrected.feature_valid[position])
        self.assertAlmostEqual(
            corrected.rv_30m_bps[position], expected_rv, places=10
        )
        self.assertEqual(corrected.rv_30m_bps[position], helper[p0.VOL_INDEX])
        self.assertTrue(
            np.array_equal(corrected.feature_valid, frozen.feature_valid)
        )
        self.assertTrue(
            np.array_equal(corrected.rv_30m_bps, frozen.rv_30m_bps, equal_nan=True)
        )

    def test_invalid_state_anywhere_in_30m_window_remains_invalid(self):
        valid = np.ones(10_000, dtype=bool)
        valid[7001] = False
        day = _synthetic_historical_day(10_000, book_valid=valid)
        dataset = p0.build_historical_adapter_dataset(day)
        position = int(np.flatnonzero(dataset.decision_indices == 7200)[0])
        self.assertFalse(dataset.feature_valid[position])
        self.assertTrue(np.isnan(dataset.rv_30m_bps[position]))

    def test_target_semantics_preserve_exact_entry_exit_and_day_end(self):
        day = _synthetic_historical_day(3_000)
        day.bid[1], day.ask[1], day.mid[1] = 99.9, 100.0, 99.95
        day.bid[2401], day.ask[2401], day.mid[2401] = 100.5, 100.6, 100.55
        corrected = p0.build_historical_adapter_dataset(day)
        frozen = executable_fixed_horizon(
            day,
            corrected.decision_indices,
            p0.HORIZON_S,
        )
        self.assertEqual(frozen["entry_index"][0], 1)
        self.assertEqual(frozen["exit_index"][0], 2401)
        self.assertTrue(corrected.target_valid[0])
        self.assertEqual(corrected.label[0], 1)
        self.assertFalse(corrected.target_valid[-1])
        self.assertTrue(np.array_equal(corrected.target_valid, frozen["valid"]))

    def test_future_mutation_does_not_change_current_feature(self):
        original = _synthetic_historical_day(10_000)
        changed = _synthetic_historical_day(10_000)
        changed.mid[7201:] *= 5.0
        changed.bid[7201:] = changed.mid[7201:] - 0.01
        changed.ask[7201:] = changed.mid[7201:] + 0.01
        first = p0.build_historical_adapter_dataset(original)
        second = p0.build_historical_adapter_dataset(changed)
        position = int(np.flatnonzero(first.decision_indices == 7200)[0])
        self.assertEqual(
            first.rv_30m_bps[position], second.rv_30m_bps[position]
        )

    def test_temporal_null_semantics_are_unchanged(self):
        labels = np.asarray(([1] + [0] * 39) * 30, dtype=np.int8)
        probabilities = np.linspace(0.01, 0.99, len(labels))
        self.assertEqual(p0.eligible_circular_shifts(1200)[0], 30)
        self.assertEqual(p0.eligible_circular_shifts(1200)[-1], 1170)
        shifted = p0.circular_shift_labels(labels, 30)
        self.assertTrue(np.array_equal(shifted, np.roll(labels, 30)))
        values = np.arange(1.0, 21.0)
        self.assertEqual(
            p0.higher_q95(values),
            float(np.quantile(values, 0.95, method="higher")),
        )
        null = np.asarray([0.1, 0.5, 0.7, 0.9])
        self.assertEqual(p0.empirical_one_sided_p(null, 0.7), 3 / 5)
        self.assertEqual(
            p0.temporal_shift_null(labels, probabilities),
            frozen_p1.temporal_shift_null(labels, probabilities),
        )

    def test_adapter_rejects_every_august_day_before_frozen_helper_call(self):
        august = _synthetic_historical_day(10, day=date(2026, 8, 28))
        with mock.patch.object(
            frozen_p1,
            "build_prospective_dataset",
            side_effect=AssertionError("must not inspect August"),
        ) as build:
            with self.assertRaisesRegex(ValueError, "Jan-Jul"):
                p0.build_historical_adapter_dataset(august)
        build.assert_not_called()


class Exp023P0ArchitectureAndOutputTests(unittest.TestCase):
    def test_preflight_pass_and_scientific_mismatch_fail_are_nonpredictive(self):
        common_patches = (
            mock.patch.object(p0, "assert_frozen_workspace"),
            mock.patch.object(
                p0,
                "verify_frozen_references",
                return_value=_fake_references(),
            ),
            mock.patch.object(p0, "_is_ancestor", return_value=True),
        )
        for patcher in common_patches:
            patcher.start()
            self.addCleanup(patcher.stop)

        with mock.patch.object(
            p0,
            "_historical_preflight",
            return_value=_fake_historical_preflight(exact=True),
        ):
            passed = p0._preflight_once(
                feature_dir=Path("synthetic"),
                workspace=Path("synthetic"),
                frozen_commit="0" * 40,
            )
        self.assertEqual(passed["status"], p0.PASS_STATUS)
        self.assertFalse(passed["predictive_claim_permitted"])
        self.assertFalse(passed["predictive_metrics_produced"])

        with mock.patch.object(
            p0,
            "_historical_preflight",
            return_value=_fake_historical_preflight(exact=False),
        ):
            failed = p0._preflight_once(
                feature_dir=Path("synthetic"),
                workspace=Path("synthetic"),
                frozen_commit="0" * 40,
            )
        self.assertEqual(failed["status"], p0.FAIL_STATUS)
        self.assertFalse(failed["predictive_claim_permitted"])

    def test_preflight_does_not_fit_model_or_calculate_metrics(self):
        with mock.patch.object(
            p0, "assert_frozen_workspace"
        ), mock.patch.object(
            p0,
            "verify_frozen_references",
            return_value=_fake_references(),
        ), mock.patch.object(
            p0,
            "_is_ancestor",
            return_value=True,
        ), mock.patch.object(
            p0,
            "_historical_preflight",
            return_value=_fake_historical_preflight(),
        ), mock.patch(
            "sklearn.linear_model.LogisticRegression.fit",
            side_effect=AssertionError("model fit forbidden"),
        ) as fit:
            result = p0._preflight_once(
                feature_dir=Path("synthetic"),
                workspace=Path("synthetic"),
                frozen_commit="0" * 40,
            )
        fit.assert_not_called()
        self.assertFalse(result["model_fit"])
        self.assertNotIn("primary_metrics", result)
        self.assertNotIn("secondary_calibration_diagnostics", result)

    def test_only_preflight_mode_exists_and_no_august_input_is_accepted(self):
        main_source = inspect.getsource(p0.main)
        preflight_source = inspect.getsource(p0._preflight_once)
        module_source = inspect.getsource(p0)
        self.assertNotIn('"execute"', main_source)
        self.assertNotIn("--grid", main_source)
        self.assertNotIn("--raw", main_source)
        self.assertNotIn("authorize_prospective_grid", preflight_source)
        self.assertNotIn("load_prospective_grid", preflight_source)
        self.assertNotIn("requests", module_source)
        self.assertNotIn("urlopen", module_source)
        self.assertNotIn("websocket", module_source.lower())
        self.assertNotIn("railway", module_source.lower())

        with mock.patch.object(p0, "run_preflight") as run:
            with self.assertRaises(SystemExit):
                p0.main(
                    [
                        "--mode",
                        "preflight",
                        "--workspace",
                        "synthetic",
                        "--feature-dir",
                        "synthetic",
                        "--output",
                        "synthetic.json",
                        "--frozen-commit",
                        "0" * 40,
                        "--grid",
                        "forbidden.csv",
                    ]
                )
        run.assert_not_called()

    def test_execution_guards_are_exact_builtin_false_values(self):
        guards = p0.execution_guards()
        self.assertEqual(
            set(guards),
            {
                "direction_scored",
                "pnl_scored",
                "leverage_scored",
                "older_august_holdout_opened",
                "historical_aug1_feature_reparsed",
                "network_accessed",
                "prospective_raw_opened",
            },
        )
        self.assertTrue(
            all(type(value) is bool and not value for value in guards.values())
        )

    def test_existing_final_output_and_part_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "result.json"
            output.write_text("immutable", encoding="utf-8")
            with mock.patch.object(p0, "_preflight_once") as preflight:
                with self.assertRaises(FileExistsError):
                    p0.run_preflight(
                        feature_dir=root,
                        output=output,
                        workspace=root,
                        frozen_commit="0" * 40,
                    )
            preflight.assert_not_called()
            self.assertEqual(output.read_text(encoding="utf-8"), "immutable")

            output.unlink()
            part = output.with_name(output.name + ".part")
            part.write_text("interrupted", encoding="utf-8")
            with mock.patch.object(p0, "_preflight_once") as preflight:
                with self.assertRaises(FileExistsError):
                    p0.run_preflight(
                        feature_dir=root,
                        output=output,
                        workspace=root,
                        frozen_commit="0" * 40,
                    )
            preflight.assert_not_called()
            self.assertEqual(part.read_text(encoding="utf-8"), "interrupted")

    def test_first_write_is_atomic_and_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "result.json"
            payload = {
                "experiment_id": p0.EXPERIMENT_ID,
                "status": p0.PASS_STATUS,
                "invariants": {"synthetic": True},
                **p0.execution_guards(),
            }
            p0._write_once(output, payload)
            self.assertTrue(output.is_file())
            self.assertFalse(output.with_name(output.name + ".part").exists())
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8"))["status"],
                p0.PASS_STATUS,
            )
            with self.assertRaises(FileExistsError):
                p0._write_once(output, payload)

    def test_preflight_error_creates_one_json_safe_invalid_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "result.json"
            with mock.patch.object(
                p0,
                "_preflight_once",
                side_effect=RuntimeError("synthetic provenance failure"),
            ):
                result = p0.run_preflight(
                    feature_dir=Path(temp_dir),
                    output=output,
                    workspace=Path(temp_dir),
                    frozen_commit="0" * 40,
                )
            self.assertEqual(result["status"], p0.INVALID_STATUS)
            self.assertTrue(output.is_file())
            self.assertFalse(output.with_name(output.name + ".part").exists())
            decoded = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(decoded["status"], p0.INVALID_STATUS)
            self.assertTrue(
                all(type(value) is bool for value in decoded["invariants"].values())
            )

    def test_json_failure_cannot_create_or_reuse_part_marker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "result.json"
            with self.assertRaises(p0.InvariantTypeError):
                p0._write_once(
                    output,
                    {"invariants": {"bad": np.bool_(True)}},
                )
            self.assertFalse(output.exists())
            self.assertFalse(output.with_name(output.name + ".part").exists())


if __name__ == "__main__":
    unittest.main()
