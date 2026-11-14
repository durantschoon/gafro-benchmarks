# Gafro Cross-Language Benchmark Shootout

Comparative performance evaluation between **Gafro C++26**, **Gafro Rust**,
**gafro-julia** and **gafro-fstar** (F*/Low*, extracted to C by KaRaMeL).

The F* column is measured inside an OrbStack machine in a pinned Guix toolchain,
not natively on the host; no ratio against it is offered, because such a ratio
would cross a virtualisation boundary rather than compare two languages.

| Benchmark | C++26 Latency | Rust Latency | Julia Latency | F* Latency (in-VM) | Relative Speed (C++/Rust) | Relative Speed (C++/Julia) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `spatial_inertia_action/f64/wrench_checksum` | absent | absent | 1416.92 | absent | **n/a** | **n/a** |
| `spatial_inertia_transform/f64/e01_mass` | absent | absent | 9527.42 | absent | **n/a** | **n/a** |
| `dense_geometric_product/f64/scalar` | absent | absent | 7204.18 | absent | **n/a** | **n/a** |
| `dense_geometric_product/f64/orthogonal` | absent | absent | unsupported | absent | **n/a** | **n/a** |
| `dense_geometric_product/f64/orthogonal_conversion` | absent | absent | unsupported | absent | **n/a** | **n/a** |
| `motor_composition_gp/f64/scalar` | absent | absent | 515.34 | absent | **n/a** | **n/a** |
| `sandwich_point_transform/f64/e1` | absent | absent | 2335.03 | absent | **n/a** | **n/a** |
| `point_pair_outer_product/f64/e12` | absent | absent | 322.69 | absent | **n/a** | **n/a** |
| `rotor_construction/f64/scalar` | absent | absent | 196.73 | absent | **n/a** | **n/a** |
| `translator_construction/f64/e1i` | absent | absent | 7.70 | absent | **n/a** | **n/a** |
| `batch_motor_composition/f64/n16/scalar_lane0` | absent | absent | 27.74 | absent | **n/a** | **n/a** |
| `batch_motor_composition/f64/n256/scalar_lane0` | absent | absent | 22.70 | absent | **n/a** | **n/a** |
| `batch_motor_composition/f64/n4096/scalar_lane0` | absent | absent | 31.32 | absent | **n/a** | **n/a** |
| `batch_point_transform/f64/n16/e1_lane0` | absent | absent | 4.21 | absent | **n/a** | **n/a** |
| `batch_point_transform/f64/n256/e1_lane0` | absent | absent | 6.59 | absent | **n/a** | **n/a** |
| `batch_point_transform/f64/n4096/e1_lane0` | absent | absent | 3.23 | absent | **n/a** | **n/a** |
| `robotics_forward_kinematics_2r/f64/motor_checksum` | absent | absent | 1577.51 | absent | **n/a** | **n/a** |
| `robotics_geometric_jacobian_2r/f64/base_checksum` | absent | absent | 59960.48 | absent | **n/a** | **n/a** |
