# Stage 16 — Spatial Physics, Inertia & Multi-Body Robotics Parity

## Context

Stages 01–15 established foundational algebra, rigid transformations, forward kinematics, geometric Jacobians, CPU SoA batching, and precision studies across C++, Rust, and Idris 2.

The next major capability family is spatial physics and inertia dynamics. In 3D Conformal Geometric Algebra, spatial physics maps 6D twists (angular and linear velocities) to 6D spatial wrenches (torques and forces) via a 6x6 spatial inertia tensor ($W = I \cdot T$). Furthermore, spatial inertia tensors transform under rigid motors ($I' = M I \widetilde{M}$).

This stage integrates spatial inertia action and spatial inertia transformation into the canonical workload suite with deterministic fixtures, exact mathematical oracles, and explicit capability accounting across C++, Rust, and Idris 2.

## Required work

1. **Contract and Workload Definitions**:
   Add the following canonical spatial physics workloads to `contracts/workloads-v1.json`:
   - `spatial_inertia_action/f64/wrench_checksum`:
     - Evaluates spatial inertia tensor acting on a spatial twist producing a spatial wrench ($W = I \cdot T$).
     - Canonical fixture: mass $m = 2.0\,\text{kg}$, diagonal principal moments $I_{xx} = 0.5, I_{yy} = 0.5, I_{zz} = 0.8\,\text{kg}\cdot\text{m}^2$, off-diagonal products $0.0$.
     - Canonical twist: linear velocity $v = [1.0, 2.0, 3.0]\,\text{m/s}$, angular velocity components $w_{12} = 0.1, w_{13} = 0.2, w_{23} = 0.3\,\text{rad/s}$.
     - Output oracle: wrench coordinates $[f_1=2.0, f_2=4.0, \tau_{12}=0.08, f_3=6.0, \tau_{13}=0.10, \tau_{23}=0.15]$.
     - Checksum observable: sum of 6 coordinates $= 12.33$.
   - `spatial_inertia_transform/f64/e01_mass`:
     - Evaluates spatial inertia tensor transformation under translation motor $M = \text{translator}([1.0, 2.0, 3.0])$.
     - Output oracle and observable: element 0 (linear mass along $e_{01}$) remains $2.0$.

2. **Adapter Implementations**:
   - **C++ Adapter (`cpp/bench_cga.cpp`)**:
     - Connect `gafro::Inertia<double>`, `gafro::Twist<double>`, and `gafro::Wrench<double>`.
     - Implement both `spatial_inertia_action` and `spatial_inertia_transform`.
   - **Rust Adapter (`rust/src/main.rs`)**:
     - Connect `gafro::physics::Inertia`, `gafro::physics::Twist`, and `gafro::physics::Wrench`.
     - Implement both `spatial_inertia_action` and `spatial_inertia_transform`.
   - **Idris 2 Adapter (`idris2/src/Main.idr`)**:
     - Connect `Gafro.Robotics.Physics` (`Twist`, `Wrench`, `SpatialInertia`, `applyInertia`) to implement `spatial_inertia_action`.
     - Emit an explicit `unsupported` record for `spatial_inertia_transform` documenting the lack of inertia transformation API in `Gafro.Robotics.Physics`.

3. **Harness & Contract Tests**:
   - Update contract test suites in `tests/test_contract.py` and `tests/test_discovery.py` to validate the new physics workloads and oracles.

4. **Report & Roadmap Updates**:
   - Author `docs/stages/stage-16-REPORT.md`.
   - Update `docs/stages/ROUTE.md` and `docs/benchmark_parity_roadmap.md`.

## Verification

```text
make check
make test
make benchmark-smoke
```

## Commit

`bench: implement spatial physics and inertia parity workloads`
