# Stage 09: Rust CUDA benchmark adapter

## Goal

Benchmark the feature-gated Rust CUDA backend with the same workloads, timing
boundaries, and hardware conditions used for the C++ CUDA adapter.

## Entry prerequisite

The selected `gafro-rust` revision must provide its planned `cuda` Cargo feature,
`cudarc` integration, and at least one production device kernel. At the current
revision these are still roadmap items. Existing `BatchMotorSoA`,
`BatchPointSoA`, and batch kinematics are CPU baselines, not CUDA results.

## Required changes

1. Record Rust revision/dirty state, rustc target/profile/features/RUSTFLAGS,
   `cudarc` and PTX/kernel revisions, CUDA driver/toolkit, GPU identity, and
   compilation architecture.
2. Add Rust CUDA workloads only where semantic and precision parity with the
   Stage 07 manifest is demonstrated.
3. Implement kernel, resident-pipeline, and end-to-end timing with the same
   buffer residency, synchronization, and operation counting as C++.
4. Retain Rust scalar and optimized CPU SoA/batch runs from the same NVIDIA host
   as baselines; report packing and allocation variants separately.
5. Validate full output buffers against the canonical reference before timing,
   including boundary batch sizes and non-multiples of the CUDA block size.
6. Ensure asynchronous driver errors are surfaced at a checked synchronization
   boundary and cannot become plausible timing samples.
7. Use the repository's remote GPU tooling through explicit configuration and
   return immutable raw evidence to the central runner.

## Constraints

- Preserve all unrelated and in-progress Rust changes.
- Do not call CPU SoA/SIMD execution GPU acceleration.
- Do not compare Rust-generated PTX and nvcc-generated kernels without recording
  both code-generation paths.
- An unavailable or incomplete `cuda` feature is a blocked prerequisite, not a
  reason to invent a benchmark-only CUDA implementation.

## Definition of done

- `make check`, `make test`, and `make benchmark-smoke` pass locally.
- On the same NVIDIA host/profile used by Stage 08, Rust CUDA tests and
  benchmarks emit schema-valid, oracle-checked raw samples.
- Every C++ CUDA workload has either a compatible Rust CUDA result or an
  explicit unsupported reason.
- `docs/stages/stage-09-REPORT.md` records remote commands, hardware/toolchain
  identity, run IDs, gates, deviations, and open questions.
