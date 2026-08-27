import json
import unittest
from pathlib import Path

from benchmark_harness.core import ContractError, parse_json, reconcile_results, summarize_results, validate_complete_run, validate_manifest, validate_result

ROOT = Path(__file__).resolve().parents[1]


def identity(family="cpp"):
    return {"family": family, "name": "fixture", "repository_revision": "abc", "dirty": False, "compiler": "fixture", "backend": "cpu", "flags": []}


def result(family="cpp", workload="motor_composition_gp/f64/scalar", status="supported"):
    value = {"schema_version": "gafro-benchmark-result/v1", "implementation": identity(family), "host": {}, "workload_id": workload, "status": status, "reason": ""}
    if status == "supported":
        value.update(warmup_operations=1, operations_per_sample=2, sample_durations_ns=[20, 10, 30], oracle={"value": 1})
    else:
        value["reason"] = "fixture reason"
    return value


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = validate_manifest(json.loads((ROOT / "contracts/workloads-v1.json").read_text()))

    def test_malformed_json(self):
        with self.assertRaisesRegex(ContractError, "invalid JSON"):
            parse_json("{")

    def test_schema_mismatch(self):
        value = result()
        value["schema_version"] = "v0"
        with self.assertRaisesRegex(ContractError, "schema_version"):
            validate_result(value)

    def test_non_supported_requires_reason(self):
        value = result(status="failed")
        value["reason"] = ""
        with self.assertRaisesRegex(ContractError, "requires a reason"):
            validate_result(value)

    def test_duplicate_benchmark_ids(self):
        with self.assertRaisesRegex(ContractError, "duplicate result"):
            reconcile_results(self.manifest, [result(), result()])

    def test_workload_mismatch(self):
        with self.assertRaisesRegex(ContractError, "unknown workload"):
            reconcile_results(self.manifest, [result(workload="not-present")])

    def test_deterministic_ordering(self):
        rows = [result("rust"), result("cpp"), result("idris2", status="unsupported")]
        first = summarize_results(reconcile_results(self.manifest, rows))
        second = summarize_results(reconcile_results(self.manifest, reversed(rows)))
        self.assertEqual(first, second)
        self.assertEqual([row["implementation"] for row in first], ["cpp", "idris2", "rust"])

    def test_complete_run_rejects_missing_ids(self):
        with self.assertRaisesRegex(ContractError, "missing benchmark ids"):
            validate_complete_run(self.manifest, [result()], "cpp")

    def test_complete_run_rejects_wrong_oracle(self):
        rows = [result(workload=item["id"]) for item in self.manifest["workloads"]]
        rows[0]["oracle"]["value"] = 99
        with self.assertRaisesRegex(ContractError, "wrong oracle"):
            validate_complete_run(self.manifest, rows, "cpp")

    def test_complete_run_rejects_inconsistent_operation_count(self):
        rows = [result(workload=item["id"]) for item in self.manifest["workloads"]]
        with self.assertRaisesRegex(ContractError, "inconsistent operation count"):
            validate_complete_run(self.manifest, rows, "cpp", expected_operations=3)

    def test_complete_run_accepts_per_workload_operation_counts(self):
        rows = [result(workload=item["id"]) for item in self.manifest["workloads"]]
        expected = {}
        for index, (row, definition) in enumerate(zip(rows, self.manifest["workloads"]), start=1):
            row["operations_per_sample"] = index
            row["oracle"]["value"] = definition["observable"]["reference"]
            expected[row["workload_id"]] = index
        checked = validate_complete_run(self.manifest, rows, "cpp", expected_operations=expected)
        self.assertEqual(len(checked), len(rows))

    def test_robotics_contract_fixes_axes_frames_and_layout(self):
        definitions = {item["id"]: item for item in self.manifest["workloads"]}
        fk = definitions["robotics_forward_kinematics_2r/f64/motor_checksum"]
        jac = definitions["robotics_geometric_jacobian_2r/f64/base_checksum"]
        for definition in (fk, jac):
            operands = definition["operands"]
            self.assertEqual(operands["joint_types"], ["revolute", "revolute"])
            self.assertEqual(operands["ordered_axes_xyz"], [[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]])
            self.assertEqual([frame["translation_xyz"] for frame in operands["joint_fixed_frames"]],
                             [[0.0, 1.0, 0.0], [0.0, 1.0, 0.0]])
            self.assertIn("fixed_frame_0 * rotor_z(q0)", operands["composition_order"])
            self.assertEqual(len(operands["joint_vectors_radians"]), 2)
        self.assertEqual(jac["oracle"]["frame"], "base")
        self.assertEqual(jac["oracle"]["matrix_layout"], "column-major 6x2; one twist column per joint")
        self.assertEqual(jac["oracle"]["twist_coefficient_order"],
                         ["e12", "e13", "e23", "e1i", "e2i", "e3i"])
        self.assertEqual(jac["oracle"]["columns"],
                         [[1.0, 0.0, 0.0, 1.0, 0.0, 0.0], [1.0, 0.0, 0.0, 2.0, 0.0, 0.0]])


if __name__ == "__main__":
    unittest.main()
