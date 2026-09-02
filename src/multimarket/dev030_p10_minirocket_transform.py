"""Deterministic equal-length multivariate MiniRocket-style transform for DEV030-P10.

This module contains representation code only. It does not load project data, fit the
P10 classifier, score folds, or write a canonical P10 artifact.

The implementation is an adaptation of the BSD-3-Clause sktime multivariate
MiniRocket implementation reviewed at commit
d26be800f423eb273d8a83269a2e9ec6dd524d77.

Reference files:
- sktime/transformations/rocket/_minirocket_multivariate.py
- sktime/transformations/rocket/_minirocket_multi_numba.py

MiniRocket scientific reference:
Dempster, Schmidt, Webb, KDD 2021, arXiv:2012.08791.

The original angus924/minirocket repository is GPL-3.0 and is not copied here.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import struct
from typing import Any

import numpy as np

try:
    import numba
    from numba import njit
except ImportError as exc:  # pragma: no cover - dependency gate
    raise ImportError(
        "DEV030-P10 transform requires the isolated p10 dependency: "
        "numba==0.67.0"
    ) from exc


EXPERIMENT_ID = "DEV030-P10"
DESIGN_VERSION = "price-minirocket-multivariate-linear-v1"

REFERENCE_REPOSITORY = "sktime/sktime"
REFERENCE_COMMIT = "d26be800f423eb273d8a83269a2e9ec6dd524d77"
REFERENCE_WRAPPER_BLOB = "4349de033310bbcbf51e105f899a9b83a296b7e7"
REFERENCE_NUMBA_BLOB = "2f62d055107e4ae04cc6a50eea57dab0fc0310b5"
REFERENCE_LICENSE_BLOB = "e321b92c174d19654c0bf83f6ee73f50b024f92c"
REFERENCE_LICENSE = "BSD-3-Clause"

EXPECTED_PYTHON_MAJOR_MINOR = (3, 14)
EXPECTED_NUMPY = "2.5.2"
EXPECTED_NUMBA = "0.67.0"
EXPECTED_LLVM_LITE = "0.49.0"

NUM_KERNELS = 84
KERNEL_LENGTH = 9
REQUESTED_FEATURES = 10_000
ACTUAL_FEATURES = 9_996
FEATURES_PER_KERNEL = 119
MAX_DILATIONS_PER_KERNEL = 32
RANDOM_STATE = 0
TRANSFORM_THREADS = 1

EXPECTED_CHANNELS = 3
EXPECTED_TIMEPOINTS = 32
EXPECTED_DILATIONS = (1, 2, 3)
EXPECTED_FEATURES_PER_DILATION = (60, 37, 22)

PARAMETER_HASH_DOMAIN = b"DEV030-P10-MINIROCKET-PARAMETERS-V1\x00"
FEATURE_HASH_DOMAIN = b"DEV030-P10-MINIROCKET-FEATURES-V1\x00"


class P10TransformError(RuntimeError):
    """Frozen P10 transform invariant failure."""

    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")


@dataclass(frozen=True)
class MiniRocketParameters:
    """Frozen fitted transform parameters."""

    num_channels_per_combination: np.ndarray
    channel_indices: np.ndarray
    bias_instance_indices: np.ndarray
    dilations: np.ndarray
    num_features_per_dilation: np.ndarray
    biases: np.ndarray
    n_channels: int
    n_timepoints: int
    requested_features: int
    actual_features: int
    random_state: int


def runtime_versions() -> dict[str, str]:
    """Return transform dependency versions without mutating the environment."""
    import llvmlite

    return {
        "numpy": np.__version__,
        "numba": numba.__version__,
        "llvmlite": llvmlite.__version__,
    }


def validate_frozen_runtime() -> dict[str, str]:
    """Require the exact locally frozen P10 transform dependency versions."""
    versions = runtime_versions()
    expected = {
        "numpy": EXPECTED_NUMPY,
        "numba": EXPECTED_NUMBA,
        "llvmlite": EXPECTED_LLVM_LITE,
    }
    for name, value in expected.items():
        if versions[name] != value:
            raise P10TransformError(
                "dependency_version_mismatch",
                f"{name}: expected={value} actual={versions[name]}",
            )
    return versions


def _kernel_indices() -> np.ndarray:
    """Return the 84 fixed length-9 MiniRocket kernel index triplets."""
    result = np.asarray(
        tuple(itertools.combinations(range(KERNEL_LENGTH), 3)),
        dtype=np.int32,
    )
    if result.shape != (NUM_KERNELS, 3):
        raise P10TransformError("kernel_index_shape_mismatch")
    return result


KERNEL_INDICES = _kernel_indices()


def fit_dilations(
    n_timepoints: int,
    num_features: int = REQUESTED_FEATURES,
    max_dilations_per_kernel: int = MAX_DILATIONS_PER_KERNEL,
) -> tuple[np.ndarray, np.ndarray]:
    """Reproduce the frozen MiniRocket dilation allocation."""
    if int(n_timepoints) < KERNEL_LENGTH:
        raise P10TransformError(
            "series_too_short",
            f"minimum={KERNEL_LENGTH} actual={n_timepoints}",
        )
    if int(num_features) < NUM_KERNELS:
        num_features = NUM_KERNELS
    num_features_per_kernel = int(num_features) // NUM_KERNELS
    true_max = min(num_features_per_kernel, int(max_dilations_per_kernel))
    if true_max <= 0:
        raise P10TransformError("invalid_dilation_count")

    multiplier = num_features_per_kernel / true_max
    max_exponent = np.log2((int(n_timepoints) - 1) / (KERNEL_LENGTH - 1))
    dilations, counts = np.unique(
        np.logspace(
            0,
            max_exponent,
            true_max,
            base=2,
        ).astype(np.int32),
        return_counts=True,
    )
    num_features_per_dilation = (counts * multiplier).astype(np.int32)

    remainder = num_features_per_kernel - int(
        np.sum(num_features_per_dilation)
    )
    index = 0
    while remainder > 0:
        num_features_per_dilation[index] += 1
        remainder -= 1
        index = (index + 1) % len(num_features_per_dilation)

    return dilations.astype(np.int32), num_features_per_dilation.astype(np.int32)


def _quantiles(n: int) -> np.ndarray:
    golden = (np.sqrt(5.0) + 1.0) / 2.0
    return np.asarray(
        [((i * golden) % 1.0) for i in range(1, int(n) + 1)],
        dtype=np.float32,
    )


def _validate_input(X: Any) -> np.ndarray:
    array = np.asarray(X, dtype=np.float32)
    if array.ndim != 3:
        raise P10TransformError("input_must_be_3d")
    n_instances, n_channels, n_timepoints = array.shape
    if n_instances < 1:
        raise P10TransformError("input_has_no_instances")
    if n_channels < 1:
        raise P10TransformError("input_has_no_channels")
    if n_timepoints < KERNEL_LENGTH:
        raise P10TransformError(
            "series_too_short",
            f"minimum={KERNEL_LENGTH} actual={n_timepoints}",
        )
    if not bool(np.all(np.isfinite(array))):
        raise P10TransformError("input_non_finite")
    return np.ascontiguousarray(array, dtype=np.float32)


def validate_frozen_geometry(X: Any) -> np.ndarray:
    """Require the P10 canonical 3-channel x 32-timepoint geometry."""
    array = _validate_input(X)
    if array.shape[1:] != (EXPECTED_CHANNELS, EXPECTED_TIMEPOINTS):
        raise P10TransformError(
            "canonical_geometry_mismatch",
            f"expected=(*,{EXPECTED_CHANNELS},{EXPECTED_TIMEPOINTS}) "
            f"actual={array.shape}",
        )
    return array


def _frozen_sampling_plan(
    *,
    n_instances: int,
    n_channels: int,
    num_combinations: int,
    random_state: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create all random choices before entering Numba.

    sktime seeds channel-combination selection and separately reseeds bias-example
    selection. We preserve that structure while materialising every random choice
    explicitly so fresh-process reproducibility is directly hashable.
    """
    channel_rng = np.random.RandomState(int(random_state))
    max_num_channels = min(int(n_channels), KERNEL_LENGTH)
    max_exponent = np.log2(max_num_channels + 1)

    num_channels_per_combination = (
        2
        ** channel_rng.uniform(
            0.0,
            max_exponent,
            int(num_combinations),
        )
    ).astype(np.int32)

    channel_indices = np.zeros(
        int(np.sum(num_channels_per_combination)),
        dtype=np.int32,
    )
    start = 0
    for count in num_channels_per_combination.tolist():
        end = start + int(count)
        channel_indices[start:end] = channel_rng.choice(
            int(n_channels),
            int(count),
            replace=False,
        ).astype(np.int32)
        start = end

    bias_rng = np.random.RandomState(int(random_state))
    bias_instance_indices = bias_rng.randint(
        0,
        int(n_instances),
        size=int(num_combinations),
    ).astype(np.int32)

    return (
        num_channels_per_combination,
        channel_indices,
        bias_instance_indices,
    )


@njit(cache=True, fastmath=True)
def _fit_biases_core(
    X: np.ndarray,
    kernel_indices: np.ndarray,
    num_channels_per_combination: np.ndarray,
    channel_indices: np.ndarray,
    bias_instance_indices: np.ndarray,
    dilations: np.ndarray,
    num_features_per_dilation: np.ndarray,
    quantiles: np.ndarray,
) -> np.ndarray:
    n_instances, _, n_timepoints = X.shape
    num_kernels = kernel_indices.shape[0]
    num_features = num_kernels * np.sum(num_features_per_dilation)
    biases = np.zeros(num_features, dtype=np.float32)

    feature_start = 0
    combination_index = 0
    channel_start = 0

    for dilation_index in range(len(dilations)):
        dilation = dilations[dilation_index]
        padding = ((KERNEL_LENGTH - 1) * dilation) // 2
        features_this_dilation = num_features_per_dilation[dilation_index]

        for kernel_index in range(num_kernels):
            feature_end = feature_start + features_this_dilation
            channel_count = num_channels_per_combination[combination_index]
            channel_end = channel_start + channel_count
            channels = channel_indices[channel_start:channel_end]

            example_index = bias_instance_indices[combination_index]
            if example_index < 0 or example_index >= n_instances:
                raise ValueError("bias instance index out of range")
            selected = X[example_index][channels]

            A = -selected
            G = selected + selected + selected

            C_alpha = np.zeros(
                (channel_count, n_timepoints),
                dtype=np.float32,
            )
            C_alpha[:] = A
            C_gamma = np.zeros(
                (KERNEL_LENGTH, channel_count, n_timepoints),
                dtype=np.float32,
            )
            C_gamma[KERNEL_LENGTH // 2] = G

            start = dilation
            end = n_timepoints - padding

            for gamma_index in range(KERNEL_LENGTH // 2):
                C_alpha[:, -end:] = C_alpha[:, -end:] + A[:, :end]
                C_gamma[gamma_index, :, -end:] = G[:, :end]
                end += dilation

            for gamma_index in range(
                KERNEL_LENGTH // 2 + 1,
                KERNEL_LENGTH,
            ):
                C_alpha[:, :-start] = C_alpha[:, :-start] + A[:, start:]
                C_gamma[gamma_index, :, :-start] = G[:, start:]
                start += dilation

            index_0 = kernel_indices[kernel_index, 0]
            index_1 = kernel_indices[kernel_index, 1]
            index_2 = kernel_indices[kernel_index, 2]

            C = (
                C_alpha
                + C_gamma[index_0]
                + C_gamma[index_1]
                + C_gamma[index_2]
            )
            C = np.sum(C, axis=0)

            biases[feature_start:feature_end] = np.quantile(
                C,
                quantiles[feature_start:feature_end],
            ).astype(np.float32)

            feature_start = feature_end
            combination_index += 1
            channel_start = channel_end

    return biases


@njit(cache=True, fastmath=True)
def _transform_core(
    X: np.ndarray,
    kernel_indices: np.ndarray,
    num_channels_per_combination: np.ndarray,
    channel_indices: np.ndarray,
    dilations: np.ndarray,
    num_features_per_dilation: np.ndarray,
    biases: np.ndarray,
) -> np.ndarray:
    n_instances, n_channels, n_timepoints = X.shape
    num_kernels = kernel_indices.shape[0]
    num_features = num_kernels * np.sum(num_features_per_dilation)
    features = np.zeros((n_instances, num_features), dtype=np.float32)

    for example_index in range(n_instances):
        selected_example = X[example_index]
        A = -selected_example
        G = selected_example + selected_example + selected_example

        feature_start = 0
        combination_index = 0
        channel_start = 0

        for dilation_index in range(len(dilations)):
            padding_zero = dilation_index % 2
            dilation = dilations[dilation_index]
            padding = ((KERNEL_LENGTH - 1) * dilation) // 2
            features_this_dilation = num_features_per_dilation[dilation_index]

            C_alpha = np.zeros(
                (n_channels, n_timepoints),
                dtype=np.float32,
            )
            C_alpha[:] = A
            C_gamma = np.zeros(
                (KERNEL_LENGTH, n_channels, n_timepoints),
                dtype=np.float32,
            )
            C_gamma[KERNEL_LENGTH // 2] = G

            start = dilation
            end = n_timepoints - padding

            for gamma_index in range(KERNEL_LENGTH // 2):
                C_alpha[:, -end:] = C_alpha[:, -end:] + A[:, :end]
                C_gamma[gamma_index, :, -end:] = G[:, :end]
                end += dilation

            for gamma_index in range(
                KERNEL_LENGTH // 2 + 1,
                KERNEL_LENGTH,
            ):
                C_alpha[:, :-start] = C_alpha[:, :-start] + A[:, start:]
                C_gamma[gamma_index, :, :-start] = G[:, start:]
                start += dilation

            for kernel_index in range(num_kernels):
                feature_end = feature_start + features_this_dilation
                channel_count = num_channels_per_combination[combination_index]
                channel_end = channel_start + channel_count
                channels = channel_indices[channel_start:channel_end]

                padding_one = (padding_zero + kernel_index) % 2

                index_0 = kernel_indices[kernel_index, 0]
                index_1 = kernel_indices[kernel_index, 1]
                index_2 = kernel_indices[kernel_index, 2]

                C = (
                    C_alpha[channels]
                    + C_gamma[index_0][channels]
                    + C_gamma[index_1][channels]
                    + C_gamma[index_2][channels]
                )
                C = np.sum(C, axis=0)

                for feature_count in range(features_this_dilation):
                    bias = biases[feature_start + feature_count]
                    if padding_one == 0:
                        count = 0
                        for value in C:
                            if value > bias:
                                count += 1
                        ppv = count / len(C)
                    else:
                        start_index = padding
                        stop_index = len(C) - padding
                        count = 0
                        length = stop_index - start_index
                        for position in range(start_index, stop_index):
                            if C[position] > bias:
                                count += 1
                        ppv = count / length

                    features[
                        example_index,
                        feature_start + feature_count,
                    ] = np.float32(ppv)

                feature_start = feature_end
                combination_index += 1
                channel_start = channel_end

    return features


def fit(
    X: Any,
    *,
    requested_features: int = REQUESTED_FEATURES,
    max_dilations_per_kernel: int = MAX_DILATIONS_PER_KERNEL,
    random_state: int = RANDOM_STATE,
    require_canonical_geometry: bool = True,
) -> MiniRocketParameters:
    """Fit one deterministic MiniRocket-style transform."""
    if int(requested_features) != REQUESTED_FEATURES:
        raise P10TransformError("feature_count_override_forbidden")
    if int(max_dilations_per_kernel) != MAX_DILATIONS_PER_KERNEL:
        raise P10TransformError("dilation_override_forbidden")
    if int(random_state) != RANDOM_STATE:
        raise P10TransformError("random_state_override_forbidden")

    array = (
        validate_frozen_geometry(X)
        if require_canonical_geometry
        else _validate_input(X)
    )
    n_instances, n_channels, n_timepoints = array.shape

    dilations, num_features_per_dilation = fit_dilations(
        n_timepoints,
        requested_features,
        max_dilations_per_kernel,
    )
    actual_features = int(NUM_KERNELS * np.sum(num_features_per_dilation))

    if require_canonical_geometry:
        if tuple(dilations.tolist()) != EXPECTED_DILATIONS:
            raise P10TransformError("canonical_dilation_mismatch")
        if tuple(num_features_per_dilation.tolist()) != (
            EXPECTED_FEATURES_PER_DILATION
        ):
            raise P10TransformError(
                "canonical_features_per_dilation_mismatch"
            )
        if actual_features != ACTUAL_FEATURES:
            raise P10TransformError("canonical_feature_count_mismatch")

    num_combinations = int(NUM_KERNELS * len(dilations))
    (
        num_channels_per_combination,
        channel_indices,
        bias_instance_indices,
    ) = _frozen_sampling_plan(
        n_instances=n_instances,
        n_channels=n_channels,
        num_combinations=num_combinations,
        random_state=random_state,
    )

    num_features_per_kernel = int(np.sum(num_features_per_dilation))
    quantiles = _quantiles(NUM_KERNELS * num_features_per_kernel)

    biases = _fit_biases_core(
        array,
        KERNEL_INDICES,
        num_channels_per_combination,
        channel_indices,
        bias_instance_indices,
        dilations,
        num_features_per_dilation,
        quantiles,
    )

    if len(biases) != actual_features:
        raise P10TransformError("bias_feature_count_mismatch")
    if not bool(np.all(np.isfinite(biases))):
        raise P10TransformError("bias_non_finite")

    return MiniRocketParameters(
        num_channels_per_combination=np.ascontiguousarray(
            num_channels_per_combination,
            dtype=np.int32,
        ),
        channel_indices=np.ascontiguousarray(
            channel_indices,
            dtype=np.int32,
        ),
        bias_instance_indices=np.ascontiguousarray(
            bias_instance_indices,
            dtype=np.int32,
        ),
        dilations=np.ascontiguousarray(dilations, dtype=np.int32),
        num_features_per_dilation=np.ascontiguousarray(
            num_features_per_dilation,
            dtype=np.int32,
        ),
        biases=np.ascontiguousarray(biases, dtype=np.float32),
        n_channels=int(n_channels),
        n_timepoints=int(n_timepoints),
        requested_features=int(requested_features),
        actual_features=int(actual_features),
        random_state=int(random_state),
    )


def transform(X: Any, parameters: MiniRocketParameters) -> np.ndarray:
    """Apply fitted transform parameters without refitting."""
    array = _validate_input(X)
    if array.shape[1] != parameters.n_channels:
        raise P10TransformError("transform_channel_count_mismatch")
    if array.shape[2] != parameters.n_timepoints:
        raise P10TransformError("transform_timepoint_count_mismatch")

    features = _transform_core(
        array,
        KERNEL_INDICES,
        parameters.num_channels_per_combination,
        parameters.channel_indices,
        parameters.dilations,
        parameters.num_features_per_dilation,
        parameters.biases,
    )
    features = np.ascontiguousarray(features, dtype=np.float32)

    if features.shape != (len(array), parameters.actual_features):
        raise P10TransformError("transform_feature_shape_mismatch")
    if not bool(np.all(np.isfinite(features))):
        raise P10TransformError("transform_non_finite")
    if not bool(np.all((features >= 0.0) & (features <= 1.0))):
        raise P10TransformError("transform_ppv_range_invalid")
    return features


def parameter_sha256(parameters: MiniRocketParameters) -> str:
    """Hash fitted parameters with explicit dtype/shape framing."""
    digest = hashlib.sha256()
    digest.update(PARAMETER_HASH_DOMAIN)
    digest.update(
        struct.pack(
            ">iiii",
            int(parameters.n_channels),
            int(parameters.n_timepoints),
            int(parameters.actual_features),
            int(parameters.random_state),
        )
    )
    for array in (
        parameters.num_channels_per_combination,
        parameters.channel_indices,
        parameters.bias_instance_indices,
        parameters.dilations,
        parameters.num_features_per_dilation,
        parameters.biases,
    ):
        contiguous = np.ascontiguousarray(array)
        digest.update(str(contiguous.dtype).encode("ascii"))
        digest.update(struct.pack(">I", contiguous.ndim))
        for size in contiguous.shape:
            digest.update(struct.pack(">Q", int(size)))
        digest.update(contiguous.tobytes(order="C"))
    return digest.hexdigest()


def feature_sha256(features: Any) -> str:
    """Hash transformed float32 features with explicit shape framing."""
    array = np.ascontiguousarray(features, dtype=np.float32)
    if array.ndim != 2:
        raise P10TransformError("feature_hash_requires_2d")
    digest = hashlib.sha256()
    digest.update(FEATURE_HASH_DOMAIN)
    digest.update(struct.pack(">QQ", int(array.shape[0]), int(array.shape[1])))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def used_channels(parameters: MiniRocketParameters) -> tuple[int, ...]:
    """Return sorted unique channel ids used by fitted combinations."""
    return tuple(
        int(value)
        for value in np.unique(parameters.channel_indices).tolist()
    )


__all__ = [
    "ACTUAL_FEATURES",
    "DESIGN_VERSION",
    "EXPERIMENT_ID",
    "EXPECTED_DILATIONS",
    "EXPECTED_FEATURES_PER_DILATION",
    "EXPECTED_TIMEPOINTS",
    "FEATURES_PER_KERNEL",
    "MAX_DILATIONS_PER_KERNEL",
    "MiniRocketParameters",
    "NUM_KERNELS",
    "P10TransformError",
    "RANDOM_STATE",
    "REQUESTED_FEATURES",
    "fit",
    "fit_dilations",
    "feature_sha256",
    "parameter_sha256",
    "runtime_versions",
    "transform",
    "used_channels",
    "validate_frozen_geometry",
    "validate_frozen_runtime",
]
