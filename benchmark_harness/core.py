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
HETEROGENEOUS_VERSION = "gafro-benchmark-heterogeneous/v1"
SCALAR_TYPES = frozenset({"fp32", "fp64"})
TIMING_SCOPES = frozenset({
    "cpu_scalar_loop", "cpu_optimized_batch", "kernel",
    "resident_pipeline", "end_to_end",
})
GPU_TIMING_SCOPES = frozenset({"kernel", "resident_pipeline", "end_to_end"})
RATIO_DIMENSIONS = (
    "operation", "batch_size", "batch_semantics", "scalar_type",
    "input_layout", "output_layout", "comparison_scope", "state",
    "packing_boundary", "allocation_boundary", "invocations_per_sample",
    "input_fixture_id", "input_digest", "output_elements_per_item",
)


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


def validate_heterogeneous_contract(value: Any) -> dict[str, Any]:
    """Validate the versioned CPU/CUDA experiment definition."""
    data = _mapping(value, "heterogeneous contract")
    _equals(data, "schema_version", HETEROGENEOUS_VERSION)
    dimensions = _list(data, "dimensions")
    required = set(RATIO_DIMENSIONS + ("device_residency", "stream_count", "timing_scope"))
    missing = sorted(required - set(dimensions))
    if missing:
        raise ContractError(f"heterogeneous contract missing dimensions: {', '.join(missing)}")
    sweep = _mapping(data.get("batch_sweep"), "batch_sweep")
    sizes = _list(sweep, "sizes")
    if (not sizes or sizes != sorted(set(sizes)) or
            any(not isinstance(size, int) or isinstance(size, bool) or size <= 0 for size in sizes)):
        raise ContractError("batch_sweep.sizes must be unique increasing positive integers")
    for tier in ("latency_sensitive", "expected_crossover", "throughput"):
        members = _list(sweep, tier)
        if not members or any(member not in sizes for member in members):
            raise ContractError(f"batch_sweep.{tier} must be a non-empty subset of sizes")
    _nonempty_string(sweep, "truncation_policy")
    precisions = _mapping(data.get("precision_experiments"), "precision_experiments")
    for scalar_type in SCALAR_TYPES:
        experiment = _mapping(precisions.get(scalar_type), f"precision_experiments.{scalar_type}")
        _nonempty_string(experiment, "reference")
        for field in ("absolute_tolerance", "relative_tolerance"):
            number = experiment.get(field)
            if (not isinstance(number, (int, float)) or isinstance(number, bool) or
                    number <= 0 or not math.isfinite(number)):
                raise ContractError(f"precision_experiments.{scalar_type}.{field} must be positive and finite")
    measurements = _mapping(data.get("measurements"), "measurements")
    if set(measurements) != TIMING_SCOPES:
        raise ContractError("measurements must define every CPU/CUDA timing scope exactly once")
    _nonempty_string(data, "operation_count")
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
    if "execution" in data:
        _validate_execution(data, require_evidence=status == "supported")
    return dict(data)


def validate_ratio_compatibility(left: Mapping[str, Any], right: Mapping[str, Any]) -> None:
    """Reject a ratio whose semantics or application timing boundary differ."""
    checked = (validate_result(left), validate_result(right))
    for result in checked:
        if result["status"] != "supported":
            raise ContractError("ratio compatibility requires two supported results")
        if "execution" not in result:
            raise ContractError("ratio compatibility requires heterogeneous execution metadata")
    left_execution, right_execution = (item["execution"] for item in checked)
    mismatches = [field for field in RATIO_DIMENSIONS if left_execution[field] != right_execution[field]]
    if mismatches:
        raise ContractError(f"ratio-incompatible execution dimensions: {', '.join(mismatches)}")


def ratio_compatible(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    try:
        validate_ratio_compatibility(left, right)
    except ContractError:
        return False
    return True


def plan_gpu_sweep(
    contract: Mapping[str, Any], *, operation: str, scalar_type: str,
    input_layout: str, bytes_per_item: int, cuda_available: bool,
    available_memory_bytes: int | None = None,
    unavailable_reason: str = "CUDA hardware unavailable",
) -> dict[str, Any]:
    """Build a deterministic, side-effect-free GPU sweep plan."""
    checked = validate_heterogeneous_contract(contract)
    if scalar_type not in SCALAR_TYPES:
        raise ContractError(f"scalar_type must be one of: {', '.join(sorted(SCALAR_TYPES))}")
    if not operation.strip() or not input_layout.strip():
        raise ContractError("operation and input_layout must be non-empty")
    if not isinstance(bytes_per_item, int) or isinstance(bytes_per_item, bool) or bytes_per_item <= 0:
        raise ContractError("bytes_per_item must be a positive integer")
    base = {
        "schema_version": "gafro-benchmark-gpu-plan/v1",
        "operation": operation,
        "scalar_type": scalar_type,
        "input_layout": input_layout,
        "timing_scopes": ["kernel", "resident_pipeline", "end_to_end"],
        "oracle": checked["oracle"],
    }
    if not cuda_available:
        if not unavailable_reason.strip():
            raise ContractError("an unavailable CUDA plan requires a reason")
        return {**base, "status": "unavailable", "reason": unavailable_reason,
                "batches": [], "truncation": None}
    if available_memory_bytes is not None and (
            not isinstance(available_memory_bytes, int) or isinstance(available_memory_bytes, bool) or
            available_memory_bytes <= 0):
        raise ContractError("available_memory_bytes must be a positive integer")
    batches = []
    truncation = None
    for batch_size in checked["batch_sweep"]["sizes"]:
        required_bytes = batch_size * bytes_per_item
        if available_memory_bytes is not None and required_bytes > available_memory_bytes:
            truncation = {
                "first_omitted_batch_size": batch_size,
                "required_memory_bytes": required_bytes,
                "available_memory_bytes": available_memory_bytes,
                "reason": "canonical sweep truncated because required buffers exceed the declared device-memory limit",
            }
            break
        batches.append({"batch_size": batch_size, "memory_bytes": required_bytes})
    return {**base, "status": "available", "reason": "", "batches": batches, "truncation": truncation}


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
                    "execution": result.get("execution"),
                }
                supported.append(cell)
            cells.append(cell)
        environment_compatible = _compatible_environments(supported)
        execution_compatible = _compatible_execution_contracts(supported)
        compatible = environment_compatible and execution_compatible
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
            "environments_compatible": environment_compatible,
            "execution_contracts_compatible": execution_compatible,
            "ratio_compatible": compatible,
            "comparison_note": ("compatible within recorded metadata" if compatible else
                                "rankings omitted: fewer than two supported implementations" if len(supported) < 2 else
                                "rankings omitted: heterogeneous execution dimensions differ" if not execution_compatible else
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


def _compatible_execution_contracts(cells: list[Mapping[str, Any]]) -> bool:
    """Preserve legacy reports, but never ratio mixed heterogeneous rows."""
    if len(cells) < 2:
        return False
    executions = [cell.get("execution") for cell in cells]
    if all(execution is None for execution in executions):
        return True
    if any(execution is None for execution in executions):
        return False
    first = executions[0]
    return all(
        all(first[field] == execution[field] for field in RATIO_DIMENSIONS)
        for execution in executions[1:]
    )


def _validate_execution(data: Mapping[str, Any], *, require_evidence: bool) -> None:
    workload_id = str(data.get("workload_id", "result"))
    execution = _mapping(data.get("execution"), "execution")
    required = (
        "operation", "batch_size", "batch_semantics", "invocations_per_sample", "scalar_type",
        "input_fixture_id", "input_digest", "output_elements_per_item",
        "input_layout", "output_layout", "device_residency", "stream_count",
        "state", "timing_scope", "comparison_scope", "timer", "synchronization",
        "packing_boundary", "allocation_boundary", "timed_phases",
    )
    for field in required:
        if field not in execution:
            raise ContractError(f"{workload_id}: execution missing {field}")
    for field in (
        "operation", "batch_semantics", "input_fixture_id", "input_digest",
        "input_layout", "output_layout", "synchronization",
        "packing_boundary", "allocation_boundary",
    ):
        _nonempty_string(execution, field)
    _positive_int(execution, "batch_size")
    invocations = _positive_int(execution, "invocations_per_sample")
    output_elements_per_item = _positive_int(execution, "output_elements_per_item")
    if require_evidence and data["operations_per_sample"] != execution["batch_size"] * invocations:
        raise ContractError(f"{workload_id}: operations_per_sample must equal batch_size times invocations_per_sample")
    scalar_type = _nonempty_string(execution, "scalar_type")
    if scalar_type not in SCALAR_TYPES:
        raise ContractError(f"{workload_id}: scalar_type must be fp32 or fp64")
    residency = _nonempty_string(execution, "device_residency")
    if residency not in {"host", "device", "host_and_device"}:
        raise ContractError(f"{workload_id}: invalid device_residency")
    stream_count = _positive_int(execution, "stream_count", allow_zero=True)
    state = _nonempty_string(execution, "state")
    if state not in {"warm", "cold"}:
        raise ContractError(f"{workload_id}: state must be warm or cold")
    scope = _nonempty_string(execution, "timing_scope")
    if scope not in TIMING_SCOPES:
        raise ContractError(f"{workload_id}: unknown timing_scope {scope}")
    timer = _nonempty_string(execution, "timer")
    expected_timer = "cuda_event" if scope in {"kernel", "resident_pipeline"} else "host_monotonic"
    if timer != expected_timer:
        raise ContractError(f"{workload_id}: {scope} requires {expected_timer} timing")
    comparison_scope = {
        "cpu_scalar_loop": "application_end_to_end",
        "cpu_optimized_batch": "application_end_to_end",
        "kernel": "device_kernel",
        "resident_pipeline": "device_resident_pipeline",
        "end_to_end": "application_end_to_end",
    }[scope]
    if execution["comparison_scope"] != comparison_scope:
        raise ContractError(f"{workload_id}: {scope} requires comparison_scope {comparison_scope}")
    synchronization = {
        "cpu_scalar_loop": "completed_before_host_timer_stop",
        "cpu_optimized_batch": "completed_before_host_timer_stop",
        "kernel": "cuda_event_synchronize_after_stop_on_measured_stream",
        "resident_pipeline": "stream_synchronize_after_all_device_work",
        "end_to_end": "host_wait_after_d2h_before_observation",
    }[scope]
    if execution["synchronization"] != synchronization:
        raise ContractError(f"{workload_id}: incomplete synchronization for {scope}")
    phases = _list(execution, "timed_phases")
    if scope == "end_to_end":
        expected_phases = ["host_packing", "h2d", "execution", "d2h", "host_observation", "host_synchronization"]
        if phases != expected_phases or execution["packing_boundary"] != "included_host_packing":
            raise ContractError(f"{workload_id}: end_to_end must include host packing, transfers, execution, observation, and synchronization")
    elif not phases or any(not isinstance(phase, str) or not phase for phase in phases):
        raise ContractError(f"{workload_id}: timed_phases must be explicit")
    if scope in GPU_TIMING_SCOPES:
        if stream_count < 1:
            raise ContractError(f"{workload_id}: GPU timing requires at least one stream")
        expected_residency = "host_and_device" if scope == "end_to_end" else "device"
        if residency != expected_residency:
            raise ContractError(f"{workload_id}: {scope} requires {expected_residency} residency")
        _validate_gpu_metadata(data, scope)
    else:
        if stream_count != 0 or residency != "host":
            raise ContractError(f"{workload_id}: CPU timing requires host residency and zero CUDA streams")
        _validate_cpu_metadata(data)
    if require_evidence:
        oracle = _mapping(data.get("oracle"), "oracle")
        for flag in ("deterministic_inputs", "full_output_checked", "passed"):
            if oracle.get(flag) is not True:
                raise ContractError(f"{workload_id}: oracle.{flag} must be true before timing")
        _nonempty_string(oracle, "reference_precision")
        _nonempty_string(oracle, "comparison_method")
        checked_elements = _positive_int(oracle, "checked_output_elements")
        if checked_elements != execution["batch_size"] * output_elements_per_item:
            raise ContractError(f"{workload_id}: oracle.checked_output_elements must cover the complete output")
        maximum = 1e-5 if scalar_type == "fp32" else 1e-10
        for field in ("absolute_tolerance", "relative_tolerance"):
            tolerance = oracle.get(field)
            if (not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or
                    tolerance <= 0 or not math.isfinite(tolerance)):
                raise ContractError(f"{workload_id}: oracle.{field} must be positive and finite")
            if tolerance > maximum:
                raise ContractError(f"{workload_id}: oracle.{field} exceeds the {scalar_type} contract tolerance")


def _validate_cpu_metadata(data: Mapping[str, Any]) -> None:
    workload_id = str(data.get("workload_id", "result"))
    cpu = _mapping(data.get("cpu"), "cpu")
    _positive_int(cpu, "thread_count")
    for field in ("affinity", "simd_target"):
        try:
            _nonempty_string(cpu, field)
        except ContractError as exc:
            raise ContractError(f"{workload_id}: cpu.{field} must be recorded") from exc


def _validate_gpu_metadata(data: Mapping[str, Any], scope: str) -> None:
    workload_id = str(data.get("workload_id", "result"))
    gpu = _mapping(data.get("gpu"), "gpu")
    for field in ("model", "uuid", "compute_capability", "driver", "runtime", "toolkit", "ecc_state", "mig_state"):
        try:
            _nonempty_string(gpu, field)
        except ContractError as exc:
            raise ContractError(f"{workload_id}: gpu.{field} must be recorded") from exc
    for field in ("clocks", "power_mode"):
        value = gpu.get(field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ContractError(f"{workload_id}: gpu.{field} must be null or a non-empty string")
    for field in ("launch_geometry", "stream", "cuda_event_timing"):
        _mapping(gpu.get(field), f"gpu.{field}")
    memory_bytes = gpu.get("memory_bytes")
    if not isinstance(memory_bytes, int) or isinstance(memory_bytes, bool) or memory_bytes < 0:
        raise ContractError(f"{workload_id}: gpu.memory_bytes must be a non-negative integer")
    event = _mapping(gpu["cuda_event_timing"], "gpu.cuda_event_timing")
    if scope in {"kernel", "resident_pipeline"}:
        if event.get("used") is not True or event.get("stream_matches_launch") is not True:
            raise ContractError(f"{workload_id}: CUDA events must bracket work on the measured stream")
        if event.get("includes_synchronization") is not True:
            raise ContractError(f"{workload_id}: CUDA-event timing metadata must record synchronization")
    elif event.get("used") is not False:
        raise ContractError(f"{workload_id}: end_to_end must use host timing, not CUDA events")


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
