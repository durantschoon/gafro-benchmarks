# Stage 13: comparable CPU batch parity

## Motivation

Rust currently reports SoA batch workloads, while C++ and Idris are explicitly
missing contract CPU batch APIs. These are useful optimization experiments, but
they cannot establish portability until all implementations use the same batch
semantics, precision, layout, and output oracle.

## Required changes

1. Define the batch contract for motor composition and point transformation,
   including batch sizes, lane observation, packing, allocation boundaries, and
   operation counts.
2. Add C++ and Idris adapters only where production APIs can satisfy that
   contract; otherwise preserve precise unsupported records.
3. Keep scalar-loop measurements alongside batch measurements. Batch rows remain
   optimization variants and never replace canonical scalar rows.
4. Validate every output buffer against the same high-precision reference before
   collecting samples.
5. Record SIMD target, thread count, alignment, and allocation/packing costs.

## Allowed files

- `cpp/**`
- `idris2/**`
- `rust/**`
- `contracts/workloads-v1.json`
- `benchmark_harness/**`
- `tests/**`
- `docs/stages/stage-13-REPORT.md`

## Definition of done

- `make check`
- `make test`
- `make benchmark-smoke`
- Each batch size has either compatible results for at least two
  implementations or a non-empty capability-gap reason.
- Reports distinguish per-batch latency, per-item latency, throughput, and
  packing/allocation overhead.
- The report records whether any apparent batch winner is attributable to layout,
  SIMD, compiler, or amortization rather than language alone.

## Commit

`bench: establish cross-language CPU batch parity`
