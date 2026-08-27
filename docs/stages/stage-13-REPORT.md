# Stage 13 report: comparable CPU batch parity

## Result

The C++ adapter continues to emit precise unsupported records for the six
contract CPU batch workloads. `gafro-cpp` exposes no production CPU SoA batch
API, and an AoS loop would not be comparable to the contract's device-resident
SoA workload.

Rust continues to use its production SoA batch APIs. Its batch records now carry
the same metadata fields, so comparisons expose layout, SIMD, threading, and
packing assumptions. Scalar rows remain present and unchanged.

Idris 2 remains explicitly unsupported for all six batch workloads. The
production Idris 2 API has no CPU batch/SoA abstraction; the adapter retains
non-empty capability-gap records rather than timing a scalar loop under a batch
name.

## Verification

- `make check` — passed.
- `make test` — passed, 23 tests.
- Explicit-path `make benchmark-smoke` across C++, Idris 2, and Rust — passed; run archive `20260827T140111.922423Z` validated the complete capability matrix.
- `git diff --check` — passed.

## Interpretation and deviations

Rust remains the only supported implementation for these batch IDs. The
capability gap is actionable: add a production C++ SoA type first, then add a
new adapter and validate every output lane. No cross-language winner is claimed
until that happens.

Packing/allocation overhead is not measured in this stage because the contract
declares both excluded. A future packing-inclusive variant should be a separate
workload ID. Idris 2 needs a production batch API before it can participate in
this comparison.

## Changed files

- `rust/src/main.rs`
- `benchmark_harness/cli.py`
- `docs/stages/stage-13-REPORT.md`
