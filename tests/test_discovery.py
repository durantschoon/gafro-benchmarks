import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmark_harness.cli import benchmark_idris2, benchmark_julia, discover


class DiscoveryTests(unittest.TestCase):
    def test_missing_implementation(self):
        with tempfile.TemporaryDirectory() as directory:
            row = discover(Path(directory) / "benchmarks", "rust", None)
            self.assertEqual(row["status"], "unavailable")
            self.assertIn("Cargo.toml", row["reason"])

    def test_override_requires_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            row = discover(Path(directory), "cpp", directory)
            self.assertEqual(row["status"], "unavailable")

    def test_idris2_missing_compiler_is_clear(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            implementation = root / "implementation"
            implementation.mkdir()
            (implementation / "gafro.ipkg").write_text("package fixture\n")
            args = type("Args", (), {
                "idris2_path": str(implementation),
                "idris2_compiler": "missing-idris2",
                "idris2_backend": "chez",
                "profile": "smoke",
            })()
            with patch("benchmark_harness.cli.shutil.which", return_value=None):
                with self.assertRaisesRegex(SystemExit, "Idris 2 compiler not found"):
                    benchmark_idris2(args, root, {"workloads": []}, 1000, root / "run")

    def test_julia_missing_executable_is_clear(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            implementation = root / "implementation"
            implementation.mkdir()
            (implementation / "Project.toml").write_text('name = "Fixture"\n')
            args = type("Args", (), {"julia_path": str(implementation), "julia": "missing-julia", "profile": "smoke"})()
            with patch("benchmark_harness.cli.shutil.which", return_value=None):
                with self.assertRaisesRegex(SystemExit, "Julia executable not found"):
                    benchmark_julia(args, root, {"workloads": []}, {}, root / "run")

    def test_julia_checkout_without_contract_runner_is_clear(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            implementation = root / "implementation"
            (implementation / "benchmark").mkdir(parents=True)
            (implementation / "Project.toml").write_text('name = "Fixture"\n')
            args = type("Args", (), {"julia_path": str(implementation), "julia": "julia", "profile": "smoke"})()
            with patch("benchmark_harness.cli.shutil.which", return_value="/fixture/bin/julia"):
                with patch("benchmark_harness.cli.subprocess.run") as run:
                    with self.assertRaisesRegex(SystemExit, "no contract runner"):
                        benchmark_julia(args, root, {"workloads": []}, {}, root / "run")
                    run.assert_not_called()

    def test_idris_adapter_declares_totality_and_provenance(self):
        source = (Path(__file__).resolve().parents[1] / "idris2/src/Main.idr").read_text()
        self.assertIn("%default total", source)
        self.assertIn('"--backend"', source)
        self.assertIn('"--c-compiler"', source)
        self.assertIn('"--c-flags"', source)

    def test_rust_adapter_reports_batch_capabilities_and_provenance(self):
        source = (Path(__file__).resolve().parents[1] / "rust/src/main.rs").read_text()
        self.assertIn("BatchMotorSoA", source)
        self.assertIn("BatchPointSoA", source)
        self.assertIn("BatchMotorSoA::<f64, N>", source)
        self.assertIn("BatchPointSoA::<f64, N>", source)
        self.assertIn("Motor::<f64>::identity()", source)
        self.assertIn('"--rustflags"', source)
        self.assertIn("codegen-units: 1", source)
        self.assertIn("lto: fat", source)

    def test_robotics_adapters_declare_matching_capabilities(self):
        root = Path(__file__).resolve().parents[1]
        cpp = (root / "cpp/bench_cga.cpp").read_text()
        rust = (root / "rust/src/main.rs").read_text()
        idris = (root / "idris2/src/Main.idr").read_text()
        fk = "robotics_forward_kinematics_2r/f64/motor_checksum"
        jacobian = "robotics_geometric_jacobian_2r/f64/base_checksum"
        self.assertIn(fk, cpp)
        self.assertIn(jacobian, cpp)
        self.assertIn(fk, rust)
        self.assertIn("corrected_jacobian_checksum", rust)
        self.assertIn(fk, idris)
        self.assertIn(jacobian, idris)
        self.assertIn("forwardKinematics", idris)
        self.assertIn("spatialAxes", idris)

    def test_spatial_physics_adapters_declare_matching_capabilities(self):
        root = Path(__file__).resolve().parents[1]
        cpp = (root / "cpp/bench_cga.cpp").read_text()
        rust = (root / "rust/src/main.rs").read_text()
        idris = (root / "idris2/src/Main.idr").read_text()
        action = "spatial_inertia_action/f64/wrench_checksum"
        transform = "spatial_inertia_transform/f64/e01_mass"
        self.assertIn(action, cpp)
        self.assertIn(transform, cpp)
        self.assertIn(action, rust)
        self.assertIn(transform, rust)
        self.assertIn(action, idris)
        self.assertIn(transform, idris)
        self.assertIn("applyInertia", idris)



class EnvelopeLayoutDiscoveryTests(unittest.TestCase):
    """Default discovery of egafro-<family>/gafro-<family> sibling checkouts."""

    @staticmethod
    def make_checkout(path, marker="CMakeLists.txt"):
        path.mkdir(parents=True)
        (path / marker).write_text("fixture\n")
        return path.resolve()

    def test_envelope_checkout_found_from_grandparent(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "egafro-benchmarks" / "gafro-benchmarks"
            root.mkdir(parents=True)
            expected = self.make_checkout(base / "egafro-cpp" / "gafro-cpp")
            row = discover(root, "cpp", None)
            self.assertEqual(row["status"], "available")
            self.assertEqual(row["path"], str(expected))

    def test_envelope_checkout_found_from_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "gafro-benchmarks"
            root.mkdir()
            expected = self.make_checkout(base / "egafro-rust" / "gafro-rust", "Cargo.toml")
            row = discover(root, "rust", None)
            self.assertEqual(row["status"], "available")
            self.assertEqual(row["path"], str(expected))

    def test_plain_sibling_wins_over_envelope_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "gafro-benchmarks"
            root.mkdir()
            plain = self.make_checkout(base / "gafro-cpp")
            self.make_checkout(base / "egafro-cpp" / "gafro-cpp")
            row = discover(root, "cpp", None)
            self.assertEqual(row["status"], "available")
            self.assertEqual(row["path"], str(plain))


if __name__ == "__main__":
    unittest.main()
