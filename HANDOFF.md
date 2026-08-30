# Gafro-Benchmarks Session Handoff

Date: 2026-08-30

This is the durable resumption record for the `gafro-benchmarks` cross-language benchmark suite.

## Active Repository and Scope

- **Envelope checkout**: `/Users/durant/Repos/enveloped/gafro-benchmarks`
- **Inner repository**: `gafro-benchmarks/`
- **Completed Stages**:
  - Stages 01–14: Harness contract, C++, Idris 2, Rust adapters, 2R FK & Jacobian parity, CPU SoA batching baselines, canonical constructors.
  - Stage 15: Cross-Language Precision (FP32 vs FP64), Numerical Drift, and Multi-Core Rayon Scaling Study.
  - Stage 16: Spatial Physics, Inertia Tensor Action ($W = I \cdot T$), and Motor Transformation ($I' = M I \widetilde{M}$) Parity.
  - Stage 17: CUDA Heterogeneous Adapter Integration, Multi-Tier Batch Sweeping (`make plan-gpu`), and GPU Evidence Ingestion.

## Sibling State

- **`gafro-rust`**: All 15 modernization stages complete on `main` (Modern grade-indexed CGA core, SI units, zero-dependency ROS 2 mirrors, FP32/FP64 generics, SIMD SoA containers, chunked Rayon, `cudarc` PTX kernels, marine robotics, swarm coordination).
- **`gafro-cpp`**: Modernization pipeline in flight (Stages 01–06 CUDA foundation complete, Stages 07–13 modern types migration active, CPU SIMD SoA batch architecture specified in `docs/simd_soa_cpu_batch_architecture.md`).
- **`gafro-idris2`**: CGA algebra core, products, versors, 2R FK, geometric Jacobians, and spatial physics (`applyInertia`) complete.

## Next Active Work Items & Stages

1. **Stage 18 — Geometric Primitives Parity**:
   - Add canonical workloads for typed Lines, Planes, Spheres, Circles, and Point-Pair intersections.
   - Reconcile observables across C++, Rust, and Idris 2.
2. **Stage 19 — C++ SIMD SoA Benchmark Ingestion**:
   - Once `gafro-cpp` implements `BatchPointSoA` and `BatchMotorSoA` (as specified in its handoff), connect the C++ adapter rows for `batch_motor_composition` and `batch_point_transform` to produce direct C++ vs Rust AVX2/AVX-512 comparison.
3. **Stage 20 — 6-DOF / 7-DOF Kinematics & Dynamics Scaling**:
   - Standardize Franka Emika Panda 7-DOF / Puma 560 6-DOF kinematic chains and Recursive Newton-Euler Algorithm (RNEA) dynamics across C++ and Rust.
4. **Stage 21 — Automated Remote GPU Cloud Execution Harness**:
   - Automated cloud instance runner (Runpod / Lambda) for on-demand GPU sweep execution and raw evidence gathering.

## Verification

```text
make check
make test
make benchmark-smoke
make plan-gpu
```
