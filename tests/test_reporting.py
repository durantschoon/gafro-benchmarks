import json
import tempfile
import unittest
from pathlib import Path

from benchmark_harness.cli import create_run_directory
from benchmark_harness.core import (build_summary_model, render_summary_markdown,
                                    workload_definition_id, workload_input_digest)
from tests.test_heterogeneous_contract import result as heterogeneous_result

ROOT = Path(__file__).resolve().parents[1]


def evidence(family, host=None, samples=(10.0, 20.0, 30.0)):
    return {
        "schema_version": "gafro-benchmark-result/v1",
        "implementation": {"family": family, "name": family, "repository_revision": "abc", "dirty": False,
                           "compiler": f"{family}-compiler", "backend": "release", "flags": ["optimized"]},
        "host": host or {"system": "FixtureOS", "machine": "fixture64"},
        "workload_id": "motor_composition_gp/f64/scalar", "status": "supported", "reason": "",
        "warmup_operations": 1, "operations_per_sample": 2,
        "sample_durations_ns": list(samples), "oracle": {"value": 1.0},
    }


class ReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "contracts/workloads-v1.json").read_text())

    def test_order_rounding_ratios_and_incomplete_matrix(self):
        model = build_summary_model(self.manifest, [evidence("rust", samples=(21, 23, 25)), evidence("cpp")], run_ids=["b", "a"])
        self.assertEqual(model["input_run_ids"], ["a", "b"])
        row = next(item for item in model["workloads"] if item["workload_id"].startswith("motor_composition"))
        self.assertEqual([cell["implementation"] for cell in row["cells"]], ["cpp", "idris2", "rust"])
        self.assertEqual(row["cells"][1]["status"], "blocked")
        self.assertEqual(row["cells"][1]["gap"]["classification"], "blocked_validation_or_environment")
        self.assertAlmostEqual(row["ratios"][0]["median_ratio"], 20 / 23)
        self.assertIn("10.000 +/- 5.000", render_summary_markdown(model))

    def test_incompatible_hosts_omit_ratios_and_winner(self):
        rows = [evidence("cpp"), evidence("rust", host={"system": "Other", "machine": "fixture64"})]
        model = build_summary_model(self.manifest, rows, run_ids=["run"])
        row = next(item for item in model["workloads"] if item["workload_id"].startswith("motor_composition"))
        self.assertFalse(row["environments_compatible"])
        self.assertEqual(row["ratios"], [])
        self.assertIsNone(row["apparent_winner"])

    def test_incompatible_build_modes_omit_rankings(self):
        cpp = evidence("cpp")
        cpp["implementation"]["flags"] = ["debug"]
        model = build_summary_model(self.manifest, [cpp, evidence("rust")], run_ids=["run"])
        row = next(item for item in model["workloads"] if item["workload_id"].startswith("motor_composition"))
        self.assertFalse(row["environments_compatible"])
        self.assertEqual(row["ratios"], [])

    def test_variants_are_separate_from_canonical_workloads(self):
        model = build_summary_model(self.manifest, [], run_ids=["run"])
        categories = [row["category"] for row in model["workloads"]]
        self.assertEqual(categories, sorted(categories))
        self.assertIn("Optimization variants", model["comparison_policy"])

    def test_layout_gap_is_actionable(self):
        row = evidence("rust")
        row.update(status="unsupported", reason="alternate coefficient layout")
        row.pop("sample_durations_ns")
        model = build_summary_model(self.manifest, [row], run_ids=["run"])
        workload = next(item for item in model["workloads"] if item["workload_id"].startswith("motor_composition"))
        rust = workload["cells"][2]
        self.assertEqual(rust["gap"]["classification"], "alternate_api_or_layout")
        self.assertIn("conversion", rust["gap"]["required_work"])

    def test_unique_runs_preserve_prior_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_id, first = create_run_directory(root)
            (first / "sentinel").write_text("keep")
            second_id, second = create_run_directory(root)
            self.assertNotEqual(first_id, second_id)
            self.assertTrue((first / "sentinel").is_file())
            self.assertTrue(second.is_dir())

    def test_summary_omits_ratio_for_mixed_heterogeneous_dimensions(self):
        cpp = heterogeneous_result(family="cpp")
        rust = heterogeneous_result(family="rust")
        workload = "batch_point_transform/f64/n256/e1_lane0"
        definition = next(item for item in self.manifest["workloads"] if item["id"] == workload)
        cpp["workload_id"] = workload
        rust["workload_id"] = workload
        for row in (cpp, rust):
            row["execution"].update(definition["execution_contract"])
            row["execution"]["input_fixture_id"] = f"{workload}/inputs-v1"
            row["execution"]["input_digest"] = workload_input_digest(definition)
            row["execution"]["workload_definition_id"] = workload_definition_id(definition)
        rust["execution"]["state"] = "cold"
        model = build_summary_model(self.manifest, [cpp, rust], run_ids=["run"])
        row = next(item for item in model["workloads"] if item["workload_id"] == workload)
        self.assertEqual(row["ratios"], [])
        self.assertIn("execution dimensions differ", row["comparison_note"])

    def test_summary_retains_gpu_provenance_and_rejects_cross_gpu_ratio(self):
        cpp = heterogeneous_result("end_to_end", family="cpp")
        rust = heterogeneous_result("end_to_end", family="rust")
        workload = "batch_point_transform/f64/n256/e1_lane0"
        definition = next(item for item in self.manifest["workloads"] if item["id"] == workload)
        for row in (cpp, rust):
            row["workload_id"] = workload
            row["execution"].update(definition["execution_contract"])
            row["execution"]["input_fixture_id"] = f"{workload}/inputs-v1"
            row["execution"]["input_digest"] = workload_input_digest(definition)
            row["execution"]["workload_definition_id"] = workload_definition_id(definition)
        rust["gpu"]["uuid"] = "GPU-other"
        model = build_summary_model(self.manifest, [cpp, rust], run_ids=["run"])
        row = next(item for item in model["workloads"] if item["workload_id"] == workload)
        self.assertEqual(row["ratios"], [])
        self.assertFalse(row["environments_compatible"])
        self.assertEqual(row["cells"][0]["gpu"]["uuid"], "GPU-fixture")
        self.assertEqual(row["cells"][2]["gpu"]["uuid"], "GPU-other")


if __name__ == "__main__":
    unittest.main()
