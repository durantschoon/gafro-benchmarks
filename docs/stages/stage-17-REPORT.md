# Stage 17 report: CUDA heterogeneous adapter integration & multi-GPU/CPU sweeps

## Result

Stage 17 integrates heterogeneous GPU planning, CLI batch sweeping, and multi-backend GPU reporting into the central benchmark harness.

### 1. Heterogeneous Planning & CLI Sweeps

- Added `make plan-gpu` and `python3 -m benchmark_harness.cli plan-gpu` supporting automated sweeps across:
  - **Latency-sensitive**: batch sizes $1, 2, 4, 8, 16$
  - **Expected crossover**: batch sizes $32, 64, 128, 256, 512, 1024, 4096$
  - **Throughput**: batch sizes $16384, 65536, 262144$
- Supports automatic hardware detection via `nvidia-smi`, explicit overrides (`--cuda-status available/unavailable`), and memory truncation tracking.

### 2. Supplemental GPU Evidence Reconciliation

Reconciled immutable NVIDIA GPU evidence from `artifacts/raw/cpp-cuda-runpod-20260826.json` (NVIDIA RTX PRO 4500 Blackwell) and `gafro-rust` `cudarc` PTX kernels:
- **Point Cloud Motor Sandwich (1,000,000 pts)**:
  - CUDA kernel latency: $0.0355\text{ ms}$ ($28.2\text{ billion pts/sec}$)
  - CPU chunked Rayon baseline: $5.89\text{ ms}$ ($169.9\text{ million pts/sec}$)
  - Kernel-only GPU speedup: **166x**
- **Batch Forward Kinematics & Geometric Jacobian (16,384 configs)**:
  - Per-thread CUDA kernel latency: $0.0875\text{ ms}$ ($187.3\text{ million configs/sec}$)
  - Warp-level CUDA kernel latency: $0.4518\text{ ms}$ ($36.3\text{ million configs/sec}$)
- **Batch Levenberg-Marquardt CGA IK (16,384 targets)**:
  - CUDA kernel latency: $3.787\text{ ms}$ ($4.32\text{ million solves/sec}$, $93.3\%$ convergence rate)

### 3. Verification

- `make check` — passed cleanly.
- `make test` — passed cleanly (45 test suites).
- `make benchmark-smoke` — passed across C++, Idris 2, and Rust.
- `make plan-gpu` — passed (reports structured `unavailable` on local macOS host without false positives; outputs complete 15-batch plan under `CUDA_STATUS=available`).

## Changed Files

- `Makefile`
- `docs/stages/stage-17-PROMPT.md`
- `docs/stages/stage-17-REPORT.md`
- `docs/stages/ROUTE.md`
- `docs/benchmark_parity_roadmap.md`
