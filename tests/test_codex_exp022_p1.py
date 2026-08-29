import csv
import hashlib
import inspect
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import numpy as np

import multimarket.codex_exp022_p1 as p1
from multimarket.codex_exp004_headroom import executable_fixed_horizon
from multimarket.codex_exp004_p1 import _r_features, _spread
from multimarket.v23_phase0dl_score import DayData


def _synthetic_day(
    rows: int,
    *,
    day: date = p1.PROSPECTIVE_DAY,
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
    return DayData(
        day=day,
        ts=p1.DAY_START_US + np.arange(rows, dtype=np.int64) * p1.GRID_US,
        bid=bid,
        ask=ask,
        mid=mid,
        book_valid=valid,
        valid={},
        X={},
    )


def _write_grid(
    path: Path,
    rows: int,
    *,
    header: tuple[str, ...] = p1.GRID_COLUMNS,
    flags: list[int] | None = None,
) -> None:
    row_flags = flags or [1] * rows
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for i in range(rows):
            valid = row_flags[i]
            bid = 100.0 + i * 0.01 if valid else float("nan")
            ask = bid + 0.1 if valid else float("nan")
            mid = (bid + ask) / 2.0 if valid else float("nan")
            writer.writerow(
                [
                    p1.DAY_START_US + i * p1.GRID_US,
                    bid,
                    ask,
                    mid,
                    valid,
                    0.0 if valid else float("nan"),
                    1 if valid else "",
                    i if valid else "",
                    "",
                    "",
                ]
            )


def _p0_audit(status: str = p1.P0_STATUS) -> dict:
    gates = {name: True for name in p1.P0_TRUE_GATES}
    gates.update({name: False for name in p1.P0_FALSE_GATES})
    return {
        "experiment_id": "CODEX-EXP-022-P0",
        "status": status,
        "symbol": p1.SYMBOL,
        "collection_day": p1.PROSPECTIVE_DAY.isoformat(),
        "raw_sha256": p1.PROSPECTIVE_RAW_SHA256,
        "grid_sha256": p1.PROSPECTIVE_GRID_SHA256,
        "grid_bytes": p1.PROSPECTIVE_GRID_BYTES,
        "integrity_gates": gates,
    }


class Exp022P1IdentityTests(unittest.TestCase):
    def test_frozen_identity_configuration_and_preregistration_hash(self):
        self.assertEqual(p1.EXPERIMENT_ID, "CODEX-EXP-022-P1")
        self.assertEqual(p1.SYMBOL, "BTCUSDT")
        self.assertEqual(
            p1.TRAIN_DAYS,
            tuple(date(2026, month, 1) for month in range(1, 8)),
        )
        self.assertEqual(p1.PROSPECTIVE_DAY, date(2026, 8, 28))
        self.assertEqual(p1.VOL_FEATURE, "rv_30m_bps")
        self.assertEqual(p1.DECISION_STEP_ROWS, 240)
        self.assertEqual(p1.HORIZON_S, 600)
        self.assertEqual(p1.LABEL_THRESHOLD_BPS, 24.0)
        self.assertEqual(p1.EXPECTED_GRID_ROWS, 345_600)
        self.assertEqual(p1.GRID_US, 250_000)
        self.assertEqual(
            p1.PREREGISTRATION_SHA256,
            "e4c9ca4075834de29d01613c695b534081a01b506e7f233ca6fa9542419e3f5b",
        )

    def test_fixed_model_parameters_are_exact(self):
        model = p1.FixedLogistic()
        params = model.model.get_params()
        self.assertEqual(params["C"], 1.0)
        self.assertEqual(params["penalty"], "l2")
        self.assertEqual(params["solver"], "lbfgs")
        self.assertIsNone(params["class_weight"])
        self.assertEqual(params["max_iter"], 1000)
        self.assertEqual(params["random_state"], 20260825)


class Exp022P1GridAndSemanticsTests(unittest.TestCase):
    def test_small_strict_grid_fixture_validates_frozen_schema_and_spacing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / p1.PROSPECTIVE_GRID_FILENAME
            _write_grid(path, 8, flags=[0, 1, 1, 1, 1, 1, 1, 1])
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            authorization = p1.authorize_prospective_grid(
                path,
                expected_bytes=path.stat().st_size,
                expected_sha256=digest,
            )
            day = p1.load_prospective_grid(
                path,
                authorization,
                expected_rows=8,
            )

        self.assertEqual(len(day.ts), 8)
        self.assertTrue(np.all(np.diff(day.ts) == 250_000))
        self.assertEqual(day.ts[0], p1.DAY_START_US)
        self.assertEqual(day.ts[-1], p1.DAY_START_US + 7 * 250_000)
        self.assertFalse(day.book_valid[0])
        self.assertTrue(np.all(day.book_valid[1:]))

    def test_grid_schema_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / p1.PROSPECTIVE_GRID_FILENAME
            wrong = tuple(reversed(p1.GRID_COLUMNS))
            _write_grid(path, 2, header=wrong)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            authorization = p1.authorize_prospective_grid(
                path,
                expected_bytes=path.stat().st_size,
                expected_sha256=digest,
            )
            with self.assertRaisesRegex(RuntimeError, "schema mismatch"):
                p1.load_prospective_grid(
                    path,
                    authorization,
                    expected_rows=2,
                )

    def test_grid_data_row_schema_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / p1.PROSPECTIVE_GRID_FILENAME
            _write_grid(path, 2)
            lines = path.read_text(encoding="utf-8").splitlines()
            lines[-1] = "1,2,3"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            authorization = p1.authorize_prospective_grid(
                path,
                expected_bytes=path.stat().st_size,
                expected_sha256=digest,
            )
            with self.assertRaisesRegex(RuntimeError, "data-row schema"):
                p1.load_prospective_grid(
                    path,
                    authorization,
                    expected_rows=2,
                )

    def test_raw_filename_is_rejected_before_any_opaque_open(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            raw = Path(temp_dir) / "2026-08-28.jsonl.gz"
            with mock.patch.object(p1, "_sha256_opaque") as sha:
                with self.assertRaisesRegex(RuntimeError, "filename"):
                    p1.authorize_prospective_grid(raw)
                sha.assert_not_called()

    def test_decisions_are_aligned_every_sixty_seconds(self):
        dataset = p1.build_prospective_dataset(_synthetic_day(10_000))
        self.assertTrue(
            np.all(np.diff(dataset.timestamp_us) == 60_000_000)
        )
        self.assertTrue(dataset.nonoverlap_10m[0])
        self.assertFalse(dataset.nonoverlap_10m[1])
        self.assertTrue(dataset.nonoverlap_10m[10])

    def test_rv_uses_exactly_31_samples_and_30_returns(self):
        day = _synthetic_day(10_000)
        dataset = p1.build_prospective_dataset(day)
        position = int(np.flatnonzero(dataset.decision_indices == 7200)[0])
        expected_return = 240.0e-6
        expected = 10_000.0 * np.sqrt(30.0 * expected_return**2)
        frozen = _r_features(day, 7200, _spread(day))

        self.assertTrue(dataset.feature_valid[position])
        self.assertAlmostEqual(dataset.rv_30m_bps[position], expected, places=10)
        self.assertEqual(
            dataset.rv_30m_bps[position],
            frozen[p1.VOL_INDEX],
        )

    def test_any_invalid_state_in_full_lookback_invalidates_feature(self):
        valid = np.ones(10_000, dtype=bool)
        valid[7001] = False
        day = _synthetic_day(10_000, book_valid=valid)
        dataset = p1.build_prospective_dataset(day)
        position = int(np.flatnonzero(dataset.decision_indices == 7200)[0])
        self.assertFalse(dataset.feature_valid[position])
        self.assertTrue(np.isnan(dataset.rv_30m_bps[position]))

    def test_future_mutation_cannot_change_current_feature(self):
        original = _synthetic_day(10_000)
        changed = _synthetic_day(10_000)
        changed.mid[7201:] *= 5.0
        changed.bid[7201:] = changed.mid[7201:] - 0.01
        changed.ask[7201:] = changed.mid[7201:] + 0.01
        a = p1.build_prospective_dataset(original)
        b = p1.build_prospective_dataset(changed)
        position = int(np.flatnonzero(a.decision_indices == 7200)[0])
        self.assertEqual(a.rv_30m_bps[position], b.rv_30m_bps[position])

    def test_target_reuses_exact_entry_exit_and_day_end_semantics(self):
        day = _synthetic_day(3_000)
        day.bid[1], day.ask[1], day.mid[1] = 99.9, 100.0, 99.95
        day.bid[2401], day.ask[2401], day.mid[2401] = 100.5, 100.6, 100.55
        dataset = p1.build_prospective_dataset(day)
        frozen = executable_fixed_horizon(
            day,
            dataset.decision_indices,
            p1.HORIZON_S,
        )

        self.assertEqual(frozen["entry_index"][0], 1)
        self.assertEqual(frozen["exit_index"][0], 2401)
        self.assertTrue(dataset.target_valid[0])
        self.assertEqual(dataset.label[0], 1)
        self.assertFalse(dataset.target_valid[-1])
        self.assertTrue(np.array_equal(dataset.target_valid, frozen["valid"]))

    def test_common_support_requires_feature_target_and_finite_score(self):
        dataset = p1.ProspectiveDataset(
            decision_indices=np.arange(4),
            timestamp_us=np.arange(4, dtype=np.int64) * 60_000_000,
            rv_30m_bps=np.asarray([1.0, 2.0, np.nan, 4.0]),
            label=np.asarray([0, 1, 1, 0], dtype=np.int8),
            feature_valid=np.asarray([True, True, False, True]),
            target_valid=np.asarray([True, True, True, False]),
            candidate_support=np.asarray([True, True, False, False]),
            nonoverlap_10m=np.asarray([True, False, False, False]),
        )
        rows = p1.finalize_common_support(dataset, np.asarray([0.2, np.nan]))
        self.assertEqual(rows.timestamp_us.tolist(), [0])
        self.assertEqual(rows.label.tolist(), [0])
        self.assertEqual(rows.probability.tolist(), [0.2])


class Exp022P1MetricAndStatusTests(unittest.TestCase):
    def test_top_decile_ties_use_ascending_timestamp(self):
        timestamps = np.arange(20, dtype=np.int64) * 60_000_000
        labels = np.asarray([1, 0, 1] + [0] * 16 + [1], dtype=np.int8)
        probabilities = np.asarray([0.9, 0.9, 0.9] + [0.1] * 17)
        metrics = p1.p1_metrics(timestamps, labels, probabilities)
        self.assertEqual(metrics["top_decile_precision"], 0.5)

    def test_metric_function_does_not_fit_any_calibrator(self):
        timestamps = np.arange(20, dtype=np.int64)
        labels = np.asarray([0, 1] * 10, dtype=np.int8)
        probabilities = np.linspace(0.05, 0.95, 20)
        with mock.patch(
            "sklearn.linear_model.LogisticRegression.fit",
            side_effect=AssertionError("calibration fit forbidden"),
        ) as fit:
            metrics = p1.p1_metrics(timestamps, labels, probabilities)
        fit.assert_not_called()
        self.assertNotIn("calibration", metrics)
        self.assertNotIn("intercept", metrics)
        self.assertNotIn("slope", metrics)

    def test_support_threshold_boundaries(self):
        passing = np.asarray([1] * 10 + [0] * 1190, dtype=np.int8)
        self.assertTrue(p1.support_is_sufficient(passing))
        self.assertFalse(p1.support_is_sufficient(passing[:-1]))
        self.assertFalse(
            p1.support_is_sufficient(
                np.asarray([1] * 9 + [0] * 1191, dtype=np.int8)
            )
        )
        self.assertFalse(
            p1.support_is_sufficient(
                np.asarray([1] * 1100 + [0] * 99, dtype=np.int8)
            )
        )

    def test_eligible_circular_shifts_are_exact(self):
        shifts = p1.eligible_circular_shifts(1200)
        self.assertEqual(shifts[0], 30)
        self.assertEqual(shifts[-1], 1170)
        self.assertEqual(len(shifts), 39)
        self.assertNotIn(0, shifts)

    def test_circular_shift_orientation_is_numpy_roll(self):
        labels = np.asarray(([1] + [0] * 69), dtype=np.int8)
        shifted = p1.circular_shift_labels(labels, 30)
        self.assertEqual(np.flatnonzero(shifted).tolist(), [30])
        self.assertTrue(np.array_equal(shifted, np.roll(labels, 30)))

    def test_q95_and_empirical_p_are_frozen_formulas(self):
        values = np.arange(1.0, 21.0)
        self.assertEqual(
            p1.higher_q95(values),
            float(np.quantile(values, 0.95, method="higher")),
        )
        null = np.asarray([0.1, 0.5, 0.7, 0.9])
        self.assertEqual(p1.empirical_one_sided_p(null, 0.7), 3 / 5)

    def test_pass_fail_inconclusive_and_invalid_statuses(self):
        metrics = {
            "roc_auc": 0.70,
            "average_precision": 0.30,
            "average_precision_over_prevalence": 2.0,
            "top_decile_lift": 2.0,
        }
        null = {
            "auc_null_q95": 0.60,
            "ap_null_q95": 0.20,
            "auc_empirical_p": 0.04,
            "ap_empirical_p": 0.04,
        }
        gates = p1.primary_gates(metrics, null, True)
        self.assertEqual(
            p1.adjudicate_status(
                support_sufficient=True,
                null_support_sufficient=True,
                gates=gates,
                invariants_pass=True,
            ),
            p1.PASS_STATUS,
        )

        failed = dict(gates)
        failed["prospective_auc_at_least_0_60"] = False
        self.assertEqual(
            p1.adjudicate_status(
                support_sufficient=True,
                null_support_sufficient=True,
                gates=failed,
                invariants_pass=True,
            ),
            p1.FAIL_STATUS,
        )
        self.assertEqual(
            p1.adjudicate_status(
                support_sufficient=False,
                null_support_sufficient=True,
                gates=failed,
                invariants_pass=True,
            ),
            p1.INCONCLUSIVE_STATUS,
        )
        self.assertEqual(
            p1.adjudicate_status(
                support_sufficient=True,
                null_support_sufficient=True,
                gates=gates,
                invariants_pass=False,
            ),
            p1.INVALID_STATUS,
        )

    def test_nonoverlap_diagnostic_is_non_gating_and_null_without_two_classes(self):
        rows = p1.SupportedRows(
            timestamp_us=np.arange(20, dtype=np.int64) * 60_000_000,
            label=np.asarray([0, 1] + [0] * 18, dtype=np.int8),
            probability=np.linspace(0.1, 0.9, 20),
            nonoverlap_10m=np.asarray(
                [True] + [False] * 9 + [True] + [False] * 9
            ),
        )
        diagnostic = p1.nonoverlap_diagnostic(rows)
        self.assertEqual(diagnostic["n"], 2)
        self.assertEqual(diagnostic["positives"], 0)
        self.assertIsNone(diagnostic["roc_auc"])


class Exp022P1SafetyTests(unittest.TestCase):
    def test_synthetic_p0_audit_provenance_pass_and_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "audit.json"
            payload = _p0_audit()
            path.write_text(json.dumps(payload), encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            verified = p1.verify_p0_audit(path, expected_sha256=digest)
            self.assertEqual(verified["status"], p1.P0_STATUS)

            payload["status"] = "FAIL"
            path.write_text(json.dumps(payload), encoding="utf-8")
            bad_digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(RuntimeError, "status"):
                p1.verify_p0_audit(path, expected_sha256=bad_digest)

    def test_existing_output_and_part_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "result.json"
            output.write_text("immutable", encoding="utf-8")
            with mock.patch.object(p1, "_execute_once") as execute:
                with self.assertRaises(FileExistsError):
                    p1.run_execute(
                        feature_dir=root,
                        grid=root / "grid.csv",
                        output=output,
                        workspace=root,
                        frozen_commit="0" * 40,
                        p0_audit=root / "audit.json",
                    )
                execute.assert_not_called()
            self.assertEqual(output.read_text(encoding="utf-8"), "immutable")

            output.unlink()
            part = output.with_name(output.name + ".part")
            part.write_text("interrupted", encoding="utf-8")
            with mock.patch.object(p1, "_execute_once") as execute:
                with self.assertRaises(FileExistsError):
                    p1.run_execute(
                        feature_dir=root,
                        grid=root / "grid.csv",
                        output=output,
                        workspace=root,
                        frozen_commit="0" * 40,
                        p0_audit=root / "audit.json",
                    )
                execute.assert_not_called()
            self.assertEqual(part.read_text(encoding="utf-8"), "interrupted")

    def test_execution_error_creates_one_atomic_invalid_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "result.json"
            with mock.patch.object(
                p1,
                "_execute_once",
                side_effect=RuntimeError("synthetic provenance failure"),
            ):
                result = p1.run_execute(
                    feature_dir=root,
                    grid=root / "grid.csv",
                    output=output,
                    workspace=root,
                    frozen_commit="0" * 40,
                    p0_audit=root / "audit.json",
                )
            self.assertEqual(result["status"], p1.INVALID_STATUS)
            self.assertTrue(output.is_file())
            self.assertFalse(output.with_name(output.name + ".part").exists())
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8"))["status"],
                p1.INVALID_STATUS,
            )

    def test_artifact_schema_excludes_forbidden_outputs_and_has_guards(self):
        state = p1.ExecutionState()
        payload = p1.invalid_payload(RuntimeError("synthetic"), "0" * 40, state)
        self.assertNotIn("long_gross_bps", json.dumps(payload))
        self.assertNotIn("short_gross_bps", json.dumps(payload))
        for name in (
            "direction_scored",
            "pnl_scored",
            "leverage_scored",
            "older_august_holdout_opened",
            "historical_aug1_feature_reparsed",
            "network_accessed",
            "prospective_raw_opened",
        ):
            self.assertIs(payload[name], False)

        source = inspect.getsource(p1._execute_once)
        self.assertNotIn('"long_gross_bps"', source)
        self.assertNotIn('"short_gross_bps"', source)
        self.assertNotIn("winning_direction", source)

    def test_preflight_does_not_fit_model_or_accept_grid(self):
        fake_history = (
            [],
            [],
            np.ones((2, 1)),
            np.asarray([0, 1], dtype=np.int8),
            [],
        )
        with mock.patch.object(p1, "verify_preregistration", return_value="x"), mock.patch.object(
            p1,
            "verify_p0_audit",
            return_value={},
        ), mock.patch.object(
            p1,
            "_prepare_historical",
            return_value=fake_history,
        ), mock.patch(
            "sklearn.linear_model.LogisticRegression.fit",
            side_effect=AssertionError("preflight fit forbidden"),
        ) as fit:
            result = p1.run_preflight(
                feature_dir=Path("synthetic"),
                workspace=Path("synthetic"),
                p0_audit=Path("synthetic-audit"),
            )
        fit.assert_not_called()
        self.assertFalse(result["model_fit"])
        self.assertFalse(result["prospective_grid_analytically_opened"])

        with self.assertRaises(SystemExit):
            p1.main(
                [
                    "--mode",
                    "preflight",
                    "--workspace",
                    "synthetic",
                    "--feature-dir",
                    "synthetic",
                    "--grid",
                    "forbidden.csv",
                ]
            )

    def test_module_has_no_raw_or_network_interface(self):
        main_source = inspect.getsource(p1.main)
        module_source = inspect.getsource(p1)
        self.assertNotIn("--raw", main_source)
        self.assertNotIn("urlopen", module_source)
        self.assertNotIn("requests", module_source)
        self.assertNotIn("websocket", module_source.lower())
        self.assertNotIn("railway", module_source.lower())


if __name__ == "__main__":
    unittest.main()
