# Gafro Cross-Language Benchmark Shootout

Comparative performance evaluation between **Gafro C++26** and **Gafro Rust** (incorporating modernization stages 01–15).

## 1. Workload Comparison Matrix

| Benchmark | C++26 Latency | Rust Latency | C++26 Throughput | Rust Throughput | Relative Speed | Target / Execution Mode |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| `motor_composition_gp` | 6.26 ns | 18.41 ns | 159,744,409 | 54,320,518 | **2.94x faster (C++)** | Single-threaded microbench (FP64) |
| `sandwich_point_transform` | 1.00 ns | 13.26 ns | 995,024,876 | 75,389,787 | **13.26x faster (C++)** | Single-threaded microbench (FP64) |
| `point_pair_outer_product` | 0.25 ns | 32.04 ns | 3,984,063,745 | 31,211,209 | **128.16x faster (C++)** | Single-threaded microbench (FP64) |
| `kinematics_fk_6dof` | 135.29 ns | 95.66 ns | 7,391,311 | 10,454,109 | **1.41x faster (Rust)** | Serial 6-DOF robot forward kinematics (FP64) |
| `kinematics_geometric_jacobian_6dof` | 264.30 ns | 658.68 ns | 3,783,637 | 1,518,193 | **2.49x faster (C++)** | Serial 6-DOF geometric Jacobian matrix (FP64) |
| `fused_fk_and_jacobian_6dof` | N/A | 598.41 ns | N/A | 1,671,095 | **Rust-only fused pass** | Single-pass joint kinematics + Jacobian (FP64) |
| `batch_motor_soa_per_motor` | N/A | 7.98 ns (f64) / 2.77 ns (f32) | N/A | 125,374,802 / 361,010,830 | **Rust SIMD SoA** | Structure-of-Arrays batch motor composition |
| `batch_point_transform_parallel_rayon` | N/A | 5.89 ns | N/A | 169,913,891 | **Rust Multi-Core** | 1,000,000 point cloud chunked Rayon execution |
| `kinematics_fk_batch_parallel_rayon` | N/A | 33.09 ns | N/A | 30,224,803 | **Rust Multi-Core** | 100,000 configuration batch Rayon execution |

---

## 2. FP32 vs FP64 Precision & Drift Findings

1. **Throughput Scaling in SIMD SoA**:
   - `BatchMotorSoA<f32>` achieves **2.77 ns/motor** vs **7.98 ns/motor** for `BatchMotorSoA<f64>` (**4.36x speedup** on vector batching).
   - Scalar microbenchmarks exhibit comparable latency across FP32 and FP64 due to 64-bit native ALU word size on 64-bit architectures.
2. **Projective Normalization Drift**:
   - Over 10,000 continuous sequential sandwich transformations without renormalization, single-precision (FP32) introduces significant Euclidean drift ($\approx 20.0\text{ m}$ accumulation) compared to FP64 ($< 10^{-12}\text{ m}$).
   - **Recommendation**: Retain FP64 for open-loop robotics kinematic integration and state estimation; use FP32 for batched point cloud perception with periodic motor normalization.

---

## 3. Multi-Core Rayon Scaling (1M Point Cloud)

| Thread Count | Latency / Pt | Batch Latency | Throughput | Parallel Efficiency |
|:---:|:---:|:---:|:---:|:---:|
| 1 thread | 6.25 ns | 6.25 ms | 159.9M pts/sec | 100% (Baseline) |
| 2 threads | 4.26 ns | 4.26 ms | 234.9M pts/sec | 73.4% |
| 4 threads | 4.64 ns | 4.64 ms | 215.6M pts/sec | Memory bandwidth limited |
| 8 threads | 5.08 ns | 5.08 ms | 196.8M pts/sec | Memory bandwidth limited |
| 10 threads | 5.76 ns | 5.76 ms | 173.6M pts/sec | Memory bandwidth limited |
