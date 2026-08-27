# Cross-language benchmark parity roadmap

The benchmark suite should answer two different questions in order:

1. **Parity:** does each implementation provide the same observable operation
   with the same inputs, precision, output oracle, and timing boundary?
2. **Performance:** once parity exists, which representation, compiler, or
   optimization is faster, and what portability tradeoffs does it introduce?

The latest compatible run (`20260827T094539.804842Z`) identifies the following
priorities:

| Priority | Evidence | Work |
| --- | --- | --- |
| P0 correctness | Rust joint-to-end-effector twist map (geometric Jacobian) is blocked by a base-frame oracle failure | Repair joint-origin placement and re-run the oracle before ranking Rust. |
| P0 layout parity | Rust dense GP is reported as `alternate_api_or_layout` because the contract uses orthogonal `ePlus/eMinus` coefficients | Add the Rust orthogonal-layout adapter and measure conversion-free and conversion-inclusive paths separately. |
| P1 capability parity | Idris 2 has no validated 2R robotics adapter | Add canonical FK and joint-to-end-effector twist map (geometric Jacobian) adapters with shared oracle fixtures. |
| P1 optimization parity | C++ and Idris have no contract CPU SoA batch APIs | Add equivalent batch adapters only after scalar semantics are validated; keep them labeled optimization variants. |
| P1 coverage | The harness does not yet measure all commonly exposed operations | Add canonical dynamics and geometric-primitive workloads where at least one production implementation can provide an oracle. |
| P2 performance | Rust trails C++ on point-pair outer product and motor composition, while winning 2R FK and nearly matching sandwich transform | Profile and optimize only after the corresponding parity stage is green; preserve and explain wins. |
| P2 precision | No evidence yet establishes whether FP32 or FP64 is the practical deployment choice | Run separate FP32/FP64 end-to-end studies with error, drift, throughput, and latency results. |

## Stage sequence

Stages 07–10 define the heterogeneous CPU/CUDA contract and GPU comparison
route. The CPU parity sequence below is the prerequisite for trustworthy
optimization conclusions and should be completed before publishing mixed
CPU/GPU rankings:

11. **Rust correctness and orthogonal-layout parity.** Fix the blocked joint-to-end-effector twist map (geometric Jacobian)
    oracle and add a canonical dense geometric-product adapter using the new
    orthogonal multivector type.
12. **Idris robotics parity.** Implement and validate the 2R FK and joint-to-end-effector twist map (geometric Jacobian)
    adapters, or record a precise blocked reason if the production API
    is not available.
13. **CPU batch parity.** Add comparable C++ and Idris SoA/batch adapters for
    the existing Rust optimization workloads, retaining scalar baselines.
14. **Canonical workload expansion.** Add inverse/forward dynamics and selected
    rotor, translator, line, plane, sphere, and point-pair workloads with shared
    deterministic fixtures and output checks.
15. **Precision and optimization study.** Run separate FP32 and FP64 studies,
    quantify numerical error/drift, identify real-world winners and losses, and
    document whether each optimization is portable across implementations.

Every stage must distinguish genuinely missing functionality from an alternate
API/layout and from an environment or validation block. A faster result is only
called a winner among compatible samples from the same controlled run; the
report must explain likely representation, compiler, backend, and allocation
causes. A missing implementation remains visible as an actionable gap rather
than being replaced by a nearby operation.
