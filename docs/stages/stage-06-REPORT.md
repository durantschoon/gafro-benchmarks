# Stage 06 report: reproducible aggregation and reporting

## Outcome

Benchmark execution now creates a unique append-only directory under
`results/runs/`. Each run contains the exact manifest, runner configuration and
path overrides, host/toolchain metadata, raw adapter stdout, stdout/stderr logs,
validated adapter bundles, repository revisions and dirty flags, diagnostics,
and JSON/Markdown derived from one pure summary model. A failed run preserves
its evidence and does not publish a comparison. `benchmark_harness.cli report
--run-id` deterministically regenerates reports from the saved evidence.

The model retains all ns/op samples and counts, reports median and unscaled MAD,
and calculates named ratios from unrounded medians. It fills the complete C++,
Idris 2, and Rust capability matrix with explicit blocked cells. Host mismatch
suppresses ratios and apparent winners. Any winner is labeled as applying only
to the compatible run, with representation/compiler/backend as likely causes;
it is not a significance claim.

Canonical scalar GA and robotics operations are primary. SoA/SIMD batch rows
are explicit optimization variants and cannot replace canonical results. Their
interpretation calls out layout, batch size, and amortization. GPU experiments
remain outside this CPU report until Stage 07 defines compatible residency and
timing boundaries.

Capability gaps are actionable metadata, classified as equivalent supported,
alternate API/layout, genuinely missing, or blocked validation/environment.
Each gap records whether an existing algorithm can guide a port, the adapter or
production API work required, and tradeoffs in correctness, conversion and
allocation cost, SIMD/GPU portability, API complexity, and maintenance.

## Published evidence

- Full run `20260827T094539.804842Z`: 15 samples for each supported workload,
  all C++, Idris 2, and Rust cells recorded.
- Smoke run `20260827T094320.444494Z`: 3 samples for each supported workload;
  byte-for-byte deterministic JSON regeneration verified with `cmp`.
- Failed discovery run `20260827T094308.050354Z`: intentionally preserved; its
  diagnostic records that the isolated worktree could not discover a C++
  sibling without explicit overrides.

The full-run canonical medians include C++/Rust motor composition at
1.0417/2.9334 ns/op, point transform at 6.7084/5.7250 ns/op, outer product at
0.6916/21.1083 ns/op, and 2R FK at 82.5750/38.5625 ns/op. These are local run
evidence only. Idris 2 results use its current dense representation and Chez
backend; Rust batch results are separate SoA optimization variants.

## Gates and commands

The following passed on 2026-08-27 from the isolated worktree:

```text
make check
make test
make benchmark-smoke CPP_PATH=/Users/durant/Repos/enveloped/gafro-cpp/gafro-cpp CPP_BUILD_PATH=/Users/durant/Repos/enveloped/gafro-cpp/gafro-cpp/build IDRIS2_PATH=/Users/durant/Repos/enveloped/gafro-idris2/gafro-idris2 IDRIS2_COMPILER=/opt/homebrew/bin/idris2 RUST_PATH=/Users/durant/Repos/enveloped/gafro-rust/gafro-rust
make benchmark IMPLEMENTATIONS=cpp,idris2,rust CPP_PATH=/Users/durant/Repos/enveloped/gafro-cpp/gafro-cpp CPP_BUILD_PATH=/Users/durant/Repos/enveloped/gafro-cpp/gafro-cpp/build IDRIS2_PATH=/Users/durant/Repos/enveloped/gafro-idris2/gafro-idris2 IDRIS2_COMPILER=/opt/homebrew/bin/idris2 RUST_PATH=/Users/durant/Repos/enveloped/gafro-rust/gafro-rust
python3 -m benchmark_harness.cli report --run-id 20260827T094320.444494Z
cmp /tmp/stage06-summary-before.json results/runs/20260827T094320.444494Z/report/summary.json
```

The first unqualified `make benchmark-smoke` failed with `no validated
CMakeLists.txt checkout` because an isolated `/private/tmp` worktree has no
sibling implementations. It created the preserved failed run listed above;
the explicit-path invocation then passed.

The outer repository instructions also request `make markdownlint`. It could
not run because this repository's Makefile has no `markdownlint` target: `make:
*** No rule to make target 'markdownlint'. Stop.` `git diff --check` passed as
the available Markdown/whitespace sanity check; it is not treated as a
substitute gate.

## Deviations and open questions

- `docs/envelope_project_context.md` named by the outer repository instructions
  is not present in this benchmark repository/worktree. The committed stage
  architecture, route, prompt, and Stage 05 report were used as context.
- Adapter build subprocess output still streams to the invoking terminal;
  adapter process stdout/stderr, which contain the primary raw result evidence,
  are archived. Capturing verbose compiler output as an additional log would be
  useful but is not required to reconstruct the measured bundles.
- The legacy preview remains in the README but is now prominently labeled
  historical and non-reproducible; no legacy value was promoted into a
  generated report.
- Cross-run aggregation is represented by `input_run_ids` in the pure model;
  the current CLI regenerates one archived run at a time. A later interface may
  combine selected run IDs while retaining the same compatibility policy.
