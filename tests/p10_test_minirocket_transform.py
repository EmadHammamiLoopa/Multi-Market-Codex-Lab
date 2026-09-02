from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from multimarket import dev030_p10_minirocket_transform as mr


def _fixture(n: int = 24) -> np.ndarray:
    t = np.arange(mr.EXPECTED_TIMEPOINTS, dtype=np.float32)
    X = np.zeros((n, 3, mr.EXPECTED_TIMEPOINTS), dtype=np.float32)
    for i in range(n):
        phase = np.float32(i * 0.07)
        X[i, 0] = np.sin(t * np.float32(0.13) + phase) + np.float32(i * 0.001)
        X[i, 1] = np.cos(t * np.float32(0.09) - phase) + np.float32(i * 0.002)
        X[i, 2] = (
            np.sin(t * np.float32(0.05) + phase)
            - np.cos(t * np.float32(0.03))
            + np.float32(i * 0.003)
        )
    return X


def _reason(fn, *args, **kwargs) -> str:
    with pytest.raises(mr.P10TransformError) as exc:
        fn(*args, **kwargs)
    return exc.value.reason


def test_runtime_versions_exact() -> None:
    assert mr.validate_frozen_runtime() == {
        "numpy": "2.5.2",
        "numba": "0.67.0",
        "llvmlite": "0.49.0",
    }


def test_length32_frozen_dilation_geometry() -> None:
    dilations, counts = mr.fit_dilations(32)
    assert tuple(dilations.tolist()) == (1, 2, 3)
    assert tuple(counts.tolist()) == (60, 37, 22)
    assert int(mr.NUM_KERNELS * counts.sum()) == 9_996


def test_series_shorter_than_nine_rejected() -> None:
    X = np.zeros((4, 3, 8), dtype=np.float32)
    assert _reason(
        mr.fit,
        X,
        require_canonical_geometry=False,
    ) == "series_too_short"


def test_canonical_geometry_rejects_wrong_channel_count() -> None:
    X = np.zeros((4, 2, 32), dtype=np.float32)
    assert _reason(mr.fit, X) == "canonical_geometry_mismatch"


def test_parameter_and_feature_hashes_repeat_exactly() -> None:
    X = _fixture()
    p1 = mr.fit(X)
    p2 = mr.fit(X)

    assert mr.parameter_sha256(p1) == mr.parameter_sha256(p2)

    f1 = mr.transform(X, p1)
    f2 = mr.transform(X, p2)

    assert mr.feature_sha256(f1) == mr.feature_sha256(f2)
    assert np.array_equal(f1, f2)


def test_output_shape_dtype_range_and_channels() -> None:
    X = _fixture()
    params = mr.fit(X)
    features = mr.transform(X, params)

    assert features.shape == (len(X), 9_996)
    assert features.dtype == np.float32
    assert np.all(np.isfinite(features))
    assert np.all(features >= 0)
    assert np.all(features <= 1)
    assert mr.used_channels(params) == (0, 1, 2)


def test_one_channel_perturbation_changes_transform() -> None:
    X = _fixture()
    params = mr.fit(X)
    base = mr.transform(X, params)

    changed = X.copy()
    changed[:, 2, :] += np.linspace(
        0.0,
        0.25,
        mr.EXPECTED_TIMEPOINTS,
        dtype=np.float32,
    )
    perturbed = mr.transform(changed, params)

    assert mr.feature_sha256(base) != mr.feature_sha256(perturbed)
    assert not np.array_equal(base, perturbed)


def test_transform_does_not_modify_input() -> None:
    X = _fixture()
    original = X.copy()
    params = mr.fit(X)
    _ = mr.transform(X, params)
    assert np.array_equal(X, original)


def test_frozen_parameter_overrides_rejected() -> None:
    X = _fixture()
    assert _reason(mr.fit, X, requested_features=5_000) == (
        "feature_count_override_forbidden"
    )
    assert _reason(mr.fit, X, max_dilations_per_kernel=16) == (
        "dilation_override_forbidden"
    )
    assert _reason(mr.fit, X, random_state=1) == (
        "random_state_override_forbidden"
    )


def test_feature_hash_shape_sensitive() -> None:
    X = _fixture(4)
    params = mr.fit(X)
    features = mr.transform(X, params)
    assert mr.feature_sha256(features) != mr.feature_sha256(features[:3])


def test_fresh_process_hashes_match() -> None:
    code = r"""
import numpy as np
from multimarket import dev030_p10_minirocket_transform as mr

t = np.arange(mr.EXPECTED_TIMEPOINTS, dtype=np.float32)
X = np.zeros((24, 3, mr.EXPECTED_TIMEPOINTS), dtype=np.float32)
for i in range(24):
    phase = np.float32(i * 0.07)
    X[i, 0] = np.sin(t * np.float32(0.13) + phase) + np.float32(i * 0.001)
    X[i, 1] = np.cos(t * np.float32(0.09) - phase) + np.float32(i * 0.002)
    X[i, 2] = (
        np.sin(t * np.float32(0.05) + phase)
        - np.cos(t * np.float32(0.03))
        + np.float32(i * 0.003)
    )
params = mr.fit(X)
features = mr.transform(X, params)
print(mr.parameter_sha256(params))
print(mr.feature_sha256(features))
"""
    first = subprocess.check_output(
        [sys.executable, "-c", code],
        text=True,
    ).strip().splitlines()
    second = subprocess.check_output(
        [sys.executable, "-c", code],
        text=True,
    ).strip().splitlines()

    assert len(first) == 2
    assert first == second
