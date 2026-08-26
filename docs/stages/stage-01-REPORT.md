# Stage 01 report: benchmark contract and harness foundation

## Outcome

Stage 01 adds a standard-library-only Python contract core, an imperative CLI
boundary, validated implementation discovery, fixtures/tests, stable Make gates,
and versioned workload/result contracts. Existing result files remain unchanged.

## Contract and architecture

- `contracts/workloads-v1.json` defines canonical workload IDs, operands,
  binary64 numeric type, warm-up counts, operations per sample, and observable
  coefficients.
- `contracts/result-v1.schema.json` documents implementation/revision/dirty
  identity, compiler/backend/flags, host metadata, capability state, raw sample
  durations, operation counts, and oracle output.
- `benchmark_harness/core.py` contains pure parsing, validation,
  reconciliation, and deterministic summary planning. Filesystem access,
  discovery, subprocess execution, and CLI output remain in `cli.py`.
- `supported`, `unsupported`, `unavailable`, and `failed` are distinct; all
  non-supported observations require a non-empty reason.

## Discovery deviation

The prompt says the Rust checkout is currently missing. That observation became
stale: `../gafro-rust/gafro-rust/Cargo.toml` now exists. Discovery therefore
reports that validated nested checkout as available. The legacy benchmark's
Cargo dependency still targets the non-package Envelope root; later adapter
stages will replace that assumption.

## Verification

Run from this repository root:

```text
make check
make test
make benchmark-smoke
make inventory
```

The smoke path is synthetic by design, requires no language compiler, and
exercises supported, unsupported, and unavailable results.

## Open questions

- Later stages must pin exact fixture operands and oracle tolerances as adapters
  replace the legacy loops.
- The legacy full benchmark remains behind `make benchmark` until Stage 02 and
  Stage 04 migrate C++ and Rust respectively.
