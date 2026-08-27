# Stage 11: Rust correctness and orthogonal-layout parity

## Motivation

Run `20260827T094539.804842Z` reports Rust dense geometric product as an
`alternate_api_or_layout` and blocks Rust geometric-Jacobian ranking because the
base-frame oracle fails. The Rust library now provides an orthogonal dense
multivector type; this stage connects it to the canonical benchmark contract.

## Required changes

1. Correct the Rust geometric-Jacobian adapter or production call so each joint
   axis includes its joint-origin transform in the declared base frame.
2. Add a Rust canonical dense geometric-product adapter using the orthogonal
   `ePlus/eMinus` layout, with explicit conversion boundaries if conversion is
   needed by the production API.
3. Preserve the existing null-basis adapter and report conversion-inclusive and
   conversion-free measurements as distinct workload variants.
4. Add full-output oracle checks and capability metadata for every new variant.

## Allowed files

- `rust/src/main.rs`
- `rust/Cargo.toml`
- `rust/Cargo.lock`
- `contracts/workloads-v1.json`
- `benchmark_harness/**`
- `tests/**`
- `docs/stages/stage-11-REPORT.md`

## Definition of done

- `make check`
- `make test`
- `make benchmark-smoke`
- Rust FK and geometric-Jacobian oracle checks pass.
- Dense GP is either directly comparable or has an explicit, non-empty blocked
  reason naming the remaining boundary.
- A report records revisions, commands, timings, conversion/allocation scope,
  deviations, and open questions.

## Commit

`bench: restore Rust robotics correctness and orthogonal GP parity`
