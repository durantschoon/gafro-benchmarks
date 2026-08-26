# Stage 05: robotics workload family

## Goal

Add fair forward-kinematics and geometric-Jacobian measurements for every
implementation that exposes semantically equivalent robotics operations.

## Baseline

The legacy C++ and Rust adapters contain nominal 6-DOF FK and Jacobian loops, but
their joint-axis conventions differ and no oracle proves equivalent chains or
outputs. The Idris 2 implementation has no robotics layer. Existing numbers
therefore do not establish an apples-to-apples robotics comparison.

## Required changes

1. Extend the workload manifest with one canonical serial-chain description:
   joint types, ordered axes, fixed frames, composition order, joint vector,
   requested end-effector frame, Jacobian convention, and observed coefficients.
2. Define language-neutral FK and Jacobian oracle outputs, tolerances, matrix
   layout, frame, twist ordering, and sign conventions.
3. Implement the workloads in C++ and any attached Rust revision only after each
   adapter passes the same oracle. Mark Idris 2 unsupported until its library has
   a real robotics API.
4. Separate chain construction from evaluation timing and report allocations
   only where a reliable, documented measurement method exists.
5. Add perturbed joint vectors or a deterministic input sequence so constant
   folding cannot turn the workload into a precomputed answer.
6. Add cross-adapter tests that fail on axis, frame, coefficient-order, or
   operations-per-sample disagreement.
7. Preserve the older third-party robotics benchmark sources as a separate
   legacy suite unless they are individually brought under this same contract.

## Constraints

- Capability parity is required before latency comparison.
- Do not add a benchmark-only robotics implementation to Idris 2.
- Do not call unlike Jacobians equivalent; unsupported is the correct result
  when frame or representation cannot be reconciled.
- Robot/model parsing and heap setup remain outside timed regions.

## Definition of done

- `make check`, `make test`, `make benchmark-smoke`, and `make benchmark` pass
  for every available adapter.
- Every supported robotics result includes a passing oracle; every other adapter
  has a non-empty unsupported reason.
- Generated reports group robotics comparisons only across compatible results.
- `docs/stages/stage-05-REPORT.md` records gates, convention evidence,
  deviations, and open questions.
