# Stage 03 report: Idris 2 benchmark adapter

## Outcome

The contract harness now builds an isolated Idris 2 executable against an
explicit sibling checkout and validates four common binary64 workloads: dense
geometric product, point-pair outer product, motor composition, and motor
application to a point. C++ and Idris 2 observe the same scalar or coefficient
for every shared workload.

The timed loops alternate canonical inputs and reduce every observation into a
scalar accumulator. The accumulator is consumed after the stop timestamp, so
the operations cannot be eliminated; C++ uses the same per-iteration addition.
Fixture construction, oracle checks, JSON encoding, and output are untimed.

## Provenance and build

The successful local build used:

- `gafro-idris2` revision
  `1bf475078ce50832feeab1b55961237136891daa`, clean;
- Idris 2 0.7.0, matching the implementation's pin;
- Chez code generator and Chez Scheme 10.2.0;
- an isolated temporary source, build, and output tree with a link to the
  selected checkout's `src/Gafro` module hierarchy.

Every new Idris module declares `%default total`. The clock, sampling, oracle
failure exit, and `main` functions use `covering` because Idris 2 cannot prove
totality across the `IO` clock/process boundary. No sibling API or source file
was changed.

The local shell process is `x86_64`, while Homebrew's Idris support and RefC
archives are `arm64`. RefC generated its C translation but could not link those
archives, so the working Chez backend was selected instead. Generated C
compiler and flags are recorded as not applicable for this backend; Chez and
RefC results must remain separate series.

## Gates and evidence

The following passed on 2026-08-26:

```text
make check
make test
make benchmark-smoke
make benchmark IMPLEMENTATIONS=cpp,idris2
```

The smoke profile emitted three positive samples for each workload at 1,000
operations per sample. The full profile emitted 15 positive samples for each
workload at 10,000 operations per sample. All four Idris oracle observations
equaled the C++ references: `1.0`, `1.0`, `3.5`, and `1.0` for dense product,
motor composition, point transformation, and point-pair outer product,
respectively.

Raw validated bundles are written to
`artifacts/raw/{cpp,idris2}-{smoke,full}-latest.json`. Tests cover malformed
results, missing IDs, incorrect oracle values, inconsistent operation counts,
missing compiler reporting, totality policy, and provenance arguments.

## Deviations and open questions

- Stage 03 asks for explicit unsupported Idris robotics records, but the current
  manifest contains no robotics workload IDs. Stage 05 owns the canonical
  chain, frame, Jacobian, and observation definitions. Placeholder IDs here
  would violate the permanent rule that every ID fully denotes one operation,
  so unsupported records are deferred until Stage 05 creates those IDs.
- The attached Idris checkout has advanced beyond the prompt baseline and now
  contains robotics modules. They are deliberately not benchmarked early:
  Stage 05 must first establish semantic parity and will decide support from
  the selected revision's actual API.
- Full Idris measurements are slow because the implementation's intentionally
  dense algebra traverses its complete coefficient product. Later reporting
  must present this as representation/backend evidence, not as a claim about
  Idris as a language. The shared full profile was calibrated from 100,000 to
  10,000 operations per sample: each Idris sample remains long enough for a
  stable clock observation, while the full gate remains practical. Both
  adapters use the same revised count.
- The reusable compiler and isolated-sibling build findings were added to the
  envelope-owned Idris 2 learning document and propagated to envelope `main`.
