"""Pure parsing, validation, reconciliation, and report planning."""

from __future__ import annotations

import json
import math
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
