# Stage 07: heterogeneous CPU/CUDA workload contract

## Goal

Extend the benchmark contract so CPU scalar, CPU batch, and CUDA execution can
be compared without hiding transfer, launch, synchronization, precision, or
amortization differences.

## Baseline

C++ has CUDA 12.6/C++20 build support and a one-thread device verification
kernel. Rust has CPU SoA batch containers and remote GPU tooling in development,
while its planned feature-gated `cudarc` kernels do not yet exist. Neither path
currently supplies comparable production GPU measurements.

## Required changes

1. Add heterogeneous workload dimensions: operation, batch size, scalar type,
   input layout, device residency, stream count, warm/cold state, and timing
   boundary.
2. Define canonical batch-size sweeps including small latency-sensitive batches,
   expected crossover sizes, and throughput-oriented large batches. Allow device
   memory limits to truncate the sweep with an explicit reason.
3. Define three separately named GPU measurements:
   - `kernel`: CUDA events around kernel execution on already-resident buffers;
   - `resident_pipeline`: all device work and synchronization with resident data;
   - `end_to_end`: host packing, H2D, execution, D2H, and host observation.
4. Define matching CPU scalar-loop and optimized-batch baselines, including
   thread count, affinity, SIMD target, packing, and allocation boundaries.
5. Require identical deterministic inputs and full-output oracle checks against
   a high-precision CPU reference before timing. Specify FP32 and FP64 as
   separate experiments with separate tolerances.
6. Extend the result schema with GPU model/UUID, compute capability, driver,
   runtime, toolkit, clocks/power mode when available, ECC/MIG state, launch
   geometry, stream, memory bytes, and CUDA-event timing metadata.
7. Add validator tests rejecting mixed precision, different batch semantics,
   incomparable timing scopes, incomplete synchronization, or mismatched output
   layouts.

## Constraints

- Do not infer GPU speedup from the existing one-thread C++ verification kernel.
- Do not use host wall time for `kernel` results or CUDA events for `end_to_end`.
- Synchronization is part of the declared boundary and must be explicit.
- No GPU is required for schema/unit tests; use fixture adapter outputs.

## Definition of done

- `make check`, `make test`, and `make benchmark-smoke` pass without CUDA.
- Fixture results prove that only matching operation, batch, precision, layout,
  and timing-scope records are ratio-compatible.
- The CLI can plan a GPU sweep and report unavailable CUDA hardware cleanly.
- `docs/stages/stage-07-REPORT.md` records gates, contract decisions,
  deviations, and open questions.
