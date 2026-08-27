"""Imperative CLI boundary for discovery and benchmark execution."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .core import (IMPLEMENTATIONS, build_summary_model, parse_json,
                   reconcile_results, render_summary_markdown,
                   summarize_results, validate_complete_run, validate_manifest)

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


def complete_adapter_results(manifest: dict[str, object], results: list[dict[str, object]], family: str) -> list[dict[str, object]]:
    """Make capability gaps explicit when a legacy adapter predates new workloads."""
    definitions = {item["id"] for item in manifest["workloads"]}
    present = {item["workload_id"] for item in results}
    if not results:
        return results
    identity = dict(results[0]["implementation"])
    return results + [
        {"schema_version": "gafro-benchmark-result/v1", "implementation": identity, "host": {},
         "workload_id": workload_id, "status": "unsupported",
         "reason": f"{family} adapter predates this canonical workload variant"}
        for workload_id in sorted(definitions - present)
    ]


def write_bundle(run_dir: Path, family: str, checked: list[dict[str, object]], stdout: str, stderr: str) -> Path:
    destination = run_dir / "adapters" / f"{family}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"schema_version": "gafro-benchmark-bundle/v1", "results": checked}, indent=2, sort_keys=True) + "\n")
    logs = run_dir / "logs"
    logs.mkdir(exist_ok=True)
    (logs / f"{family}.stdout.log").write_text(stdout)
    (logs / f"{family}.stderr.log").write_text(stderr)
    return destination


def preserve_adapter_output(run_dir: Path, family: str, stdout: str, stderr: str) -> None:
    raw = run_dir / "raw"
    logs = run_dir / "logs"
    raw.mkdir(exist_ok=True)
    logs.mkdir(exist_ok=True)
    (raw / f"{family}.stdout").write_text(stdout)
    (logs / f"{family}.stdout.log").write_text(stdout)
    (logs / f"{family}.stderr.log").write_text(stderr)


def benchmark_cpp(args: argparse.Namespace, root: Path, manifest: dict[str, object], expected_operations: int, run_dir: Path) -> Path:
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
    preserve_adapter_output(run_dir, "cpp", completed.stdout, completed.stderr)
    bundle = parse_json(completed.stdout)
    checked = validate_complete_run(manifest, complete_adapter_results(manifest, bundle.get("results", []), "cpp"), "cpp", expected_operations=expected_operations)
    return write_bundle(run_dir, "cpp", checked, completed.stdout, completed.stderr)


def benchmark_idris2(args: argparse.Namespace, root: Path, manifest: dict[str, object], expected_operations: int, run_dir: Path) -> Path:
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
    preserve_adapter_output(run_dir, "idris2", completed.stdout, completed.stderr)
    bundle = parse_json(completed.stdout)
    checked = validate_complete_run(manifest, complete_adapter_results(manifest, bundle.get("results", []), "idris2"), "idris2", expected_operations=expected_operations)
    return write_bundle(run_dir, "idris2", checked, completed.stdout, completed.stderr)


def benchmark_rust(args: argparse.Namespace, root: Path, manifest: dict[str, object], expected_operations: dict[str, int], run_dir: Path) -> Path:
    found = discover(root, "rust", args.rust_path)
    if found["status"] != "available":
        raise SystemExit(found["reason"])
    implementation_path = Path(found["path"])
    cargo = shutil.which(args.cargo)
    rustc = shutil.which(args.rustc)
    if cargo is None or rustc is None:
        raise SystemExit(f"Rust toolchain unavailable: cargo={args.cargo}, rustc={args.rustc}")
    metadata = parse_json(subprocess.run([cargo, "metadata", "--no-deps", "--format-version", "1"], cwd=implementation_path, check=True, text=True, capture_output=True).stdout)
    packages = metadata.get("packages", [])
    if not any(package.get("name") == "gafro" for package in packages):
        raise SystemExit("Rust checkout Cargo metadata has no gafro package")
    revision, dirty = repository_identity(implementation_path)
    rustc_verbose = subprocess.run([rustc, "-Vv"], check=True, text=True, capture_output=True).stdout
    compiler = next((line for line in rustc_verbose.splitlines() if line.startswith("rustc ")), "rustc unknown")
    target = next((line.split(":", 1)[1].strip() for line in rustc_verbose.splitlines() if line.startswith("host:")), "unknown")
    rustflags = os.environ.get("RUSTFLAGS", "none")
    with tempfile.TemporaryDirectory(prefix="gafro-benchmark-rust-") as directory:
        staging = Path(directory)
        source = staging / "adapter"
        shutil.copytree(root / "rust", source)
        cargo_toml = source / "Cargo.toml"
        cargo_toml.write_text(cargo_toml.read_text().replace("__GAFRO_RUST_PATH__", str(implementation_path)))
        target_dir = staging / "target"
        environment = {**os.environ, "CARGO_TARGET_DIR": str(target_dir)}
        # The copied adapter lock records the placeholder path package; refresh
        # it after substituting the explicitly selected sibling checkout.
        subprocess.run([cargo, "generate-lockfile", "--offline"], cwd=source, env=environment, check=True)
        subprocess.run([cargo, "build", "--release", "--locked"], cwd=source, env=environment, check=True)
        completed = subprocess.run([
            str(target_dir / "release/gafro-bench-rust"), "--profile", args.profile,
            "--revision", revision, "--dirty", str(dirty).lower(), "--compiler", compiler,
            "--target", target, "--rustflags", rustflags,
        ], check=True, text=True, capture_output=True)
    preserve_adapter_output(run_dir, "rust", completed.stdout, completed.stderr)
    bundle = parse_json(completed.stdout)
    checked = validate_complete_run(manifest, bundle.get("results", []), "rust", expected_operations=expected_operations)
    return write_bundle(run_dir, "rust", checked, completed.stdout, completed.stderr)


def create_run_directory(root: Path) -> tuple[str, Path]:
    base = root / "results" / "runs"
    base.mkdir(parents=True, exist_ok=True)
    stem = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    for suffix in range(1000):
        run_id = stem if suffix == 0 else f"{stem}-{suffix}"
        destination = base / run_id
        try:
            destination.mkdir()
            return run_id, destination
        except FileExistsError:
            pass
    raise SystemExit("could not allocate a unique run ID")


def publish_report(run_dir: Path, manifest: dict[str, object], run_id: str) -> None:
    results = []
    host = json.loads((run_dir / "host-toolchain.json").read_text())
    for path in sorted((run_dir / "adapters").glob("*.json")):
        bundle = parse_json(path.read_text())
        for result in bundle.get("results", []):
            results.append({**result, "host": {**host, **result.get("host", {})}})
    model = build_summary_model(manifest, results, run_ids=[run_id])
    report_dir = run_dir / "report"
    report_dir.mkdir(exist_ok=True)
    (report_dir / "summary.json").write_text(json.dumps(model, indent=2, sort_keys=True) + "\n")
    (report_dir / "summary.md").write_text(render_summary_markdown(model))


def regenerate_report(args: argparse.Namespace, root: Path) -> int:
    if not args.run_id or Path(args.run_id).name != args.run_id:
        raise SystemExit("report requires a simple --run-id")
    run_dir = root / "results" / "runs" / args.run_id
    if not run_dir.is_dir():
        raise SystemExit(f"unknown run ID: {args.run_id}")
    manifest = validate_manifest(json.loads((run_dir / "manifest.json").read_text()))
    publish_report(run_dir, manifest, args.run_id)
    print(run_dir / "report")
    return 0


def benchmark(args: argparse.Namespace, root: Path) -> int:
    requested = tuple(part.strip() for part in args.implementations.split(",") if part.strip())
    unknown = sorted(set(requested) - set(IMPLEMENTATIONS))
    if unknown:
        raise SystemExit(f"unknown implementations: {', '.join(unknown)}")
    manifest = validate_manifest(json.loads((root / "contracts/workloads-v1.json").read_text()))
    run_id, run_dir = create_run_directory(root)
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    config = {
        "run_id": run_id, "profile": args.profile, "implementations": list(requested),
        "paths": {family: getattr(args, f"{family}_path") for family in IMPLEMENTATIONS},
        "cpp_build_path": args.cpp_build_path, "cpp_compiler": args.cpp_compiler,
        "idris2_compiler": args.idris2_compiler, "idris2_backend": args.idris2_backend,
        "cargo": args.cargo, "rustc": args.rustc,
    }
    (run_dir / "runner-config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n")
    host = {"system": platform.system(), "release": platform.release(), "machine": platform.machine(), "python": platform.python_version()}
    (run_dir / "host-toolchain.json").write_text(json.dumps(host, indent=2, sort_keys=True) + "\n")
    expected_operations = 1000 if args.profile == "smoke" else 10000
    definitions = {item["id"]: item for item in manifest["workloads"]}
    expected_by_workload = {
        workload_id: (item["operands"].get("batch_size", expected_operations) if args.profile == "smoke" else item["operations_per_sample"])
        for workload_id, item in definitions.items()
    }
    destinations = []
    try:
        if "cpp" in requested:
            destinations.append(benchmark_cpp(args, root, manifest, expected_operations, run_dir))
        if "idris2" in requested:
            destinations.append(benchmark_idris2(args, root, manifest, expected_operations, run_dir))
        if "rust" in requested:
            destinations.append(benchmark_rust(args, root, manifest, expected_by_workload, run_dir))
        publish_report(run_dir, manifest, run_id)
    except (Exception, SystemExit) as exc:
        (run_dir / "diagnostic.txt").write_text(f"{type(exc).__name__}: {exc}\n")
        raise
    for destination in destinations:
        print(destination)
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Gafro benchmark orchestrator")
    result.add_argument("command", choices=("inventory", "smoke", "benchmark", "report"))
    result.add_argument("--run-id")
    for family in IMPLEMENTATIONS:
        result.add_argument(f"--{family}-path")
    result.add_argument("--cpp-build-path")
    result.add_argument("--cpp-compiler")
    result.add_argument("--idris2-compiler", default="idris2")
    result.add_argument("--idris2-backend", default="chez", choices=("chez", "refc"))
    result.add_argument("--cargo", default="cargo")
    result.add_argument("--rustc", default="rustc")
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
    if args.command == "report":
        return regenerate_report(args, root)
    return benchmark(args, root)


if __name__ == "__main__":
    raise SystemExit(main())
