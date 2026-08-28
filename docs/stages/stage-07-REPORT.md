# Stage 07 report: heterogeneous CPU/CUDA workload contract

## Result

The benchmark contract now records the dimensions needed for honest CPU/CUDA
comparisons: operation, batch semantics and size, precision, input/output
layout, deterministic fixture identity, complete output cardinality, warm/cold
state, packing/allocation boundaries, residency, streams, and timing scope.

CPU scalar and optimized-batch rows share the `application_end_to_end`
comparison scope with GPU `end_to_end` rows. A ratio is permitted only when all
semantic and boundary dimensions match. CUDA kernel-only and device-resident
pipeline rows remain distinct and cannot masquerade as CPU application speedup.

The result contract validates CUDA-event timing and checked synchronization for
kernel/device-resident scopes, host timing with packing, transfers, execution,
observation, and synchronization for end-to-end scope, complete pre-timing
oracles, FP32/FP64 tolerances, and CPU/GPU provenance. The CLI can produce a
deterministic GPU sweep or a clean unavailable plan without CUDA hardware.

## Verification

- `make check` — passed.
- `make test` — passed, 40 tests.
- `git diff --check` — passed.
- `make markdownlint` — unavailable in this benchmark subrepository: `make: *** No rule to make target 'markdownlint'. Stop.` The Stage 07 prompt's discovered gates are `make check`, `make test`, and `make benchmark-smoke`.
- `make benchmark-smoke CPP_PATH=/Users/durant/Repos/enveloped/gafro-cpp/gafro-cpp CPP_BUILD_PATH=/Users/durant/Repos/enveloped/gafro-cpp/gafro-cpp/build IDRIS2_PATH=/Users/durant/Repos/enveloped/gafro-idris2/gafro-idris2 IDRIS2_COMPILER=/opt/homebrew/bin/idris2 RUST_PATH=/Users/durant/Repos/ds/gafro-rust IDRIS2_BACKEND=chez`
  — passed for C++, Idris 2, and Rust; run
  `20260828T105630.526424Z` produced all three validated adapter bundles.

## Deviations and open questions

- Existing v1 adapter rows remain valid without `execution` metadata so prior
  evidence stays readable. A mixed legacy/heterogeneous pair is never directly
  ratio-compatible.
- Independent review tightened the initial checkpoint: heterogeneous evidence
  is now bound to a manifest execution contract and definition digest, every
  timing scope has exact phases, high-precision oracle completion is explicit,
  and stream/GPU configuration participates in compatibility and reporting.
- Stages 08–10 still require production CUDA kernels and a controlled NVIDIA
  host. Stage 07 defines and validates the comparison boundary; it does not
  invent benchmark-only kernels.
- CPU/GPU comparison requires a CPU row at the same batch size and with matching
  packing/allocation semantics. Existing scalar rows are not silently promoted
  into such baselines.
