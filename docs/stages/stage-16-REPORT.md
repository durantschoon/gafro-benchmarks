# Stage 16 report: spatial physics, inertia & multi-body robotics parity

## Result

Stage 16 adds canonical spatial physics workloads to the cross-language benchmark suite:
1. `spatial_inertia_action/f64/wrench_checksum`: evaluation of a 6x6 spatial inertia tensor acting on a 6D spatial twist ($W = I \cdot T$).
2. `spatial_inertia_transform/f64/e01_mass`: rigid motor transformation of a spatial inertia tensor ($I' = M I \widetilde{M}$).

The fixtures use canonical mass $m = 2.0\text{ kg}$, principal diagonal moments $I_{xx} = 0.5, I_{yy} = 0.5, I_{zz} = 0.8\text{ kg}\cdot\text{m}^2$, zero off-diagonal inertia products, and a 6D twist with linear velocities $v = [1.0, 2.0, 3.0]\text{ m/s}$ and angular bivectors $w = [w_{12}=0.1, w_{13}=0.2, w_{23}=0.3]\text{ rad/s}$.

### Workload Compatibility Matrix

| Workload | C++ | Idris 2 | Rust |
|---|:---:|:---:|:---:|
| `spatial_inertia_action/f64/wrench_checksum` | supported (6.38 ns) | supported (411.0 ns) | supported (88.17 ns) |
| `spatial_inertia_transform/f64/e01_mass` | supported (346.2 ns) | unsupported: gafro-idris2 does not expose an inertia transformation API | supported (471.5 ns) |

All supported adapters pass the untimed oracle and checksum verification before timing.

### Verification Evidence

- Run ID: `20260830T193812.461448Z`
- `make check`: passed cleanly.
- `make test`: passed cleanly (45 test suites).
- `make benchmark-smoke`: passed across C++, Idris 2, and Rust.

## Changed Files

- `contracts/workloads-v1.json`
- `cpp/bench_cga.cpp`
- `rust/src/main.rs`
- `idris2/src/Main.idr`
- `tests/test_discovery.py`
- `docs/stages/stage-16-PROMPT.md`
- `docs/stages/stage-16-REPORT.md`
- `docs/stages/ROUTE.md`
- `docs/benchmark_parity_roadmap.md`
