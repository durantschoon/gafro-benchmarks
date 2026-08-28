import argparse
import contextlib
import io
import json
import unittest
from pathlib import Path

from benchmark_harness.cli import gpu_plan
from benchmark_harness.core import (
    ContractError,
    plan_gpu_sweep,
    ratio_compatible,
    reconcile_results,
    validate_heterogeneous_contract,
    validate_ratio_compatibility,
    validate_result,
    workload_definition_id,
    workload_input_digest,
)

ROOT = Path(__file__).resolve().parents[1]


def execution(scope="cpu_optimized_batch", scalar_type="fp64"):
    gpu = scope in {"kernel", "resident_pipeline", "end_to_end"}
    comparison = {
        "cpu_scalar_loop": "application_end_to_end",
        "cpu_optimized_batch": "application_end_to_end",
        "kernel": "device_kernel",
        "resident_pipeline": "device_resident_pipeline",
        "end_to_end": "application_end_to_end",
    }[scope]
    synchronization = {
        "cpu_scalar_loop": "completed_before_host_timer_stop",
        "cpu_optimized_batch": "completed_before_host_timer_stop",
        "kernel": "cuda_event_synchronize_after_stop_on_measured_stream",
        "resident_pipeline": "stream_synchronize_after_all_device_work",
        "end_to_end": "host_wait_after_d2h_before_observation",
    }[scope]
    phases = {
        "cpu_scalar_loop": ["scalar_loop", "host_observation"],
        "cpu_optimized_batch": ["optimized_batch", "host_observation"],
        "kernel": ["kernel_execution", "event_synchronization"],
        "resident_pipeline": ["all_device_work", "device_synchronization"],
        "end_to_end": ["host_packing", "h2d", "execution", "d2h", "host_synchronization", "host_observation"],
    }[scope]
    return {
        "operation": "batch_point_transform", "batch_size": 256,
        "batch_semantics": "one independently transformed point per output item",
        "invocations_per_sample": 1, "input_fixture_id": "points-v1",
        "input_digest": "sha256:fixture", "output_elements_per_item": 5,
        "scalar_type": scalar_type, "input_layout": "structure_of_arrays_xyzw",
        "output_layout": "structure_of_arrays_xyzw",
        "device_residency": "host_and_device" if scope == "end_to_end" else "device" if gpu else "host",
        "stream_count": 1 if gpu else 0, "state": "warm", "timing_scope": scope,
        "comparison_scope": comparison,
        "timer": "cuda_event" if scope in {"kernel", "resident_pipeline"} else "host_monotonic",
        "synchronization": synchronization,
        "packing_boundary": "excluded_prepacked" if scope in {"kernel", "resident_pipeline"} else "included_host_packing",
        "allocation_boundary": "excluded_preallocated_buffers", "timed_phases": phases,
        "workload_definition_id": "fixture-definition",
    }


def result(scope="cpu_optimized_batch", scalar_type="fp64", family="cpp"):
    row = {
        "schema_version": "gafro-benchmark-result/v1",
        "implementation": {"family": family, "name": "fixture", "repository_revision": "abc",
                           "dirty": False, "compiler": "fixture compiler", "backend": "release", "flags": ["optimized"]},
        "host": {"system": "FixtureOS", "machine": "fixture64"},
        "workload_id": "fixture/batch_point_transform", "status": "supported", "reason": "",
        "warmup_operations": 256, "operations_per_sample": 256,
        "sample_durations_ns": [1000, 1100, 900], "execution": execution(scope, scalar_type),
        "oracle": {"value": 1.0, "deterministic_inputs": True, "full_output_checked": True,
                   "passed": True,
                   "reference_precision": "cpu-fp64-or-higher" if scalar_type == "fp32" else "cpu-fp80-or-higher",
                   "comparison_method": "all coefficients", "completed_before_timing": True,
                   "checked_output_elements": 1280,
                   "absolute_tolerance": 1e-5 if scalar_type == "fp32" else 1e-10,
                   "relative_tolerance": 1e-5 if scalar_type == "fp32" else 1e-10},
    }
    if scope in {"cpu_scalar_loop", "cpu_optimized_batch"}:
        row["cpu"] = {"thread_count": 1, "affinity": "cpu0", "simd_target": "avx2"}
    else:
        row["gpu"] = {"model": "Fixture GPU", "uuid": "GPU-fixture", "compute_capability": "9.0",
                      "driver": "fixture-driver", "runtime": "fixture-runtime", "toolkit": "fixture-toolkit",
                      "clocks": None, "power_mode": None, "ecc_state": "off", "mig_state": "disabled",
                      "launch_geometry": {"grid": [1, 1, 1], "block": [256, 1, 1]},
                      "stream": {"index": 0}, "memory_bytes": 32768,
                      "cuda_event_timing": {"used": scope != "end_to_end",
                                            "stream_matches_launch": scope != "end_to_end",
                                            "includes_synchronization": scope != "end_to_end"}}
    return row


class HeterogeneousContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = validate_heterogeneous_contract(json.loads((ROOT / "contracts/heterogeneous-v1.json").read_text()))

    def test_contract_has_latency_crossover_and_throughput_sweeps(self):
        sweep = self.contract["batch_sweep"]
        self.assertLess(max(sweep["latency_sensitive"]), min(sweep["throughput"]))
        self.assertIn(256, sweep["expected_crossover"])
        self.assertEqual(set(self.contract["precision_experiments"]), {"fp32", "fp64"})

    def test_cpu_and_gpu_end_to_end_are_application_ratio_compatible(self):
        validate_ratio_compatibility(result(family="cpp"), result("end_to_end", family="rust"))

    def test_kernel_and_resident_scopes_do_not_masquerade_as_end_to_end(self):
        for scope in ("kernel", "resident_pipeline"):
            with self.assertRaisesRegex(ContractError, "comparison_scope"):
                validate_ratio_compatibility(result(), result(scope, family="rust"))

    def test_ratio_rejects_mixed_precision_batch_semantics_size_and_layout(self):
        for field, value in (("scalar_type", "fp32"), ("batch_semantics", "reduction"),
                             ("batch_size", 512), ("output_layout", "array_of_structures")):
            other = result(family="rust")
            other["execution"][field] = value
            if field == "scalar_type":
                other["oracle"]["absolute_tolerance"] = other["oracle"]["relative_tolerance"] = 1e-5
                other["oracle"]["reference_precision"] = "cpu-fp64-or-higher"
            with self.assertRaisesRegex(ContractError, field):
                validate_ratio_compatibility(result(), other)

    def test_validation_rejects_wrong_timer_and_incomplete_synchronization(self):
        row = result("kernel")
        row["execution"]["timer"] = "host_monotonic"
        with self.assertRaisesRegex(ContractError, "cuda_event"):
            validate_result(row)
        row = result("end_to_end")
        row["execution"]["synchronization"] = "kernel_launch_only"
        with self.assertRaisesRegex(ContractError, "incomplete synchronization"):
            validate_result(row)

    def test_validation_rejects_cuda_events_or_hidden_phases_for_end_to_end(self):
        row = result("end_to_end")
        row["gpu"]["cuda_event_timing"]["used"] = True
        with self.assertRaisesRegex(ContractError, "host timing"):
            validate_result(row)
        row = result("end_to_end")
        row["execution"]["timed_phases"].remove("d2h")
        with self.assertRaisesRegex(ContractError, "timed_phases"):
            validate_result(row)

    def test_end_to_end_waits_before_host_observation(self):
        phases = result("end_to_end")["execution"]["timed_phases"]
        self.assertLess(phases.index("host_synchronization"), phases.index("host_observation"))

    def test_kernel_and_resident_require_exact_timed_phases(self):
        for scope in ("kernel", "resident_pipeline"):
            row = result(scope)
            row["execution"]["timed_phases"] = ["not_the_declared_boundary"]
            with self.assertRaisesRegex(ContractError, "timed_phases"):
                validate_result(row)

    def test_validation_requires_full_high_precision_oracle(self):
        row = result(scalar_type="fp32")
        row["oracle"]["full_output_checked"] = False
        with self.assertRaisesRegex(ContractError, "full_output_checked"):
            validate_result(row)
        row = result()
        row["oracle"]["checked_output_elements"] -= 1
        with self.assertRaisesRegex(ContractError, "complete output"):
            validate_result(row)
        row = result()
        row["oracle"]["reference_precision"] = "gpu-fp16"
        with self.assertRaisesRegex(ContractError, "reference_precision"):
            validate_result(row)
        row = result()
        row["oracle"]["completed_before_timing"] = False
        with self.assertRaisesRegex(ContractError, "completed_before_timing"):
            validate_result(row)

    def test_validation_requires_cpu_and_gpu_provenance(self):
        row = result()
        del row["cpu"]["affinity"]
        with self.assertRaisesRegex(ContractError, "affinity"):
            validate_result(row)
        row = result("kernel")
        row["gpu"]["uuid"] = ""
        with self.assertRaisesRegex(ContractError, "uuid"):
            validate_result(row)
        row = result("kernel")
        row["gpu"]["launch_geometry"] = {}
        with self.assertRaisesRegex(ContractError, "launch_geometry"):
            validate_result(row)

    def test_memory_limit_truncates_only_suffix_with_reason(self):
        plan = plan_gpu_sweep(self.contract, operation="batch_point_transform", scalar_type="fp64",
                              input_layout="structure_of_arrays", bytes_per_item=128,
                              cuda_available=True, available_memory_bytes=4096)
        self.assertEqual(plan["batches"][-1]["batch_size"], 32)
        self.assertEqual(plan["truncation"]["first_omitted_batch_size"], 64)
        self.assertTrue(plan["truncation"]["reason"])

    def test_unavailable_cuda_is_a_clean_empty_plan(self):
        plan = plan_gpu_sweep(self.contract, operation="batch_point_transform", scalar_type="fp64",
                              input_layout="structure_of_arrays", bytes_per_item=128,
                              cuda_available=False, unavailable_reason="fixture host has no CUDA")
        self.assertEqual(plan["status"], "unavailable")
        self.assertEqual(plan["batches"], [])

    def test_cli_plans_explicitly_unavailable_cuda_without_hardware(self):
        args = argparse.Namespace(cuda_status="unavailable", cuda_unavailable_reason="fixture unavailable",
                                  device_memory_bytes=None, operation="batch_point_transform", scalar_type="fp64",
                                  input_layout="structure_of_arrays", bytes_per_item=128)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(gpu_plan(args, ROOT), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "unavailable")

    def test_legacy_and_heterogeneous_rows_are_not_directly_ratio_compatible(self):
        legacy = result()
        del legacy["execution"]
        del legacy["cpu"]
        self.assertFalse(ratio_compatible(legacy, result(family="rust")))

    def test_gpu_stream_and_hardware_configuration_must_match(self):
        first = result("end_to_end", family="cpp")
        second = result("end_to_end", family="rust")
        second["execution"]["stream_count"] = 8
        with self.assertRaisesRegex(ContractError, "stream_count"):
            validate_ratio_compatibility(first, second)
        second = result("end_to_end", family="rust")
        second["gpu"]["uuid"] = "GPU-other"
        with self.assertRaisesRegex(ContractError, "gpu_configuration"):
            validate_ratio_compatibility(first, second)

    def test_reconciliation_binds_execution_to_workload_contract(self):
        manifest = json.loads((ROOT / "contracts/workloads-v1.json").read_text())
        definition = next(item for item in manifest["workloads"] if item["id"] == "batch_point_transform/f64/n256/e1_lane0")
        row = result()
        row["workload_id"] = definition["id"]
        row["execution"].update(definition["execution_contract"])
        row["execution"]["input_fixture_id"] = f"{definition['id']}/inputs-v1"
        row["execution"]["input_digest"] = workload_input_digest(definition)
        row["execution"]["workload_definition_id"] = workload_definition_id(definition)
        reconcile_results(manifest, [row])
        row["execution"]["operation"] = "batch_motor_composition"
        with self.assertRaisesRegex(ContractError, "operation"):
            reconcile_results(manifest, [row])


if __name__ == "__main__":
    unittest.main()
