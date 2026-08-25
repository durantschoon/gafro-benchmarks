#!/usr/bin/env python3
# SPDX-FileCopyrightText: Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Tobias Loew <tobias.loew@idiap.ch>
# SPDX-FileContributor: Durant Schoon <durant.schoon@gmail.com>
#
# SPDX-License-Identifier: MPL-2.0

"""
Central Cross-Language Benchmark Shootout Runner for Gafro.
Runs C++26 and Rust implementations, collects standardized JSON metrics,
and generates side-by-side comparisons and markdown reports.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CPP_DIR = ROOT_DIR / "cpp"
RUST_DIR = ROOT_DIR / "rust"
RESULTS_DIR = ROOT_DIR / "results"

def build_cpp():
    print("[1/4] Building C++26 benchmarks...")
    build_dir = CPP_DIR / "build"
    build_dir.mkdir(exist_ok=True)
    subprocess.run(["cmake", "-B", str(build_dir), "-S", str(CPP_DIR)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["cmake", "--build", str(build_dir), "-j10"], check=True, stdout=subprocess.DEVNULL)

def build_rust():
    print("[2/4] Building Rust benchmarks...")
    subprocess.run(["cargo", "build", "--release"], cwd=str(RUST_DIR), check=True, stdout=subprocess.DEVNULL)

def run_cpp():
    print("[3/4] Running C++26 benchmarks...")
    binary = CPP_DIR / "build" / "bench_cga_cpp"
    proc = subprocess.run([str(binary), "--json"], capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)

def run_rust():
    print("[4/4] Running Rust benchmarks...")
    binary = RUST_DIR / "target" / "release" / "gafro-bench-rust"
    proc = subprocess.run([str(binary), "--json"], capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)

def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    build_cpp()
    build_rust()

    cpp_data = run_cpp()
    rust_data = run_rust()

    cpp_results = {r["benchmark"]: r for r in cpp_data["results"]}
    rust_results = {r["benchmark"]: r for r in rust_data["results"]}

    all_benchmarks = list(cpp_results.keys())

    header = f"{'Benchmark':<35} | {'C++26 (ns)':>12} | {'Rust (ns)':>12} | {'C++ ops/sec':>15} | {'Rust ops/sec':>15} | {'Ratio (C++/Rust)':>18}"
    sep = "-" * len(header)

    print("\n" + "=" * len(header))
    print(" GAFRO CROSS-LANGUAGE BENCHMARK SHOOTOUT (C++26 vs RUST)")
    print("=" * len(header))
    print(header)
    print(sep)

    md_rows = []

    for b in all_benchmarks:
        c = cpp_results.get(b, {})
        r = rust_results.get(b, {})

        c_ns = c.get("time_per_op_ns", 0.0)
        r_ns = r.get("time_per_op_ns", 0.0)
        c_ops = c.get("ops_per_sec", 0.0)
        r_ops = r.get("ops_per_sec", 0.0)

        ratio = (r_ns / c_ns) if c_ns > 0 else 0.0
        ratio_str = f"{ratio:0.2f}x faster" if ratio >= 1.0 else f"{1.0/ratio:0.2f}x slower"

        print(f"{b:<35} | {c_ns:>12.2f} | {r_ns:>12.2f} | {c_ops:>15,.0f} | {r_ops:>15,.0f} | {ratio_str:>18}")

        md_rows.append(f"| `{b}` | {c_ns:.2f} ns | {r_ns:.2f} ns | {c_ops:,.0f} | {r_ops:,.0f} | **{ratio_str}** |")

    print("=" * len(header) + "\n")

    # Save summary JSON
    summary_json = {
        "cpp": cpp_data,
        "rust": rust_data
    }
    with open(RESULTS_DIR / "benchmark_summary.json", "w") as f:
        json.dump(summary_json, f, indent=2)

    # Save summary Markdown
    md_content = f"""# Gafro Cross-Language Benchmark Shootout

Comparative performance evaluation between **Gafro C++26** and **Gafro Rust**.

| Benchmark | C++26 Latency | Rust Latency | C++26 Throughput | Rust Throughput | Relative Speed |
|:---|:---:|:---:|:---:|:---:|:---:|
""" + "\n".join(md_rows) + "\n"

    with open(RESULTS_DIR / "benchmark_summary.md", "w") as f:
        f.write(md_content)

    print(f"Results saved to:\n  - {RESULTS_DIR / 'benchmark_summary.json'}\n  - {RESULTS_DIR / 'benchmark_summary.md'}\n")

if __name__ == "__main__":
    main()
