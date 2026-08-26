# Stage 04: Rust CPU and batch adapter

## Goal

Replace the stale Rust benchmark assumptions with a correctness-checked adapter
for the attached implementation, covering both scalar operations and the CPU
batch optimizations exposed by the selected revision.

## Baseline

`../gafro-rust/gafro-rust` is now attached at revision `fdad7cc` plus unrelated
in-progress working-tree changes. The committed implementation includes sparse
multivector indexing, closed-form motor composition, `BatchMotorSoA`, manifold
normalization, and fused kinematics. Additional `BatchPointSoA` and remote GPU
tooling changes are currently uncommitted and belong to their author; preserve
them. The Cargo package does not yet expose a `cuda` feature.

## Required changes

1. Validate the selected Rust repository by Cargo metadata and record its
   revision and dirty state; accept a CLI path override rather than embedding a
   machine-specific absolute path.
2. Scout its public API and publish a capability map against every contract
   workload before changing the adapter.
3. Update `rust/Cargo.toml` and the adapter to the real package/API. Implement
   only supported workloads with the canonical inputs and observations.
4. Use release builds with recorded rustc version, target, feature set, profile,
   codegen units, LTO, and relevant `RUSTFLAGS`.
5. Add untimed oracle checks, `std::hint::black_box` or an equally documented
   barrier, multiple raw samples, and schema-valid output.
6. Add distinct scalar and CPU-batch workload IDs. For batch operations, sweep
   canonical sizes and include packing/unpacking only in explicitly named
   end-to-end variants.
7. Emit explicit unsupported records for absent algebra, rigid-motion, robotics,
   or CUDA capabilities and add adapter/schema/oracle tests.
8. Remove tracked Rust build artifacts from future source control only after
   confirming they are generated and recoverable; document the cleanup.

## Constraints

- Preserve all pre-existing Rust working-tree changes; do not stage, rewrite, or
  incorporate them implicitly.
- Do not alter the Rust implementation API merely to match the stale adapter
  without a separate, justified implementation change.
- Do not label missing capabilities as benchmark failures or zero-duration
  results.
- Keep dependency locking reproducible and report any lockfile update.

## Definition of done

- `make check`, `make test`, and `make benchmark-smoke` pass.
- `make benchmark IMPLEMENTATIONS=cpp,idris2,rust` produces validated results or
  explicit capability statuses for every workload.
- `docs/stages/stage-04-REPORT.md` records repository identity and dirty state,
  gates, capabilities, deviations, and open questions.
