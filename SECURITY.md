# Security policy

## Supported versions

TMB Codec is pre-1.0 software. Only the latest published `0.2.x` release receives
security fixes.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's private
vulnerability reporting form for this repository and include:

- affected version and platform;
- a minimal TMB1 input or reproduction;
- observed crash, memory-safety report, or resource usage;
- sanitizer output when available.

We will acknowledge a report, reproduce it against the current release, and
coordinate a fix and disclosure through the private report.

## Untrusted inputs

The public decoder validates TMB1 headers, section boundaries, entropy streams,
topology references, output counts, and reconstructed indices. CI runs truncated
and mutated inputs under AddressSanitizer and UndefinedBehaviorSanitizer. Callers
should still impose compressed-size, decompressed-size, vertex-count, face-count,
memory, and execution-time limits appropriate to their service.
