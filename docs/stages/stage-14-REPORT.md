# Stage 14 report — canonical workload expansion

## Scope and inventory

The shared fixture is a unit z-axis quarter-turn (`axis=[0,0,1]`, `angle=pi/2`)
and displacement `[1,2,3]`, both IEEE binary64. Production inventory and the
latest smoke evidence confirm the axis-angle rotor constructor in all three
adapters. C++ and Rust emit the standalone translator-construction row; the
Idris adapter uses translators internally but does not yet emit that dedicated
row. Existing point-pair and robotics rows were left unchanged. Dynamics and
typed line/plane/sphere observables remain deferred because no shared
three-adapter oracle was found.

## Workloads and compatibility

| Workload | C++ | Rust | Idris 2 |
|---|---|---|---|
| `rotor_construction/f64/scalar` | supported | supported | supported |
| `translator_construction/f64/e1i` | supported | supported | unsupported: Idris adapter does not emit a standalone translator row |

Each supported adapter validates the scalar oracle before timing; the C++ and
Rust implementations also inspect the remaining translator coefficients.
These are canonical constructor workloads, not layout or batch variants.

## Verification

`make check`, `make markdownlint`, and `make test` passed (44 tests). The latest
default smoke benchmark compiled and ran all three adapters successfully after
the Idris rotor fixture was changed to the native fallible axis constructor.
Run ID: `20260829T071519.563336Z`.

The run recorded C++ revision `5aebbf3`, Idris 2 revision `3215c8f`, and Rust
revision `145e95e`. It contains seven supported Idris rows, including the
rotor and both robotics observables; its translator and new orthogonal-GP rows
remain explicit unsupported records.

No timing ranking is reported: this stage establishes compatible coverage;
measurements from the failed aggregate run are not evidence.

## Follow-up gaps

Add the standalone Idris translator row, forward/inverse dynamics, and typed
line, plane, and sphere observables only after equivalent production APIs and
complete-output oracles exist. FP32 and directly comparable CUDA measurements
remain future stages.
