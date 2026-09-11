cmake_minimum_required(VERSION 3.20)
project(tmb_codec VERSION 0.2.0 LANGUAGES CXX)

option(TMB_BUILD_TESTS "Build native codec tests" ON)

if(EMSCRIPTEN)
    add_executable(tmb_codec src/tmb_codec.cpp)
    set_target_properties(tmb_codec PROPERTIES SUFFIX ".js")
    target_link_options(tmb_codec PRIVATE
        "--no-entry"
        "-sWASM=1"
        "-sMODULARIZE=1"
        "-sEXPORT_ES6=1"
        "-sEXPORT_NAME=createTmbCodec"
        "-sENVIRONMENT=web,worker,node"
        "-sALLOW_MEMORY_GROWTH=1"
        "-sFILESYSTEM=0"
        "-sEXPORTED_FUNCTIONS=['_tmb_encode_lossless','_tmb_decode_lossless','_tmb_encode_quantized','_tmb_decode_quantized','_tmb_free','_malloc','_free']"
        "-sEXPORTED_RUNTIME_METHODS=['cwrap','HEAPU8','HEAPU32','HEAPF32']")
else()
    add_library(tmb_codec SHARED src/tmb_codec.cpp)
    set_target_properties(tmb_codec PROPERTIES
        CXX_VISIBILITY_PRESET hidden
        VISIBILITY_INLINES_HIDDEN YES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
        LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
        ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib")
endif()

target_compile_features(tmb_codec PRIVATE cxx_std_17)
target_compile_definitions(tmb_codec PRIVATE TMB_BUILDING_LIBRARY=1)
target_include_directories(tmb_codec PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>)

if(MSVC)
    target_compile_options(tmb_codec PRIVATE /fp:strict /utf-8 /W4)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
        target_compile_options(tmb_codec PRIVATE /clang:-msse4.1)
    endif()
elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(tmb_codec PRIVATE -Wall -Wextra -Wpedantic)
endif()

if(TMB_BUILD_TESTS AND NOT EMSCRIPTEN)
    enable_testing()
    add_executable(tmb_native_smoke tests/native_smoke.cpp)
    target_compile_features(tmb_native_smoke PRIVATE cxx_std_17)
    target_link_libraries(tmb_native_smoke PRIVATE tmb_codec)
    set_target_properties(tmb_native_smoke PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
    add_test(NAME tmb_native_smoke COMMAND tmb_native_smoke)
endif()

include(GNUInstallDirs)
if(NOT EMSCRIPTEN)
    if(SKBUILD)
        install(TARGETS tmb_codec
            RUNTIME DESTINATION tmb_codec/_native
            LIBRARY DESTINATION tmb_codec/_native)
        install(FILES licenses/CORTO_LICENSE.txt DESTINATION tmb_codec/licenses)
    else()
        install(TARGETS tmb_codec
            RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
            LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
            ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
        install(FILES include/tmb_codec.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
        install(FILES licenses/CORTO_LICENSE.txt DESTINATION ${CMAKE_INSTALL_DATADIR}/tmb_codec/licenses)
    endif()
endif()
