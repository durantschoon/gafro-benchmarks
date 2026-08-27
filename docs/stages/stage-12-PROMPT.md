# Stage 12: Idris 2 robotics parity

## Motivation

The latest report marks Idris 2 FK and joint-to-end-effector twist map (geometric Jacobian) workloads as
`genuinely_missing`: no canonical robotics adapter has been validated against
the shared 2R chain and oracle. This stage closes that capability gap without
substituting a non-equivalent calculation.

## Required changes

1. Inspect the selected Idris 2 production API and implement a language-native
   2R FK adapter if the required operations exist.
2. Implement the matching base-frame joint-to-end-effector twist map (geometric Jacobian) adapter, including the
   same joint-origin convention used by the C++ and Rust oracle.
3. Add deterministic fixtures and full-output oracle checks before timing.
4. If production functionality is unavailable, retain an explicit
   `genuinely_missing` or `blocked_validation_or_environment` record with the
   exact missing API and a porting path.

## Allowed files

- `idris2/**`
- `contracts/workloads-v1.json`
- `benchmark_harness/**`
- `tests/**`
- `docs/stages/stage-12-REPORT.md`

## Definition of done

- `make check`
- `make test`
- `make benchmark-smoke`
- Idris FK and joint-to-end-effector twist map (geometric Jacobian) results pass the shared 2R oracle, or the report
  documents an evidenced blocker rather than a synthetic timing value.
- No unsupported record is silently converted into a timing result.
- The report records compiler/backend provenance, commands, deviations, and
  open questions.

## Commit

`bench: add Idris 2 canonical robotics adapters`
