"""Pure parsing, validation, reconciliation, and report planning."""

from __future__ import annotations

import json
import math
import hashlib
from collections.abc import Iterable, Mapping
from statistics import median
from typing import Any

SCHEMA_VERSION = "gafro-benchmark-result/v1"
MANIFEST_VERSION = "gafro-benchmark-workloads/v1"
STATUSES = frozenset({"supported", "unsupported", "unavailable", "failed"})
IMPLEMENTATIONS = ("cpp", "idris2", "rust")


class ContractError(ValueError):
    """Raised when benchmark evidence violates the versioned contract."""


def parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid JSON: {exc.msg}") from exc


def validate_manifest(value: Any) -> dict[str, Any]:
    data = _mapping(value, "manifest")
    _equals(data, "schema_version", MANIFEST_VERSION)
    workloads = _list(data, "workloads")
    seen: set[str] = set()
    required = (
        "id", "operation", "operands", "numeric_type", "warmup_operations",
        "operations_per_sample", "observable",
    )
    for index, raw in enumerate(workloads):
        item = _mapping(raw, f"workloads[{index}]")
        for field in required:
            if field not in item:
                raise ContractError(f"workloads[{index}] missing {field}")
        workload_id = _nonempty_string(item, "id")
        if workload_id in seen:
            raise ContractError(f"duplicate workload id: {workload_id}")
        seen.add(workload_id)
        _positive_int(item, "warmup_operations", allow_zero=True)
        _positive_int(item, "operations_per_sample")
        _mapping(item["observable"], f"workloads[{index}].observable")
    return dict(data)


def validate_result(value: Any) -> dict[str, Any]:
    data = _mapping(value, "result")
    _equals(data, "schema_version", SCHEMA_VERSION)
    implementation = _mapping(data.get("implementation"), "implementation")
    family = _nonempty_string(implementation, "family")
    if family not in IMPLEMENTATIONS:
        raise ContractError(f"unknown implementation family: {family}")
    for field in ("name", "repository_revision", "compiler", "backend"):
        _nonempty_string(implementation, field)
    if not isinstance(implementation.get("dirty"), bool):
        raise ContractError("implementation.dirty must be boolean")
    if not isinstance(implementation.get("flags"), list):
        raise ContractError("implementation.flags must be a list")
    _mapping(data.get("host"), "host")
    workload_id = _nonempty_string(data, "workload_id")
    status = _nonempty_string(data, "status")
    if status not in STATUSES:
        raise ContractError(f"{workload_id}: invalid status {status}")
    reason = data.get("reason", "")
    if not isinstance(reason, str):
        raise ContractError(f"{workload_id}: reason must be a string")
    if status != "supported" and not reason.strip():
        raise ContractError(f"{workload_id}: {status} requires a reason")
    if status == "supported":
        warmup = _positive_int(data, "warmup_operations", allow_zero=True)
        operations = _positive_int(data, "operations_per_sample")
        samples = _list(data, "sample_durations_ns")
        if not samples:
            raise ContractError(f"{workload_id}: supported result needs samples")
        if any(not isinstance(x, (int, float)) or isinstance(x, bool) or x <= 0 or not math.isfinite(x) for x in samples):
            raise ContractError(f"{workload_id}: sample durations must be positive finite numbers")
        if warmup < 0 or operations <= 0 or "oracle" not in data:
            raise ContractError(f"{workload_id}: incomplete supported result")
    return dict(data)


def reconcile_results(manifest: Mapping[str, Any], results: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    checked_manifest = validate_manifest(manifest)
    workload_ids = {item["id"] for item in checked_manifest["workloads"]}
    reconciled: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw in results:
        result = validate_result(raw)
        key = (result["implementation"]["family"], result["workload_id"])
        if key in seen:
            raise ContractError(f"duplicate result: {key[0]}/{key[1]}")
        if result["workload_id"] not in workload_ids:
            raise ContractError(f"unknown workload: {result['workload_id']}")
        seen.add(key)
        reconciled.append(result)
    return sorted(reconciled, key=lambda item: (item["workload_id"], item["implementation"]["family"]))


def validate_complete_run(manifest: Mapping[str, Any], results: Iterable[Mapping[str, Any]], family: str, *, expected_operations: int | Mapping[str, int] | None = None) -> list[dict[str, Any]]:
    checked_manifest = validate_manifest(manifest)
    reconciled = reconcile_results(checked_manifest, results)
    expected_ids = {item["id"] for item in checked_manifest["workloads"]}
    actual_ids = {item["workload_id"] for item in reconciled if item["implementation"]["family"] == family}
    missing = sorted(expected_ids - actual_ids)
    if missing:
        raise ContractError(f"{family}: missing benchmark ids: {', '.join(missing)}")
    definitions = {item["id"]: item for item in checked_manifest["workloads"]}
    for result in reconciled:
        if result["implementation"]["family"] != family or result["status"] != "supported":
            continue
        expected = expected_operations.get(result["workload_id"]) if isinstance(expected_operations, Mapping) else expected_operations
        if expected is not None and result["operations_per_sample"] != expected:
            raise ContractError(f"{result['workload_id']}: inconsistent operation count")
        observable = definitions[result["workload_id"]]["observable"]
        actual = result["oracle"].get("value") if isinstance(result["oracle"], Mapping) else None
        if not isinstance(actual, (int, float)) or not math.isfinite(actual):
            raise ContractError(f"{result['workload_id']}: non-finite oracle")
        if abs(actual - observable["reference"]) > observable["absolute_tolerance"]:
            raise ContractError(f"{result['workload_id']}: wrong oracle value")
    return reconciled


def summarize_results(results: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    summary = []
    for result in sorted(results, key=lambda item: (item["workload_id"], item["implementation"]["family"])):
        row = {"workload_id": result["workload_id"], "implementation": result["implementation"]["family"], "status": result["status"]}
        if result["status"] == "supported":
            row["median_ns_per_operation"] = median(result["sample_durations_ns"]) / result["operations_per_sample"]
        else:
            row["reason"] = result["reason"]
        summary.append(row)
    return summary


def median_absolute_deviation(values: Iterable[float]) -> float:
    """Return the unscaled median absolute deviation (MAD)."""
    samples = tuple(float(value) for value in values)
    if not samples:
        raise ContractError("cannot summarize an empty sample set")
    center = median(samples)
    return median(abs(value - center) for value in samples)


def workload_definition_id(definition: Mapping[str, Any]) -> str:
    """Return a stable identity for the complete mathematical workload definition."""
    encoded = json.dumps(definition, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def build_summary_model(
    manifest: Mapping[str, Any],
    results: Iterable[Mapping[str, Any]],
    *,
    run_ids: Iterable[str],
) -> dict[str, Any]:
    """Build the single pure model consumed by JSON and Markdown renderers."""
    checked_manifest = validate_manifest(manifest)
    checked_results = reconcile_results(checked_manifest, results)
    definitions = {item["id"]: item for item in checked_manifest["workloads"]}
    by_key = {
        (item["implementation"]["family"], item["workload_id"]): item
        for item in checked_results
    }
    rows: list[dict[str, Any]] = []
    ordered_ids = sorted(definitions, key=lambda item: (item.startswith("batch_"), item))
    for workload_id in ordered_ids:
        definition = definitions[workload_id]
        category = "optimization_variant" if workload_id.startswith("batch_") else "canonical"
        cells = []
        supported = []
        for family in IMPLEMENTATIONS:
            result = by_key.get((family, workload_id))
            if result is None:
                cell = {"implementation": family, "status": "blocked", "reason": "no adapter evidence in this run"}
                cell["gap"] = gap_guidance("blocked", cell["reason"])
            elif result["status"] != "supported":
                cell = {"implementation": family, "status": result["status"], "reason": result["reason"]}
                cell["gap"] = gap_guidance(result["status"], result["reason"])
            else:
                per_operation = [float(value) / result["operations_per_sample"] for value in result["sample_durations_ns"]]
                cell = {
                    "implementation": family,
                    "status": "supported",
                    "sample_count": len(per_operation),
                    "samples_ns_per_operation": per_operation,
                    "median_ns_per_operation": median(per_operation),
                    "mad_ns_per_operation": median_absolute_deviation(per_operation),
                    "dispersion": "unscaled median absolute deviation (MAD)",
                    "environment": {
                        "host": result["host"],
                        "compiler": result["implementation"]["compiler"],
                        "backend": result["implementation"]["backend"],
                        "flags": result["implementation"]["flags"],
                    },
                    "repository_revision": result["implementation"]["repository_revision"],
                    "dirty": result["implementation"]["dirty"],
                    "capability_class": "equivalent_supported",
                }
                supported.append(cell)
            cells.append(cell)
        compatible = _compatible_environments(supported)
        ratios = []
        if compatible:
            for numerator in supported:
                for denominator in supported:
                    if numerator["implementation"] >= denominator["implementation"]:
                        continue
                    ratios.append({
                        "numerator": numerator["implementation"],
                        "denominator": denominator["implementation"],
                        "median_ratio": numerator["median_ns_per_operation"] / denominator["median_ns_per_operation"],
                    })
        winner = None
        if compatible and supported:
            fastest = min(supported, key=lambda item: item["median_ns_per_operation"])
            reason = ("batch size, structure-of-arrays layout, and SIMD amortization are likely contributors"
                      if category == "optimization_variant" else
                      "representation, compiler, and backend code generation are likely contributors")
            winner = {"implementation": fastest["implementation"], "scope": "this compatible run only", "likely_reason": reason}
        rows.append({
            "workload_id": workload_id,
            "category": category,
            "definition_id": workload_definition_id(definition),
            "cells": cells,
            "environments_compatible": compatible,
            "comparison_note": ("compatible within recorded metadata" if compatible else
                                "rankings omitted: fewer than two supported implementations" if len(supported) < 2 else
                                "rankings omitted: host or build metadata differ"),
            "ratios": ratios,
            "apparent_winner": winner,
        })
    return {
        "schema_version": "gafro-benchmark-summary/v1",
        "input_run_ids": sorted(set(run_ids)),
        "statistics": {"center": "median", "dispersion": "unscaled median absolute deviation (MAD)"},
        "comparison_policy": "Canonical GA computations are primary. Optimization variants are reported separately and never replace a canonical operation.",
        "workloads": rows,
    }


def render_summary_markdown(model: Mapping[str, Any]) -> str:
    """Render a deterministic human report from a summary model."""
    lines = [
        "# Gafro benchmark report", "",
        f"Input run IDs: {', '.join(model['input_run_ids'])}", "",
        model["comparison_policy"], "",
        "Values are median ns/op with unscaled median absolute deviation (MAD). A single run does not establish statistical significance.", "",
        "| Workload | C++ | Idris 2 | Rust | Comparison |", "| --- | ---: | ---: | ---: | --- |",
    ]
    for workload in model["workloads"]:
        cells = {cell["implementation"]: cell for cell in workload["cells"]}
        rendered = []
        for family in IMPLEMENTATIONS:
            cell = cells[family]
            if cell["status"] == "supported":
                rendered.append(f"{cell['median_ns_per_operation']:.3f} +/- {cell['mad_ns_per_operation']:.3f} (n={cell['sample_count']})")
            else:
                gap = cell["gap"]
                rendered.append(f"{gap['classification']}: {cell['reason']} Action: {gap['required_work']} Tradeoffs: {gap['tradeoffs']}")
        ratios = "; ".join(
            f"{ratio['numerator']}/{ratio['denominator']}={ratio['median_ratio']:.3f}"
            for ratio in workload["ratios"]
        ) or workload["comparison_note"]
        if workload["apparent_winner"]:
            winner = workload["apparent_winner"]
            ratios += f"; apparent winner: {winner['implementation']} ({winner['scope']}); {winner['likely_reason']}"
        if workload["category"] == "optimization_variant":
            ratios = "optimization variant; " + ratios
        lines.append(f"| `{workload['workload_id']}` | {rendered[0]} | {rendered[1]} | {rendered[2]} | {ratios} |")
    return "\n".join(lines) + "\n"


def gap_guidance(status: str, reason: str) -> dict[str, str]:
    """Classify a capability gap and provide actionable, conservative guidance."""
    lowered = reason.lower()
    if status in {"unavailable", "failed", "blocked"} or "fails the canonical" in lowered:
        return {
            "classification": "blocked_validation_or_environment",
            "algorithm_portability": "Do not port for timing until the environment or canonical oracle is satisfied.",
            "required_work": "restore the toolchain/checkout or adapt the existing API and pass the full oracle",
            "tradeoffs": "correctness risk first; added adapter and maintenance work",
        }
    if "layout" in lowered or "nearby" in lowered:
        return {
            "classification": "alternate_api_or_layout",
            "algorithm_portability": "The algorithm may be portable only with an explicit basis/layout conversion or a new matched workload.",
            "required_work": "document and validate conversion semantics, allocation boundaries, and the same observable",
            "tradeoffs": "conversion cost, allocation/layout changes, and reduced SIMD/GPU portability",
        }
    return {
        "classification": "genuinely_missing",
        "algorithm_portability": "A proven algorithm from another implementation can guide a native implementation, but cannot be benchmarked as if already present.",
        "required_work": "add a production API plus a language-native adapter and canonical oracle tests",
        "tradeoffs": "API complexity and maintenance; representation choices affect allocation and SIMD/GPU portability",
    }


def _compatible_environments(cells: list[Mapping[str, Any]]) -> bool:
    if len(cells) < 2:
        return False
    host_keys = ("system", "release", "machine", "python")
    hosts = {
        json.dumps({key: cell["environment"]["host"].get(key) for key in host_keys}, sort_keys=True)
        for cell in cells
    }
    # Compiler names necessarily differ by language. Backend and flags are build
    # provenance, not required to be textually identical, but must be present.
    builds_complete = all(cell["environment"]["compiler"] and cell["environment"]["backend"] for cell in cells)
    modes = []
    for cell in cells:
        build_text = " ".join([cell["environment"]["backend"], *map(str, cell["environment"]["flags"])]).lower()
        modes.append("debug" if "debug" in build_text and "ndebug" not in build_text else "non-debug")
    return len(hosts) == 1 and builds_complete and len(set(modes)) == 1


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{name} must be an object")
    return value


def _list(data: Mapping[str, Any], field: str) -> list[Any]:
    value = data.get(field)
    if not isinstance(value, list):
        raise ContractError(f"{field} must be a list")
    return value


def _nonempty_string(data: Mapping[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be a non-empty string")
    return value


def _positive_int(data: Mapping[str, Any], field: str, *, allow_zero: bool = False) -> int:
    value = data.get(field)
    minimum = 0 if allow_zero else 1
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ContractError(f"{field} must be an integer >= {minimum}")
    return value


def _equals(data: Mapping[str, Any], field: str, expected: str) -> None:
    if data.get(field) != expected:
        raise ContractError(f"{field} must be {expected!r}")
