# Gafro Multi-Language Benchmarks

A language-agnostic performance evaluation suite for **Gafro** implementations across C++26, Rust, and third-party Geometric Algebra and robotics libraries.

---

## Architecture

This repository benchmarks:
- **Core CGA Algebraic Operations**:
  - Geometric Product ($A B$)
  - Outer / Wedge Product ($A \wedge B$)
  - Sandwich Product ($M A \tilde{M}$)
  - Motor Composition ($M_1 M_2$)
- **Robotics & Spatial Kinematics**:
  - Serial multi-joint Forward Kinematics (FK)
  - Geometric Jacobian evaluations
- **Standards & Specifications**:
  - Strictly $\tau$-based calculations ($\tau = 2\pi$).
  - Full details in [`PORTING_AND_STANDARDS.md`](PORTING_AND_STANDARDS.md).
  - GA Notation Reference: [durantschoon/wedgeGA-symbols](https://github.com/durantschoon/wedgeGA-symbols).

---

## Directory Structure

```
gafro-benchmarks/
├── runner/
│   └── run_all.py            # Central cross-language shootout orchestrator
├── cpp/
│   ├── CMakeLists.txt        # C++26 benchmark build
│   └── bench_cga.cpp         # C++26 benchmarks (gafro-cpp)
├── rust/
│   ├── Cargo.toml            # Rust benchmark build
│   └── src/main.rs           # Rust benchmarks (gafro-rust)
└── results/
    ├── benchmark_summary.json # Standardized JSON metrics
    └── benchmark_summary.md   # Formatted markdown shootout table
```

---

## Running the Cross-Language Shootout

To build and run all benchmarks and generate side-by-side comparison tables:

```bash
python3 runner/run_all.py
```

### Individual Runs

**C++26 Benchmark**:
```bash
cd cpp
cmake -B build -S . && cmake --build build -j10
./build/bench_cga_cpp         # Terminal table
./build/bench_cga_cpp --json  # Machine-readable JSON
```

**Rust Benchmark**:
```bash
cd rust
cargo run --release           # Terminal table
cargo run --release -- --json # Machine-readable JSON
```

---

## Benchmark Results Preview

| Benchmark | C++26 Latency | Rust Latency | C++26 Throughput | Rust Throughput |
|:---|:---:|:---:|:---:|:---:|
| `motor_composition_gp` | 6.28 ns | 127.67 ns | 159,146,972 ops/s | 7,832,811 ops/s |
| `sandwich_point_transform` | 1.02 ns | 440.67 ns | 984,251,969 ops/s | 2,269,263 ops/s |
| `point_pair_outer_product` | 0.25 ns | 49.54 ns | 3,937,007,874 ops/s | 20,186,167 ops/s |
| `kinematics_fk_6dof` | 135.54 ns | 925.05 ns | 7,378,005 ops/s | 1,081,023 ops/s |
| `kinematics_geometric_jacobian_6dof` | 273.44 ns | 2275.51 ns | 3,657,056 ops/s | 439,463 ops/s |

---

## License

MPL-2.0 License.