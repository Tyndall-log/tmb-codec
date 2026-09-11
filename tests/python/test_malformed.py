from __future__ import annotations

import numpy as np
import pytest

import tmb_codec


def encoded_mesh() -> bytes:
    vertices = np.array(
        [[-2, 0, 0], [3, 0, 0], [0, 4, 0], [0, 0, 2]], dtype=np.float32
    )
    faces = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]], dtype=np.uint32)
    return tmb_codec.encode(vertices, faces, bits=14, compress=False)


def test_every_truncated_prefix_is_rejected() -> None:
    valid = encoded_mesh()
    for cut in range(len(valid)):
        with pytest.raises(ValueError):
            tmb_codec.decode(valid[:cut], compressed=False)


def test_single_byte_mutations_never_escape_output_bounds() -> None:
    valid = encoded_mesh()
    for offset in range(len(valid)):
        for mask in (0x01, 0x80, 0xFF):
            mutated = bytearray(valid)
            mutated[offset] ^= mask
            try:
                vertices, faces = tmb_codec.decode(mutated, compressed=False)
            except ValueError:
                continue
            assert np.isfinite(vertices).all()
            assert faces.min() >= 0
            assert faces.max() < len(vertices)
