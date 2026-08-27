# Stage 11 report — Rust correctness and orthogonal-layout parity

## Outcome

Stage 11 connects the Rust benchmark adapter to the new orthogonal dense
multivector API and restores the canonical 2R joint-to-end-effector twist map
(geometric Jacobian) workload. The existing legacy dense-GP ID remains an
explicit alternate-layout capability gap; two explicit orthogonal variants are
now measured instead:

- `dense_geometric_product/f64/orthogonal`: resident orthogonal operands;
- `dense_geometric_product/f64/orthogonal_conversion`: explicit conversion at
  both API boundaries.

The Rust Jacobian adapter now applies each joint origin transform before
placing its axis in the base frame. Its checksum passes the shared `5.0`
oracle. C++ and Idris adapters receive explicit unsupported records for the new
workload IDs when their legacy adapters do not emit those IDs.

## Verification

Commands run from the isolated Stage 11 worktree:

```text
make check
make test
make benchmark-smoke CPP_PATH=/Users/durant/Repos/enveloped/gafro-cpp/gafro-cpp CPP_BUILD_PATH=/Users/durant/Repos/enveloped/gafro-cpp/gafro-cpp/build IDRIS2_PATH=/Users/durant/Repos/enveloped/gafro-idris2/gafro-idris2 IDRIS2_COMPILER=/opt/homebrew/bin/idris2 RUST_PATH=/Users/durant/Repos/ds/gafro-rust
git diff --check
```

Results:

- `make check`: passed (`compileall`, inventory, and contract/discovery tests).
- `make test`: passed, 23 tests.
- `make benchmark-smoke`: passed for all three adapters.
- Successful run archive: `20260827T131213.701549Z`.
- Rust adapter-only smoke run: `20260827T131152.345151Z`.

The successful run used the explicit sibling paths above and rebuilt the Rust
adapter against Rust revision `6051ab9`. The Rust output contained 14 workload
records: the legacy dense ID is explicitly unsupported, the two orthogonal
dense IDs and the repaired Jacobian are supported, and existing workloads
remain present.

## Review findings and fixes

1. The initial implementation declared `2.0` for the dense-GP oracle although
   the contract reference is `1.0`; corrected before acceptance.
2. The initial Rust smoke path aborted when a very small batch measured as
   `0 ns`; durations now clamp to the contract minimum of `1 ns` rather than
   emitting an invalid sample.
3. The initial implementation omitted the legacy dense workload record,
   causing complete-run reconciliation to fail. It now preserves an explicit
   alternate-layout unsupported record.
4. Cargo lockfile regeneration is performed after substituting the selected
   Rust checkout, avoiding stale placeholder-path failures in isolated builds.

## Deviations

- The full-run result archive is not required for this stage; only the smoke
  run was published. Timing values are smoke evidence and are not a new
  performance ranking.
- The legacy dense workload remains non-comparable because its contract ID does
  not declare a basis. Stage 14/15 may revise the contract after the orthogonal
  API has established the intended canonical representation.
- Rust emits a dead-code warning only if the unsupported helper is removed from
  use; no new warning is treated as a gate failure. Repository-wide Clippy has
  known pre-existing warnings outside this stage.

## Open questions

- Should the benchmark contract rename the legacy dense ID to make its basis
  explicit, or should the orthogonal resident variant become the canonical ID?
- Should sub-nanosecond batch smoke measurements use a larger smoke operation
  count instead of the current `1 ns` lower bound?
- The next parity stage should add Idris 2 canonical robotics adapters before
  comparing optimization or precision choices.
