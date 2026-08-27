# Benchmark implementation route

The route separates semantic agreement from performance measurement. Stages
01–02 establish trustworthy evidence; stages 03–05 add the sibling language
implementations; stage 06 publishes CPU comparisons without erasing capability
or environment differences. Stages 07–10 extend the same discipline to the CUDA
optimizations under development in C++ and Rust.

1. **Stage 01 — contract and harness foundation.** Define the versioned workload
   and result schemas, path discovery, capability reporting, validation, tests,
   and Make gates.
2. **Stage 02 — C++ reference adapter.** Port the C++ measurements to the
   contract, add correctness oracles and statistically useful raw samples, and
   establish the reference outputs for shared workloads.
3. **Stage 03 — Idris 2 adapter.** Benchmark the common algebra/rigid-motion
   surface without claiming the absent robotics layer; record Idris codegen and
   compiler provenance.
4. **Stage 04 — Rust adapter.** Benchmark the attached Rust implementation,
   including its optimized scalar and CPU batch paths, while recording the exact
   revision and preserving explicit capability gaps.
5. **Stage 05 — robotics workload family.** Add forward kinematics and Jacobian
   workloads only for implementations with semantically matching robotics APIs;
   retain explicit unsupported entries elsewhere.
6. **Stage 06 — reproducible aggregation and reporting.** Run repeated samples,
   preserve raw evidence, summarize distributions and provenance, and generate
   fair comparison reports with compatibility checks.
7. **Stage 07 — heterogeneous workload contract.** Define batch-size sweeps,
   precision modes, residency/timing boundaries, CUDA-event measurement, memory
   accounting, and CPU baselines before adding GPU numbers.
8. **Stage 08 — C++ CUDA adapter.** Track the evolving GAFro-CUDA API and measure
   its validated device kernels separately as kernel-only, resident-pipeline,
   and end-to-end operations.
9. **Stage 09 — Rust CUDA adapter.** Add measurements after the planned
   feature-gated `cudarc` backend exposes production kernels; keep CPU SoA/SIMD
   batch measurements as distinct baselines.
10. **Stage 10 — CUDA comparison and profiling.** Compare both CUDA adapters on
    the same NVIDIA host, workload manifest, precision, launch policy, and power
    state; publish crossover curves and profiler evidence rather than one peak
    speedup number.
11. **Stage 11 — Rust correctness and orthogonal-layout parity.** Repair the
    blocked Jacobian oracle and connect the orthogonal dense multivector API to
    the canonical dense-product workload.
12. **Stage 12 — Idris robotics parity.** Add validated 2R FK and Jacobian
    adapters, or preserve precise production-API blockers.
13. **Stage 13 — comparable CPU batch parity.** Add C++ and Idris batch adapters
    where production APIs support them; retain scalar baselines and explicit
    capability gaps.
14. **Stage 14 — canonical workload expansion.** Extend coverage to dynamics and
    selected geometric primitives with shared fixtures and output oracles.
15. **Stage 15 — precision and optimization study.** Measure FP32 and FP64
    separately, quantify error/drift, and explain whether optimizations port.

## Completion boundary

The route is complete when each discovered implementation has either validated
results or a machine-readable unsupported/blocked reason for every workload;
all results can be reproduced from recorded commands and revisions; and no
summary compares incompatible observations as if they were equivalent.
