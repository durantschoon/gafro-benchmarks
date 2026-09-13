#!/usr/bin/env python3
# SPDX-FileCopyrightText: Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Tobias Loew <tobias.loew@idiap.ch>
# SPDX-FileContributor: Durant Schoon <durant.schoon@gmail.com>
#
# SPDX-License-Identifier: MPL-2.0

"""
Central Cross-Language Benchmark Shootout Runner for Gafro.
Runs C++26, Rust and F*/Low* implementations, collects standardized JSON
metrics, and generates side-by-side comparisons and markdown reports.
"""

import os
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


def build_cpp():
    print("[1/6] Building C++26 benchmarks...")
    build_dir = CPP_DIR / "build"
    build_dir.mkdir(exist_ok=True)
    subprocess.run(["cmake", "-B", str(build_dir), "-S", str(CPP_DIR)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["cmake", "--build", str(build_dir), "-j10"], check=True, stdout=subprocess.DEVNULL)

def build_rust():
    print("[2/6] Building Rust benchmarks...")
    subprocess.run(["cargo", "build", "--release"], cwd=str(RUST_DIR), check=True, stdout=subprocess.DEVNULL)

def build_fstar():
    # Nothing to do here, and that is the point.  gafro-fstar's toolchain
    # is a lock (channels.scm + manifest.scm + opam/pins.env) that is only
    # ever instantiated inside an OrbStack machine running Guix; its
    # Makefile assumes no compiler on this host.  The build happens inside
    # the machine as part of `make bench', which fstar/run_fstar.py drives.
    print("[3/6] F*/Low* member builds inside its own pinned machine; nothing to build here.")

def run_cpp():
    print("[4/6] Running C++26 benchmarks...")
    binary = CPP_DIR / "build" / "bench_cga_cpp"
    proc = subprocess.run([str(binary), "--json"], capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)

def run_rust():
    print("[5/6] Running Rust benchmarks...")
    binary = RUST_DIR / "target" / "release" / "gafro-bench-rust"
    proc = subprocess.run([str(binary), "--json"], capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)

def run_fstar():
    # Never `check=True': this member is allowed to report itself
    # unavailable on a host without OrbStack, and an unavailable member
    # must not take the shootout down with it.  fstar/run_fstar.py always
    # emits one row per contract id and always exits 0; see its docstring
    # for the available / unavailable / failed split.
    print("[6/6] Running F*/Low* benchmarks (inside the pinned OrbStack machine)...")
    script = FSTAR_DIR / "run_fstar.py"
    proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        print(f"      F* member produced no bundle (exit {proc.returncode}); reporting no rows.")
        return {"results": []}
    return json.loads(proc.stdout)

def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    build_cpp()
    build_rust()
    build_fstar()

    cpp_data = run_cpp()
    rust_data = run_rust()
    fstar_data = run_fstar()

    cpp_results = {row_key(r): r for r in cpp_data["results"]}
    rust_results = {row_key(r): r for r in rust_data["results"]}
    fstar_results = {row_key(r): r for r in fstar_data["results"]}

    # Union, not just C++'s keys: a workload only one member implements
    # is exactly the kind of gap this table exists to show.
    all_benchmarks = list(cpp_results)
    for key in list(rust_results) + list(fstar_results):
        if key not in all_benchmarks:
            all_benchmarks.append(key)

    header = (f"{'Benchmark':<47} | {'C++26 (ns)':>12} | {'Rust (ns)':>12} | "
              f"{'F* in-VM (ns)':>14} | {'Ratio (C++/Rust)':>18}")
    sep = "-" * len(header)

    print("\n" + "=" * len(header))
    print(" GAFRO CROSS-LANGUAGE BENCHMARK SHOOTOUT (C++26 vs RUST vs F*/Low*)")
    print("=" * len(header))
    print(header)
    print(sep)

    md_rows = []

    def cell(row, width):
        ns = row_ns_per_op(row)
        return f"{ns:>{width}.2f}" if ns is not None else f"{row_note(row):>{width}}"

    for b in all_benchmarks:
        c = cpp_results.get(b, {})
        r = rust_results.get(b, {})
        f = fstar_results.get(b, {})

        c_ns = row_ns_per_op(c)
        r_ns = row_ns_per_op(r)

        # The C++/Rust ratio is between two natively built members, so it
        # stays.  No fstar ratio is printed: those numbers are measured
        # inside a virtual machine (and, on Apple Silicon, under a
        # different guest architecture), so a ratio against a native
        # member would not be a language comparison.  benchmark_harness's
        # reconciler declines it for the same reason, from the host keys
        # the fstar rows themselves declare.
        if c_ns and r_ns:
            ratio = r_ns / c_ns
            ratio_str = f"{ratio:0.2f}x faster" if ratio >= 1.0 else f"{1.0/ratio:0.2f}x slower"
        else:
            ratio_str = "n/a"

        print(f"{b:<47} | {cell(c, 12)} | {cell(r, 12)} | {cell(f, 14)} | {ratio_str:>18}")

        md_rows.append(
            f"| `{b}` | {cell(c, 0).strip()} | {cell(r, 0).strip()} | "
            f"{cell(f, 0).strip()} | **{ratio_str}** |"
        )

    print("=" * len(header) + "\n")
    print("The F* column is measured INSIDE an OrbStack machine, in a pinned Guix toolchain;")
    print("every other column is built natively on this host. Those numbers sit on opposite")
    print("sides of a virtualisation boundary (and, on Apple Silicon, an architecture")
    print("boundary), so no ratio against the F* column is offered here.\n")

    # Save summary JSON
    summary_json = {
        "cpp": cpp_data,
        "rust": rust_data,
        "fstar": fstar_data,
    }
    with open(RESULTS_DIR / "benchmark_summary.json", "w") as f:
        json.dump(summary_json, f, indent=2)

    # Save summary Markdown
    md_content = f"""# Gafro Cross-Language Benchmark Shootout

Comparative performance evaluation between **Gafro C++26**, **Gafro Rust** and
**gafro-fstar** (F*/Low*, extracted to C by KaRaMeL).

The F* column is measured inside an OrbStack machine in a pinned Guix toolchain,
not natively on the host; no ratio against it is offered, because such a ratio
would cross a virtualisation boundary rather than compare two languages.

| Benchmark | C++26 Latency | Rust Latency | F* Latency (in-VM) | Relative Speed (C++/Rust) |
|:---|:---:|:---:|:---:|:---:|
""" + "\n".join(md_rows) + "\n"

    with open(RESULTS_DIR / "benchmark_summary.md", "w") as f:
        f.write(md_content)

    print(f"Results saved to:\n  - {RESULTS_DIR / 'benchmark_summary.json'}\n  - {RESULTS_DIR / 'benchmark_summary.md'}\n")

if __name__ == "__main__":
    main()
