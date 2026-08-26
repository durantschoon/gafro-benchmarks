# Gafro Cross-Language Benchmark Shootout

Comparative performance evaluation between **Gafro C++26** and **Gafro Rust**.

| Benchmark | C++26 Latency | Rust Latency | C++26 Throughput | Rust Throughput | Relative Speed |
|:---|:---:|:---:|:---:|:---:|:---:|
| `motor_composition_gp` | 6.26 ns | 11.54 ns | 159,744,409 | 86,650,731 | **1.84x faster** |
| `sandwich_point_transform` | 1.00 ns | 156.25 ns | 995,024,876 | 6,399,985 | **156.25x faster** |
| `point_pair_outer_product` | 0.25 ns | 22.65 ns | 3,984,063,745 | 44,147,511 | **90.60x faster** |
| `kinematics_fk_6dof` | 135.29 ns | 102.37 ns | 7,391,311 | 9,768,527 | **1.32x slower** |
| `kinematics_geometric_jacobian_6dof` | 264.30 ns | 663.25 ns | 3,783,637 | 1,507,716 | **2.51x faster** |
