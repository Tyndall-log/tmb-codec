#include "teeth_mesh_codec.h"

#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

namespace {
const std::array<float, 12> vertices = {
    -20.125f, 4.25f, -0.0f,
    31.75f, -14.5f, 2.125f,
    0.125f, 20.5f, 7.75f,
    -3.5f, 1.0f, 42.0f,
};
const std::array<uint32_t, 12> faces = {0, 2, 1, 0, 1, 3, 1, 2, 3, 2, 0, 3};

std::vector<std::array<uint32_t, 3>> canonical(const uint32_t* data) {
    std::vector<std::array<uint32_t, 3>> rows;
    for (size_t i = 0; i < faces.size(); i += 3) {
        std::array<uint32_t, 3> row = {data[i], data[i + 1], data[i + 2]};
        std::sort(row.begin(), row.end());
        rows.push_back(row);
    }
    std::sort(rows.begin(), rows.end());
    return rows;
}

void check_lossless() {
    unsigned char* encoded = nullptr;
    size_t encoded_size = 0;
    double encode_timings[3] = {};
    assert(tmb_encode_lossless(vertices.data(), 4, faces.data(), 4, TMB_VERTEX_IDS,
                               &encoded, &encoded_size, encode_timings) == TMB_OK);
    std::array<float, 12> decoded_vertices = {};
    std::array<uint32_t, 12> decoded_faces = {};
    double decode_timings[2] = {};
    assert(tmb_decode_lossless(encoded, encoded_size, decoded_vertices.data(),
                               decoded_faces.data(), 4, 4, TMB_VERTEX_IDS,
                               decode_timings) == TMB_OK);
    assert(std::memcmp(vertices.data(), decoded_vertices.data(), sizeof(vertices)) == 0);
    assert(canonical(faces.data()) == canonical(decoded_faces.data()));
    tmb_free(encoded);
}

void check_quantized(uint32_t bits) {
    unsigned char* encoded = nullptr;
    size_t encoded_size = 0;
    double encode_timings[3] = {};
    assert(tmb_encode_quantized(vertices.data(), 4, faces.data(), 4, TMB_VERTEX_IDS,
                                bits, &encoded, &encoded_size, encode_timings) == TMB_OK);
    std::array<float, 12> decoded_vertices = {};
    std::array<uint32_t, 12> decoded_faces = {};
    double decode_timings[2] = {};
    assert(tmb_decode_quantized(encoded, encoded_size, decoded_vertices.data(),
                                decoded_faces.data(), 4, 4, TMB_VERTEX_IDS, bits,
                                decode_timings) == TMB_OK);
    const float tolerance = 62.125f / static_cast<float>((uint64_t{1} << bits) - 1) + 1e-5f;
    for (size_t i = 0; i < vertices.size(); ++i) {
        assert(std::abs(vertices[i] - decoded_vertices[i]) <= tolerance);
    }
    assert(canonical(faces.data()) == canonical(decoded_faces.data()));
    tmb_free(encoded);
}
}

int main() {
    check_lossless();
    for (uint32_t bits : {1u, 16u, 17u, 31u}) {
        check_quantized(bits);
    }
    return 0;
}
