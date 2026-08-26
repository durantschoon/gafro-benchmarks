# Stage 06: reproducible aggregation and reporting

## Goal

Turn validated adapter samples into auditable cross-language reports without
overstating precision or comparing incompatible environments.

## Baseline

The current runner records one aggregate per implementation, computes ratios
from rounded values, assumes the C++ workload list is authoritative, and
overwrites a JSON and Markdown summary without a run identity or raw evidence
archive.

## Required changes

1. Store each run in a unique results directory containing the manifest,
   adapter outputs, runner configuration, stdout/stderr logs, repository
   revisions, dirty flags, and host/toolchain metadata.
2. Validate all adapter results before publishing. A failed oracle, incompatible
   schema, duplicate ID, or mismatched workload definition prevents comparison
   but preserves the raw evidence and diagnostic.
3. Summarize raw samples with median and a documented dispersion statistic;
   retain sample count and values. Do not imply significance from a single run.
4. Generate JSON and Markdown from the same pure summary model. Report capability
   gaps and failures alongside timings without converting them to zero.
5. Compute ratios from unrounded compatible estimates, name the numerator and
   denominator, and omit rankings when environment compatibility checks fail.
6. Add deterministic golden tests for report ordering, rounding, ratios,
   incomplete matrices, incompatible hosts/builds, and preservation of prior
   runs.
7. Update the README with quick smoke, full local run, explicit path overrides,
   interpreting statistics, and reproducibility limitations.
8. Replace the legacy preview numbers only with a generated report from a fully
   recorded run; otherwise label them historical and non-reproducible.

## Constraints

- Never delete or overwrite a prior raw run as part of normal execution.
- Generated summaries must identify their input run IDs.
- Cross-machine data may be displayed side by side but not ranked by default.
- Benchmark timing is not a correctness or CI pass/fail threshold.

## Definition of done

- `make check`, `make test`, `make benchmark-smoke`, and `make benchmark` pass
  for all available implementations.
- Re-running report generation from saved raw evidence is deterministic.
- The final capability matrix covers C++, Idris 2, and Rust, including explicit
  blocked or unsupported cells.
- `docs/stages/stage-06-REPORT.md` records gates, the published run IDs,
  deviations, and remaining open questions.
