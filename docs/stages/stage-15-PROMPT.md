# Stage 15 — Precision, Multi-Core & Cross-Language Optimization Study

## Context

`gafro-rust` has completed its full 15-stage modernization pipeline, providing:
- Full grade-indexed modern CGA core, SI dimensional units, and ROS 2 boundary mirrors.
- FP32/FP64 precision generics and SIMD-accelerated batch SoA containers (`BatchPointSoA`, `BatchMotorSoA`).
- Chunked Rayon multi-core execution for point clouds, motor compositions, and forward kinematics.
- Feature-gated CUDA kernels (`cudarc`) and differential CPU/GPU verification.
- Marine robotics hydrodynamics, restoring wrenches, and thruster allocation geometry.
- Swarm coordination virtual structures, Laplacian consensus, and CGA bounding sphere collision avoidance.
- Standalone machine-readable JSON benchmark runner emitting cross-language metrics conforming to `results/benchmark_summary.json`.

With `gafro-cpp` and `gafro-idris2` adapters established in earlier stages, Stage 15 in `gafro-benchmarks` conducts the cross-language precision, scaling, and optimization study.

## Required work

1. **Ingest and Harmonize Rust Benchmark Suite**:
   - Integrate `gafro-rust/benches/benchmark_parity.rs` outputs into the central benchmark harness.
   - Align workload IDs across C++, Rust, and Idris 2 for:
     - `motor_composition_gp`
     - `sandwich_point_transform`
     - `point_pair_outer_product`
     - `kinematics_fk_6dof`
     - `kinematics_geometric_jacobian_6dof`
     - `fused_fk_and_jacobian_6dof`
     - `batch_motor_soa_per_motor` (SIMD / SoA)
     - `batch_point_transform_parallel_rayon` (Multi-core)
     - `kinematics_fk_batch_parallel_rayon` (Multi-core)
2. **FP32 vs FP64 Precision & Drift Study**:
   - Measure execution latency and throughput differences between FP32 and FP64 across single and batch workloads.
   - Quantify numerical drift and projective normalization error under repeated sandwich transforms and kinematic chains.
3. **Multi-Core & Scaling Study**:
   - Compare serial CPU, SIMD SoA, multi-threaded CPU (OpenMP/TBB vs Rayon), and GPU execution crossovers.
4. **Publish Comparison Report**:
   - Author `docs/stages/stage-15-REPORT.md` and update `results/benchmark_summary.json` and `results/benchmark_summary.md`.
   - Maintain strict separation of genuine algorithmic advantages from representation differences or missing capabilities.

## Verification

```text
make check
make test
make benchmark-smoke
```

## Commit

`bench: conduct cross-language precision and multi-core optimization study`
