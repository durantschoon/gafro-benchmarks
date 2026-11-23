"""Derive the spatial inertia action oracles from operands, never by hand.

The oracle below is pure: it reads a workload's operands and convention and
returns wrench coordinates in the contract's coordinate order
(f1, f2, tau12, f3, tau13, tau23).  It must reproduce the committed diagonal
oracle before it is trusted for the full-tensor entry.
"""

import argparse
import json
import math
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from benchmark_harness import cli
from benchmark_harness.core import ContractError, validate_complete_run, validate_manifest

ROOT = Path(__file__).resolve().parents[1]
DIAGONAL_ID = "spatial_inertia_action/f64/wrench_checksum"
FULL_TENSOR_ID = "spatial_inertia_action/f64/full_tensor_wrench_checksum"
TOLERANCE = 1e-10


def rotational_tensor(operands):
    """Return the symmetric 3x3 rotational inertia tensor as nested tuples.

    Accepts the diagonal form ``inertia_diagonal: [Ixx, Iyy, Izz]`` or the
    axis-form entries ``inertia_tensor: {Ixx, Ixy, Ixz, Iyy, Iyz, Izz}``,
    which are the tensor's own entries.
    """
    if "inertia_tensor" in operands:
        entries = operands["inertia_tensor"]
        ixx, ixy, ixz = entries["Ixx"], entries["Ixy"], entries["Ixz"]
        iyy, iyz, izz = entries["Iyy"], entries["Iyz"], entries["Izz"]
    else:
        ixx, iyy, izz = operands["inertia_diagonal"]
        ixy = ixz = iyz = 0.0
    return ((ixx, ixy, ixz), (ixy, iyy, iyz), (ixz, iyz, izz))


def wrench_coordinates(operands):
    """Compute (f1, f2, tau12, f3, tau13, tau23) for W = I * T.

    Convention: omega = (e23, -e13, e12) (right-handed dual e23 <-> x,
    e13 <-> -y, e12 <-> z), tau = I * omega mapped back through the same
    dual, and f = mass * linear velocity.
    """
    bivectors = operands["twist_angular_bivectors"]
    omega = (bivectors["e23"], -bivectors["e13"], bivectors["e12"])
    tensor = rotational_tensor(operands)
    tau_x, tau_y, tau_z = (sum(row[axis] * omega[axis] for axis in range(3)) for row in tensor)
    force_x, force_y, force_z = (operands["mass"] * velocity for velocity in operands["twist_linear_xyz"])
    return [force_x, force_y, tau_z, force_z, -tau_y, tau_x]


def rounded(value):
    """Round to 15 significant digits, the precision committed in the contract."""
    return float(f"{value:.15g}")


def identity(family="cpp"):
    return {"family": family, "name": "fixture", "repository_revision": "abc", "dirty": False,
            "compiler": "fixture", "backend": "cpu", "flags": []}


def supported_row(definition):
    return {"schema_version": "gafro-benchmark-result/v1", "implementation": identity(), "host": {},
            "workload_id": definition["id"], "status": "supported", "reason": "",
            "warmup_operations": 1, "operations_per_sample": 2, "sample_durations_ns": [20, 10, 30],
            "oracle": {"value": definition["observable"]["reference"]}}


class InertiaOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = validate_manifest(json.loads((ROOT / "contracts/workloads-v1.json").read_text()))
        cls.definitions = {item["id"]: item for item in cls.manifest["workloads"]}

    def assert_coordinates_close(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for observed, committed in zip(actual, expected):
            self.assertLessEqual(abs(observed - committed), TOLERANCE)

    def test_oracle_reproduces_diagonal_workload(self):
        """T1: the derivation reproduces the committed diagonal oracle and checksum."""
        definition = self.definitions[DIAGONAL_ID]
        derived = wrench_coordinates(definition["operands"])
        self.assert_coordinates_close(derived, [2.0, 4.0, 0.08, 6.0, 0.10, 0.15])
        self.assert_coordinates_close(derived, definition["oracle"]["wrench_coordinates"])
        self.assertLessEqual(abs(sum(derived) - 12.33), TOLERANCE)
        self.assertLessEqual(abs(sum(derived) - definition["observable"]["reference"]), TOLERANCE)

    def test_full_tensor_oracle_matches_derivation(self):
        """T2: the committed full-tensor oracle is the derivation, rounded to 15 digits."""
        definition = self.definitions[FULL_TENSOR_ID]
        diagonal = self.definitions[DIAGONAL_ID]
        derived = wrench_coordinates(definition["operands"])
        committed = definition["oracle"]["wrench_coordinates"]
        self.assert_coordinates_close(committed, derived)
        self.assertEqual(committed, [rounded(value) for value in derived])
        self.assertEqual(definition["oracle"]["coordinate_order"], diagonal["oracle"]["coordinate_order"])
        observable = definition["observable"]
        self.assertEqual(observable["kind"], "coordinate_checksum")
        self.assertEqual(observable["name"], "sum_wrench_coordinates")
        self.assertEqual(observable["absolute_tolerance"], TOLERANCE)
        self.assertLessEqual(abs(observable["reference"] - sum(committed)), TOLERANCE)
        self.assertEqual(observable["reference"], rounded(sum(derived)))
        # Off-diagonal terms must actually move the torque coordinates.
        self.assertGreater(max(abs(a - b) for a, b in zip(derived, wrench_coordinates(diagonal["operands"]))), 1e-3)

    def test_full_tensor_entry_matches_diagonal_except_tensor(self):
        definition = self.definitions[FULL_TENSOR_ID]
        diagonal = self.definitions[DIAGONAL_ID]
        for field in ("numeric_type", "warmup_operations", "operations_per_sample"):
            self.assertEqual(definition[field], diagonal[field])
        for field in ("kind", "mass", "twist_linear_xyz", "twist_angular_bivectors"):
            self.assertEqual(definition["operands"][field], diagonal["operands"][field])
        self.assertIn("convention", definition["operands"])

    def test_manifest_validates_with_nineteen_ids(self):
        """T3: the manifest still validates and holds 19 unique ids."""
        ids = [item["id"] for item in self.manifest["workloads"]]
        self.assertEqual(len(ids), 19)
        self.assertEqual(len(set(ids)), 19)
        self.assertEqual(ids[-1], FULL_TENSOR_ID)

    def test_complete_run_accepts_failed_full_tensor_row(self):
        """T4a: a failed full-tensor row with a reason is a complete run."""
        rows = [supported_row(item) for item in self.manifest["workloads"]]
        for row in rows:
            if row["workload_id"] == FULL_TENSOR_ID:
                for key in ("warmup_operations", "operations_per_sample", "sample_durations_ns", "oracle"):
                    del row[key]
                row["status"] = "failed"
                row["reason"] = "untimed oracle mismatch: expected [2, 4, 0.08, 6, 0.102, 0.142], observed [2, 4, 0.08, 6, 0.098, 0.142]"
        checked = validate_complete_run(self.manifest, rows, "cpp")
        statuses = {row["workload_id"]: row["status"] for row in checked}
        self.assertEqual(statuses[FULL_TENSOR_ID], "failed")

    def test_complete_run_rejects_supported_full_tensor_row_with_wrong_oracle(self):
        """T4b: a supported full-tensor row with a wrong checksum is rejected."""
        rows = [supported_row(item) for item in self.manifest["workloads"]]
        for row in rows:
            if row["workload_id"] == FULL_TENSOR_ID:
                # The diagonal checksum: what a library that drops cross terms would report.
                row["oracle"]["value"] = 12.33
        with self.assertRaisesRegex(ContractError, "wrong oracle"):
            validate_complete_run(self.manifest, rows, "cpp")

    def test_committed_values_are_finite(self):
        definition = self.definitions[FULL_TENSOR_ID]
        self.assertTrue(all(math.isfinite(value) for value in definition["oracle"]["wrench_coordinates"]))


class JuliaBackfillTests(unittest.TestCase):
    """The Julia runner lives in the sibling and may predate a manifest id."""

    def test_julia_bundle_missing_one_id_is_backfilled_as_unsupported(self):
        manifest = validate_manifest(json.loads((ROOT / "contracts/workloads-v1.json").read_text()))
        definitions = [item for item in manifest["workloads"] if item["id"] != FULL_TENSOR_ID]
        rows = []
        for definition in definitions:
            row = supported_row(definition)
            row["implementation"] = identity("julia")
            rows.append(row)
        stdout = json.dumps({"results": rows})
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory) / "gafro-julia"
            (checkout / "benchmark").mkdir(parents=True)
            (checkout / "benchmark/contract_main.jl").write_text("# fixture\n")
            run_dir = Path(directory) / "run"
            run_dir.mkdir()
            completed = subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")
            version = subprocess.CompletedProcess(args=[], returncode=0, stdout="julia version 1.12.7\n", stderr="")
            args = argparse.Namespace(julia_path=None, julia="julia", profile="smoke")
            found = {"family": "julia", "status": "available", "path": str(checkout), "marker": "Project.toml"}
            with mock.patch.object(cli, "discover", return_value=found), \
                    mock.patch.object(cli.shutil, "which", return_value="/usr/bin/julia"), \
                    mock.patch.object(cli, "repository_identity", return_value=("abc", False)), \
                    mock.patch.object(cli.subprocess, "run", side_effect=[version, completed, completed]):
                destination = cli.benchmark_julia(args, ROOT, manifest, {}, run_dir)
            bundle = json.loads(destination.read_text())
        statuses = {row["workload_id"]: row for row in bundle["results"]}
        self.assertEqual(len(statuses), 19)
        self.assertEqual(statuses[FULL_TENSOR_ID]["status"], "unsupported")
        self.assertEqual(statuses[FULL_TENSOR_ID]["reason"], "julia adapter predates this canonical workload variant")
        self.assertEqual(statuses[FULL_TENSOR_ID]["implementation"]["family"], "julia")
        self.assertEqual(statuses[DIAGONAL_ID]["status"], "supported")


if __name__ == "__main__":
    unittest.main()
