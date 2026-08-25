# Gafro Multi-Language Porting, Standards & Specification

This document establishes the architecture, standards, testing protocols, and mathematical conventions for all implementations and ports of **Gafro** across different programming languages (C++, Rust, Python, Julia, etc.).

---

## 1. Unified Cross-Language JSON Test Suite (`test_fixtures/`)

To guarantee 100% mathematical consistency, numerical precision, and algorithmic equivalence across all language implementations:

- **Single Source of Truth**: All implementations (C++, Rust, Python, etc.) must consume and validate against the same canonical JSON test fixtures in [`test_fixtures/`](./test_fixtures).
- **Test Coverage**:
  - **Basis Blades & Algebra Definition** ([`cga3d_blades.json`](./test_fixtures/cga3d_blades.json)): Canonical null basis $\{e_0, e_\infty\}$, Euclidean basis $\{e_1, e_2, e_3\}$, 32 basis blade bitmaps, grades, and Poincaré dual pairings.
  - **Exhaustive Cayley Tables** ([`cga3d_algebra_operations.json`](./test_fixtures/cga3d_algebra_operations.json)): All $32 \times 32 = 1,024$ basis blade combinations for Geometric Product ($A B$), Outer Product ($A \wedge B$), and Inner Product ($A \cdot B$), as well as multivector reversion, conjugation, and norms.
  - **Geometric Primitives** ([`cga3d_primitives.json`](./test_fixtures/cga3d_primitives.json)): CGA Points, Lines, Planes, Spheres, and Circles.
  - **Motors & Transformations** ([`cga3d_motors.json`](./test_fixtures/cga3d_motors.json)): Rotors, Translators, Rigid Motors, Lie algebra bivector exponentials $\exp(B)$, and sandwich product applications.
  - **Spatial Physics & Mechanics** ([`cga3d_physics.json`](./test_fixtures/cga3d_physics.json)): Spatial Twists, Spatial Wrenches, Inertia Tensors, and momentum transformations.
  - **Robotic Kinematics** ([`cga3d_kinematics.json`](./test_fixtures/cga3d_kinematics.json)): Multi-joint serial kinematics, forward kinematic motor compositions, and Jacobians.

### Port Compliance Requirement
Any pull request or new language port must include an automated test harness that parses these JSON fixtures and asserts that all operations produce outputs within floating-point tolerance ($\epsilon \le 10^{-7}$).

---

## 2. Language-Agnostic Benchmarking Architecture

The benchmarking suite will start from [idiap/gafro_benchmarks](https://github.com/idiap/gafro_benchmarks) and be restructured into a language-agnostic performance suite:

- **Standardized Workloads**:
  - 10,000 to 1,000,000 geometric products of arbitrary multivectors.
  - Rigid body motor composition ($M_1 M_2 M_3 \dots$).
  - Transformation / sandwich products on point clouds ($M P \tilde{M}$).
  - Multi-body robot forward kinematics and geometric Jacobian evaluations.
  - Twist / wrench / inertia spatial mechanics transformations.
- **Output Format**:
  - All benchmarks will emit structured JSON/CSV metrics:
    ```json
    {
      "language": "rust",
      "implementation": "gafro-rs",
      "compiler": "rustc 1.85",
      "benchmark": "geometric_product_dense",
      "iterations": 1000000,
      "total_time_ns": 4210500,
      "time_per_op_ns": 4.21,
      "allocations": 0
    }
    ```
- **Cross-Language Comparison**: A centralized runner will execute and plot performance comparisons across C++, Rust, Python/C-bindings, Julia, etc.

---

## 3. Geometric Algebra Symbols & Notation Preferences

Geometric Algebra notation across literature varies widely. For this project and its ports, symbol preferences, wedge replacements, and operator notations are tracked in:

- **Author's GA Symbols & Notation Reference**:
  - [durantschoon/wedgeGA-symbols](https://github.com/durantschoon/wedgeGA-symbols)

- **Basis & Naming Conventions**:
  - Null basis vectors are denoted $e_0$ (origin) and $e_\infty$ / $e_i$ (infinity).
  - Spatial Euclidean vectors are $e_1, e_2, e_3$.
  - Bivectors and multi-blade combinations use concatenated indices (e.g. $e_{12}, e_{13}, e_{23}, e_{0123\infty}$).
- **Operator Notation**:
  - Geometric Product: juxtaposition or `*` ($A B$)
  - Outer (Wedge) Product: $\wedge$ or `^` ($A \wedge B$) (subject to updates per [wedgeGA-symbols](https://github.com/durantschoon/wedgeGA-symbols))
  - Inner (Dot / Contraction) Product: $\cdot$ or `|` ($A \cdot B$)
  - Reversion: $\tilde{A}$ or `~A`
  - Conjugation / Spatial Inversion: $\bar{A}$ or `A.conjugate()`
  - Sandwich Action: $M A \tilde{M}$ or `motor.apply(A)`

---

## 4. Mandatory Tau-Based Calculations ($\tau = 2\pi$)

All angular calculations, rotational mathematics, and joint limits in all repositories and ports are strictly **$\tau$-based**:

$$\tau = 2\pi \approx 6.283185307179586476925286766559\dots$$

### Principles:
1. **1 Turn $= \tau$**: Rotations are naturally measured in fractions of a full circle turn:
   - Full rotation: $\tau$ ($360^\circ$)
   - Three-quarter rotation: $\frac{3\tau}{4}$ ($270^\circ$)
   - Half rotation: $\frac{\tau}{2}$ ($180^\circ$)
   - Quarter rotation (right angle): $\frac{\tau}{4}$ ($90^\circ$)
   - Eighth rotation: $\frac{\tau}{8}$ ($45^\circ$)
2. **Rotor Construction**:
   - For a unit bivector generator $\hat{B}$ and angle of rotation $\theta$:
     $$R = \cos\left(\frac{\theta}{2}\right) - \sin\left(\frac{\theta}{2}\right) \hat{B}$$
   - When $\theta = \tau/4$ ($90^\circ$), $\frac{\theta}{2} = \tau/8$ ($45^\circ$), giving equal scalar and bivector weights $\frac{\sqrt{2}}{2} \approx 0.70710678$.
3. **No Raw $\pi$ References**:
   - Codebases and test suites must define and use $\tau$ (`gafro::math::tau` in C++, `std::f64::consts::TAU` in Rust, `math.tau` in Python) rather than legacy $\pi$ formulas.
