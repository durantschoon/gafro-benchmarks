# Stage 03: Idris 2 benchmark adapter

## Goal

Add Idris 2 as a first-class benchmark implementation for the common algebra and
rigid-motion surface, with its backend and runtime provenance made explicit.

## Baseline

`../gafro-idris2/gafro-idris2` provides dense multivectors, geometric and outer
products, points, rotors, translators, motors, composition, and object
application. It does not yet provide kinematic chains or Jacobians. Its project
is pinned to Idris 2 0.7.0 and requires `%default total` in source modules.

## Required changes

1. Add an Idris benchmark package and executable in this repository that imports
   the sibling package without editing its public API.
2. Implement the contract workloads supported by the existing API: at minimum a
   dense geometric product, point-pair outer product, motor composition, and
   motor application to a point, where semantic parity is confirmed.
3. Emit schema-valid JSON without placing encoding or output inside timed
   regions. Record Idris compiler version, selected code generator, generated C
   compiler/version and flags when applicable, implementation revision, and
   dirty state.
4. Add untimed oracle checks against the Stage 02 reference observations and
   explicit unsupported records for robotics workloads.
5. Prevent elimination of measured work using an Idris-appropriate observable
   accumulator whose cost is either outside timing or identically specified by
   the contract.
6. Add smoke and full profiles through the central Make targets, plus tests for
   JSON validity, capability reporting, and oracle failure.
7. Document backend-specific reproducibility limits and append any newly learned
   compiler behavior to the Idris repository's `IDRIS2_LESSONS.md` only if that
   repository is intentionally changed as a separately reported mutation.

## Constraints

- All new Idris modules declare `%default total`; disclose any unavoidable
  `covering` boundary.
- No robotics facsimile is introduced in the benchmark adapter.
- Do not compare Idris results produced by different backends as one continuous
  series.
- Preserve the implementation's pinned Idris 2 version check.

## Definition of done

- `make check`, `make test`, and `make benchmark-smoke` pass with the Idris
  adapter available, and missing-tool behavior is reported clearly otherwise.
- `make benchmark IMPLEMENTATIONS=cpp,idris2` produces schema-valid results with
  equal oracle observations for every shared workload.
- Robotics workloads appear as explicit `unsupported` records for Idris 2.
- `docs/stages/stage-03-REPORT.md` records gates, backend/toolchain provenance,
  deviations, and open questions.
