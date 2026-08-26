# Stage 04 report: Rust CPU and batch adapter

## Outcome

The Rust adapter now uses the selected checkout's real Cargo package and emits
contract results for scalar rigid-motion operations and FP64 CPU SoA batches.
Batch motor composition and point transformation sweep 16, 256, and 4096
elements, with construction, packing, and unpacking outside timed regions.
Every supported result performs an untimed oracle check and uses
`std::hint::black_box` plus an observed scalar accumulator.

## Repository and capability audit

The selected checkout was clean at
`dfa8e66d6625a5d039e911e949738973cd0e1e19`. This differs from the prompt's
older, dirty `fdad7cc` baseline: the previously in-progress batch point and
precision work is now committed. Cargo metadata identifies package `gafro`
0.1.0 and no `cuda` feature.

| Contract area | Status | API evidence |
| --- | --- | --- |
| Dense raw geometric product | Unsupported | Rust uses null `e0`/`eInf`, unlike the contract's orthogonal layout |
| Motor composition | Supported | `Motor::compose` |
| Motor-point application | Supported | `Motor::apply` |
| Point-pair outer product | Supported | `Multivector32::outer_product` |
| FP64 CPU SoA motor batch | Supported | `BatchMotorSoA<f64, N>::compose` |
| FP64 CPU SoA point batch | Supported | `BatchPointSoA<f64, N>::transform` |
| Robotics | Deferred | Real API exists; Stage 05 owns convention parity |
| CUDA | Unsupported | Cargo metadata exposes no `cuda` feature |

The dense workload is not approximated by reinterpreting equal array indices;
that would change the operands while retaining the benchmark ID.

## Toolchain and build

The adapter uses default features and a locked release build. The toolchain is
rustc 1.97.1 targeting `aarch64-apple-darwin`; the release profile records
optimization level 3, fat LTO, one codegen unit, panic abort, and effective
`RUSTFLAGS`. The lockfile was refreshed because the selected revision added
`wide` to `gafro`'s direct dependencies.

The orchestrator copies the adapter into an isolated temporary directory,
substitutes the explicit implementation path there, and uses an isolated Cargo
target directory. It does not edit or build inside the Rust checkout.

## Gates and evidence

The following passed on 2026-08-26:

```text
make check
make test
make benchmark-smoke
make benchmark IMPLEMENTATIONS=cpp,idris2,rust
```

Validated raw bundles are written under `artifacts/raw/`. Tests cover
per-workload operation accounting, missing and incorrect oracles, capability
status requirements, batch adapter presence, and recorded build settings.
The full Rust bundle contains 15 positive samples for each of nine supported
workloads: 10,000 operations per scalar sample and 16,384 elements per batch
sample. Dense algebra is the sole explicit Rust capability gap. C++ and Idris
each emit six non-empty unsupported records for the Rust-specific CPU SoA IDs.

## Deviations and open questions

- The baseline revision and dirty-state warning are stale; the selected checkout
  is newer and clean, so there were no user Rust changes to preserve.
- Robotics and CUDA records cannot precede their canonical IDs without violating
  the permanent ID contract. Stage 05 and Stage 07 add them respectively.
- Batch IDs measure already-packed CPU SoA operations. End-to-end variants
  remain separate future workloads rather than silently including conversion.
