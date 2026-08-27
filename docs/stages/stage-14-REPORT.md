# Stage 14 report — canonical workload expansion

## Inventory and result

The adapter inventory found production support for translator construction and
application, rotor-backed motor composition, point-pair construction, and the
existing 2R kinematics operations. Those semantics are already represented by
the canonical contract rows and were not duplicated under new IDs. The C++,
Rust, and Idris benchmark entry points do not currently expose one shared,
fixture-backed line/plane/sphere observable or a common spatial-inertia
twist-to-wrench/dynamics operation. Adding a timing row without that shared
observable would measure different work, so no new incompatible rows were
introduced.

The actionable gaps are therefore:

| Capability | Status | Follow-up |
| --- | --- | --- |
| Rotor/translator | covered by existing motor and sandwich rows | keep as canonical baselines |
| Point-pair | covered by existing outer-product row | add a distinct construction row only with a shared fixture |
| Line/plane/sphere | no common production observable in all adapters | expose constructors/coordinates and fixture first |
| Spatial inertia and forward/inverse dynamics | no common benchmark API/oracle | agree on state, frame, and wrench output before timing |

No cross-representation ranking is made in this stage. The gaps remain visible
for the next implementation stage rather than being replaced by nearby
operations.

## Verification

The contract and existing adapters were checked with the required repository
gates:

- `make check` — passed
- `make test` — passed
- `make benchmark-smoke` — C++ built, but the gate stopped at the existing Rust
  adapter because the checked-out sibling API no longer exports
  `OrthogonalMultivector32`, has two generic parameters for the SoA types, and
  exposes ambiguous `Motor::compose` implementations. This is an existing
  cross-repository compatibility block, not a Stage 14 workload change.
- `git diff --check` — passed

No generated benchmark run artifacts are included in the commit.
