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

## GPU execution environment (decision, 2026-09-12)

Cross-language GPU (CUDA) runs use exactly **one rented NVIDIA pod**
(RunPod or equivalent) per comparison run: every implementation family is
built and measured on that same instance, in the same session.

Justification:
- The permanent rules above already forbid presenting results from
  different machines, compiler modes, or dependency revisions as a direct
  language ranking. One pod per run is the cheapest arrangement that
  satisfies the same-host requirement by construction instead of by
  after-the-fact filtering.
- One pod means one GPU model, one driver/toolkit version, one thermal and
  clock envelope — the `host`/`gpu` metadata blocks describe every row
  identically, so ratios need no compatibility carve-outs.
- Cloud noisy-neighbor variance differs pod to pod; a single dedicated
  (secure-cloud) instance makes variance a shared property of the run
  rather than a per-language confound.
- Reproducibility: the pod is provisioned from a pinned container image,
  and the image digest + GPU model are recorded with the run. A later run
  on a different pod is a NEW experiment, never merged into an old
  ranking.
- The development machine is Apple Silicon (no CUDA); local runs cover CPU
  rows only, so the pod is the family's sole CUDA ground truth.

## Gates

Stage 01 defines stable Make targets. From that stage onward every report runs:

```text
make check
make test
make benchmark-smoke
```

Full measurements are intentionally separate: `make benchmark` may take longer
and is required only by stages that change measurement or reporting behavior.

## Coordinator practices

### Propagated from the gafro-julia stage-19 retro (2026-09-12)

Standing rule (user direction, 2026-09-12): retro findings that are not
repo-specific propagate to every gafro-family practices file in the same
retro cycle.

- **Verify citations before sealing.** Four of five gafro-julia stage
  prompts (15–19) shipped a factual error about the sibling code they cite;
  every one was ledger-tagged `overlooked`. Before sealing a forecast,
  re-read every `file:line` the prompt cites and dry-run the allow-list
  against the prompt's enumerated outputs (every ordered artifact needs a
  writable path).
- **Cross-sibling surface translation always forces a convention decision**
  — naming collisions, overload-vs-separate-names, argument-order
  divergence (gafro-rust's own `from_quantities` permutes against its own
  `new`). Delegate the decision to the executor with a
  record-the-rationale requirement, and carry one `data-shape` forecast
  branch for "sibling shape does not map 1:1".
- **Definition order is part of the additive surface.** Code whose
  signatures or types reference another layer inherits that layer's
  load/import/include order (gafro-julia stage 19: adapters needed new
  files because alias names in method signatures evaluate at definition
  time). Prompts that add such code must state where it falls in the load
  order or explicitly allow new files.

### Cross-pollinated from family retros (2026-09-12)

Deliberate pass over every gafro-family repo's accumulated retros (user
direction): each repo adopts the practices proven elsewhere that it lacked.
Provenance tagged per item.

- **Mechanical rename/move scout** (idris2, stages 05–07 retro): before
  sealing, grep the harness, contracts and docs for every identifier AND
  concept phrase a prompt moves/renames/deletes/adds, and disposition every
  hit in the prompt.
- **Toolchain existence check** (idris2, fc-07-a): every library function a
  prompt's formulas name must exist in the pinned toolchain/interpreter
  version — verify before sealing.
- **Assertion strengthening is sanctioned, not a Deviation** (idris2): adding
  assertions/samples inside an enumerated check is silently fine; dropping or
  weakening one remains a Deviation.
- **Resumed executor re-verifies isolation first** (idris2, pv-07-a) and
  **pre-launch divergence check** (idris2, pv-01-a): verify checkout
  isolation after any interruption, and fetch/verify the default branch
  before provisioning.
- **Measurement procedures, not expected numbers** (gafro-julia, stage-14
  retro): prompts specify how to measure and which gate to satisfy — never
  pre-computed expected values.
- **Known-problems register** (julia/rust/cpp convention): adopt
  `docs/stages/known-problems/KP-NNN-<slug>.md` for defects and environment
  hazards that outlive a stage.

## Route

See [ROUTE.md](ROUTE.md) for the staged sequence and completion boundaries.
