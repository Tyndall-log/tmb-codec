# TMB Codec

TMB1 (Triangle Mesh Binary) is a compact general-purpose triangle-mesh codec. The
library provides one C ABI across Windows, macOS, Linux, and WebAssembly.
Native CI builds use Clang (`clang-cl` on Windows and `clang++` elsewhere).

## Features

- Float32 bit-exact lossless positions
- Quantized positions from 1 through 31 bits
- Optional restoration of vertex IDs, face IDs, and triangle corner rotation
- Single-file C++17 implementation
- No runtime dependency on Zstd; compress the completed TMB1 bundle once outside
  the codec when using `tmb1-zstd-v1`
- Bounds-checked native decoding with malformed-input tests under ASan and UBSan

Applications that require stable per-vertex data use `TMB_VERTEX_IDS` (`flags=1`). This restores
vertex rows and triangle references to original vertex IDs while allowing face
row order and cyclic starting corners to remain in traversal order.

## Python

Install a prebuilt native wheel:

```bash
pip install tmb-codec
```

```python
from tmb_codec import decode, encode

data = encode(vertices, faces, bits=14)
decoded_vertices, decoded_faces = decode(data)

lossless = encode(vertices, faces, bits=None)
```

Wheels contain the Python API, the platform-native shared library, and license
notices. They do not contain `src/tmb_codec.cpp` or an sdist.

## Native build

Windows:

```powershell
cmake -S . -B build -G Ninja -DCMAKE_CXX_COMPILER=clang-cl -DTMB_BUILD_TESTS=ON
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

macOS and Linux:

```bash
cmake -S . -B build -G Ninja -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Release -DTMB_BUILD_TESTS=ON
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

WebAssembly with Emscripten:

```bash
emcmake cmake -S . -B build-wasm -DCMAKE_BUILD_TYPE=Release -DTMB_BUILD_TESTS=OFF
cmake --build build-wasm --parallel
node tests/wasm_smoke.mjs build-wasm/tmb_codec.js
```

The WASM build emits `tmb_codec.js` and `tmb_codec.wasm` with
memory growth enabled and exports the five public TMB functions plus malloc/free.

Every push and pull request builds native SDKs and Python wheels on Windows,
macOS, and Linux and runs their tests. WASM has a separate Node.js round-trip
test. Pushing a `v*` tag publishes wheels to PyPI. GitHub Releases contain the
platform-native SDK ZIPs and the WASM ZIP; wheels remain on PyPI.

## C API

```cpp
#include <tmb_codec.h>

unsigned char* bytes = nullptr;
size_t byte_count = 0;
double timings[3] = {};
int result = tmb_encode_quantized(
    vertices, vertex_count,
    faces, face_count,
    TMB_VERTEX_IDS, 14,
    &bytes, &byte_count, timings);
if (result == TMB_OK) {
    // Send zstd(bytes[0:byte_count]) or store the raw TMB1 bundle.
    tmb_free(bytes);
}
```

Inputs are contiguous `float[V][3]` positions and `uint32_t[F][3]` triangle
indices. Encoder output is allocated by the codec and must be released with
`tmb_free`. Decoder output arrays are allocated by the caller.

## Format

TMB1 starts with ten little-endian uint32 values:

1. Magic `TMB1`
2. Format version `1`
3. Flags
4. Vertex count
5. Face count
6. Topology section size
7. Position section size
8. Vertex-ID section size
9. Face-ID section size
10. Corner-rotation section size

Quantized streams set flag bit 8 and store the coordinate bit count in flag bits
16 through 20. Their position section begins with four little-endian float64
values: origin x/y/z and a common extent. Coordinates from 1 through 16 bits use
one integer component per axis. Coordinates from 17 through 31 bits use low/high
16-bit components to keep prediction residuals inside signed 32-bit range.

The topology and position entropy streams are defined by the reference source in
`src/tmb_codec.cpp`. Consumers should use the provided encoder and decoder
unless they also maintain compatibility tests against the reference implementation.

## License

The codec incorporates and modifies MIT-licensed Corto code. Preserve
`licenses/CORTO_LICENSE.txt` with source and binary distributions. Project-level
terms are in `LICENSE`; third-party attribution is in `THIRD_PARTY_NOTICES.md`.
Security reports should follow `SECURITY.md` rather than public issues.
