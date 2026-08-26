# Benchmark stage pipeline

This directory is the implementation plan for turning `gafro-benchmarks` into a
reproducible benchmark suite for the sibling `gafro-*` projects.

## Numbering and reports

Implement stages in numeric order. The committed `stage-NN-PROMPT.md` is the
scope contract for that stage. Each implementation stage adds a matching
`stage-NN-REPORT.md` containing the exact commands run, results, deviations,
and open questions.

## Repository inventory used by this plan

The inventory was taken on 2026-08-25 from the parent directory:

| Path | Role | State |
| --- | --- | --- |
| `../gafro-benchmarks` | Benchmark harness | Attached |
| `../gafro-cpp/gafro-cpp` | C++ implementation | Benchmarkable |
| `../gafro-idris2/gafro-idris2` | Idris 2 implementation | No robotics |
| `../gafro-rust/gafro-rust` | Rust implementation | CUDA in development |

The paths above are discovery evidence, not permanent runtime defaults. The
harness must accept explicit implementation paths and record their revisions.

## Permanent benchmark rules

- Correctness precedes timing. Every measured workload has an untimed oracle
  check on the same inputs.
- A benchmark ID denotes one mathematical operation, input, output observation,
  numeric type, and iteration accounting rule in every language.
- Unsupported capabilities are reported explicitly; they are never replaced by
  a nearby operation under the same ID.
- Timed regions exclude fixture parsing, setup, serialization, and process
  startup.
- Implementations must prevent dead-code elimination while observing the same
  minimum output in every language.
- Raw samples and environment metadata are primary evidence. Generated summary
  tables are derived artifacts and must not be hand edited.
- Results from different machines, compiler modes, or dependency revisions are
  not presented as a direct language ranking.
- GPU results distinguish kernel-only, device-resident pipeline, and end-to-end
  latency. Host/device transfer is never silently omitted.
- CPU and GPU comparisons use the same numeric precision, batch inputs, output
  oracle, and operation-count definition unless the report labels them as
  separate experiments.

## Gates

Stage 01 defines stable Make targets. From that stage onward every report runs:

```text
make check
make test
make benchmark-smoke
```

Full measurements are intentionally separate: `make benchmark` may take longer
and is required only by stages that change measurement or reporting behavior.

## Route

See [ROUTE.md](ROUTE.md) for the staged sequence and completion boundaries.
