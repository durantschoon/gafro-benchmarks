# Stage 14 — Canonical workload expansion

## Context

Stages 11–13 established scalar, robotics, and CPU-batch parity. The next
roadmap item is coverage of operations used in real geometric-algebra and
robotics workloads. This stage adds a small, deterministic set of canonical
workloads, with shared semantics and output validation across the adapters.

The goal is capability parity first. A representation-specific optimization,
layout, or convenience wrapper is not a substitute for an operation with the
same mathematical inputs and observable output. If an implementation lacks a
production API, emit an explicit `unsupported` result with an actionable
reason; do not fabricate an adapter from a different operation.

## Required work

1. Inventory the production APIs and existing deterministic fixtures available
   to the C++, Rust, and Idris 2 adapters for:
   - rotor construction/application;
   - translator construction/application;
   - line, plane, and sphere construction or a documented primitive
     observable;
   - point-pair construction/observable (extend the existing point-pair row
     only if a distinct canonical operation is needed); and
   - one spatial-physics operation (for example, a spatial-inertia
     twist-to-wrench action) and forward/inverse dynamics only where a shared
     production API and oracle can be demonstrated.
2. Add only fixture-backed workload IDs that have a precise mathematical
   definition, numeric type, operation count, observable output, tolerance,
   and oracle in `contracts/workloads-v1.json`. Keep canonical workloads
   separate from `batch_` optimization variants and from alternate layouts.
3. Implement the selected workloads in each adapter whose production API
   supports the exact semantics. Validate the complete output needed by the
   contract before timing. For unavailable functionality, add explicit
   unsupported rows through the existing harness path and name the missing
   API or blocked oracle.
4. Add or update focused contract/reporting tests so malformed workload rows,
   missing adapter results, and unsupported reasons remain detectable.
5. Write `docs/stages/stage-14-REPORT.md` with the API/fixture inventory,
   workload compatibility matrix, oracle-validation evidence, smoke results,
   and interpretation of any compatible timing differences. Call out any
   implementation that appears faster only because it uses a different
   representation or does less work. List deferred dynamics or primitive
   operations as actionable follow-up gaps.

## Allowed files

- `contracts/workloads-v1.json`
- `benchmark_harness/**`
- `cpp/**`
- `rust/**`
- `idris2/**`
- `tests/**`
- `docs/stages/stage-14-REPORT.md`

Do not modify sibling repositories, generated benchmark runs, or unrelated
documentation. Do not change existing workload semantics or remove existing
unsupported records.

## Verification and definition of done

From the repository root, run and record:

```text
make check
make test
make benchmark-smoke
```

The stage is complete when every new workload has either a validated result
from at least one adapter or an explicit, precise capability gap; all produced
rows pass the result schema and oracle checks; the three gates pass; and the
report contains no cross-representation ranking. Use commit message:
`bench: expand canonical workload coverage`.

If a required production API or oracle cannot be found, stop at the boundary,
record the evidence and exact missing dependency in the report, and leave the
gap visible for a later implementation stage.
