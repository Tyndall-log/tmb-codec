"""Python bindings for the TMB1 triangle mesh codec."""

from .codec import (
    CORNER_ROTATION,
    FACE_IDS,
    VERTEX_IDS,
    MeshInfo,
    decode,
    encode,
    inspect,
)

__all__ = [
    "CORNER_ROTATION",
    "FACE_IDS",
    "VERTEX_IDS",
    "MeshInfo",
    "decode",
    "encode",
    "inspect",
]

__version__ = "0.2.0"
