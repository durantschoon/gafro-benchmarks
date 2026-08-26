# Stage 10: controlled CUDA comparison and profiling

## Goal

Publish an auditable comparison of C++ CPU, Rust CPU, C++ CUDA, and Rust CUDA
paths that explains latency, throughput, transfer cost, and hardware utilization
across batch sizes.

## Baseline

Stages 07–09 establish compatible measurements. A single peak throughput ratio
would still obscure launch overhead, transfer amortization, precision, memory
layout, CPU batch optimizations, and the batch size at which GPU execution wins.

## Required changes

1. Run all available CPU and CUDA adapters in one controlled session on the same
   NVIDIA host with fixed workload manifest, GPU persistence/power policy, and
   recorded CPU affinity/thread settings.
2. Randomize or interleave adapter/sample order where practical, include warm-up,
   and capture temperature, clocks, throttling, and run-order metadata so drift
   is visible.
3. Generate batch-size curves for latency per batch, latency per item,
   throughput, and speedup for kernel, resident-pipeline, and end-to-end scopes.
4. Compute and report CPU-to-GPU crossover sizes separately for each language,
   operation, precision, and timing scope; omit them when confidence intervals or
   compatible samples are insufficient.
5. Add Nsight Compute profiles for representative below-crossover,
   near-crossover, and saturated batches. Record achieved occupancy, memory
   throughput, warp efficiency, launch configuration, and the profiler command.
6. Compare C++ CUDA to Rust CUDA only for matching generated math and semantics;
   use profiler evidence to discuss differences without attributing them to the
   host language alone.
7. Generate a reproducibility report containing raw run IDs, revisions, dirty
   patches or hashes, container image digest, hardware/software metadata,
   capability matrix, charts/tables, and limitations.

## Constraints

- Never combine FP32 and FP64 into one ranking.
- Never use kernel-only timing to claim application end-to-end speedup.
- Do not rank results collected on different GPUs or under different power
  limits.
- Profiling runs are diagnostic evidence and remain separate from unprofiled
  timing samples because profilers perturb execution.

## Definition of done

- `make check`, `make test`, `make benchmark-smoke`, and the controlled full-run
  target pass.
- Every published ratio is traceable to compatible raw samples and names its
  timing scope.
- Reports show CPU scalar, CPU batch, CUDA kernel, CUDA resident-pipeline, and
  CUDA end-to-end results distinctly.
- `docs/stages/stage-10-REPORT.md` records run IDs, profiler artifacts, gates,
  deviations, and remaining open questions.
