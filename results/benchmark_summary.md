# Gafro Cross-Language Benchmark Shootout

Comparative performance evaluation between **Gafro C++26** and **Gafro Rust**.

| Benchmark | C++26 Latency | Rust Latency | C++26 Throughput | Rust Throughput | Relative Speed |
|:---|:---:|:---:|:---:|:---:|:---:|
| `motor_composition_gp` | 6.28 ns | 127.67 ns | 159,146,972 | 7,832,811 | **20.33x faster** |
| `sandwich_point_transform` | 1.02 ns | 440.67 ns | 984,251,969 | 2,269,263 | **432.03x faster** |
| `point_pair_outer_product` | 0.25 ns | 49.54 ns | 3,937,007,874 | 20,186,167 | **198.16x faster** |
| `kinematics_fk_6dof` | 135.54 ns | 925.05 ns | 7,378,005 | 1,081,023 | **6.82x faster** |
| `kinematics_geometric_jacobian_6dof` | 273.44 ns | 2275.51 ns | 3,657,056 | 439,463 | **8.32x faster** |
