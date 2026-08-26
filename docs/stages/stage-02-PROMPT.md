# Stage 02: C++ reference adapter

## Goal

Produce correctness-checked, optimizer-resistant C++ measurements that establish
the reference observations for the shared workload contract.

## Baseline

`cpp/bench_cga.cpp` runs fixed iteration loops with one wall-clock aggregate.
Its inputs are constant, the loop index is unused, output observation is not
uniformly protected from optimization, and the emitted metadata omits compiler,
flags, revision, samples, and correctness evidence. Its CMake file assumes a
specific sibling layout and labels a C++26 benchmark while the legacy root build
uses C++20.

## Required changes

1. Resolve the C++ implementation from an explicit CMake/cache or CLI path and
   validate the expected headers; do not silently fall back to installed gafro.
2. Implement every Stage 01 workload supported by the checked-out C++ API using
   the exact manifest operands and observation rule.
3. Run untimed oracle checks before sampling, including finite-value checks and
   tolerance comparison to contract reference outputs.
4. Use a defensible anti-optimization boundary and vary inputs according to the
   contract without adding unrelated setup to the timed region.
5. Emit multiple raw samples after warm-up, calibrated or explicitly recorded
   operation counts, and complete compiler/build/revision provenance.
6. Add a deterministic smoke profile and tests that reject wrong oracle values,
   missing benchmark IDs, non-finite metrics, and inconsistent operation counts.
7. Document the supported C++ capability matrix and the exact release build
   command.

## Constraints

- Keep the benchmark adapter in this repository; do not add benchmark-only code
  to `gafro-cpp` unless a public API gap is discovered and separately approved.
- Do not use `volatile` assignment alone as the optimization barrier.
- Do not mix construction/setup with operation timing unless construction is the
  workload named by the contract.
- Use `double` and the tau-based inputs defined by the manifest.

## Definition of done

- `make check`, `make test`, and `make benchmark-smoke` pass.
- `make benchmark IMPLEMENTATIONS=cpp` emits schema-valid raw C++ results and
  does not modify summaries when an oracle fails.
- A clean rebuild records the actual compiler standard and optimization flags.
- `docs/stages/stage-02-REPORT.md` records gates, measurement sanity checks,
  deviations, and open questions.
