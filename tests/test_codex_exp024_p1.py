import csv
import hashlib
import inspect
import json
import tempfile
import unittest
from dataclasses import asdict
from datetime import date
from pathlib import Path
from unittest import mock

import numpy as np

import multimarket.codex_exp022_p1 as frozen_p1
import multimarket.codex_exp024_p1 as p1
from multimarket.codex_exp004_headroom import executable_fixed_horizon
from multimarket.codex_exp004_p1 import _r_features, _spread
from multimarket.codex_research import canonical_sha256
from multimarket.v23_phase0dl_score import DayData


def _synthetic_day(
    rows: int,
    *,
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
        day=p1.PROSPECTIVE_DAY,
        ts=p1.DAY_START_US + np.arange(rows, dtype=np.int64) * p1.GRID_US,
        bid=bid,
        ask=ask,
        mid=mid,
        book_valid=valid,
        valid={},
        X={},
    )


def _grid_path(root: Path) -> Path:
    path = root.joinpath(*p1.EXPECTED_GRID_PATH_SUFFIX)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _write_grid(
    path: Path,
    rows: int,
    *,
    header: tuple[str, ...] = p1.GRID_COLUMNS,
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for index in range(rows):
            bid = 100.0 + index * 0.01
            ask = bid + 0.10
            writer.writerow(
                [
                    p1.DAY_START_US + index * p1.GRID_US,
                    bid,
                    ask,
                    (bid + ask) / 2.0,
                    1,
                    0.0,
                    1,
                    index,
                    "",
                    "",
                ]
            )


def _write_authorized_pair(root: Path) -> tuple[Path, Path]:
    grid = _grid_path(root)
    grid.write_bytes(b"synthetic prospective grid fixture")
    digest = hashlib.sha256(grid.read_bytes()).hexdigest()
    audit = root / "EXP024_P0_AUDIT.json"
    audit.write_text(
        json.dumps(
            p1.synthetic_p0_audit_payload(
                grid_sha256=digest,
                grid_bytes=grid.stat().st_size,
            ),
            sort_keys=True,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    return audit, grid


class Exp024P1IdentityTests(unittest.TestCase):
    def test_identity_lineage_and_scientific_configuration_hash(self):
        self.assertEqual(p1.EXPERIMENT_ID, "CODEX-EXP-024-P1")
        self.assertEqual(p1.PROSPECTIVE_DAY, date(2026, 8, 30))
        self.assertEqual(p1.SYMBOL, "BTCUSDT")
        self.assertEqual(
            p1.TRAIN_DAYS,
            tuple(date(2026, month, 1) for month in range(1, 8)),
        )
        configuration = p1.scientific_configuration()
        self.assertEqual(
            canonical_sha256(configuration),
            p1.SCIENTIFIC_CONFIGURATION_SHA256,
        )
        self.assertEqual(
            p1.SCIENTIFIC_CONFIGURATION_SHA256,
            "3a9edfa6d2c9d15591373237574eb9552f09755eff2f0265e434621508e83b88",
        )

    def test_only_identity_and_day_differ_from_frozen_exp022_configuration(self):
        current = asdict(p1.Config())
        parent = asdict(frozen_p1.Config())
        differences = {
            name for name in current if current[name] != parent[name]
        }
        self.assertEqual(differences, {"experiment_id", "prospective_day"})

    def test_fixed_model_parameters_are_exact(self):
        wrapper = p1.FixedLogistic()
        params = wrapper.model.get_params()
        self.assertEqual(params["C"], 1.0)
        self.assertEqual(params["penalty"], "l2")
        self.assertEqual(params["solver"], "lbfgs")
        self.assertIsNone(params["class_weight"])
        self.assertEqual(params["max_iter"], 1000)
        self.assertEqual(params["random_state"], 20260825)

    def test_preregistration_hash_is_frozen_in_code(self):
        workspace = Path(__file__).resolve().parents[1]
        self.assertEqual(
            hashlib.sha256(
                (workspace / p1.PREREGISTRATION_REL).read_bytes()
            ).hexdigest(),
            p1.PREREGISTRATION_SHA256,
        )


class Exp024P1ScientificSemanticsTests(unittest.TestCase):
    def test_sixty_second_decisions_and_nonoverlap_alignment(self):
        dataset = p1.build_prospective_dataset(_synthetic_day(10_000))
        self.assertTrue(np.all(np.diff(dataset.timestamp_us) == 60_000_000))
        self.assertTrue(dataset.nonoverlap_10m[0])
        self.assertFalse(dataset.nonoverlap_10m[1])
        self.assertTrue(dataset.nonoverlap_10m[10])

    def test_rv_is_exact_frozen_31_sample_30_return_feature(self):
        day = _synthetic_day(10_000)
        current = p1.build_prospective_dataset(day)
        frozen = frozen_p1.build_prospective_dataset(day, required_day=None)
        position = int(np.flatnonzero(current.decision_indices == 7200)[0])
        one_minute_return = 240.0e-6
        expected = 10_000.0 * np.sqrt(30.0 * one_minute_return**2)
        helper = _r_features(day, 7200, _spread(day))
        self.assertTrue(current.feature_valid[position])
        self.assertAlmostEqual(current.rv_30m_bps[position], expected, places=10)
        self.assertEqual(current.rv_30m_bps[position], helper[p1.VOL_INDEX])
        self.assertTrue(
            np.array_equal(current.feature_valid, frozen.feature_valid)
        )
        self.assertTrue(
            np.allclose(
                current.rv_30m_bps,
                frozen.rv_30m_bps,
                equal_nan=True,
            )
        )

    def test_any_invalid_state_in_full_lookback_invalidates_feature(self):
        valid = np.ones(10_000, dtype=bool)
        valid[7001] = False
        dataset = p1.build_prospective_dataset(
            _synthetic_day(10_000, book_valid=valid)
        )
        position = int(np.flatnonzero(dataset.decision_indices == 7200)[0])
        self.assertFalse(dataset.feature_valid[position])
        self.assertTrue(np.isnan(dataset.rv_30m_bps[position]))

    def test_future_mutation_cannot_change_current_feature(self):
        original = _synthetic_day(10_000)
        changed = _synthetic_day(10_000)
        changed.mid[7201:] *= 4.0
        changed.bid[7201:] = changed.mid[7201:] - 0.01
        changed.ask[7201:] = changed.mid[7201:] + 0.01
        first = p1.build_prospective_dataset(original)
        second = p1.build_prospective_dataset(changed)
        position = int(np.flatnonzero(first.decision_indices == 7200)[0])
        self.assertEqual(
            first.rv_30m_bps[position], second.rv_30m_bps[position]
        )

    def test_target_preserves_exact_entry_exit_and_day_end_semantics(self):
        day = _synthetic_day(3_000)
        day.bid[1], day.ask[1], day.mid[1] = 99.9, 100.0, 99.95
        day.bid[2401], day.ask[2401], day.mid[2401] = 100.5, 100.6, 100.55
        dataset = p1.build_prospective_dataset(day)
        frozen = executable_fixed_horizon(
            day, dataset.decision_indices, p1.HORIZON_S
        )
        self.assertEqual(frozen["entry_index"][0], 1)
        self.assertEqual(frozen["exit_index"][0], 2401)
        self.assertTrue(dataset.target_valid[0])
        self.assertEqual(dataset.label[0], 1)
        self.assertFalse(dataset.target_valid[-1])
        self.assertTrue(np.array_equal(dataset.target_valid, frozen["valid"]))

    def test_common_support_and_corrected_invariant_are_exact(self):
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
        value = p1.common_support_unique_and_chronological(rows.timestamp_us)
        self.assertIs(type(value), bool)
        self.assertTrue(value)

    def test_metric_function_never_fits_a_calibrator(self):
        timestamps = np.arange(20, dtype=np.int64)
        labels = np.asarray([0, 1] * 10, dtype=np.int8)
        probabilities = np.linspace(0.05, 0.95, 20)
        with mock.patch(
            "sklearn.linear_model.LogisticRegression.fit",
            side_effect=AssertionError("calibration fitting forbidden"),
        ) as fit:
            metrics = p1.p1_metrics(timestamps, labels, probabilities)
        fit.assert_not_called()
        self.assertNotIn("calibration", json.dumps(metrics).lower())

    def test_top_decile_ties_use_ascending_timestamp(self):
        timestamps = np.arange(20, dtype=np.int64) * 60_000_000
        labels = np.asarray([1, 0, 1] + [0] * 16 + [1], dtype=np.int8)
        probabilities = np.asarray([0.9, 0.9, 0.9] + [0.1] * 17)
        metrics = p1.p1_metrics(timestamps, labels, probabilities)
        self.assertEqual(metrics["top_decile_precision"], 0.5)


class Exp024P1TemporalAndStatusTests(unittest.TestCase):
    def test_temporal_null_is_exactly_frozen(self):
        labels = np.asarray(([1] + [0] * 39) * 30, dtype=np.int8)
        probabilities = np.linspace(0.01, 0.99, len(labels))
        self.assertEqual(p1.eligible_circular_shifts(1200)[0], 30)
        self.assertEqual(p1.eligible_circular_shifts(1200)[-1], 1170)
        self.assertEqual(len(p1.eligible_circular_shifts(1200)), 39)
        self.assertTrue(
            np.array_equal(
                p1.circular_shift_labels(labels, 30), np.roll(labels, 30)
            )
        )
        self.assertEqual(
            p1.temporal_shift_null(labels, probabilities),
            frozen_p1.temporal_shift_null(labels, probabilities),
        )

    def test_higher_q95_and_empirical_p_formula(self):
        values = np.arange(1.0, 21.0)
        self.assertEqual(
            p1.higher_q95(values),
            float(np.quantile(values, 0.95, method="higher")),
        )
        null = np.asarray([0.1, 0.5, 0.7, 0.9])
        self.assertEqual(p1.empirical_one_sided_p(null, 0.7), 3 / 5)

    def test_pass_fail_inconclusive_and_invalid_status_logic(self):
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

    def test_support_boundary_is_unchanged(self):
        passing = np.asarray([1] * 10 + [0] * 1190, dtype=np.int8)
        self.assertTrue(p1.support_is_sufficient(passing))
        self.assertFalse(p1.support_is_sufficient(passing[:-1]))
        self.assertFalse(
            p1.support_is_sufficient(
                np.asarray([1] * 9 + [0] * 1191, dtype=np.int8)
            )
        )


class Exp024P1JsonSafetyTests(unittest.TestCase):
    def test_exp022_numpy_bool_bug_is_corrected(self):
        with self.assertRaises(TypeError):
            p1.validate_builtin_bool_invariants({"gate": np.bool_(True)})
        normalized = p1.normalize_result_payload(
            {"invariants": {"gate": True}, "diagnostic": np.bool_(True)}
        )
        self.assertIs(type(normalized["diagnostic"]), bool)
        json.dumps(normalized, allow_nan=False)

    def test_every_final_invariant_is_exact_builtin_bool(self):
        for status in (
            p1.PASS_STATUS,
            p1.FAIL_STATUS,
            p1.INCONCLUSIVE_STATUS,
            p1.INVALID_STATUS,
        ):
            normalized = p1.normalize_result_payload(
                p1.synthetic_result_payload(status)
            )
            self.assertTrue(
                all(type(value) is bool for value in normalized["invariants"].values())
            )

    def test_pass_fail_inconclusive_invalid_payloads_are_strict_json(self):
        for status in (
            p1.PASS_STATUS,
            p1.FAIL_STATUS,
            p1.INCONCLUSIVE_STATUS,
            p1.INVALID_STATUS,
        ):
            with self.subTest(status=status):
                payload = p1.normalize_result_payload(
                    p1.synthetic_result_payload(status)
                )
                encoded = json.dumps(payload, allow_nan=False, sort_keys=True)
                self.assertEqual(json.loads(encoded)["status"], status)
        self.assertTrue(p1.synthetic_status_payloads_serialize())

    def test_nonfinite_values_remain_forbidden(self):
        for value in (float("nan"), float("inf"), np.float64(-np.inf)):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    p1.normalize_result_payload(
                        {"invariants": {"gate": True}, "value": value}
                    )


class Exp024P1P0AuthorizationTests(unittest.TestCase):
    def test_synthetic_p0_audit_and_grid_authorization_pass(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audit, grid = _write_authorized_pair(Path(temp_dir))
            p0 = p1.verify_p0_audit(audit)
            authorization = p1.authorize_prospective_grid(grid, p0)
            self.assertEqual(authorization.sha256, p0.grid_sha256)
            self.assertEqual(authorization.byte_size, p0.grid_bytes)

    def test_every_frozen_p0_identity_field_is_required(self):
        cases = {
            "experiment_id": "wrong",
            "status": "FAIL",
            "scope": "wrong",
            "collection_day": "2026-08-31",
            "symbol": "ETHUSDT",
            "frozen_implementation_commit": "0" * 40,
            "preregistration_sha256": "0" * 64,
            "readiness_artifact_sha256": "0" * 64,
            "grid_path": "/tmp/not-exp024/grid.csv",
            "grid_sha256": "not-a-sha256",
            "grid_bytes": 0,
            "raw_sha256": "not-a-sha256",
            "raw_bytes": 0,
            "network_accessed_for_acquisition": False,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for field, wrong in cases.items():
                with self.subTest(field=field):
                    payload = p1.synthetic_p0_audit_payload(
                        grid_sha256="b" * 64,
                        grid_bytes=10,
                    )
                    payload[field] = wrong
                    audit = root / f"{field}.json"
                    audit.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaises(RuntimeError):
                        p1.verify_p0_audit(audit)

    def test_p0_predictive_and_every_no_analysis_guard_must_be_false(self):
        fields = ("predictive_metrics_calculated", *p1.P0_FALSE_GATES)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for field in fields:
                with self.subTest(field=field):
                    payload = p1.synthetic_p0_audit_payload(
                        grid_sha256="b" * 64,
                        grid_bytes=10,
                    )
                    payload[field] = True
                    audit = root / f"{field}.json"
                    audit.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaises(RuntimeError):
                        p1.verify_p0_audit(audit)

    def test_p0_acquisition_network_provenance_requires_exact_builtin_true(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audit = root / "audit.json"
            base = p1.synthetic_p0_audit_payload(
                grid_sha256="b" * 64,
                grid_bytes=10,
            )

            self.assertIs(base["network_accessed_for_acquisition"], True)
            audit.write_text(json.dumps(base), encoding="utf-8")
            p1.verify_p0_audit(audit)

            rejected = {
                "missing": None,
                "false": False,
                "string": "true",
                "integer": 1,
            }
            for case, value in rejected.items():
                with self.subTest(case=case):
                    payload = dict(base)
                    if case == "missing":
                        payload.pop("network_accessed_for_acquisition")
                    else:
                        payload["network_accessed_for_acquisition"] = value
                    audit.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaisesRegex(
                        RuntimeError, "acquisition network provenance"
                    ):
                        p1.verify_p0_audit(audit)

    def test_p0_integrity_gate_names_values_and_types_are_exact(self):
        mutations = (
            ("wrong true value", lambda gates: gates.__setitem__(p1.P0_TRUE_GATES[0], False)),
            ("wrong false value", lambda gates: gates.__setitem__(p1.P0_FALSE_GATES[0], True)),
            ("numpy bool type", lambda gates: gates.__setitem__(p1.P0_TRUE_GATES[0], np.bool_(True))),
            ("extra gate", lambda gates: gates.__setitem__("invented", True)),
            ("missing gate", lambda gates: gates.pop(p1.P0_TRUE_GATES[0])),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name, mutate in mutations:
                with self.subTest(name=name):
                    payload = p1.synthetic_p0_audit_payload(
                        grid_sha256="b" * 64,
                        grid_bytes=10,
                    )
                    mutate(payload["integrity_gates"])
                    audit = root / "audit.json"
                    if name == "numpy bool type":
                        audit.write_text("{}", encoding="utf-8")
                        with mock.patch.object(
                            Path, "read_bytes", return_value=json.dumps(
                                p1.synthetic_p0_audit_payload(
                                    grid_sha256="b" * 64, grid_bytes=10
                                )
                            ).encode(),
                        ):
                            # JSON cannot encode np.bool_; exercise the validator directly.
                            with self.assertRaises(TypeError):
                                p1.validate_builtin_bool_invariants(
                                    payload["integrity_gates"]
                                )
                    else:
                        audit.write_text(json.dumps(payload), encoding="utf-8")
                        with self.assertRaises(RuntimeError):
                            p1.verify_p0_audit(audit)

    def test_grid_path_size_and_sha_must_match_authorized_audit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            audit, grid = _write_authorized_pair(root)
            p0 = p1.verify_p0_audit(audit)

            altered = bytearray(grid.read_bytes())
            altered[0] ^= 1
            grid.write_bytes(altered)
            self.assertEqual(grid.stat().st_size, p0.grid_bytes)
            with self.assertRaisesRegex(RuntimeError, "SHA mismatch"):
                p1.authorize_prospective_grid(grid, p0)

            outside = root / p1.PROSPECTIVE_GRID_FILENAME
            outside.write_bytes(altered)
            with self.assertRaisesRegex(RuntimeError, "path"):
                p1.authorize_prospective_grid(outside, p0)

    def test_grid_is_not_touched_when_p0_audit_authorization_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "result.json"
            bad_audit = root / "bad-audit.json"
            payload = p1.synthetic_p0_audit_payload(
                grid_sha256="b" * 64,
                grid_bytes=10,
            )
            payload["status"] = "FAIL"
            bad_audit.write_text(json.dumps(payload), encoding="utf-8")
            state = p1.ExecutionState()
            with mock.patch.object(p1, "assert_frozen_workspace"), mock.patch.object(
                p1, "verify_preregistration", return_value=p1.PREREGISTRATION_SHA256
            ), mock.patch.object(
                p1, "authorize_prospective_grid"
            ) as authorize, mock.patch.object(
                p1, "_prepare_historical"
            ) as historical:
                with self.assertRaises(RuntimeError):
                    p1._execute_once(
                        feature_dir=root,
                        grid=root / "must-not-open.csv",
                        workspace=root,
                        frozen_commit="0" * 40,
                        p0_audit=bad_audit,
                        state=state,
                    )
            authorize.assert_not_called()
            historical.assert_not_called()
            self.assertFalse(state.prospective_grid_opaque_verified)
            self.assertFalse(state.prospective_grid_analytically_opened)

    def test_small_grid_adapter_is_strict_and_aug30_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            grid = _grid_path(root)
            _write_grid(grid, 8)
            digest = hashlib.sha256(grid.read_bytes()).hexdigest()
            p0 = p1.P0AuditAuthorization(
                audit_sha256="a" * 64,
                grid_sha256=digest,
                grid_bytes=grid.stat().st_size,
                grid_path=grid.as_posix(),
                frozen_implementation_commit=p1.P0_ACQUISITION_COMMIT,
            )
            authorization = p1.authorize_prospective_grid(grid, p0)
            day = p1.load_prospective_grid(
                grid, authorization, expected_rows=8
            )
            self.assertEqual(day.day, date(2026, 8, 30))
            self.assertEqual(day.ts[0], p1.DAY_START_US)
            self.assertTrue(np.all(np.diff(day.ts) == 250_000))


class Exp024P1ExecutionSafetyTests(unittest.TestCase):
    def test_existing_output_and_part_refuse_before_execution(self):
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

    def test_execution_error_creates_one_atomic_json_safe_invalid_artifact(self):
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
            json.dumps(result, allow_nan=False)

    def test_result_schema_has_no_forbidden_scientific_outputs(self):
        payloads = [
            p1.synthetic_result_payload(p1.PASS_STATUS),
            p1.invalid_payload(RuntimeError("synthetic"), "0" * 40, p1.ExecutionState()),
        ]
        forbidden = {
            "long_gross_bps",
            "short_gross_bps",
            "winning_direction",
            "directional_label",
            "directional_score",
            "PnL",
            "pnl",
            "leverage",
        }
        for payload in payloads:
            serialized = json.dumps(p1.normalize_result_payload(payload))
            for name in forbidden:
                self.assertNotIn(f'"{name}"', serialized)
            for guard in p1.EXECUTION_GUARD_NAMES:
                self.assertIs(payload[guard], False)
        source = inspect.getsource(p1._execute_once)
        for name in forbidden:
            self.assertNotIn(f'"{name}"', source)

    def test_preflight_cannot_accept_or_open_a_prospective_grid(self):
        with self.assertRaises(SystemExit), mock.patch.object(
            p1, "run_preflight"
        ) as preflight:
            p1.main(
                [
                    "--mode",
                    "preflight",
                    "--workspace",
                    ".",
                    "--feature-dir",
                    "synthetic",
                    "--grid",
                    "must-not-open.csv",
                ]
            )
        preflight.assert_not_called()

    def test_preflight_does_not_fit_or_score_and_uses_jan_jul_only(self):
        counts = [
            {"day": day.isoformat(), "common_support_n": 1}
            for day in p1.TRAIN_DAYS
        ]
        validation = [
            {
                "rv_exact_match": True,
                "target_and_support_exact_match": True,
            }
            for _ in p1.TRAIN_DAYS
        ]
        fake_history = (
            [],
            validation,
            np.ones((7, 1), dtype=np.float64),
            np.asarray([0, 1, 0, 1, 0, 1, 0], dtype=np.int8),
            counts,
        )
        with mock.patch.object(
            p1, "verify_preregistration", return_value=p1.PREREGISTRATION_SHA256
        ), mock.patch.object(
            p1,
            "verify_frozen_references",
            return_value={
                str(path): digest
                for path, digest in p1.FROZEN_REFERENCE_SHA256.items()
            },
        ), mock.patch.object(
            p1,
            "verify_exp023_readiness",
            return_value={
                "sha256": p1.EXP023_READINESS_SHA256,
                "status": p1.EXP023_READINESS_STATUS,
            },
        ), mock.patch.object(
            p1, "_prepare_historical", return_value=fake_history
        ), mock.patch(
            "sklearn.linear_model.LogisticRegression.fit",
            side_effect=AssertionError("preflight fit forbidden"),
        ) as fit, mock.patch.object(
            p1, "load_prospective_grid"
        ) as grid_loader:
            result = p1.run_preflight(
                feature_dir=Path("synthetic"), workspace=Path("synthetic")
            )
        fit.assert_not_called()
        grid_loader.assert_not_called()
        self.assertEqual(result["status"], p1.PREOPEN_PASS_STATUS)
        self.assertFalse(result["model_fit"])
        self.assertFalse(result["prospective_metrics_scored"])

    def test_module_has_no_raw_prospective_network_or_forbidden_august_interface(self):
        source = inspect.getsource(p1)
        self.assertNotIn('"--raw"', source)
        self.assertNotIn("2026-08-28", source)
        self.assertNotIn("2026-08-01", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("urlopen", source)
        self.assertNotIn("railway", source.lower())
        self.assertEqual(
            p1.TRAIN_DAYS,
            tuple(date(2026, month, 1) for month in range(1, 8)),
        )


if __name__ == "__main__":
    unittest.main()
