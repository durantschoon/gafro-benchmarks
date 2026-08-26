# Stage 01: benchmark contract and harness foundation

## Goal

Replace the current two-program shootout assumptions with a tested,
language-neutral contract and an orchestrator that can discover all sibling
implementations without hard-coded developer-machine paths.

## Baseline

The repository has handwritten C++ and Rust loops and a Python runner. The
runner assumes both implementations exist at fixed relative paths, consumes one
aggregate timing per benchmark, intersects workloads implicitly from the C++
side, and overwrites committed summaries. There are no harness tests or stable
Make gates. The current Rust dependency path resolves to the `../gafro-rust`
Envelope worktree, which presently has no Cargo package attached.

## Required changes

1. Define a versioned workload manifest containing canonical IDs, operands,
   numeric type, warm-up policy, measured operation count, and the scalar or
   coefficient used as the observable result.
2. Define and document a versioned result schema with implementation identity,
   repository revision, dirty-state flag, compiler/backend and flags, host
   metadata, capability status, warm-up count, operations per sample, raw sample
   durations, and oracle output.
3. Implement pure Python parsing, validation, capability reconciliation, and
   summary planning separately from subprocess and filesystem operations.
4. Add CLI path overrides for C++, Idris 2, and Rust. Discovery may suggest
   sibling defaults but must validate repository markers before building.
5. Represent `supported`, `unsupported`, `unavailable`, and `failed` distinctly,
   with a non-empty reason for every non-supported result.
6. Add fixture-driven unit tests for malformed JSON, duplicate benchmark IDs,
   schema mismatch, missing implementations, workload mismatch, and deterministic
   report ordering.
7. Add a Makefile with `check`, `test`, `benchmark-smoke`, and `benchmark` targets;
   document prerequisites and usage in the README.

## Constraints

- Use only the Python standard library for the orchestration core unless a
  dependency is justified in the report.
- Do not time subprocess startup or JSON serialization as workload execution.
- Do not modify sibling implementation repositories in this stage.
- Do not treat existing committed benchmark numbers as a correctness oracle.
- Preserve current result files until the new generator can replace them from
  validated raw evidence.

## Definition of done

- `make check`, `make test`, and `make benchmark-smoke` pass from the benchmark
  repository root.
- Smoke mode completes quickly and exercises success, unsupported, and missing
  implementation paths without requiring every compiler to be installed.
- The CLI inventory names all three implementation families and accurately
  reports the currently missing Rust checkout.
- `docs/stages/stage-01-REPORT.md` records gates, changes, deviations, and open
  questions.
