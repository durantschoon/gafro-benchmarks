# Stage 08: C++ CUDA benchmark adapter

## Goal

Benchmark production GAFro-CUDA operations under the Stage 07 contract while
tracking the CUDA API as it evolves from device-clean algebra to batch kernels.

## Entry prerequisite

The selected `gafro-cpp` revision must expose production kernels for at least one
contract workload. The current revision provides CUDA configuration and a device
correctness test, but not the planned batch point-transform, FK, or Jacobian
kernels. Until a production kernel exists, write a BLOCKED report rather than
benchmarking the verification kernel as representative throughput.

## Required changes

1. Record C++ revision/dirty state, CUDA toolkit, nvcc host compiler, architecture
   flags, optimization flags, and all GAFRO CUDA build options.
2. Add a C++ CUDA adapter for each genuinely supported contract workload and
   capability records for the remainder.
3. Allocate and initialize reusable buffers outside timed scopes; implement the
   contract's kernel, resident-pipeline, and end-to-end variants exactly.
4. Use CUDA events on the measured stream for device timing and explicit stream
   synchronization before reading results. Record launch geometry and dynamic
   shared memory.
5. Validate every GPU output against the same canonical CPU reference across all
   batch sizes and precision modes before collecting samples.
6. Add leak/error checks around CUDA allocation, launch, event, and transfer
   calls; failures produce diagnostics, never timing values.
7. Integrate remote execution through an explicit host/profile configuration and
   pull immutable raw result bundles back to the benchmark repository.

## Constraints

- Do not modify or overwrite in-progress C++ CUDA work from this repository.
- C++20 device compilation and C++26 host compilation are recorded separately.
- No unified-memory result may be labeled explicit-transfer end-to-end.
- Do not include first-use context/JIT cost in warm measurements; report a
  separate cold-start measurement if useful.

## Definition of done

- `make check`, `make test`, and `make benchmark-smoke` pass locally.
- On an NVIDIA host, the selected C++ CUDA tests and benchmark profiles pass and
  produce schema-valid, oracle-checked raw samples.
- Results include matching C++ scalar and CPU-batch baselines from the same host.
- `docs/stages/stage-08-REPORT.md` records remote commands, hardware/toolchain
  identity, run IDs, gates, deviations, and open questions.
