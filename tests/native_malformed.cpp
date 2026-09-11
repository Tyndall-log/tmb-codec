#include "tmb_codec.h"

#include <array>
#include <cstdlib>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

namespace {
void require(bool condition) { if(!condition) std::abort(); }
const std::array<float, 12> vertices = {
    -20.125f, 4.25f, -0.0f,
    31.75f, -14.5f, 2.125f,
    0.125f, 20.5f, 7.75f,
    -3.5f, 1.0f, 42.0f,
};
const std::array<uint32_t, 12> faces = {0, 2, 1, 0, 1, 3, 1, 2, 3, 2, 0, 3};

int decode(const unsigned char* data, size_t size) {
    std::array<float, 12> output_vertices = {};
    std::array<uint32_t, 12> output_faces = {};
    double timings[2] = {};
    int result = tmb_decode_quantized(data, size, output_vertices.data(),
                                      output_faces.data(), 4, 4, TMB_VERTEX_IDS,
                                      14, timings);
    if(result == TMB_OK) {
        for(float value: output_vertices)
            if(!std::isfinite(value)) return -100;
        for(uint32_t index: output_faces)
            if(index >= 4) return -101;
    }
    return result;
}
}

int main() {
    unsigned char* encoded = nullptr;
    size_t encoded_size = 0;
    double timings[3] = {};
    require(tmb_encode_quantized(vertices.data(), 4, faces.data(), 4,
                                TMB_VERTEX_IDS, 14, &encoded, &encoded_size,
                                timings) == TMB_OK);
    std::vector<unsigned char> valid(encoded, encoded + encoded_size);
    tmb_free(encoded);

    for(size_t cut = 0; cut < valid.size(); ++cut) {
        require(decode(valid.data(), cut) != TMB_OK);
    }

    for(size_t offset = 0; offset < valid.size(); ++offset) {
        for(unsigned char mask: {uint8_t(0x01), uint8_t(0x80), uint8_t(0xff)}) {
            std::vector<unsigned char> mutated = valid;
            mutated[offset] ^= mask;
            decode(mutated.data(), mutated.size());
        }
    }
    return 0;
}
