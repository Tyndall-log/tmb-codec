from __future__ import annotations

import numpy as np
import pytest

import tmb_codec


@pytest.fixture
def mesh() -> tuple[np.ndarray, np.ndarray]:
    vertices = np.array(
        [
            [-20.125, 4.25, -0.0],
            [31.75, -14.5, 2.125],
            [0.125, 20.5, 7.75],
            [-3.5, 1.0, 42.0],
        ],
        dtype=np.float32,
    )
    faces = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]], dtype=np.uint32)
    return vertices, faces


def canonical(faces: np.ndarray) -> np.ndarray:
    rows = np.sort(faces, axis=1)
    return rows[np.lexsort((rows[:, 2], rows[:, 1], rows[:, 0]))]


@pytest.mark.parametrize("bits", range(1, 32))
@pytest.mark.parametrize("compressed", [False, True])
def test_quantized_round_trip(mesh, bits: int, compressed: bool) -> None:
    vertices, faces = mesh
    data = tmb_codec.encode(vertices, faces, bits=bits, compress=compressed)
    info = tmb_codec.inspect(data, compressed=compressed)
    decoded_vertices, decoded_faces = tmb_codec.decode(data, compressed=compressed)
    tolerance = float(np.ptp(vertices.astype(np.float64), axis=0).max()) / ((1 << bits) - 1)
    np.testing.assert_allclose(decoded_vertices, vertices, rtol=0, atol=tolerance + 1e-6)
    np.testing.assert_array_equal(canonical(decoded_faces), canonical(faces))
    assert info.bits == bits and not info.lossless


@pytest.mark.parametrize("compressed", [False, True])
def test_lossless_round_trip_is_byte_exact(mesh, compressed: bool) -> None:
    vertices, faces = mesh
    data = tmb_codec.encode(vertices, faces, bits=None, compress=compressed)
    decoded_vertices, decoded_faces = tmb_codec.decode(data, compressed=compressed)
    assert decoded_vertices.tobytes() == vertices.tobytes()
    np.testing.assert_array_equal(canonical(decoded_faces), canonical(faces))
    assert tmb_codec.inspect(data, compressed=compressed).lossless


def test_rejects_invalid_inputs(mesh) -> None:
    vertices, faces = mesh
    with pytest.raises(ValueError, match="bits"):
        tmb_codec.encode(vertices, faces, bits=32)
    with pytest.raises(ValueError, match="indices"):
        tmb_codec.encode(vertices, np.array([[0, 1, 99]], dtype=np.int32))
    with pytest.raises(ValueError, match="Zstd"):
        tmb_codec.decode(b"not-zstd")
