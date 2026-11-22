# Gafro-Benchmarks Session Handoff

Date: 2026-11-20

This is the durable resumption record for the `gafro-benchmarks` cross-language benchmark suite.

## Active Repository and Scope

- **Repository**: `gafro-benchmarks`
- **Completed Stages**:
  - Stages 01–14: Harness contract, C++, Idris 2, Rust adapters, 2R FK & Jacobian parity, CPU SoA batching baselines, canonical constructors.
  - Stage 15: Cross-Language Precision (FP32 vs FP64), Numerical Drift, and Multi-Core Rayon Scaling Study.
  - Stage 16: Spatial Physics, Inertia Tensor Action ($W = I \cdot T$), and Motor Transformation ($I' = M I \widetilde{M}$) Parity.
  - Stage 17: CUDA Heterogeneous Adapter Integration, Multi-Tier Batch Sweeping (`make plan-gpu`), and GPU Evidence Ingestion.
  - Stage 18: Julia member registered in smoke, full and shootout comparisons (renderer emits every `IMPLEMENTATIONS` column; `make benchmark-smoke`/`benchmark` honour `IMPLEMENTATIONS` and `JULIA_PATH`; `runner/run_all.py` gains `--members`, `--julia-path`, `--output-dir` and a pure `render_table`).
  - C++ SIMD SoA benchmark ingestion (`89d9685`): the C++ adapter emits CPU SoA rows for `batch_motor_composition` and `batch_point_transform` against gafro-cpp's `BatchMotorSoA` / `BatchPointSoA`, for direct C++ vs Rust comparison. These rows have not yet reached committed run evidence.

## Sibling State

- **`gafro-rust`**: Stages 01–18 complete on `main` (Modern grade-indexed CGA core, SI units, zero-dependency ROS 2 mirrors, FP32/FP64 generics, SIMD SoA containers, chunked Rayon, `cudarc` PTX kernels, marine robotics, swarm coordination, and the modern, marine and swarm fixture suites it generates for the family).
- **`gafro-cpp`**: Stages 01–20 complete on `main` (CUDA foundation, CPU SIMD SoA containers `BatchPointSoA` / `BatchMotorSoA`, modern types, SI units, ROS 2 adapters, marine and swarm foundations, modern fixture schema). Modern fixture ingestion is on `main` and awaits its verification report; the marine and swarm fixture suite and the cross-repository parity runner remain.
- **`gafro-idris2`**: CGA algebra core, products, versors, 2R FK, geometric Jacobians, and spatial physics (`applyInertia`) complete.
- **`gafro-julia`**: Stages 01–25 merged; its contract runner (`benchmark/contract_main.jl`) tracks harness contract `db00060` and emits all 18 rows (16 supported, 2 `dense_geometric_product/f64/orthogonal*` unsupported).

## Next Active Work Items

In order:

1. **Sibling discovery and housekeeping** (this change): default discovery finds `egafro-<family>/gafro-<family>` sibling checkouts, the smoke row's oracle uses the `value` key the validator reads, and this handoff is refreshed.
2. **First-class F\* member**: register `fstar` as a harness implementation so its rows pass `validate_complete_run`.
3. **Honest row upgrades**: the Idris inertia transform, an off-diagonal inertia observable, and unsupported reasons that have gone stale against the members' current APIs.
4. **A five-member reference run from one host**: C++, Idris 2, Rust, Julia and F\* measured together, so every row reaches run evidence from a single machine.

Later:

- Typed geometric primitives (lines, planes, spheres, circles, point pairs).
- 6-DOF / 7-DOF kinematics and dynamics.
- Joint types.
- se(3) exponential and logarithm maps.
- SoA layout parity.
- CUDA on a pod.
- Domain workloads.

## Verification

```text
make check
make test
make benchmark-smoke
make plan-gpu
```
