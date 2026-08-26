"""Imperative CLI boundary for discovery and benchmark execution."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .core import IMPLEMENTATIONS, parse_json, reconcile_results, summarize_results, validate_complete_run, validate_manifest

MARKERS = {"cpp": "CMakeLists.txt", "idris2": "gafro.ipkg", "rust": "Cargo.toml"}


def discover(root: Path, family: str, override: str | None) -> dict[str, str]:
    if override:
        candidates = [Path(override).expanduser()]
    else:
        candidates = []
        for parent in (root.parent, root.parent.parent):
            checkout = parent / f"gafro-{family}"
            candidates.extend((checkout, checkout / f"gafro-{family}"))
    marker = MARKERS[family]
    for candidate in candidates:
        resolved = candidate.resolve()
        if (resolved / marker).is_file():
            return {"family": family, "status": "available", "path": str(resolved), "marker": marker}
    shown = str(candidates[0].resolve())
    return {"family": family, "status": "unavailable", "path": shown, "reason": f"no validated {marker} checkout"}


def inventory(args: argparse.Namespace, root: Path) -> int:
    rows = [discover(root, family, getattr(args, f"{family}_path")) for family in IMPLEMENTATIONS]
    print(json.dumps({"implementations": rows}, indent=2, sort_keys=True))
    return 0


def smoke(root: Path) -> int:
    manifest = validate_manifest(json.loads((root / "contracts/workloads-v1.json").read_text()))
    host = {"system": platform.system(), "machine": platform.machine()}
    identity = {"family": "cpp", "name": "synthetic-smoke", "repository_revision": "synthetic", "dirty": False, "compiler": "none", "backend": "fixture", "flags": []}
    workload = manifest["workloads"][0]
    rows = [
        {"schema_version": "gafro-benchmark-result/v1", "implementation": identity, "host": host, "workload_id": workload["id"], "status": "supported", "reason": "", "warmup_operations": workload["warmup_operations"], "operations_per_sample": workload["operations_per_sample"], "sample_durations_ns": [1000, 1100, 900], "oracle": {"scalar": 1.0}},
        {"schema_version": "gafro-benchmark-result/v1", "implementation": {**identity, "family": "idris2"}, "host": host, "workload_id": workload["id"], "status": "unsupported", "reason": "synthetic capability gap"},
        {"schema_version": "gafro-benchmark-result/v1", "implementation": {**identity, "family": "rust"}, "host": host, "workload_id": workload["id"], "status": "unavailable", "reason": "synthetic missing checkout"},
    ]
    print(json.dumps(summarize_results(reconcile_results(manifest, rows)), indent=2, sort_keys=True))
    return 0


def repository_identity(path: Path) -> tuple[str, bool]:
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, check=True, text=True, capture_output=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=path, check=True, text=True, capture_output=True).stdout.strip())
    return revision, dirty


def write_bundle(root: Path, family: str, profile: str, checked: list[dict[str, object]]) -> Path:
    destination = root / "artifacts/raw" / f"{family}-{profile}-latest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"schema_version": "gafro-benchmark-bundle/v1", "results": checked}, indent=2, sort_keys=True) + "\n")
    return destination


def benchmark_cpp(args: argparse.Namespace, root: Path, manifest: dict[str, object], expected_operations: int) -> Path:
    found = discover(root, "cpp", args.cpp_path)
    if found["status"] != "available":
        raise SystemExit(found["reason"])
    cpp_path = Path(found["path"])
    build_path = Path(args.cpp_build_path).resolve() if args.cpp_build_path else cpp_path / "build"
    compiler = args.cpp_compiler or ("/usr/bin/clang++" if platform.system() == "Darwin" else "c++")
    revision, dirty = repository_identity(cpp_path)
    with tempfile.TemporaryDirectory(prefix="gafro-benchmark-cpp-") as directory:
        subprocess.run(["cmake", "-S", str(root / "cpp"), "-B", directory, f"-DCMAKE_CXX_COMPILER={compiler}", f"-DGAFRO_CPP_DIR={cpp_path}", f"-DGAFRO_CPP_BUILD_DIR={build_path}", "-DCMAKE_BUILD_TYPE=Release"], check=True)
        subprocess.run(["cmake", "--build", directory, "--parallel"], check=True)
        completed = subprocess.run([str(Path(directory) / "bench_cga_cpp"), "--profile", args.profile, "--revision", revision, "--dirty", str(dirty).lower()], check=True, text=True, capture_output=True)
    bundle = parse_json(completed.stdout)
    checked = validate_complete_run(manifest, bundle.get("results", []), "cpp", expected_operations=expected_operations)
    return write_bundle(root, "cpp", args.profile, checked)


def benchmark_idris2(args: argparse.Namespace, root: Path, manifest: dict[str, object], expected_operations: int) -> Path:
    found = discover(root, "idris2", args.idris2_path)
    if found["status"] != "available":
        raise SystemExit(found["reason"])
    implementation_path = Path(found["path"])
    executable = shutil.which(args.idris2_compiler)
    if executable is None:
        raise SystemExit(f"Idris 2 compiler not found: {args.idris2_compiler}")
    version = subprocess.run([executable, "--version"], check=True, text=True, capture_output=True).stdout.strip()
    if "0.7.0" not in version:
        raise SystemExit(f"gafro-idris2 requires pinned Idris 2 0.7.0, found: {version}")
    revision, dirty = repository_identity(implementation_path)
    with tempfile.TemporaryDirectory(prefix="gafro-benchmark-idris2-") as directory:
        staging = Path(directory)
        source = staging / "src"
        source.mkdir()
        shutil.copy2(root / "idris2/src/Main.idr", source / "Main.idr")
        (source / "Gafro").symlink_to(implementation_path / "src/Gafro", target_is_directory=True)
        subprocess.run([
            executable, "--source-dir", str(source), "--build-dir", str(staging / "build"),
            "--output-dir", str(staging / "bin"), "--codegen", args.idris2_backend,
            "-o", "bench-cga-idris2", str(source / "Main.idr"),
        ], check=True)
        command = [
            str(staging / "bin/bench-cga-idris2"), "--profile", args.profile,
            "--revision", revision, "--dirty", str(dirty).lower(), "--compiler", version,
            "--backend", args.idris2_backend, "--c-compiler", "not-applicable",
            "--c-flags", "not-applicable",
        ]
        completed = subprocess.run(command, check=True, text=True, capture_output=True)
    bundle = parse_json(completed.stdout)
    checked = validate_complete_run(manifest, bundle.get("results", []), "idris2", expected_operations=expected_operations)
    return write_bundle(root, "idris2", args.profile, checked)


def benchmark(args: argparse.Namespace, root: Path) -> int:
    requested = tuple(part.strip() for part in args.implementations.split(",") if part.strip())
    unknown = sorted(set(requested) - set(IMPLEMENTATIONS))
    if unknown:
        raise SystemExit(f"unknown implementations: {', '.join(unknown)}")
    manifest = validate_manifest(json.loads((root / "contracts/workloads-v1.json").read_text()))
    expected_operations = 1000 if args.profile == "smoke" else 10000
    destinations = []
    if "cpp" in requested:
        destinations.append(benchmark_cpp(args, root, manifest, expected_operations))
    if "idris2" in requested:
        destinations.append(benchmark_idris2(args, root, manifest, expected_operations))
    if "rust" in requested:
        raise SystemExit("Rust adapter is introduced in Stage 04")
    for destination in destinations:
        print(destination)
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Gafro benchmark orchestrator")
    result.add_argument("command", choices=("inventory", "smoke", "benchmark"))
    for family in IMPLEMENTATIONS:
        result.add_argument(f"--{family}-path")
    result.add_argument("--cpp-build-path")
    result.add_argument("--cpp-compiler")
    result.add_argument("--idris2-compiler", default="idris2")
    result.add_argument("--idris2-backend", default="chez", choices=("chez", "refc"))
    result.add_argument("--implementations", default="cpp")
    result.add_argument("--profile", choices=("smoke", "full"), default="full")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    if args.command == "inventory":
        return inventory(args, root)
    if args.command == "smoke":
        return smoke(root)
    return benchmark(args, root)


if __name__ == "__main__":
    raise SystemExit(main())
