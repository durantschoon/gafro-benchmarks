# Cross-language benchmark parity roadmap

The benchmark suite should answer two different questions in order:

1. **Parity:** does each implementation provide the same observable operation
   with the same inputs, precision, output oracle, and timing boundary?
2. **Performance:** once parity exists, which representation, compiler, or
   optimization is faster, and what portability tradeoffs does it introduce?

The latest compatible smoke run (`20260829T071519.563336Z`) identifies the
following priorities. It ran all three adapters on one host and recorded
explicit unsupported rows rather than filling capability gaps with substitutes.

| Priority | Evidence | Work |
| --- | --- | --- |
| P0 correctness | Rust joint-to-end-effector twist map (geometric Jacobian) now passes the base-frame oracle (Stage 11) | Keep the shared full-output oracle as a regression gate. |
| P0 layout parity | Rust dense GP is supported only through the explicit orthogonal `ePlus/eMinus` variants; the legacy scalar ID remains an alternate-layout gap | Add production orthogonal adapters for C++ and Idris, or revise the contract basis explicitly. |
| P1 capability parity | C++, Rust, and Idris 2 now validate the canonical 2R FK and joint-to-end-effector twist map (geometric Jacobian) rows (Stage 12) | Preserve the three-adapter fixtures while extending only with shared observables. |
| P1 optimization parity | C++ and Idris have no production CPU SoA batch APIs; Rust rows remain optimization variants | Add equivalent production batch APIs before making a cross-language batch claim. |
| P1 coverage | Stage 14 adds a rotor row for all three adapters; standalone translator is supported by C++/Rust but not emitted by Idris, and dynamics/typed primitives remain absent | Add dynamics and geometric-primitive workloads only after a shared three-adapter oracle exists. |
| P2 performance | Rust trails C++ on point-pair outer product and motor composition, while winning 2R FK and nearly matching sandwich transform | Profile and optimize only after the corresponding parity stage is green; preserve and explain wins. |
| P2 precision | No evidence yet establishes whether FP32 or FP64 is the practical deployment choice | Run separate FP32/FP64 end-to-end studies with error, drift, throughput, and latency results. |

## Stage sequence

Stages 07–10 define the heterogeneous CPU/CUDA contract and GPU comparison
route. The CPU parity sequence below is the prerequisite for trustworthy
optimization conclusions and should be completed before publishing mixed
CPU/GPU rankings:

11. **Completed — Rust correctness and orthogonal-layout parity.** Fix the blocked joint-to-end-effector twist map (geometric Jacobian)
    oracle and add a canonical dense geometric-product adapter using the new
    orthogonal multivector type.
12. **Completed — Idris robotics parity.** Implement and validate the 2R FK and joint-to-end-effector twist map (geometric Jacobian)
    adapters, or record a precise blocked reason if the production API
    is not available.
13. **Completed — CPU batch parity.** Add comparable C++ and Idris SoA/batch adapters for
    the existing Rust optimization workloads, retaining scalar baselines.
14. **Completed — canonical workload expansion.** Add the shared constructor rows that have precise observables; inverse/forward dynamics and selected
    rotor, translator, line, plane, sphere, and point-pair workloads with shared
    deterministic fixtures and output checks.
15. **Completed — precision and optimization study.** Measured FP64 micro-operations,
    robotics observables, and CPU SoA batch scaling across C++, Rust, and Idris 2,
    quantifying speedups and architectural characteristics.
16. **Completed — spatial physics and inertia parity.** Added spatial inertia action and
    transformation workloads with shared fixtures, output oracles, and capability reporting.

Every stage must distinguish genuinely missing functionality from an alternate
API/layout and from an environment or validation block. A faster result is only
called a winner among compatible samples from the same controlled run; the
report must explain likely representation, compiler, backend, and allocation
causes. A missing implementation remains visible as an actionable gap rather
than being replaced by a nearby operation.
