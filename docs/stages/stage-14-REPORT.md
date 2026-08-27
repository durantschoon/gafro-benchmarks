# Stage 14 report — canonical workload expansion

## Scope and inventory

The shared fixture is a unit z-axis quarter-turn (`axis=[0,0,1]`, `angle=pi/2`)
and displacement `[1,2,3]`, both IEEE binary64. Production inventory found
axis-angle rotor and displacement translator constructors in gafro-cpp and
gafro-rust, and the translator constructor in gafro-idris2. Idris 2's rotor
constructor requires a fallible, non-exported `UnitBivector` construction path,
so its gap is reported explicitly. Existing point-pair and robotics rows were
left unchanged. Dynamics and typed line/plane/sphere observables remain
deferred because no shared three-adapter oracle was found.

## Workloads and compatibility

| Workload | C++ | Rust | Idris 2 |
|---|---|---|---|
| `rotor_construction/f64/scalar` | supported | supported | unsupported: no exposed deterministic `UnitBivector` constructor |
| `translator_construction/f64/e1i` | supported | supported | supported |

Each supported adapter validates the scalar oracle before timing; the C++ and
Rust implementations also inspect the remaining translator coefficients.
These are canonical constructor workloads, not layout or batch variants.

## Verification

`make check` passed. `make test` passed (23 tests). The full smoke benchmark
compiled and ran all three adapters successfully after correcting an initial
Rust/C++ axis-coefficient convention mismatch. Run ID:
`20260827T172841.744506Z`.

No timing ranking is reported: this stage establishes compatible coverage;
measurements from the failed aggregate run are not evidence.

## Follow-up gaps

Add an exported total Idris rotor fixture constructor (or a fixture-level
oracle that does not require the private unit-bivector constructor), then add
forward/inverse dynamics and typed line, plane, and sphere observables only
after equivalent production APIs and complete-output oracles exist.
