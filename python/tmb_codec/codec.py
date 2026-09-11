"""NumPy API for the native TMB1 codec."""

from __future__ import annotations

import ctypes as ct
import os
import struct
import sys
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

import numpy as np
import numpy.typing as npt
import zstandard as zstd

VERTEX_IDS = 1 << 0
FACE_IDS = 1 << 1
CORNER_ROTATION = 1 << 2

_MAGIC = 0x31424D54
_VERSION = 1
_QUANTIZED = 1 << 8
_BITS_SHIFT = 16
_HEADER = struct.Struct("<10I")
_MAX_RAW = 128 * 1024 * 1024
_LIBRARY: ct.CDLL | None = None


@dataclass(frozen=True, slots=True)
class MeshInfo:
    vertex_count: int
    face_count: int
    bits: int | None
    flags: int
    compressed: bool

    @property
    def lossless(self) -> bool:
        return self.bits is None


def _library_name() -> str:
    if os.name == "nt":
        return "tmb_codec.dll"
    if sys.platform == "darwin":
        return "libtmb_codec.dylib"
    return "libtmb_codec.so"


def _library() -> ct.CDLL:
    global _LIBRARY
    if _LIBRARY is not None:
        return _LIBRARY
    override = os.environ.get("TMB_CODEC_LIBRARY")
    path = Path(override) if override else Path(str(files("tmb_codec") / "_native" / _library_name()))
    if not path.is_file():
        raise ModuleNotFoundError(f"TMB native library is not installed: {path}")
    library = ct.CDLL(str(path.resolve()))
    encode_base = [ct.c_void_p, ct.c_uint32, ct.c_void_p, ct.c_uint32, ct.c_uint32]
    decode_base = [
        ct.c_void_p,
        ct.c_size_t,
        ct.c_void_p,
        ct.c_void_p,
        ct.c_uint32,
        ct.c_uint32,
        ct.c_uint32,
    ]
    library.tmb_encode_lossless.argtypes = encode_base + [
        ct.POINTER(ct.c_void_p),
        ct.POINTER(ct.c_size_t),
        ct.c_void_p,
    ]
    library.tmb_encode_lossless.restype = ct.c_int
    library.tmb_encode_quantized.argtypes = encode_base + [
        ct.c_uint32,
        ct.POINTER(ct.c_void_p),
        ct.POINTER(ct.c_size_t),
        ct.c_void_p,
    ]
    library.tmb_encode_quantized.restype = ct.c_int
    library.tmb_decode_lossless.argtypes = decode_base + [ct.c_void_p]
    library.tmb_decode_lossless.restype = ct.c_int
    library.tmb_decode_quantized.argtypes = decode_base + [ct.c_uint32, ct.c_void_p]
    library.tmb_decode_quantized.restype = ct.c_int
    library.tmb_free.argtypes = [ct.c_void_p]
    library.tmb_free.restype = None
    _LIBRARY = library
    return library


def _arrays(
    vertices: npt.ArrayLike, faces: npt.ArrayLike
) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.uint32]]:
    vertex_array = np.ascontiguousarray(vertices, dtype=np.float32)
    original_faces = np.asarray(faces)
    if (
        vertex_array.ndim != 2
        or vertex_array.shape[1] != 3
        or not len(vertex_array)
        or not np.isfinite(vertex_array).all()
    ):
        raise ValueError("vertices must be a finite float32 array with shape [V,3]")
    if (
        original_faces.ndim != 2
        or original_faces.shape[1] != 3
        or not len(original_faces)
        or original_faces.dtype.kind not in "iu"
        or original_faces.min() < 0
        or original_faces.max() >= len(vertex_array)
    ):
        raise ValueError("faces must contain valid triangle vertex indices")
    return vertex_array, np.ascontiguousarray(original_faces, dtype=np.uint32)


def encode(
    vertices: npt.ArrayLike,
    faces: npt.ArrayLike,
    *,
    bits: int | None = 14,
    flags: int = VERTEX_IDS,
    compress: bool = True,
    compression_level: int = 2,
) -> bytes:
    """Encode a triangle mesh; ``bits=None`` preserves float32 positions exactly."""
    if flags not in range(8):
        raise ValueError("flags must be in [0,7]")
    if bits is not None and not 1 <= bits <= 31:
        raise ValueError("bits must be None or in [1,31]")
    vertex_array, face_array = _arrays(vertices, faces)
    library = _library()
    output = ct.c_void_p()
    output_size = ct.c_size_t()
    timings = np.empty(3, dtype=np.float64)
    common = (
        vertex_array.ctypes.data,
        len(vertex_array),
        face_array.ctypes.data,
        len(face_array),
        flags,
    )
    code = (
        library.tmb_encode_lossless(
            *common, ct.byref(output), ct.byref(output_size), timings.ctypes.data
        )
        if bits is None
        else library.tmb_encode_quantized(
            *common, bits, ct.byref(output), ct.byref(output_size), timings.ctypes.data
        )
    )
    if code:
        raise ValueError(f"TMB1 encode failed ({code})")
    try:
        raw = ct.string_at(output, output_size.value)
    finally:
        library.tmb_free(output)
    return zstd.ZstdCompressor(level=compression_level).compress(raw) if compress else raw


def _raw(data: bytes | bytearray | memoryview, compressed: bool) -> bytes:
    body = bytes(data)
    if not compressed:
        return body
    try:
        size = zstd.frame_content_size(body)
        if size < 0 or size == zstd.CONTENTSIZE_UNKNOWN or size > _MAX_RAW:
            raise ValueError("invalid decompressed size")
        return zstd.ZstdDecompressor(max_window_size=128 * 1024).decompress(
            body, max_output_size=_MAX_RAW, allow_extra_data=False
        )
    except zstd.ZstdError as exc:
        raise ValueError("invalid Zstd frame") from exc


def _info(raw: bytes, compressed: bool) -> MeshInfo:
    if len(raw) < _HEADER.size:
        raise ValueError("truncated TMB1 header")
    header = _HEADER.unpack_from(raw)
    magic, version, wire_flags, vertex_count, face_count = header[:5]
    flags = wire_flags & 7
    quantized = bool(wire_flags & _QUANTIZED)
    bits = (wire_flags >> _BITS_SHIFT) & 31
    expected = flags | (_QUANTIZED if quantized else 0) | (bits << _BITS_SHIFT)
    if magic != _MAGIC or version != _VERSION or wire_flags != expected:
        raise ValueError("unsupported TMB1 version or flags")
    if not 0 < vertex_count <= 2_000_000 or not 0 < face_count <= 4_000_000:
        raise ValueError("TMB1 mesh exceeds supported limits")
    if quantized != bool(bits):
        raise ValueError("invalid TMB1 precision")
    if sum(header[5:]) != len(raw) - _HEADER.size:
        raise ValueError("invalid TMB1 section lengths")
    return MeshInfo(vertex_count, face_count, bits if quantized else None, flags, compressed)


def inspect(data: bytes | bytearray | memoryview, *, compressed: bool = True) -> MeshInfo:
    """Read validated public metadata without decoding the mesh."""
    raw = _raw(data, compressed)
    return _info(raw, compressed)


def decode(
    data: bytes | bytearray | memoryview, *, compressed: bool = True
) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.uint32]]:
    """Decode TMB1 bytes into contiguous ``vertices`` and ``faces`` arrays."""
    raw = _raw(data, compressed)
    info = _info(raw, compressed)
    vertices = np.empty((info.vertex_count, 3), dtype=np.float32)
    faces = np.empty((info.face_count, 3), dtype=np.uint32)
    timings = np.empty(2, dtype=np.float64)
    common = (
        raw,
        len(raw),
        vertices.ctypes.data,
        faces.ctypes.data,
        info.vertex_count,
        info.face_count,
        info.flags,
    )
    library = _library()
    code = (
        library.tmb_decode_lossless(*common, timings.ctypes.data)
        if info.lossless
        else library.tmb_decode_quantized(*common, info.bits, timings.ctypes.data)
    )
    if code:
        raise ValueError(f"TMB1 decode failed ({code})")
    if not np.isfinite(vertices).all() or faces.max() >= info.vertex_count:
        raise ValueError("invalid decoded mesh")
    return vertices, faces
