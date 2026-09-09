import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const modulePath = process.argv[2];
if (!modulePath) throw new Error("usage: node wasm_smoke.mjs <teeth_mesh_codec.js>");
const createModule = (await import(pathToFileURL(resolve(modulePath)).href)).default;
const codec = await createModule();

const vertices = new Float32Array([
  -20.125, 4.25, -0, 31.75, -14.5, 2.125,
  0.125, 20.5, 7.75, -3.5, 1, 42,
]);
const faces = new Uint32Array([0, 2, 1, 0, 1, 3, 1, 2, 3, 2, 0, 3]);
const malloc = codec._malloc;
const free = codec._free;

function canonical(values) {
  const rows = [];
  for (let i = 0; i < values.length; i += 3) {
    rows.push([...values.slice(i, i + 3)].sort((a, b) => a - b).join(","));
  }
  return rows.sort().join("|");
}

function roundTrip(bits) {
  const vertexPtr = malloc(vertices.byteLength);
  const facePtr = malloc(faces.byteLength);
  const outputPtrPtr = malloc(4);
  const outputSizePtr = malloc(4);
  const encodeTimingPtr = malloc(24);
  codec.HEAPF32.set(vertices, vertexPtr / 4);
  codec.HEAPU32.set(faces, facePtr / 4);
  const code = bits === 32
    ? codec._tmb_encode_lossless(vertexPtr, 4, facePtr, 4, 1, outputPtrPtr, outputSizePtr, encodeTimingPtr)
    : codec._tmb_encode_quantized(vertexPtr, 4, facePtr, 4, 1, bits, outputPtrPtr, outputSizePtr, encodeTimingPtr);
  if (code !== 0) throw new Error(`encode failed: bits=${bits}, code=${code}`);
  const encodedPtr = codec.HEAPU32[outputPtrPtr / 4];
  const encodedSize = codec.HEAPU32[outputSizePtr / 4];
  const decodedVertexPtr = malloc(vertices.byteLength);
  const decodedFacePtr = malloc(faces.byteLength);
  const decodeTimingPtr = malloc(16);
  const decodeCode = bits === 32
    ? codec._tmb_decode_lossless(encodedPtr, encodedSize, decodedVertexPtr, decodedFacePtr, 4, 4, 1, decodeTimingPtr)
    : codec._tmb_decode_quantized(encodedPtr, encodedSize, decodedVertexPtr, decodedFacePtr, 4, 4, 1, bits, decodeTimingPtr);
  if (decodeCode !== 0) throw new Error(`decode failed: bits=${bits}, code=${decodeCode}`);
  const decodedVertices = codec.HEAPF32.slice(decodedVertexPtr / 4, decodedVertexPtr / 4 + vertices.length);
  const decodedFaces = codec.HEAPU32.slice(decodedFacePtr / 4, decodedFacePtr / 4 + faces.length);
  if (canonical(decodedFaces) !== canonical(faces)) throw new Error(`topology mismatch: bits=${bits}`);
  if (bits === 32) {
    const expected = new Uint8Array(vertices.buffer);
    const actual = codec.HEAPU8.slice(decodedVertexPtr, decodedVertexPtr + vertices.byteLength);
    if (!expected.every((value, index) => value === actual[index])) throw new Error("lossless mismatch");
  } else {
    const tolerance = 62.125 / (2 ** bits - 1) + 1e-5;
    decodedVertices.forEach((value, index) => {
      if (Math.abs(value - vertices[index]) > tolerance) throw new Error(`quantized mismatch: bits=${bits}`);
    });
  }
  codec._tmb_free(encodedPtr);
  [vertexPtr, facePtr, outputPtrPtr, outputSizePtr, encodeTimingPtr,
   decodedVertexPtr, decodedFacePtr, decodeTimingPtr].forEach(free);
}

for (const bits of [1, 16, 17, 31, 32]) roundTrip(bits);
console.log("TMB1 WASM smoke test passed");
