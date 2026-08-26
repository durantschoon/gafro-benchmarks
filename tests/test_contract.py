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


if __name__ == "__main__":
    unittest.main()
