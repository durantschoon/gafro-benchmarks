#!/usr/bin/env python3
# SPDX-FileCopyrightText: Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Tobias Loew <tobias.loew@idiap.ch>
# SPDX-FileContributor: Durant Schoon <durant.schoon@gmail.com>
#
# SPDX-License-Identifier: MPL-2.0

"""
Central Cross-Language Benchmark Shootout Runner for Gafro.
Runs C++26, Rust, Julia and F*/Low* implementations, collects standardized
JSON metrics, and generates side-by-side comparisons and markdown reports.

Standard library only, and standalone: it does not import benchmark_harness.

The published comparison (results/benchmark_summary.{json,md}) is regenerated
only by a full-member run on one host -- results from different hosts are
never presented as a language ranking, and derived tables are never hand
edited.  A partial run (--members not the full set) must therefore name an
--output-dir other than results/.
"""

import argparse
import shutil
import sys
import json
import subprocess
from pathlib import Path
from statistics import median

ROOT_DIR = Path(__file__).resolve().parent.parent
CPP_DIR = ROOT_DIR / "cpp"
RUST_DIR = ROOT_DIR / "rust"
FSTAR_DIR = ROOT_DIR / "fstar"
RESULTS_DIR = ROOT_DIR / "results"

# Canonical member order: build order, run order and union order of the
# table.  julia comes last so the order of the pre-existing members (and
# hence of their rows) is unchanged.
ALL_MEMBERS = ("cpp", "rust", "fstar", "julia")

# Mirrors benchmark_harness/cli.py MARKERS["julia"] and the contract runner
# path benchmark_julia uses; duplicated on purpose so this runner stays
# standalone.
JULIA_MARKER = "Project.toml"
JULIA_CONTRACT_RUNNER = Path("benchmark") / "contract_main.jl"

# --- reading a member's rows -----------------------------------------
# Two row shapes exist in this repository's history.  The shape this
# script was first written against is flat -- `benchmark',
# `time_per_op_ns', `ops_per_sec' -- and is what PORTING_AND_STANDARDS.md
# section 2 still shows.  The shape the emitters actually produce today
# is `gafro-benchmark-result/v1' (contracts/result-v1.schema.json):
# `workload_id', `status', `sample_durations_ns', `operations_per_sample'.
# Check results/runs/*/raw/*.stdout for the evidence -- no committed run
# carries a `benchmark' key.
#
# So the accessors below read either shape rather than defaulting a
# missing key to 0.0, which would print a table of zeros and call it a
# measurement.


def row_key(row):
    """The workload this row is about, in either row shape."""
    return row.get("benchmark") or row.get("workload_id")


def row_ns_per_op(row):
    """Nanoseconds per operation, or None when the row is not a timing."""
    if "time_per_op_ns" in row:
        return float(row["time_per_op_ns"])
    if row.get("status") != "supported":
        return None
    samples = row.get("sample_durations_ns") or []
    operations = row.get("operations_per_sample") or 0
    if not samples or operations <= 0:
        return None
    return median(samples) / operations


def row_ops_per_sec(row):
    if "ops_per_sec" in row:
        return float(row["ops_per_sec"])
    ns = row_ns_per_op(row)
    return (1e9 / ns) if ns else None


def row_note(row):
    """What to print where a number would go, when there is no number."""
    status = row.get("status")
    if status and status != "supported":
        return status
    return "absent" if not row else "no timing"


class Progress:
    """Numbered `[n/total]' prefixes: one build and one run step per member."""

    def __init__(self, total):
        self.total = total
        self.done = 0

    def __call__(self, message):
        self.done += 1
        print(f"[{self.done}/{self.total}] {message}")


progress = Progress(2 * len(ALL_MEMBERS))


def build_cpp():
    progress("Building C++26 benchmarks...")
    build_dir = CPP_DIR / "build"
    build_dir.mkdir(exist_ok=True)
    subprocess.run(["cmake", "-B", str(build_dir), "-S", str(CPP_DIR)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["cmake", "--build", str(build_dir), "-j10"], check=True, stdout=subprocess.DEVNULL)

def build_rust():
    progress("Building Rust benchmarks...")
    subprocess.run(["cargo", "build", "--release"], cwd=str(RUST_DIR), check=True, stdout=subprocess.DEVNULL)

def build_fstar():
    # Nothing to do here, and that is the point.  gafro-fstar's toolchain
    # is a lock (channels.scm + manifest.scm + opam/pins.env) that is only
    # ever instantiated inside an OrbStack machine running Guix; its
    # Makefile assumes no compiler on this host.  The build happens inside
    # the machine as part of `make bench', which fstar/run_fstar.py drives.
    progress("F*/Low* member builds inside its own pinned machine; nothing to build here.")


# --- the julia member ------------------------------------------------
# gafro-julia ships its own contract runner (benchmark/contract_main.jl),
# which prints a gafro-benchmark-result/v1 bundle on stdout and progress
# logging on stderr.  The two streams are captured separately: merging
# them would corrupt the JSON.  A missing checkout or executable makes the
# member unavailable with no rows, exactly like an absent F* VM -- never a
# crash of the whole shootout.

def discover_julia(override=None):
    """Return the resolved gafro-julia checkout, or None.

    Mirrors benchmark_harness/cli.py discover() for family "julia": an
    explicit override, else ../gafro-julia and ../gafro-julia/gafro-julia
    relative to this repository's parent and grandparent.
    """
    if override:
        candidates = [Path(override).expanduser()]
    else:
        candidates = []
        for parent in (ROOT_DIR.parent, ROOT_DIR.parent.parent):
            checkout = parent / "gafro-julia"
            candidates.extend((checkout, checkout / "gafro-julia"))
    for candidate in candidates:
        resolved = candidate.resolve()
        if (resolved / JULIA_MARKER).is_file():
            return resolved
    return None


def julia_repository_identity(path):
    """(revision, dirty) of a checkout; mirrors cli.py repository_identity."""
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, check=True,
                              text=True, capture_output=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=path, check=True,
                                text=True, capture_output=True).stdout.strip())
    return revision, dirty


def build_julia(path, julia="julia"):
    """Instantiate <path>/benchmark.  None on success, else the reason it cannot run."""
    progress("Instantiating the Julia benchmark project...")
    if path is None:
        return f"no gafro-julia checkout with {JULIA_MARKER} found"
    executable = shutil.which(julia)
    if executable is None:
        return f"Julia executable not found: {julia}"
    if not (path / JULIA_CONTRACT_RUNNER).is_file():
        return f"gafro-julia checkout has no contract runner: {path / JULIA_CONTRACT_RUNNER}"
    proc = subprocess.run(
        [executable, f"--project={path / 'benchmark'}", "-e", "using Pkg; Pkg.instantiate()"],
        cwd=str(path), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return f"Pkg.instantiate failed (exit {proc.returncode}): {proc.stderr.strip()[-400:]}"
    return None


def run_julia(path, julia="julia", problem=None):
    # Never `check=True' on the measured process, for the same reason as
    # run_fstar: an unavailable member reports no rows, it does not take
    # the shootout down.
    progress("Running Julia benchmarks...")
    if problem is not None:
        print(f"      Julia member unavailable: {problem}; reporting no rows.")
        return {"results": []}
    executable = shutil.which(julia)
    try:
        revision, dirty = julia_repository_identity(path)
        version = subprocess.run([executable, "--version"], check=True, text=True,
                                 capture_output=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"      Julia member unavailable: cannot identify {path} ({exc}); reporting no rows.")
        return {"results": []}
    proc = subprocess.run([
        executable, f"--project={path / 'benchmark'}", str(path / JULIA_CONTRACT_RUNNER),
        "--profile", "full", "--revision", revision,
        "--dirty", str(dirty).lower(), "--compiler", version,
    ], cwd=str(path), capture_output=True, text=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        print(f"      Julia member produced no bundle (exit {proc.returncode}); reporting no rows.")
        print(proc.stderr.strip()[-400:])
        return {"results": []}
    return json.loads(proc.stdout)


def run_cpp():
    progress("Running C++26 benchmarks...")
    binary = CPP_DIR / "build" / "bench_cga_cpp"
    proc = subprocess.run([str(binary), "--json"], capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)

def run_rust():
    progress("Running Rust benchmarks...")
    binary = RUST_DIR / "target" / "release" / "gafro-bench-rust"
    proc = subprocess.run([str(binary), "--json"], capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)

def run_fstar():
    # Never `check=True': this member is allowed to report itself
    # unavailable on a host without OrbStack, and an unavailable member
    # must not take the shootout down with it.  fstar/run_fstar.py always
    # emits one row per contract id and always exits 0; see its docstring
    # for the available / unavailable / failed split.
    progress("Running F*/Low* benchmarks (inside the pinned OrbStack machine)...")
    script = FSTAR_DIR / "run_fstar.py"
    proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        print(f"      F* member produced no bundle (exit {proc.returncode}); reporting no rows.")
        return {"results": []}
    return json.loads(proc.stdout)


# --- functional core: the comparison table ---------------------------

def ratio_text(c_ns, other_ns):
    """C++ relative to another natively built member, or n/a if either is missing."""
    if c_ns and other_ns:
        ratio = other_ns / c_ns
        return f"{ratio:0.2f}x faster" if ratio >= 1.0 else f"{1.0/ratio:0.2f}x slower"
    return "n/a"


def render_table(members):
    """Member bundles -> (terminal_text, markdown_text).  Pure: no I/O.

    `members' maps a member name ("cpp", "rust", "fstar", "julia") to its
    bundle ({"results": [...]}); a member that is absent from the mapping
    renders as `absent' cells.
    """
    results = {
        name: {row_key(r): r for r in (members.get(name) or {}).get("results", [])}
        for name in ALL_MEMBERS
    }

    # Union, not just C++'s keys: a workload only one member implements
    # is exactly the kind of gap this table exists to show.
    all_benchmarks = list(results["cpp"])
    for name in ALL_MEMBERS[1:]:
        for key in results[name]:
            if key not in all_benchmarks:
                all_benchmarks.append(key)

    header = (f"{'Benchmark':<47} | {'C++26 (ns)':>12} | {'Rust (ns)':>12} | {'Julia (ns)':>12} | "
              f"{'F* in-VM (ns)':>14} | {'Ratio (C++/Rust)':>18} | {'Ratio (C++/Julia)':>18}")
    sep = "-" * len(header)

    terminal = [
        "",
        "=" * len(header),
        " GAFRO CROSS-LANGUAGE BENCHMARK SHOOTOUT (C++26 vs RUST vs JULIA vs F*/Low*)",
        "=" * len(header),
        header,
        sep,
    ]
    md_rows = []

    def cell(row, width):
        ns = row_ns_per_op(row)
        return f"{ns:>{width}.2f}" if ns is not None else f"{row_note(row):>{width}}"

    for b in all_benchmarks:
        c = results["cpp"].get(b, {})
        r = results["rust"].get(b, {})
        j = results["julia"].get(b, {})
        f = results["fstar"].get(b, {})

        c_ns = row_ns_per_op(c)

        # The C++/Rust and C++/Julia ratios are between natively built
        # members, so they stay.  No fstar ratio is printed: those numbers
        # are measured inside a virtual machine (and, on Apple Silicon,
        # under a different guest architecture), so a ratio against a
        # native member would not be a language comparison.
        # benchmark_harness's reconciler declines it for the same reason,
        # from the host keys the fstar rows themselves declare.
        rust_ratio = ratio_text(c_ns, row_ns_per_op(r))
        julia_ratio = ratio_text(c_ns, row_ns_per_op(j))

        terminal.append(
            f"{b:<47} | {cell(c, 12)} | {cell(r, 12)} | {cell(j, 12)} | {cell(f, 14)} | "
            f"{rust_ratio:>18} | {julia_ratio:>18}"
        )
        md_rows.append(
            f"| `{b}` | {cell(c, 0).strip()} | {cell(r, 0).strip()} | {cell(j, 0).strip()} | "
            f"{cell(f, 0).strip()} | **{rust_ratio}** | **{julia_ratio}** |"
        )

    terminal += [
        "=" * len(header),
        "",
        "The F* column is measured INSIDE an OrbStack machine, in a pinned Guix toolchain;",
        "every other column is built natively on this host. Those numbers sit on opposite",
        "sides of a virtualisation boundary (and, on Apple Silicon, an architecture",
        "boundary), so no ratio against the F* column is offered here.",
        "",
    ]

    markdown = """# Gafro Cross-Language Benchmark Shootout

Comparative performance evaluation between **Gafro C++26**, **Gafro Rust**,
**gafro-julia** and **gafro-fstar** (F*/Low*, extracted to C by KaRaMeL).

The F* column is measured inside an OrbStack machine in a pinned Guix toolchain,
not natively on the host; no ratio against it is offered, because such a ratio
would cross a virtualisation boundary rather than compare two languages.

| Benchmark | C++26 Latency | Rust Latency | Julia Latency | F* Latency (in-VM) | Relative Speed (C++/Rust) | Relative Speed (C++/Julia) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
""" + "\n".join(md_rows) + "\n"

    return "\n".join(terminal), markdown


# --- imperative shell ------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Gafro cross-language benchmark shootout")
    parser.add_argument("--members", default=",".join(ALL_MEMBERS),
                        help=f"comma list from {','.join(ALL_MEMBERS)} (default: all four)")
    parser.add_argument("--julia-path", help="gafro-julia checkout (default: sibling discovery)")
    parser.add_argument("--julia", default="julia", help="Julia executable (default: julia)")
    parser.add_argument("--output-dir",
                        help="directory for benchmark_summary.{json,md} (default: results/; "
                             "required, and not results/, for a partial --members run)")
    return parser.parse_args(argv)


def resolve_plan(args):
    """Validate the request before anything runs: (members, output_dir) or SystemExit."""
    requested = [part.strip() for part in args.members.split(",") if part.strip()]
    unknown = sorted(set(requested) - set(ALL_MEMBERS))
    if unknown or not requested:
        raise SystemExit(f"run_all.py: --members takes a comma list from {','.join(ALL_MEMBERS)}; "
                         f"got {args.members!r}")
    members = [name for name in ALL_MEMBERS if name in requested]
    output_dir = Path(args.output_dir).resolve() if args.output_dir else RESULTS_DIR.resolve()
    if set(members) != set(ALL_MEMBERS) and output_dir == RESULTS_DIR.resolve():
        raise SystemExit("run_all.py: a partial --members run needs --output-dir other than results/ "
                         "(results/benchmark_summary.* is regenerated only by a full-member run on one host)")
    return members, output_dir


def main(argv=None):
    args = parse_args(argv)
    members, output_dir = resolve_plan(args)
    progress.total = 2 * len(members)
    progress.done = 0

    julia_path = discover_julia(args.julia_path) if "julia" in members else None

    julia_problem = None
    if "cpp" in members:
        build_cpp()
    if "rust" in members:
        build_rust()
    if "fstar" in members:
        build_fstar()
    if "julia" in members:
        julia_problem = build_julia(julia_path, args.julia)

    runners = {
        "cpp": run_cpp,
        "rust": run_rust,
        "fstar": run_fstar,
        "julia": lambda: run_julia(julia_path, args.julia, julia_problem),
    }
    bundles = {name: runners[name]() for name in members}

    terminal_text, markdown_text = render_table(bundles)
    print(terminal_text)

    output_dir.mkdir(parents=True, exist_ok=True)
    # Save summary JSON: each member's raw bundle under its own key, as
    # before; a full run writes cpp, rust, fstar and julia.
    with open(output_dir / "benchmark_summary.json", "w") as f:
        json.dump(bundles, f, indent=2)

    # Save summary Markdown
    with open(output_dir / "benchmark_summary.md", "w") as f:
        f.write(markdown_text)

    print(f"Results saved to:\n  - {output_dir / 'benchmark_summary.json'}\n  - {output_dir / 'benchmark_summary.md'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
