# Stage 12 Report: Idris 2 robotics parity

## Result

Implemented the canonical two-revolute-joint robotics adapters in
`idris2/src/Main.idr` using the production `Gafro.Robotics.Kinematics` API:

- `forwardKinematics` produces the motor checksum workload.
- `spatialAxes` produces the base-frame joint-to-end-effector twist map
  (geometric Jacobian) checksum workload.
- The shared chain uses two z-axis revolute joints and fixed `(0, 1, 0)` link
  translations, matching the contract and the C++/Rust adapters.
- Invalid axis normalization remains an explicit non-supported path; no
  synthetic timing is emitted.

The discovery test was updated to assert the native API symbols used by the
adapter rather than the former unsupported-capability explanation.

## Oracle evidence

The Idris adapter compiled with Idris 2 `0.7.0`, Chez backend, and emitted:

- `robotics_forward_kinematics_2r/f64/motor_checksum`: `-1.414213562373095`
- `robotics_geometric_jacobian_2r/f64/base_checksum`: `5.0`

Both match the manifest tolerances. The full-output oracle is checked before
timing by the adapter's `measure` function.

## Verification

- `make check` — passed.
- `make test` — passed, 23 tests.
- `make benchmark-smoke CPP_PATH=/Users/durant/Repos/ds/gafro-cpp IDRIS2_PATH=/Users/durant/Repos/ds/gafro-idris2 RUST_PATH=/Users/durant/Repos/ds/gafro-rust IDRIS2_BACKEND=chez` — passed for C++, Idris 2, and Rust. The run used Idris 2 `0.7.0` and Chez and validated both robotics oracles.
- `git diff --check` — passed.

The smoke command produced disposable run directories; they were removed and
are not part of this commit.

## Deviations and open questions

The production Idris API exposes spatial axes as a `Vect` of multivectors,
not a matrix type. The adapter computes the contract's matrix checksum by
reading the six documented twist coefficients from each spatial axis. This
preserves the mathematical workload while respecting the native API.

The remaining batch workloads are intentionally unsupported because the
production API has no CPU SoA batch type. A later batch stage should add and
measure that representation separately from these canonical scalar results.
