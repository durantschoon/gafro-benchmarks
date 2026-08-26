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

The language-neutral harness requires Python 3.10 or newer and uses only the
standard library. Inspect validated sibling checkouts, run the contract tests,
and exercise the fast synthetic smoke path with:

```bash
make inventory
make check
make test
make benchmark-smoke
```

Discovery checks `../gafro-{cpp,idris2,rust}` and their Envelope-style nested
checkout directories. Override any location explicitly with `CPP_PATH=...`,
`IDRIS2_PATH=...`, or `RUST_PATH=...`; a path is available only when its
language-specific repository marker is present. The workload manifest and
result schema are versioned under [`contracts/`](contracts/). Capability status
is one of `supported`, `unsupported`, `unavailable`, or `failed`; every status
except `supported` requires a reason.

The contract full benchmark can be invoked with `make benchmark`. It writes
validated raw bundles per implementation and does not overwrite the legacy
summary tables.

### C++ reference adapter

The Stage 02 C++ capability matrix is:

| Workload | Precision | Status | Observable |
| --- | --- | --- | --- |
| Dense geometric product | `double` | Supported | scalar coefficient |
| Motor composition | `double` | Supported | scalar coefficient |
| Motor-point sandwich | `double` | Supported | `e1` coefficient |
| Point-pair outer product | `double` | Supported | `e12` coefficient |

Discovery normally finds the Envelope checkout and its configured build tree.
An explicit clean release run is:

```bash
make benchmark IMPLEMENTATIONS=cpp \
  CPP_PATH=../gafro-cpp/gafro-cpp \
  CPP_BUILD_PATH=../gafro-cpp/gafro-cpp/build \
  CPP_COMPILER=/usr/bin/clang++
```

Validated evidence is written to `artifacts/raw/cpp-full-latest.json` only after
all workload IDs, operation counts, finite samples, and oracle values pass.

### Idris 2 adapter

Stage 03 runs the same four common workloads against the attached
`gafro-idris2` checkout. The adapter requires the implementation's pinned Idris
2 0.7.0 compiler and defaults to the Chez backend. It builds from an isolated
temporary source tree, records revision and dirty state, and keeps encoding and
output outside the timed regions:

```bash
make benchmark IMPLEMENTATIONS=cpp,idris2 \
  IDRIS2_PATH=../gafro-idris2/gafro-idris2 \
  IDRIS2_COMPILER=/opt/homebrew/bin/idris2 \
  IDRIS2_BACKEND=chez
```

Chez and RefC results are separate series. RefC additionally requires a C
compiler and Idris runtime archives matching the host process architecture;
the local mixed-architecture installation cannot link RefC, so it is not used
as a fallback. Robotics capability records are introduced with the canonical
robotics IDs in Stage 05 rather than inventing placeholder operations here.

### Rust CPU and batch adapter

Stage 04 builds against an explicit Cargo checkout and records `rustc`, target,
features, release profile, LTO, codegen units, and `RUSTFLAGS`. It supports the
three convention-compatible scalar workloads plus FP64 `BatchMotorSoA`
composition and `BatchPointSoA` transforms at 16, 256, and 4096 elements.
Packing and unpacking are excluded from these CPU SoA workload IDs.

The dense raw-multivector workload is explicitly unsupported because its
contract operands use orthogonal `ePlus`/`eMinus` coefficients while the Rust
public type uses null `e0`/`eInf` coefficients. Equal array indices would not
denote equal multivectors. Run all current adapters with:

```bash
make benchmark IMPLEMENTATIONS=cpp,idris2,rust \
  RUST_PATH=../gafro-rust/gafro-rust
```

C++ and Idris report the Rust-specific CPU SoA IDs as unsupported. Robotics is
reconciled in Stage 05 and CUDA in Stage 07, once those contracts exist.

Supplemental optimized C++ CUDA evidence is available in
[`artifacts/raw/cpp-cuda-runpod-20260826.json`](artifacts/raw/cpp-cuda-runpod-20260826.json).
It contains 15 CUDA-event samples for point-cloud transforms, warp- and
thread-per-robot kinematics/Jacobians, and batch inverse kinematics, collected
from revision `cb9969a` on a Runpod RTX PRO 4500 Blackwell. These are explicitly
kernel-only measurements and are not cross-language comparable until the
heterogeneous contract in benchmark Stage 07 is implemented.

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
