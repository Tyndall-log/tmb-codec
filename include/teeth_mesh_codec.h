#ifndef TEETH_MESH_CODEC_H
#define TEETH_MESH_CODEC_H

#include <stddef.h>
#include <stdint.h>

#if defined(_WIN32)
#if defined(TMB_BUILDING_LIBRARY)
#define TMB_API __declspec(dllexport)
#else
#define TMB_API __declspec(dllimport)
#endif
#elif defined(__GNUC__) || defined(__clang__)
#define TMB_API __attribute__((visibility("default")))
#else
#define TMB_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

enum tmb_flags {
    TMB_VERTEX_IDS = 1u << 0,
    TMB_FACE_IDS = 1u << 1,
    TMB_CORNER_ROTATION = 1u << 2,
};

enum tmb_result {
    TMB_OK = 0,
    TMB_INVALID_STREAM = 1,
    TMB_ALLOCATION_FAILED = 2,
    TMB_CODEC_ERROR = 3,
    TMB_INVALID_ARGUMENT = 4,
    TMB_INDEX_OUT_OF_RANGE = 5,
    TMB_TOPOLOGY_MISMATCH = 6,
    TMB_NON_FINITE_POSITION = 7,
    TMB_INVALID_CORNER_ROTATION = 8,
};

TMB_API int tmb_encode_lossless(
    const float* vertices,
    uint32_t vertex_count,
    const uint32_t* faces,
    uint32_t face_count,
    uint32_t flags,
    unsigned char** output,
    size_t* output_size,
    double* timings);

TMB_API int tmb_decode_lossless(
    const unsigned char* input,
    size_t input_size,
    float* vertices,
    uint32_t* faces,
    uint32_t vertex_count,
    uint32_t face_count,
    uint32_t flags,
    double* timings);

TMB_API int tmb_encode_quantized(
    const float* vertices,
    uint32_t vertex_count,
    const uint32_t* faces,
    uint32_t face_count,
    uint32_t flags,
    uint32_t bits,
    unsigned char** output,
    size_t* output_size,
    double* timings);

TMB_API int tmb_decode_quantized(
    const unsigned char* input,
    size_t input_size,
    float* vertices,
    uint32_t* faces,
    uint32_t vertex_count,
    uint32_t face_count,
    uint32_t flags,
    uint32_t bits,
    double* timings);

TMB_API void tmb_free(void* output);

#ifdef __cplusplus
}
#endif

#endif
