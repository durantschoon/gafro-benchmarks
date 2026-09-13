<!--
SPDX-FileCopyrightText: Durant Schoon <durant.schoon@gmail.com>

SPDX-License-Identifier: MPL-2.0
-->

# The `fstar` member — gafro-fstar

The F*/Low* member of the shootout. Its kernels are verified in F*,
extracted to C by KaRaMeL, and committed;
[`gafro-fstar`](https://github.com/durantschoon/gafro-fstar) is the
checkout this directory drives.

```
fstar/run_fstar.py [--fstar-path PATH] [--profile smoke|full]
```

It prints a `gafro-benchmark-bundle/v1` document on stdout — one row per
id in `contracts/workloads-v1.json`, always — and its narration on
stderr. `runner/run_all.py` calls it as the third member.

## It does not build on this host, and that is deliberate

Every other member compiles here. This one does not. gafro-fstar's
toolchain is a *lock* — `channels.scm` + `manifest.scm` + `opam/pins.env`
— that is only ever instantiated inside an **OrbStack machine running
Guix**, and its `Makefile` assumes nothing on the Mac but `git`, `make`
and `orbctl`. So this wrapper compiles nothing: it runs `make bench` in
that checkout, which builds and runs the benchmark inside the machine.

**A host without OrbStack is not an error.** The wrapper checks for the
checkout, for `orbctl`, and for the machine being *running* (it will not
start or provision one — that is `make provision` in gafro-fstar and is
that repository's business). If any of those is missing it emits every
contract id as `unavailable` with the reason, and exits 0. A member that
cannot run here says so rather than taking the shootout down.

**A host *with* OrbStack where `make bench` still fails is a different
thing**, and is reported as `failed`, not `unavailable`, with the
captured stderr. Hiding a broken member behind a missing toolchain is
the one substitution this wrapper must never make.

## Read this before comparing its numbers to anything

The F* rows are measured **inside the machine**. Every other member is
built and timed natively on the host. On an Apple Silicon host it is
worse than virtualisation alone: the guest reports `aarch64` while the
host's toolchains report `x86_64`, so the two sides are not even the
same instruction set.

This is mechanised rather than foot-noted. The rows gafro-fstar emits
carry the guest's own `uname` in `host.system` / `host.release` /
`host.machine`, and `benchmark_harness/core.py`'s
`_compatible_environments` refuses to ratio two rows whose declared host
keys disagree. Telling the truth in the row is what makes the tool
decline the comparison. `runner/run_all.py` prints the F* column without
a ratio for the same reason.

## What it supports, and what it says instead

Two of the sixteen contract ids, because gafro-fstar has exactly two
kernels:

| id | why |
|---|---|
| `dense_geometric_product/f64/orthogonal` | `src/Gafro.Kernel.fst` *is* this workload: gafro-fstar indexes its 32 coefficients in gafro-lean's orthogonal `ePlus,e1,e2,e3,eMinus` basis, which is the basis this id declares |
| `sandwich_point_transform/f64/e1` | `src/Gafro.Sandwich.fst`, `M X reverse(M)` at gafro-lean's association order. The translator and the conformal point are built in the harness as data, from gafro-lean's own `nOrigin`/`nInf`/`up`/`translator` definitions; the only thing timed is the kernel |

The other fourteen are emitted as `unsupported` rows carrying a reason
that names the missing thing — no outer-product kernel, no rotor
construction (the trusted base has `dadd`/`dsub`/`dmul`/`dzero` and no
transcendental at all), no SoA batch API, no robotics layer. Notably
`motor_composition_gp/f64/scalar` is refused *even though* gafro-fstar
could compute it with the same geometric-product kernel it already
times: reporting it would claim a rigid-motor capability the repository
does not have.

Both supported rows assert their observable **before any timing**, and
more strictly than the contract asks: every operand and intermediate in
both workloads is a dyadic rational exactly representable in binary64,
so the check is bit equality, and the sandwich row checks all 32
coefficients of both operand pairs against an independently constructed
`up(p + t)` rather than the single declared observable.

## One-token registration this commit does NOT make

`benchmark_harness/core.py` hard-codes the family list:

```python
IMPLEMENTATIONS = ("cpp", "idris2", "rust", "julia")
```

and `validate_result` rejects any other `implementation.family`. So the
rows below are valid against `contracts/result-v1.schema.json` (checked:
all sixteen) and are reconciled, summarised and rendered correctly by
`benchmark_harness.core` **as soon as `"fstar"` is added to that tuple** —
verified by running `validate_complete_run(manifest, rows, "fstar")` with
the tuple extended in memory: 16 rows reconciled, both oracles accepted.

That edit is **not** in this commit, because it is outside the paths this
work was scoped to touch. Registering the member fully wants three
one-line changes, all in files this commit leaves alone:

1. `benchmark_harness/core.py` — `IMPLEMENTATIONS += ("fstar",)`
2. `benchmark_harness/core.py` — `display_names` in
   `render_summary_markdown` gains `"fstar": "F*"`
3. `benchmark_harness/cli.py` — `MARKERS` gains
   `"fstar": "bench/bench_cga.c"`, and `benchmark_fstar` joins the
   adapter set if the member is to run under
   `benchmark_harness.cli benchmark` rather than under
   `runner/run_all.py`

Proposed, recorded, and left to whoever owns those files.
