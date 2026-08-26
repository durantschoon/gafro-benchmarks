# Gafro Cross-Language Benchmark Shootout

Comparative performance evaluation between **Gafro C++26** and **Gafro Rust**.

| Benchmark | C++26 Latency | Rust Latency | C++26 Throughput | Rust Throughput | Relative Speed |
|:---|:---:|:---:|:---:|:---:|:---:|
| `motor_composition_gp` | 6.99 ns | 14.21 ns | 142,969,476 | 70,351,215 | **2.03x faster** |
| `sandwich_point_transform` | 1.04 ns | 160.16 ns | 957,854,406 | 6,243,936 | **154.00x faster** |
| `point_pair_outer_product` | 0.25 ns | 22.87 ns | 3,929,273,084 | 43,726,998 | **91.48x faster** |
| `kinematics_fk_6dof` | 137.90 ns | 100.61 ns | 7,251,842 | 9,939,156 | **1.37x slower** |
| `kinematics_geometric_jacobian_6dof` | 270.82 ns | 664.67 ns | 3,692,544 | 1,504,509 | **2.45x faster** |
