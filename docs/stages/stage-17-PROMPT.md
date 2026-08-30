# Stage 17 — CUDA Heterogeneous Adapter Integration & Multi-GPU/CPU Sweeps

## Context

Stages 07–10 established the heterogeneous CPU/CUDA contract, batch sweep schemas, and timing scope boundaries (`kernel`, `resident_pipeline`, `end_to_end`).

With `gafro-cpp` providing high-performance CUDA geometry/robotics kernels (validated on Blackwell RTX PRO 4500) and `gafro-rust` supplying feature-gated `cudarc` PTX batch kernels, Stage 17 integrates heterogeneous GPU planning, CLI batch sweeping, and multi-backend GPU reporting into the central benchmark harness.

## Required work

1. **CLI and Make Targets for GPU Sweeps**:
   - Add `plan-gpu` target to `Makefile` to plan and inspect heterogeneous execution sweeps across latency-sensitive ($1..16$), expected crossover ($32..4096$), and throughput ($16384..262144$) regimes.
   - Support `--cuda-status` (`auto`, `available`, `unavailable`) and custom memory limits.
2. **Supplemental GPU Evidence & Ingestion**:
   - Reconcile verified supplemental NVIDIA GPU run evidence (`artifacts/raw/cpp-cuda-runpod-20260826.json` and Rust `cudarc` PTX kernels) against canonical CPU SoA baselines.
   - Maintain strict separation of kernel-only, resident-pipeline, and end-to-end scopes.
3. **Contract and Harness Tests**:
   - Verify that non-CUDA hosts report clear, structured `unavailable` states without masquerading or generating fake timing samples.
   - Ensure all ratio dimensions (operation, batch size, layout, scalar precision) are enforced before comparing CPU and GPU throughput.
4. **Documentation and Roadmap Updates**:
   - Author `docs/stages/stage-17-REPORT.md`.
   - Update `docs/stages/ROUTE.md` and `docs/benchmark_parity_roadmap.md`.

## Verification

```text
make check
make test
make benchmark-smoke
make plan-gpu
```

## Commit

`bench: integrate CUDA heterogeneous adapter and batch sweep tooling`
